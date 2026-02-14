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
import PyPDF2
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
# Zero-Cost AI Fallback Architecture
# Groq → Gemini → OpenRouter
# ============================================================================
async def call_groq_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000) -> str:
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


async def call_gemini_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2}
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


async def call_ai_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", max_tokens: int = 2000) -> str:
    """Zero-Cost Triple Fallback: Groq → Gemini → OpenRouter
    
    Args:
        prompt: The user prompt to send
        system_prompt: System-level instruction for the LLM
        max_tokens: Per-prompt token budget (varies by output type)
    """
    try:
        print(f"🔵 [Matchwise] AI Layer 1: Attempting Groq (max_tokens={max_tokens})...")
        result = await call_groq_api(prompt, system_prompt, max_tokens)
        print("✅ [Matchwise] AI Layer 1 SUCCESS: Groq")
        return result
    except Exception as groq_error:
        print(f"⚠️ [Matchwise] AI Layer 1 FAILED (Groq): {groq_error}")

    try:
        print(f"🟡 [Matchwise] AI Layer 2: Attempting Gemini (max_tokens={max_tokens})...")
        result = await call_gemini_api(prompt, system_prompt, max_tokens)
        print("✅ [Matchwise] AI Layer 2 SUCCESS: Gemini")
        return result
    except Exception as gemini_error:
        print(f"⚠️ [Matchwise] AI Layer 2 FAILED (Gemini): {gemini_error}")

    try:
        print(f"🟠 [Matchwise] AI Layer 3: Attempting OpenRouter (max_tokens={max_tokens})...")
        result = await call_openrouter_api(prompt, system_prompt, max_tokens)
        print("✅ [Matchwise] AI Layer 3 SUCCESS: OpenRouter")
        return result
    except Exception as openrouter_error:
        print(f"❌ [Matchwise] AI Layer 3 FAILED (OpenRouter): {openrouter_error}")

    raise Exception("All AI services are currently unavailable. Please try again in a few minutes.")


# ============================================================================
# File Extraction Utilities
# ============================================================================
def extract_text_from_pdf(file: UploadFile) -> str:
    try:
        content = file.file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
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

        # b. Resume Summary with Comparison Table
        resume_summary_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job summary:\n\n"
            f"{job_summary}\n\n"
            "Output a comparison table between the job_summary and the upload user resume. List in the table format with Four columns: Categories (list all the key requirements regarding position responsibilities, technical and soft skills, certifications, and educations from the job requirements, each key requirement in one line), Match Status (four status will be used: ✅ Strong (the item is also mentioned in the user's resume and very well-matched with what mentioned in job_summary_prompt) / 🔷 Moderate-strong (the item is also mentioned in the user's resume and closely matched with what mentioned in job_summary_prompt)/⚠️ Partial (the item is kind of mentioned in the user's resume and some parts matched with what mentioned in job_summary_prompt)/ ❌ Lack (the item is not clearly mentioned in the user's resume and only little bit or not match with what mentioned in job_summary_prompt)), Comments (very precise comment on how the user's experiences matches with the job requirement), and Match Weight (If the Match Status is Strong, assign number 1; If the Match Status is Moderate-Strong, assign number 0.8; If the Match Status is Partial, assign number 0.5; If the Match Status is Lack, assign number 0.1). Make sure to output the table in HTML format, with <table>, <tr>, <th>, <td> tags, and do not add any explanation or extra text. The table should be styled to look clean and modern. Only output the table in HTML format, with <table>, <tr>, <th>, <td> tags, and do not add any explanation or extra text. The table should be styled to look clean and modern. Below the table, based on the Match Weight column from job_summary comparison table, calculates the percentage of the matching score. The calculation formulas are: Sum of total Match Weight numbers = sum of all numbers in the Match Weight column; Count of total Match Weight numbers = count of all numbers in the Match Weight column; Match Score (%) =(Sum of total Match Weight numbers)/(Count of total Match Weight numbers). Return the final calculation results of Sum of total Match Weight numbers, Count of total Match Weight numbers, and Match Score as the final percentage number, rounded to two decimal places. No extra text, do not show ``` symbols or word html in output. "
        )
        resume_summary = await call_ai_api(resume_summary_prompt, max_tokens=TOKEN_BUDGETS["comparison"])
        resume_summary = f"\n\n{resume_summary}"

        # Match Score extraction
        lines = resume_summary.strip().splitlines()
        if lines:
            last_line = lines[-1].strip()
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)", last_line)
            if match:
                match_score_test = float(match.group(1))
                if match_score_test <= 1:
                    match_score_test = round(match_score_test * 100, 2)
            else:
                match_score_test = last_line
        else:
            match_score_test = None

        try:
            match_score = float(str(match_score_test).strip().replace("%", ""))
        except Exception:
            match_score = match_score_test

        # c. Tailored Resume Summary
        tailored_resume_summary_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job content:\n\n"
            f"{job_text}\n\n"
            "Provide a revised one-paragraph summary based on the original summary in resume_text (the user's resume). If the user's resume does not have a summary or highlight section, write a new summary as the revised summary. Make sure this summary highlights the user's key skills and work experiences and makes it more closely match the job requirements in job_text. Please limit the overall summary to 1700 characters. The output should be in HTML format and should maintain a simple, modern style. Write this paragraph in the first person. Maintain 1.2 line spacing. Do not show the word ```html in output."
        )
        tailored_resume_summary = await call_ai_api(tailored_resume_summary_prompt, max_tokens=TOKEN_BUDGETS["resume_summary"])
        tailored_resume_summary = f"\n{tailored_resume_summary}"

        # d. Tailored Work Experience
        tailored_work_experience_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job content:\n\n"
            f"{job_text}\n\n"
            "Find the latest work experiences from the resume and modify them to better match the job requirements. Format the output as a clean HTML unordered list with no more than 7 bullet points:              <ul>             <li>     Ø  [revised work experience bullet 1]</li>             <li>     Ø  [revised work experience bullet 2]</li>             <li>     Ø  [revised work experience bullet 3]</li>             <li>     Ø  [revised work experience bullet 4]</li>             <li>     Ø  [revised work experience bullet 5]</li>             <li>     Ø  [revised work experience bullet 6]</li>             <li>     Ø  [revised work experience bullet 7]</li>             </ul>             Please provide the actual revised work experience content. Organize the output into a clean HTML bullet list using the structure above. Return the result wrapped inside triple backticks and identify the language as HTML. Focus on the most recent and relevant experiences that align with the job requirements. Keep each bullet point concise and impactful. Make sure there are line breaks between each paragraph. Ensure the output uses proper HTML bullet list formatting. Maintain 1.2 line spacing.  Do not show the word ```html in output."
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
        "ai_architecture": "groq-gemini-openrouter",
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
