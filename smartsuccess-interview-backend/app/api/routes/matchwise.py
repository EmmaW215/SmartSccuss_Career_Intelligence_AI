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
    "resume_summary": 800,
    "work_experience": 1500,
    "cover_letter": 3000,   # Cover letters need significantly more tokens
}

# ============================================================================
# AI Fallback Architecture
# Layer 1: Groq (free, fast)  →  Layer 2: Gemini (free)  →  Layer 3: OpenAI GPT-4o-mini (paid, reliable)
# Layer 4: OpenRouter (free, optional last resort)
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
        gen_config = {"maxOutputTokens": max_tokens, "temperature": 0.2}
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


async def call_ai_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000, json_mode: bool = False) -> str:
    """4-Layer Fallback: Groq → Gemini → OpenAI GPT-4o-mini → OpenRouter (free)
    
    Args:
        prompt: The user prompt to send
        system_prompt: System-level instruction for the LLM
        max_tokens: Per-prompt token budget (varies by output type)
        json_mode: If True, request structured JSON output from the LLM
    """
    try:
        print(f"🔵 [Matchwise] AI Layer 1: Attempting Groq (max_tokens={max_tokens}, json={json_mode})...")
        result = await call_groq_api(prompt, system_prompt, max_tokens, json_mode)
        print("✅ [Matchwise] AI Layer 1 SUCCESS: Groq")
        return result
    except Exception as groq_error:
        print(f"⚠️ [Matchwise] AI Layer 1 FAILED (Groq): {groq_error}")

    try:
        print(f"🟡 [Matchwise] AI Layer 2: Attempting Gemini (max_tokens={max_tokens}, json={json_mode})...")
        result = await call_gemini_api(prompt, system_prompt, max_tokens, json_mode)
        print("✅ [Matchwise] AI Layer 2 SUCCESS: Gemini")
        return result
    except Exception as gemini_error:
        print(f"⚠️ [Matchwise] AI Layer 2 FAILED (Gemini): {gemini_error}")

    try:
        print(f"🟣 [Matchwise] AI Layer 3: Attempting OpenAI GPT-4o-mini (max_tokens={max_tokens}, json={json_mode})...")
        result = await call_openai_api(prompt, system_prompt, max_tokens, json_mode)
        print("✅ [Matchwise] AI Layer 3 SUCCESS: OpenAI GPT-4o-mini")
        return result
    except Exception as openai_error:
        print(f"⚠️ [Matchwise] AI Layer 3 FAILED (OpenAI): {openai_error}")

    try:
        print(f"🟠 [Matchwise] AI Layer 4: Attempting OpenRouter (max_tokens={max_tokens})...")
        result = await call_openrouter_api(prompt, system_prompt, max_tokens)
        print("✅ [Matchwise] AI Layer 4 SUCCESS: OpenRouter")
        return result
    except Exception as openrouter_error:
        print(f"❌ [Matchwise] AI Layer 4 FAILED (OpenRouter): {openrouter_error}")

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
# Core Analysis — compare_texts (6 AI prompts)
# ============================================================================
async def compare_texts(job_text: str, resume_text: str) -> dict:
    try:
        # a. Job Summary
        job_summary_prompt = (
            "Please read the following job posting content:\n\n"
            f"{job_text}\n\n"
            "Summarize the job descriptions by extracting and organizing the following information into a clean HTML bullet list format:             <ul>            <li><strong> Ø Position Title: </strong> [extract the job title]</li>            <li><strong> Ø Position Location: </strong> [extract the location]</li>            <li><strong> Ø Potential Salary: </strong> [extract salary information if available]</li>            <li><strong> Ø Job Responsibilities: </strong>            <ul>                  <li>•     Ø [responsibility 1]</li>                   <li>•     Ø [responsibility 2]</li>                   <li>•     Ø [responsibility 3]</li>                  <li>•     Ø [responsibility 4]</li> <li>•     Ø [responsibility 5]</li>  <li>•     Ø [responsibility 6]</li>    <li>•     Ø [responsibility 7]</li>   <li>•     Ø [responsibility 8]</li>      </ul>             </li>             <li><strong> Ø Technical Skills Required: </strong>               <ul>                 <li>•     Ø [tech skill 1]</li>                 <li>•     Ø [tech skill 2]</li>                 <li>•     Ø [tech skill 3]</li>                 <li>•     Ø [tech skill 4]</li>    <li>•     Ø [tech skill 5]</li>   <li>•     Ø [tech skill 6]</li>   <li>•     Ø [tech skill 7]</li>   <li>•     Ø [tech skill 8]</li>  </ul>             </li>             <li><strong> Ø Soft Skills Required: </strong>               <ul>                 <li>•     Ø [soft skill 1]</li>                 <li>•     Ø [soft skill 2]</li>                 <li>•     Ø [soft skill 3]</li>                 <li>•     Ø [soft skill 4]</li>   <li>•     Ø [soft skill 5]</li>  <li>•     Ø [soft skill 6]</li>  <li>•     Ø [soft skill 7]</li>           </ul>             </li>             <li><strong> Ø Certifications Required: </strong> [extract certification requirements]</li>             <li><strong> Ø Education Required: </strong> [extract education requirements]</li>             <li><strong> Ø Company Vision: </strong> [extract company vision/mission if available]</li>             </ul>\n            Please extract the actual information from the job posting. Using the structure above, organize the output into a clean HTML bullet list format. If any information is not available in the job posting, use 'Not specified' for that item. Ensure the output is clean, well-structured, and uses proper HTML bullet list formatting. Maintain 1.2 line spacing. Do not show the word ```html in output."
        )
        job_summary = await call_ai_api(job_summary_prompt, max_tokens=TOKEN_BUDGETS["job_summary"])
        job_summary = f"\n\n {job_summary}"

        # b. Resume vs Job Comparison — JSON mode + server-side table rendering
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
        comparison_raw = await call_ai_api(comparison_prompt, max_tokens=TOKEN_BUDGETS["comparison"], json_mode=True)

        # Parse JSON and generate table + score server-side
        comparison_data = validate_comparison_json(comparison_raw)
        resume_summary = render_comparison_table(comparison_data)
        match_score = calculate_match_score(comparison_data)

        # c. Tailored Resume Summary (with anti-hallucination guardrails)
        tailored_resume_summary_prompt = (
            "You are revising a resume summary to better match a specific job posting.\n\n"
            "THE APPLICANT'S ACTUAL RESUME:\n"
            f"{resume_text}\n\n"
            "THE JOB POSTING:\n"
            f"{job_text}\n\n"
            "TASK: Write a revised one-paragraph professional summary (max 1700 characters).\n\n"
            "STRICT RULES:\n"
            "1. ONLY mention skills, technologies, and experiences that ACTUALLY appear in the resume above.\n"
            "2. DO NOT fabricate or invent any certifications, years of experience, tools, or achievements.\n"
            "3. If the applicant lacks a required skill, frame adjacent experience as transferable "
            "(e.g., 'Leveraging my background in X to quickly adapt to Y').\n"
            "4. If the resume already has a summary section, use it as a base and enhance it.\n"
            "5. If the resume does not have a summary, write a new one based solely on actual resume content.\n"
            "6. Highlight the applicant's key skills and experiences that best match the job requirements.\n"
            "7. Write in the first person.\n"
            "8. Output in HTML format using <p> tags. No markdown, no ```html.\n"
            "9. Maintain 1.2 line spacing.\n"
        )
        tailored_resume_summary = await call_ai_api(tailored_resume_summary_prompt, max_tokens=TOKEN_BUDGETS["resume_summary"])
        tailored_resume_summary = f"\n{tailored_resume_summary}"

        # d. Tailored Work Experience (with anti-hallucination guardrails)
        tailored_work_experience_prompt = (
            "You are revising work experience bullet points to better match a specific job posting.\n\n"
            "THE APPLICANT'S ACTUAL RESUME:\n"
            f"{resume_text}\n\n"
            "THE JOB POSTING:\n"
            f"{job_text}\n\n"
            "TASK: Find the most recent and relevant work experiences from the resume and revise them "
            "to better align with the job requirements. Output 5-7 bullet points.\n\n"
            "STRICT RULES:\n"
            "1. ONLY use work experiences that ACTUALLY appear in the resume. DO NOT invent new experiences.\n"
            "2. You may rephrase, reorganize, and emphasize existing experiences to highlight relevant skills.\n"
            "3. You may add relevant keywords from the job posting IF the applicant demonstrably has that skill "
            "(e.g., if the resume shows Python projects, you can mention 'Python' even if not explicitly stated).\n"
            "4. DO NOT fabricate metrics, percentages, dollar amounts, or team sizes unless they appear in the resume.\n"
            "5. Frame transferable skills honestly (e.g., 'Applied data analysis techniques' rather than inventing a role).\n"
            "6. Each bullet should start with a strong action verb.\n"
            "7. Keep each bullet concise and impactful (1-2 sentences max).\n"
            "8. Format as an HTML unordered list: <ul><li>...</li></ul>\n"
            "9. No markdown, no ```html, no extra text outside the list.\n"
        )
        tailored_work_experience_html = await call_ai_api(tailored_work_experience_prompt, max_tokens=TOKEN_BUDGETS["work_experience"])

        # e. Cover Letter (with anti-hallucination guardrails)
        cover_letter_prompt = (
            "Write a professional cover letter for the following job application.\n\n"
            "APPLICANT'S ACTUAL BACKGROUND (from resume):\n"
            f"{resume_text}\n\n"
            "JOB POSTING:\n"
            f"{job_text}\n\n"
            "STRICT RULES YOU MUST FOLLOW:\n"
            "1. Start the letter with 'Dear Hiring Manager,' — do NOT use any person's name from the job posting or resume.\n"
            "2. End the letter with 'Sincerely,' followed by a blank line for the applicant's signature (use '[Your Name]' as placeholder).\n"
            "3. ONLY reference skills, technologies, and experiences that ACTUALLY appear in the resume above. Do NOT fabricate or invent any experience the applicant does not have.\n"
            "4. If the applicant lacks a required skill, frame adjacent experience as transferable (e.g., 'My experience in X provides a strong foundation for Y').\n"
            "5. Extract the correct job title and company name from the job posting and use them in the letter.\n"
            "6. Write exactly 4 paragraphs: (a) opening hook with position and company, (b) relevant technical experience, (c) soft skills and cultural fit, (d) closing with enthusiasm and interview request.\n"
            "7. Keep the letter between 400-600 words. The tone should be confident, honest, and professional.\n"
            "8. Write in the first person.\n"
            "9. Output ONLY in HTML format using <p> tags for paragraphs. No markdown, no ```html, no extra text outside the letter.\n"
            "10. Make sure there are line breaks between each paragraph.\n"
        )
        cover_letter = await call_ai_api(cover_letter_prompt, max_tokens=TOKEN_BUDGETS["cover_letter"])
        cover_letter = f"\n{cover_letter}"

        return {
            "job_summary": job_summary,
            "resume_summary": resume_summary,
            "match_score": match_score,
            "tailored_resume_summary": tailored_resume_summary,
            "tailored_work_experience": tailored_work_experience_html,
            "cover_letter": cover_letter,
        }
    except Exception as e:
        raise Exception(f"Comparison failed: {str(e)}")


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/health")
async def matchwise_health():
    return {
        "status": "ok",
        "module": "matchwise",
        "version": "2.0.0",
        "ai_architecture": "groq-gemini-openai-openrouter",
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
