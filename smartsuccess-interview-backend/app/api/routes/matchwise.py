"""
MatchWise AI v2 — Resume Comparison & Analysis Module
Integrated into SmartSuccess.AI Backend as an independent route module.

All endpoints are prefixed with /api/matchwise/
This module is self-contained and does NOT affect any existing interview/dashboard/voice routes.

Endpoints:
  POST /api/matchwise/compare            — Main resume analysis
  GET  /api/matchwise/user/status        — Get user subscription status
  GET  /api/matchwise/user/can-generate  — Check if user can generate
  POST /api/matchwise/user/use-trial     — Mark trial as used
  POST /api/matchwise/create-checkout-session — Stripe checkout
  POST /api/matchwise/stripe-webhook     — Stripe webhook handler
  GET  /api/matchwise/health             — Module health check
"""

import os
import io
import re
import json
import time
import asyncio
from datetime import datetime, timedelta

import aiohttp
import stripe
import pdfplumber
from docx import Document
from bs4 import BeautifulSoup
import requests

from fastapi import APIRouter, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Stripe Configuration (isolated to Matchwise module)
# ============================================================================
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# ============================================================================
# Firebase Admin SDK (isolated initialization for Matchwise)
# ============================================================================
import firebase_admin
from firebase_admin import credentials, firestore

# Use a named app to avoid conflicts with any other Firebase instance
_matchwise_firebase_app = None
_matchwise_db = None

def _get_matchwise_db():
    """Lazy-initialize Firebase for the Matchwise module."""
    global _matchwise_firebase_app, _matchwise_db
    if _matchwise_db is not None:
        return _matchwise_db
    
    try:
        # Try to get existing app first (if already initialized by another module)
        _matchwise_firebase_app = firebase_admin.get_app('matchwise')
    except ValueError:
        # App doesn't exist yet, create it
        # Look for serviceAccountKey.json in multiple locations
        key_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'serviceAccountKey.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'serviceAccountKey.json'),
            'serviceAccountKey.json',
            os.path.join(os.getcwd(), 'serviceAccountKey.json'),
        ]
        
        cred_path = None
        for path in key_paths:
            if os.path.exists(path):
                cred_path = os.path.abspath(path)
                break
        
        if cred_path:
            cred = credentials.Certificate(cred_path)
            _matchwise_firebase_app = firebase_admin.initialize_app(cred, name='matchwise')
            print(f"✅ Matchwise Firebase initialized from: {cred_path}")
        else:
            # Try default credentials (for cloud environments)
            try:
                _matchwise_firebase_app = firebase_admin.initialize_app(name='matchwise')
                print("✅ Matchwise Firebase initialized with default credentials")
            except Exception as e:
                print(f"⚠️  Matchwise Firebase initialization failed: {e}")
                print("   MatchWise user management features will be unavailable.")
                return None
    
    _matchwise_db = firestore.client(app=_matchwise_firebase_app)
    return _matchwise_db


# ============================================================================
# Router
# ============================================================================
router = APIRouter(prefix="/api/matchwise", tags=["matchwise"])


# ============================================================================
# User Status Management
# ============================================================================
class MatchwiseUserStatus:
    def __init__(self, uid: str):
        self.uid = uid
        self.db = _get_matchwise_db()
        self.user_ref = self.db.collection("users").document(uid) if self.db else None
        self.now_month = datetime.now().strftime("%Y-%m")
    
    def get_status(self):
        if not self.user_ref:
            return self._get_default_status()
        try:
            doc = self.user_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return self._process_user_data(data)
            else:
                return self._get_default_status()
        except Exception as e:
            print(f"Error getting user status: {e}")
            return self._get_default_status()
    
    def _process_user_data(self, data):
        subscription_end = data.get("subscriptionEnd")
        is_subscription_active = True
        if subscription_end:
            try:
                is_subscription_active = datetime.utcnow() < datetime.fromisoformat(subscription_end)
            except Exception:
                is_subscription_active = False

        return {
            "trialUsed": data.get("trialUsed", False),
            "isUpgraded": data.get("isUpgraded", False),
            "planType": data.get("planType"),
            "scanLimit": data.get("scanLimit"),
            "scansUsed": data.get("scansUsed", 0),
            "lastScanMonth": self.now_month,
            "subscriptionActive": is_subscription_active,
            "subscriptionEnd": subscription_end,
        }
    
    def _get_default_status(self):
        return {
            "trialUsed": False,
            "isUpgraded": False,
            "planType": None,
            "scanLimit": None,
            "scansUsed": 0,
            "lastScanMonth": self.now_month
        }
    
    def can_generate(self):
        status = self.get_status()
        if not status["trialUsed"]:
            return True, "trial_available"
        if status["isUpgraded"]:
            if "subscriptionActive" in status and not status["subscriptionActive"]:
                return False, "subscription_expired"
            if status["scanLimit"] is None:
                return True, "unlimited"
            if status["scansUsed"] < status["scanLimit"]:
                return True, "subscription_available"
            else:
                return False, "subscription_limit_reached"
        return False, "trial_used"
    
    def mark_trial_used(self):
        if self.user_ref:
            self.user_ref.set({"trialUsed": True}, merge=True)
    
    def increment_scan_count(self):
        if not self.user_ref:
            return
        status = self.get_status()
        if status["isUpgraded"] and status["scanLimit"] is not None:
            self.user_ref.set({
                "scansUsed": status["scansUsed"] + 1,
                "lastScanMonth": self.now_month
            }, merge=True)


# ============================================================================
# Per-Prompt Token Budget Configuration
# Different output types need different token limits to avoid truncation
# ============================================================================
TOKEN_BUDGETS = {
    "job_summary": 1500,
    "comparison": 2500,
    "resume_summary": 1000,     # Increased from 800 for safety margin
    "work_experience": 1500,
    "cover_letter": 4096,       # Increased from 3000 — prevents truncation even with thinking overhead
}

# ============================================================================
# Model-Specific System Prompts
# Different output types benefit from different role framing & constraints
# ============================================================================
PROMPT_CONFIGS = {
    "job_summary": {
        "system_prompt": (
            "You are a job posting analyst. Extract structured information accurately "
            "from job descriptions. Output clean, well-organized HTML bullet lists "
            "with professional formatting. Use <strong> tags for labels. "
            "Do NOT use special symbols like Ø or decorative characters. Keep output clean and scannable."
        ),
    },
    "comparison": {
        "system_prompt": (
            "You are a resume-to-job matching analyst. Compare resumes against job requirements "
            "with precision. Return ONLY valid JSON. Be objective and evidence-based in your "
            "assessments. Never output markdown, HTML, or extra text — only raw JSON."
        ),
    },
    "resume_summary": {
        "system_prompt": (
            "You are a professional resume writer following North American resume conventions. "
            "Write in the 'implied first person' — NEVER use personal pronouns (I, my, me, we, our). "
            "Start sentences with strong action verbs or descriptive phrases. "
            "Write honest, accurate summaries that highlight real qualifications. "
            "Never fabricate experience. Frame transferable skills truthfully."
        ),
    },
    "work_experience": {
        "system_prompt": (
            "You are a career coach specializing in resume optimization. "
            "Your job is to EXTRACT real work experiences from resumes and LIGHTLY REFRAME "
            "them to highlight relevance to specific job postings. "
            "NEVER invent new experiences. NEVER use personal pronouns (I, my, me, we). "
            "Always start bullets with strong past-tense action verbs. "
            "Output ONLY HTML <ul><li> lists with no extra text."
        ),
    },
    "cover_letter": {
        "system_prompt": (
            "You are a professional cover letter writer. Write compelling, honest, and "
            "well-structured letters. ALWAYS start with 'Dear Hiring Manager,' — NEVER use "
            "any person's name from job postings. ALWAYS end with 'Sincerely,' and '[Your Name]'. "
            "Only reference real experience from the resume. Write exactly 4 paragraphs."
        ),
    },
}

# ============================================================================
# Privacy-Aware Data Handling
# Redact PII before sending to free-tier (less trusted) AI providers
# ============================================================================
_PII_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
    (re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'), '[PHONE_REDACTED]'),
    (re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'), '[SSN_REDACTED]'),
]

def redact_pii(text: str) -> str:
    """Strip common PII patterns (email, phone, SSN) from text.
    Used before sending data to free-tier AI providers with weaker privacy guarantees.
    """
    result = text
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# ============================================================================
# AI Fallback Architecture
# Layer 1: Groq (free, fast)  →  Layer 2: Gemini (free)  →  Layer 3: OpenAI GPT-4o-mini (paid, reliable)
# Layer 4: OpenRouter (free, optional last resort — PII redacted)
# ============================================================================

async def call_groq_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000, json_mode: bool = False) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("GROQ_API_KEY not set")

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}
        try:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 429:
                    raise Exception(f"Groq rate limit exceeded (429)")
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Groq API error: {response.status} - {error_text}")
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            raise Exception(f"Groq API request failed: {str(e)}")


async def call_gemini_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000, json_mode: bool = False) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}
        gen_config = {
            "maxOutputTokens": max_tokens,
            "temperature": 0.2,
            # Disable thinking to prevent token budget theft.
            # Gemini 2.5 Flash uses thinking tokens by default which consume
            # maxOutputTokens silently (~50-65%), causing truncation on
            # generation tasks (cover letters, summaries) that don't need CoT.
            "thinkingConfig": {"thinkingBudget": 0},
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"
        data = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
            "generationConfig": gen_config
        }
        try:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 429:
                    raise Exception(f"Gemini rate limit exceeded (429)")
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error: {response.status} - {error_text}")
                result = await response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except aiohttp.ClientError as e:
            raise Exception(f"Gemini API request failed: {str(e)}")


async def call_openai_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000, json_mode: bool = False) -> str:
    """OpenAI GPT-4o-mini — reliable paid fallback (~$0.15/1M input, $0.60/1M output).
    Only triggered when both Groq and Gemini fail (~5% of requests). Cost: ~$0.25/month.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY not set")

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}
        try:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers, json=data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 429:
                    raise Exception(f"OpenAI rate limit exceeded (429)")
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")


# OpenRouter kept as optional Layer 4 (free, less reliable)
OPENROUTER_FREE_MODELS = [
    "openrouter/free",                        # OpenRouter smart router — auto-selects available free models
    "arcee-ai/trinity-large-preview:free",     # 400B MoE model, currently active
    "stepfun/step-3.5-flash:free",             # 196B MoE, 256K context
    "z-ai/glm-4.5-air:free",                  # Lightweight MoE, 131K context
    "meta-llama/llama-3.2-3b-instruct:free",   # Meta Llama confirmed free variant
]

async def call_openrouter_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000, model_index: int = 0) -> str:
    if model_index >= len(OPENROUTER_FREE_MODELS):
        raise Exception("All OpenRouter free models exhausted")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY not set")

    model = OPENROUTER_FREE_MODELS[model_index]

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("FRONTEND_URL", "https://smart-sccuss-career-intelligence-ai.vercel.app"),
            "X-Title": "MatchWise AI (SmartSuccess)",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=data,
                timeout=aiohttp.ClientTimeout(total=45)
            ) as response:
                if response.status == 429:
                    print(f"⚠️ OpenRouter model {model} rate limited, trying next...")
                    return await call_openrouter_api(prompt, system_prompt, max_tokens, model_index + 1)
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error ({model}): {response.status} - {error_text}")
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            raise Exception(f"OpenRouter API request failed ({model}): {str(e)}")


async def call_ai_api(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.",
    max_tokens: int = 2000,
    json_mode: bool = False,
    call_label: str = "",
) -> tuple[str, str]:
    """4-Layer Fallback: Groq → Gemini → OpenAI GPT-4o-mini → OpenRouter (free)
    
    Returns:
        (result_text, provider_name) tuple for tracking which provider served each prompt.
    """
    label = f"[{call_label}] " if call_label else ""
    # OpenRouter (Layer 4) uses PII-redacted prompt — free-tier has weaker privacy guarantees
    redacted_prompt = redact_pii(prompt)
    layers = [
        ("Groq",      "🔵", lambda: call_groq_api(prompt, system_prompt, max_tokens, json_mode)),
        ("Gemini",    "🟡", lambda: call_gemini_api(prompt, system_prompt, max_tokens, json_mode)),
        ("OpenAI",    "🟣", lambda: call_openai_api(prompt, system_prompt, max_tokens, json_mode)),
        ("OpenRouter", "🟠", lambda: call_openrouter_api(redacted_prompt, system_prompt, max_tokens)),
    ]

    for i, (name, icon, fn) in enumerate(layers, 1):
        try:
            t0 = time.time()
            print(f"{icon} [Matchwise] {label}Layer {i}: Attempting {name} (max_tokens={max_tokens}, json={json_mode})...")
            result = await fn()
            elapsed = round(time.time() - t0, 2)
            print(f"✅ [Matchwise] {label}Layer {i} SUCCESS: {name} | {elapsed}s | {len(result)} chars")
            return result, name
        except Exception as err:
            elapsed = round(time.time() - t0, 2)
            print(f"⚠️ [Matchwise] {label}Layer {i} FAILED ({name}, {elapsed}s): {err}")

    raise Exception("All AI services are currently unavailable. Please try again in a few minutes.")


# ============================================================================
# File Extraction Utilities
# ============================================================================
def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract text from PDF using pdfplumber (preserves multi-column layouts)."""
    try:
        content = file.file.read()
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {str(e)}")

def extract_text_from_docx(file: UploadFile) -> str:
    try:
        content = file.file.read()
        doc = Document(io.BytesIO(content))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract DOCX text: {str(e)}")


# ============================================================================
# Comparison Table — JSON validation + server-side rendering
# ============================================================================
STATUS_CONFIG = {
    "Strong":   {"emoji": "✅", "weight": 1.0,  "color": "#dcfce7"},
    "Moderate": {"emoji": "🔷", "weight": 0.8,  "color": "#dbeafe"},
    "Partial":  {"emoji": "⚠️", "weight": 0.5,  "color": "#fef9c3"},
    "Lack":     {"emoji": "❌", "weight": 0.1,  "color": "#fee2e2"},
}


def validate_comparison_json(raw: str) -> list:
    """Parse and validate LLM comparison JSON output. Returns list of row dicts."""
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Attempt to extract JSON object from surrounding text
        match = re.search(r'\{[\s\S]*"rows"[\s\S]*\}', cleaned)
        if match:
            parsed = json.loads(match.group())
        else:
            print(f"⚠️ [Matchwise] Failed to parse comparison JSON, using fallback")
            return []

    rows = parsed.get("rows", []) if isinstance(parsed, dict) else parsed
    validated = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = str(row.get("category", "Unknown"))
        status = str(row.get("status", "Lack"))
        comment = str(row.get("comment", ""))
        # Normalize status to known values
        if status not in STATUS_CONFIG:
            status_lower = status.lower()
            if "strong" in status_lower and "moderate" not in status_lower:
                status = "Strong"
            elif "moderate" in status_lower:
                status = "Moderate"
            elif "partial" in status_lower:
                status = "Partial"
            else:
                status = "Lack"
        validated.append({"category": category, "status": status, "comment": comment})
    return validated


def render_comparison_table(rows: list) -> str:
    """Deterministically generate HTML comparison table from validated data."""
    if not rows:
        return "<p>Comparison data unavailable.</p>"

    html = (
        '<table style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.6;">'
        '<thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">'
        '<th style="padding:10px 12px;text-align:left;font-weight:600;">Category</th>'
        '<th style="padding:10px 12px;text-align:center;font-weight:600;">Match Status</th>'
        '<th style="padding:10px 12px;text-align:left;font-weight:600;">Comments</th>'
        '<th style="padding:10px 12px;text-align:center;font-weight:600;">Weight</th>'
        '</tr></thead><tbody>'
    )

    for row in rows:
        cfg = STATUS_CONFIG.get(row["status"], STATUS_CONFIG["Lack"])
        html += (
            f'<tr style="border-bottom:1px solid #e2e8f0;background:{cfg["color"]}20;">'
            f'<td style="padding:8px 12px;">{row["category"]}</td>'
            f'<td style="padding:8px 12px;text-align:center;">{cfg["emoji"]} {row["status"]}</td>'
            f'<td style="padding:8px 12px;color:#4a5568;">{row["comment"]}</td>'
            f'<td style="padding:8px 12px;text-align:center;font-weight:600;">{cfg["weight"]}</td>'
            f'</tr>'
        )

    html += '</tbody></table>'
    return html


def calculate_match_score(rows: list) -> float:
    """Calculate match score as percentage from comparison rows. Pure math, no LLM."""
    if not rows:
        return 0.0
    total_weight = sum(STATUS_CONFIG.get(r["status"], STATUS_CONFIG["Lack"])["weight"] for r in rows)
    count = len(rows)
    score = (total_weight / count) * 100
    return round(score, 2)


# ============================================================================
# Retry-with-Correction: Validated JSON call for comparison table
# ============================================================================
async def call_ai_with_validation(
    prompt: str,
    max_tokens: int = 2500,
    call_label: str = "comparison",
    max_retries: int = 2,
    system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.",
) -> tuple[list, str]:
    """Call AI API expecting JSON comparison output. Retry with error feedback if validation fails.
    
    Returns:
        (validated_rows, provider_name)
    """
    current_prompt = prompt
    last_provider = "unknown"

    for attempt in range(1, max_retries + 2):  # 1 initial + max_retries correction attempts
        raw, provider = await call_ai_api(
            current_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            json_mode=True,
            call_label=f"{call_label} (attempt {attempt})",
        )
        last_provider = provider

        rows = validate_comparison_json(raw)
        if rows:
            if attempt > 1:
                print(f"✅ [Matchwise] {call_label} JSON validated on retry attempt {attempt}")
            return rows, provider

        if attempt <= max_retries:
            # Append correction feedback to the prompt for the next attempt
            correction = (
                "\n\n--- CORRECTION REQUIRED ---\n"
                "Your previous response could NOT be parsed as valid JSON.\n"
                "Please output ONLY a valid JSON object with this exact structure:\n"
                '{"rows": [{"category": "...", "status": "Strong|Moderate|Partial|Lack", "comment": "..."}]}\n'
                "No markdown fences, no extra text. Just the raw JSON.\n"
            )
            current_prompt = prompt + correction
            print(f"🔄 [Matchwise] {call_label} JSON validation failed, retrying with correction (attempt {attempt + 1})...")

    # All retries exhausted — return empty (graceful degradation will handle it)
    print(f"❌ [Matchwise] {call_label} JSON validation failed after {max_retries + 1} attempts")
    return [], last_provider


# ============================================================================
# Core Analysis — compare_texts (6 AI prompts)
# ============================================================================
async def compare_texts(job_text: str, resume_text: str) -> dict:
    """Run all 5 AI analysis prompts with parallel execution and graceful degradation.
    
    Architecture:
      Step 1 (sequential): Job Summary — other prompts depend on it
      Step 2 (parallel via asyncio.gather): Comparison + Resume Summary + Work Experience + Cover Letter
      
    Each prompt has independent error handling. A single failure returns a friendly
    placeholder instead of crashing the entire analysis.
    """
    t_start = time.time()
    warnings = []
    providers_used = {}

    # ── Step 1: Job Summary (sequential — other prompts depend on it) ──
    job_summary_prompt = (
        f"Analyze the following job posting and extract key information.\n\n"
        f"═══ JOB POSTING CONTENT ═══\n"
        f"{job_text}\n\n"
        f"═══ OUTPUT INSTRUCTIONS ═══\n"
        "Extract and organize the information into a clean, professional HTML bullet list.\n"
        "Use the EXACT structure below. Replace bracketed placeholders with actual content from the job posting.\n"
        "If any information is not available, write 'Not specified' for that item.\n\n"
        'Output ONLY the HTML below — no markdown, no ```html, no preamble:\n\n'
        '<ul style="list-style-type: disc; padding-left: 20px; line-height: 1.8;">\n'
        "  <li><strong>Position Title:</strong> [exact job title]</li>\n"
        "  <li><strong>Company Name:</strong> [company name and any client info if mentioned]</li>\n"
        "  <li><strong>Department:</strong> [department if mentioned, else 'Not specified']</li>\n"
        "  <li><strong>Location:</strong> [location and work arrangement (remote/onsite/hybrid)]</li>\n"
        "  <li><strong>Employment Type:</strong> [full-time/contract/etc., else 'Not specified']</li>\n"
        "  <li><strong>Compensation:</strong>\n"
        '    <ul style="list-style-type: circle; padding-left: 20px;">\n'
        "      <li><strong>Salary/Rate:</strong> [salary info if available, else 'Not specified']</li>\n"
        "      <li><strong>Benefits:</strong> [benefits if mentioned, else 'Not specified']</li>\n"
        "    </ul>\n"
        "  </li>\n"
        "  <li><strong>Environment/Company Culture:</strong> [company culture/vision if available, else 'Not specified']</li>\n"
        "  <li><strong>Key Responsibilities:</strong>\n"
        '    <ul style="list-style-type: circle; padding-left: 20px;">\n'
        "      <li>[responsibility 1]</li>\n"
        "      <li>[responsibility 2]</li>\n"
        "      <li>[up to 8 responsibilities]</li>\n"
        "    </ul>\n"
        "  </li>\n"
        "  <li><strong>Technical Skills Required:</strong>\n"
        '    <ul style="list-style-type: circle; padding-left: 20px;">\n'
        "      <li>[tech skill 1]</li>\n"
        "      <li>[tech skill 2]</li>\n"
        "      <li>[up to 10 technical skills]</li>\n"
        "    </ul>\n"
        "  </li>\n"
        "  <li><strong>Soft Skills Required:</strong>\n"
        '    <ul style="list-style-type: circle; padding-left: 20px;">\n'
        "      <li>[soft skill 1]</li>\n"
        "      <li>[soft skill 2]</li>\n"
        "      <li>[up to 7 soft skills]</li>\n"
        "    </ul>\n"
        "  </li>\n"
        "  <li><strong>Certifications Required:</strong> [certifications if any, else 'Not specified']</li>\n"
        "  <li><strong>Education Required:</strong> [education requirements, else 'Not specified']</li>\n"
        "</ul>"
    )

    try:
        job_summary_raw, js_provider = await call_ai_api(
            job_summary_prompt,
            system_prompt=PROMPT_CONFIGS["job_summary"]["system_prompt"],
            max_tokens=TOKEN_BUDGETS["job_summary"],
            call_label="job_summary",
        )
        job_summary = f"\n\n {job_summary_raw}"
        providers_used["job_summary"] = js_provider
    except Exception as e:
        # Job summary is critical — without it, comparison quality drops severely
        raise Exception(f"Comparison failed: Job summary generation failed: {str(e)}")

    # ── Step 2: Build prompts for parallel execution ──

    # b. Comparison prompt (uses job_summary)
    comparison_prompt = (
        "Compare the following resume against the job requirements.\n\n"
        "RESUME:\n"
        f"{resume_text}\n\n"
        "JOB REQUIREMENTS (summarized):\n"
        f"{job_summary}\n\n"
        "For each key requirement in the job posting (responsibilities, technical skills, "
        "soft skills, certifications, education), evaluate how well the resume matches.\n\n"
        "Return a JSON object with this EXACT structure:\n"
        '{\n'
        '  "rows": [\n'
        '    {\n'
        '      "category": "requirement name",\n'
        '      "status": "Strong" | "Moderate" | "Partial" | "Lack",\n'
        '      "comment": "brief explanation of how the resume matches or gaps"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "RULES:\n"
        "- 'Strong': skill/experience clearly present and well-matched\n"
        "- 'Moderate': skill/experience present but not a perfect match\n"
        "- 'Partial': somewhat related experience exists\n"
        "- 'Lack': not mentioned or very weak match\n"
        "- List 10-20 key requirements. Each row must have all 3 fields.\n"
        "- ONLY output valid JSON. No markdown, no extra text.\n"
    )

    # c. Tailored Resume Summary (implied first person — no pronouns)
    tailored_resume_summary_prompt = (
        "You are revising a professional resume summary to better match a specific job posting.\n\n"
        "═══ RESUME WRITING CONVENTION (CRITICAL) ═══\n"
        "Use 'implied first person' — this is the standard North American resume format:\n"
        "- NEVER use personal pronouns: I, my, me, we, our\n"
        "- Start sentences with action verbs or descriptive noun phrases\n"
        "- The subject 'I' is implied and never written\n"
        "- Examples:\n"
        '  CORRECT: "Senior AI Solution Architect with 14+ years of experience..."\n'
        '  WRONG:   "I am a Senior AI Solution Architect with 14+ years..."\n'
        '  CORRECT: "Proven track record in designing production-grade RAG pipelines..."\n'
        '  WRONG:   "I have a proven track record in designing..."\n'
        '  CORRECT: "Adept at leveraging cloud-native architectures to deliver scalable AI solutions."\n'
        '  WRONG:   "I am adept at leveraging my cloud-native architecture skills..."\n\n'
        "═══ CONTENT RULES ═══\n"
        "1. Write ONE paragraph, maximum 150 words.\n"
        "2. ONLY mention skills, technologies, and experiences that ACTUALLY appear in the resume below.\n"
        "3. DO NOT fabricate or invent any certifications, years of experience, tools, or achievements.\n"
        "4. If the applicant lacks a required skill, frame adjacent experience as transferable\n"
        "   (e.g., 'Leveraging background in X to rapidly adapt to Y' — no 'I' or 'my').\n"
        "5. If the resume has an existing summary section, use it as a base and enhance it.\n"
        "6. If no summary exists, write a new one based solely on actual resume content.\n"
        "7. Highlight key skills and experiences that best match the job requirements.\n"
        "8. Output a single HTML <p> tag. No markdown, no ```html, no preamble text.\n\n"
        "═══ APPLICANT'S ACTUAL RESUME ═══\n"
        f"{resume_text}\n\n"
        "═══ TARGET JOB POSTING ═══\n"
        f"{job_text}\n\n"
        "Now write the revised summary following ALL conventions above. Do NOT use any personal pronouns."
    )

    # d. Tailored Work Experience (two-step: EXTRACT then REFRAME)
    tailored_work_experience_prompt = (
        "You are a career coach helping reframe existing resume bullet points for a specific job application.\n\n"
        "═══ RESUME WRITING CONVENTION (CRITICAL) ═══\n"
        "Use 'implied first person' — standard North American resume format:\n"
        "- NEVER use personal pronouns: I, my, me, we, our\n"
        "- Start EVERY bullet with a strong past-tense action verb "
        "(Led, Designed, Implemented, Engineered, Directed, Built, Optimized, Architected, Developed, Managed)\n"
        "- The subject 'I' is implied and never written\n\n"
        "═══ TASK: TWO-STEP PROCESS ═══\n\n"
        "STEP 1 — EXTRACT: Identify the 5-7 most relevant work experience bullet points\n"
        "from the resume that best align with the target job requirements.\n"
        "Pick ACTUAL bullet points or descriptions from the resume's work history.\n\n"
        "STEP 2 — REFRAME: For each extracted bullet, lightly reframe the wording to:\n"
        "  - Highlight relevance to the target job\n"
        "  - Add relevant keywords from the job posting ONLY IF the skill genuinely exists in the resume\n"
        "  - Strengthen the action verb if needed\n"
        "  - Preserve the original achievement, metric, or context\n\n"
        "═══ STRICT RULES ═══\n"
        "1. Every bullet MUST be traceable to a REAL experience in the resume. If you cannot point to the source, do not include it.\n"
        "2. DO NOT invent projects, tools, technologies, metrics, team sizes, or dollar amounts that aren't in the resume.\n"
        "3. DO NOT fully rewrite or create new experiences. ONLY reframe existing ones.\n"
        "4. Each bullet: strong action verb + context + measurable result (if available in resume).\n"
        "5. Keep each bullet to 1-2 concise sentences maximum.\n"
        "6. Frame transferable skills honestly (e.g., 'Applied RF propagation modeling methodologies to...' rather than inventing a new role).\n\n"
        "═══ OUTPUT FORMAT (CRITICAL — MUST FOLLOW EXACTLY) ═══\n"
        "Output as an HTML unordered list. EVERY experience must be a <li> inside a <ul>.\n"
        "Do NOT output plain text paragraphs. Do NOT output markdown.\n"
        "Do NOT add any preamble, title, or explanation outside the list.\n"
        "Output ONLY this structure:\n\n"
        "<ul>\n"
        "<li>Bullet point 1 here</li>\n"
        "<li>Bullet point 2 here</li>\n"
        "<li>Bullet point 3 here</li>\n"
        "<li>Bullet point 4 here</li>\n"
        "<li>Bullet point 5 here</li>\n"
        "</ul>\n\n"
        "═══ APPLICANT'S ACTUAL RESUME ═══\n"
        f"{resume_text}\n\n"
        "═══ TARGET JOB POSTING ═══\n"
        f"{job_text}\n\n"
        "Now output ONLY the <ul>...</ul> list. No other text."
    )

    # e. Cover Letter (rules-first structure to prevent "lost in the middle" attention decay)
    cover_letter_prompt = (
        "You are writing a professional cover letter. Follow ALL rules below EXACTLY.\n\n"
        "═══ MANDATORY FORMAT RULES ═══\n"
        "1. Start EXACTLY with 'Dear Hiring Manager,'\n"
        "2. Write EXACTLY 4 paragraphs:\n"
        "   - Paragraph 1: Opening hook — state the position title and company name, express enthusiasm\n"
        "   - Paragraph 2: Relevant technical experience — highlight 3-4 specific skills/projects from the resume that match job requirements\n"
        "   - Paragraph 3: Soft skills, leadership, and cultural fit\n"
        "   - Paragraph 4: Closing — express enthusiasm for interview opportunity\n"
        "3. End EXACTLY with:\n"
        "   <p>Sincerely,</p>\n"
        "   <p>[Your Name]</p>\n"
        "4. Total length: 400-500 words (4 paragraphs)\n"
        "5. Output ONLY in HTML using <p> tags. No markdown, no ```html.\n\n"
        "═══ CONTENT INTEGRITY RULES ═══\n"
        "6. ONLY reference skills, technologies, and experiences that ACTUALLY appear in the RESUME below.\n"
        "7. DO NOT fabricate or invent any experience, certification, or achievement.\n"
        "8. If the applicant lacks a required skill, frame adjacent experience as transferable\n"
        "   (e.g., 'My experience in X provides a strong foundation for Y').\n"
        "9. Extract the correct job title and company name from the JOB POSTING below.\n"
        "10. Tone: confident, honest, professional. First person.\n\n"
        "═══ RESUME (applicant's actual background) ═══\n"
        f"{resume_text}\n\n"
        "═══ JOB POSTING ═══\n"
        f"{job_text}\n\n"
        'Now write the cover letter following ALL rules above. Start with "Dear Hiring Manager,"'
    )

    # ── Step 2: Execute remaining 4 prompts in parallel via asyncio.gather ──

    async def _run_comparison():
        """Comparison with retry-with-correction validation."""
        rows, provider = await call_ai_with_validation(
            comparison_prompt,
            max_tokens=TOKEN_BUDGETS["comparison"],
            call_label="comparison",
            system_prompt=PROMPT_CONFIGS["comparison"]["system_prompt"],
        )
        table_html = render_comparison_table(rows)
        score = calculate_match_score(rows)
        return table_html, score, provider

    async def _run_resume_summary():
        result, provider = await call_ai_api(
            tailored_resume_summary_prompt,
            system_prompt=PROMPT_CONFIGS["resume_summary"]["system_prompt"],
            max_tokens=TOKEN_BUDGETS["resume_summary"],
            call_label="resume_summary",
        )
        return result, provider

    async def _run_work_experience():
        result, provider = await call_ai_api(
            tailored_work_experience_prompt,
            system_prompt=PROMPT_CONFIGS["work_experience"]["system_prompt"],
            max_tokens=TOKEN_BUDGETS["work_experience"],
            call_label="work_experience",
        )
        # HTML format enforcement — ensure proper <ul><li> structure
        cleaned = re.sub(r'```html?\s*', '', result)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        if '<ul' not in cleaned.lower():
            # LLM output plain text instead of HTML list — wrap it
            lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
            lines = [re.sub(r'^[\-\*\d\.•Ø]+\s*', '', l) for l in lines if l]
            cleaned = '<ul>' + ''.join(f'<li>{l}</li>' for l in lines) + '</ul>'
            print(f"⚠️ [Matchwise] Work experience output lacked <ul> — auto-wrapped. Provider: {provider}")
        return cleaned, provider

    async def _run_cover_letter():
        result, provider = await call_ai_api(
            cover_letter_prompt,
            system_prompt=PROMPT_CONFIGS["cover_letter"]["system_prompt"],
            max_tokens=TOKEN_BUDGETS["cover_letter"],
            call_label="cover_letter",
        )
        # Truncation detection — a properly completed cover letter must end with signature
        if "sincerely" not in result.lower():
            print(f"⚠️ [Matchwise] Cover letter may be truncated (no 'Sincerely' found). "
                  f"Provider: {provider}, output length: {len(result)} chars")
            result += "\n<p>Sincerely,</p>\n<p>[Your Name]</p>"
        return result, provider

    # Launch all 4 concurrently — each wrapped in independent error handling
    tasks = await asyncio.gather(
        _run_comparison(),
        _run_resume_summary(),
        _run_work_experience(),
        _run_cover_letter(),
        return_exceptions=True,
    )

    # ── Step 3: Unpack results with graceful degradation ──

    # b. Comparison table
    if isinstance(tasks[0], Exception):
        warnings.append(f"Comparison table temporarily unavailable: {tasks[0]}")
        resume_summary = "<p>Comparison table temporarily unavailable. Please try again.</p>"
        match_score = 0.0
        providers_used["comparison"] = "failed"
    else:
        resume_summary, match_score, cmp_provider = tasks[0]
        providers_used["comparison"] = cmp_provider

    # c. Tailored Resume Summary
    if isinstance(tasks[1], Exception):
        warnings.append(f"Resume summary temporarily unavailable: {tasks[1]}")
        tailored_resume_summary = "<p>Tailored resume summary temporarily unavailable. Please try again.</p>"
        providers_used["resume_summary"] = "failed"
    else:
        tailored_resume_summary, rs_provider = tasks[1]
        providers_used["resume_summary"] = rs_provider

    # d. Work Experience
    if isinstance(tasks[2], Exception):
        warnings.append(f"Work experience suggestions temporarily unavailable: {tasks[2]}")
        tailored_work_experience_html = "<ul><li>Work experience suggestions temporarily unavailable. Please try again.</li></ul>"
        providers_used["work_experience"] = "failed"
    else:
        tailored_work_experience_html, we_provider = tasks[2]
        providers_used["work_experience"] = we_provider

    # e. Cover Letter
    if isinstance(tasks[3], Exception):
        warnings.append(f"Cover letter temporarily unavailable: {tasks[3]}")
        cover_letter = "<p>Cover letter temporarily unavailable. Please try again.</p>"
        providers_used["cover_letter"] = "failed"
    else:
        cover_letter, cl_provider = tasks[3]
        providers_used["cover_letter"] = cl_provider

    total_time = round(time.time() - t_start, 2)
    print(f"📊 [Matchwise] Analysis complete in {total_time}s | providers: {providers_used} | warnings: {len(warnings)}")

    result = {
        "job_summary": job_summary,
        "resume_summary": resume_summary,
        "match_score": match_score,
        "tailored_resume_summary": tailored_resume_summary,
        "tailored_work_experience": tailored_work_experience_html,
        "cover_letter": cover_letter,
        "providers_used": providers_used,
        "total_time_seconds": total_time,
    }
    if warnings:
        result["warnings"] = warnings

    return result


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/health")
async def matchwise_health():
    return {
        "status": "ok",
        "module": "matchwise",
        "version": "2.1.0",
        "ai_architecture": "groq-gemini-openai-openrouter",
        "features": ["model_specific_prompts", "pii_redaction", "parallel_execution", "graceful_degradation"],
        "firebase": "connected" if _get_matchwise_db() else "unavailable"
    }


@router.get("/user/status")
async def get_user_status(uid: str = Query(...)):
    try:
        user_status = MatchwiseUserStatus(uid)
        return user_status.get_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/user/can-generate")
async def can_generate(uid: str = Query(...)):
    try:
        user_status = MatchwiseUserStatus(uid)
        can_gen, reason = user_status.can_generate()
        return {
            "canGenerate": can_gen,
            "reason": reason,
            "status": user_status.get_status()
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/user/use-trial")
async def use_trial(request: Request):
    try:
        # Support both JSON body and query params
        uid = request.query_params.get("uid")
        if not uid:
            try:
                data = await request.json()
                uid = data.get("uid")
            except Exception:
                pass
        return JSONResponse({"success": True, "message": "Trial used."})
    except Exception as e:
        return JSONResponse({"error": str(e)})


@router.post("/compare")
async def compare(job_text: str = Form(...), resume: UploadFile = File(...), uid: str = Form(None)):
    try:
        # 1. Check user permissions
        if uid:
            user_status = MatchwiseUserStatus(uid)
            can_gen, reason = user_status.can_generate()
            
            if not can_gen:
                error_messages = {
                    "trial_used": "Your free trial is finished. Please upgrade to continue using MatchWise!",
                    "subscription_limit_reached": "You have reached your monthly scan limit.",
                    "subscription_expired": "Your subscription has expired. Please renew to continue."
                }
                return JSONResponse(
                    status_code=403, 
                    content={"error": error_messages.get(reason, "Access denied")}
                )
        
        # 2. Parse resume file
        resume_text = ""
        if resume.filename and resume.filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(resume)
        elif resume.filename and resume.filename.endswith((".doc", ".docx")):
            resume_text = extract_text_from_docx(resume)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Unsupported file format. Please upload PDF or DOCX."},
            )
        
        # 3. Run AI analysis
        result = await compare_texts(job_text, resume_text)
        
        # 4. Update user status
        if uid:
            user_status = MatchwiseUserStatus(uid)
            status = user_status.get_status()
            if not status["trialUsed"]:
                user_status.mark_trial_used()
            if status["isUpgraded"]:
                user_status.increment_scan_count()
        
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing error: {str(e)}"},
        )


@router.post("/create-checkout-session")
async def create_checkout_session(uid: str = Form(...), price_id: str = Form(...), mode: str = Form(...)):
    try:
        frontend_url = os.getenv("FRONTEND_URL", "https://smart-sccuss-career-intelligence-ai.vercel.app")
        success_url = f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/cancel"
        
        if mode == "payment":
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"uid": uid}
            )
        elif mode == "subscription":
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"uid": uid}
            )
        else:
            return {"error": "Invalid mode"}
        return {"checkout_url": session.url}
    except Exception as e:
        return {"error": str(e)}


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print(f"⚠️  [Matchwise] Webhook signature verification failed: {e}")
        return {"status": "error", "message": str(e)}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        uid = session["metadata"].get("uid")
        price_id = None

        try:
            if session.get("mode") == "payment":
                line_items = stripe.checkout.Session.list_line_items(session["id"], limit=1)
                if line_items and line_items["data"]:
                    price_id = line_items["data"][0]["price"]["id"]
            elif session.get("mode") == "subscription" and session.get("subscription"):
                subscription = stripe.Subscription.retrieve(session["subscription"])
                price_id = subscription["items"]["data"][0]["price"]["id"]

            if uid and price_id:
                user_status = MatchwiseUserStatus(uid)
                
                if price_id == "price_1RnBbcE6OOEHr6Zo6igE1U8B":
                    user_status.user_ref.set({
                        "isUpgraded": True, "planType": "one_time",
                        "scanLimit": 1, "scansUsed": 0,
                        "lastScanMonth": datetime.now().strftime("%Y-%m")
                    }, merge=True)
                    print(f"✅ [Matchwise] User {uid} upgraded to one-time plan")
                    
                elif price_id == "price_1RnBehE6OOEHr6Zo4QLLJZTg":
                    now = datetime.utcnow()
                    user_status.user_ref.set({
                        "isUpgraded": True, "planType": "basic",
                        "scanLimit": 30, "scansUsed": 0,
                        "subscriptionStart": now.isoformat(),
                        "subscriptionEnd": (now + timedelta(days=30)).isoformat()
                    }, merge=True)
                    print(f"✅ [Matchwise] User {uid} upgraded to basic subscription")
                    
                elif price_id == "price_1RnBgPE6OOEHr6Zo9EFmgyA5":
                    now = datetime.utcnow()
                    user_status.user_ref.set({
                        "isUpgraded": True, "planType": "pro",
                        "scanLimit": 180, "scansUsed": 0,
                        "subscriptionStart": now.isoformat(),
                        "subscriptionEnd": (now + timedelta(days=30)).isoformat()
                    }, merge=True)
                    print(f"✅ [Matchwise] User {uid} upgraded to pro subscription")
                else:
                    print(f"⚠️ [Matchwise] Unknown price_id: {price_id}")
            else:
                print(f"⚠️ [Matchwise] Missing uid or price_id")
                
        except Exception as e:
            print(f"❌ [Matchwise] Error processing webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        print(f"📝 [Matchwise] Subscription cancelled: {subscription['id']}")
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        print(f"❌ [Matchwise] Payment failed for invoice: {invoice['id']}")
    
    return {"status": "success"}
