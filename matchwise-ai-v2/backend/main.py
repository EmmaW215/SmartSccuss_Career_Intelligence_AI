from fastapi import FastAPI, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document
import io
import aiohttp
import json
import os
import re

import stripe

from dotenv import load_dotenv
load_dotenv()
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()

# ============================================================================
# User Status Management (PRESERVED — identical to original)
# ============================================================================
class UserStatus:
    def __init__(self, uid: str):
        self.uid = uid
        self.user_ref = db.collection("users").document(uid)
        self.now_month = datetime.now().strftime("%Y-%m")
    
    def get_status(self):
        """Get complete user status"""
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
        """Process user data including cross-month reset"""
        lastScanMonth = data.get("lastScanMonth", "")
        scansUsed = data.get("scansUsed", 0)
        
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
            "scansUsed": scansUsed,
            "lastScanMonth": self.now_month,
            "subscriptionActive": is_subscription_active,
            "subscriptionEnd": subscription_end,
        }
    
    def _get_default_status(self):
        """Get default status for new users"""
        return {
            "trialUsed": False,
            "isUpgraded": False,
            "planType": None,
            "scanLimit": None,
            "scansUsed": 0,
            "lastScanMonth": self.now_month
        }
    
    def can_generate(self):
        """Check if user can generate an analysis"""
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
        """Mark trial as used"""
        self.user_ref.set({"trialUsed": True}, merge=True)
    
    def increment_scan_count(self):
        """Increment scan count for subscription users"""
        status = self.get_status()
        if status["isUpgraded"] and status["scanLimit"] is not None:
            self.user_ref.set({
                "scansUsed": status["scansUsed"] + 1,
                "lastScanMonth": self.now_month
            }, merge=True)


# ============================================================================
# API Endpoints — User Status (PRESERVED)
# ============================================================================
@app.get("/api/user/status")
async def get_user_status(uid: str = Query(...)):
    try:
        user_status = UserStatus(uid)
        return user_status.get_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/user/can-generate")
async def can_generate(uid: str = Query(...)):
    try:
        user_status = UserStatus(uid)
        can_gen, reason = user_status.can_generate()
        return {
            "canGenerate": can_gen,
            "reason": reason,
            "status": user_status.get_status()
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# CORS Configuration (UPDATED — added new Vercel domain)
# ============================================================================
allowed_origins = [
    "https://matchwise-ai.vercel.app",          # Original Vercel domain
    "https://matchwise-ai-v2.vercel.app",        # NEW: v2 Vercel domain
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",                      # NEW: Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",                     # NEW: Vite default port
    "http://192.168.86.47:3000"
]

# Allow environment variable override for custom domains
if os.getenv("ALLOWED_ORIGINS"):
    additional_origins = os.getenv("ALLOWED_ORIGINS")
    if additional_origins:
        allowed_origins.extend(additional_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# NEW: Zero-Cost AI Fallback Architecture
# Replaces: call_openai_api → call_xai_api → generate_mock_ai_response
# New flow: call_groq_api → call_gemini_api → call_openrouter_api
# ============================================================================

async def call_groq_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.") -> str:
    """
    Layer 1: Groq Cloud — Llama 3.3 70B Versatile
    Free tier: ~1000 requests/day | Ultra-fast inference
    Cost: $0 (free tier)
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("GROQ_API_KEY not set in environment variables")

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        try:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 429:
                    error_text = await response.text()
                    raise Exception(f"Groq rate limit exceeded (429): {error_text}")
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Groq API error: {response.status} - {error_text}")
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            raise Exception(f"Groq API request failed: {str(e)}")


async def call_gemini_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.") -> str:
    """
    Layer 2: Google Gemini 2.5 Flash
    Free tier: 50 requests/day | Beyond that: ~$0.00075/call
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY not set in environment variables")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 2000,
                "temperature": 0.3
            }
        }
        try:
            async with session.post(
                url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 429:
                    error_text = await response.text()
                    raise Exception(f"Gemini rate limit exceeded (429): {error_text}")
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error: {response.status} - {error_text}")
                result = await response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except aiohttp.ClientError as e:
            raise Exception(f"Gemini API request failed: {str(e)}")


# OpenRouter free model rotation list
OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

async def call_openrouter_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.", model_index: int = 0) -> str:
    """
    Layer 3: OpenRouter Free Models
    Rotates through multiple free models on rate limit (429)
    Cost: $0 (free tier with rate limits)
    """
    if model_index >= len(OPENROUTER_FREE_MODELS):
        raise Exception("All OpenRouter free models exhausted — all rate limited")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY not set in environment variables")

    model = OPENROUTER_FREE_MODELS[model_index]

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("FRONTEND_URL", "https://matchwise-ai-v2.vercel.app"),
            "X-Title": "MatchWise AI",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=45)
            ) as response:
                if response.status == 429:
                    print(f"⚠️ OpenRouter model {model} rate limited, trying next model...")
                    return await call_openrouter_api(prompt, system_prompt, model_index + 1)
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error ({model}): {response.status} - {error_text}")
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            raise Exception(f"OpenRouter API request failed ({model}): {str(e)}")


async def call_ai_api(prompt: str, system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.") -> str:
    """
    Zero-Cost Triple Fallback AI Orchestrator
    ─────────────────────────────────────────
    Layer 1: Groq Cloud (Llama 3.3 70B)   — Free ~1000 req/day, ultra-fast
    Layer 2: Google Gemini 2.5 Flash       — Free 50/day, then ~$0.00075/call
    Layer 3: OpenRouter :free models       — Free with rate limits, rotates 4 models
    
    Replaces the old: OpenAI → xAI → Mock AI architecture
    """
    # Layer 1: Groq Cloud — Primary (Free, Ultra-fast)
    try:
        print("🔵 AI Layer 1: Attempting Groq Llama 3.3 70B...")
        result = await call_groq_api(prompt, system_prompt)
        print("✅ AI Layer 1 SUCCESS: Groq")
        return result
    except Exception as groq_error:
        print(f"⚠️ AI Layer 1 FAILED (Groq): {groq_error}")

    # Layer 2: Gemini 2.5 Flash — Secondary
    try:
        print("🟡 AI Layer 2: Attempting Gemini 2.5 Flash...")
        result = await call_gemini_api(prompt, system_prompt)
        print("✅ AI Layer 2 SUCCESS: Gemini")
        return result
    except Exception as gemini_error:
        print(f"⚠️ AI Layer 2 FAILED (Gemini): {gemini_error}")

    # Layer 3: OpenRouter Free Models — Fallback (rotates through 4 models)
    try:
        print("🟠 AI Layer 3: Attempting OpenRouter free models...")
        result = await call_openrouter_api(prompt, system_prompt)
        print("✅ AI Layer 3 SUCCESS: OpenRouter")
        return result
    except Exception as openrouter_error:
        print(f"❌ AI Layer 3 FAILED (OpenRouter): {openrouter_error}")

    # All layers failed
    raise Exception("All AI services are currently unavailable. Please try again in a few minutes.")


# ============================================================================
# File Extraction (PRESERVED — identical to original)
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

def extract_text_from_url(url: str) -> str:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        full_text = soup.get_text(separator=" ", strip=True)
        return full_text
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch job posting: {str(e)}")


# ============================================================================
# Core Analysis — compare_texts (PRESERVED — all 6 AI prompts identical)
# Only change: call_ai_api now routes through Groq → Gemini → OpenRouter
# ============================================================================
async def compare_texts(job_text: str, resume_text: str) -> dict:
    try:
        # a. Job Summary (Module 1: Job Posting Parsing)
        job_summary_prompt = (
            "Please read the following job posting content:\n\n"
            f"{job_text}\n\n"
            
            "Summarize the job descriptions by extracting and organizing the following information into a clean HTML bullet list format:             <ul>            <li><strong> Ø Position Title: </strong> [extract the job title]</li>            <li><strong> Ø Position Location: </strong> [extract the location]</li>            <li><strong> Ø Potential Salary: </strong> [extract salary information if available]</li>            <li><strong> Ø Job Responsibilities: </strong>            <ul>                  <li>•     Ø [responsibility 1]</li>                   <li>•     Ø [responsibility 2]</li>                   <li>•     Ø [responsibility 3]</li>                  <li>•     Ø [responsibility 4]</li> <li>•     Ø [responsibility 5]</li>  <li>•     Ø [responsibility 6]</li>    <li>•     Ø [responsibility 7]</li>   <li>•     Ø [responsibility 8]</li>      </ul>             </li>             <li><strong> Ø Technical Skills Required: </strong>               <ul>                 <li>•     Ø [tech skill 1]</li>                 <li>•     Ø [tech skill 2]</li>                 <li>•     Ø [tech skill 3]</li>                 <li>•     Ø [tech skill 4]</li>    <li>•     Ø [tech skill 5]</li>   <li>•     Ø [tech skill 6]</li>   <li>•     Ø [tech skill 7]</li>   <li>•     Ø [tech skill 8]</li>  </ul>             </li>             <li><strong> Ø Soft Skills Required: </strong>               <ul>                 <li>•     Ø [soft skill 1]</li>                 <li>•     Ø [soft skill 2]</li>                 <li>•     Ø [soft skill 3]</li>                 <li>•     Ø [soft skill 4]</li>   <li>•     Ø [soft skill 5]</li>  <li>•     Ø [soft skill 6]</li>  <li>•     Ø [soft skill 7]</li>           </ul>             </li>             <li><strong> Ø Certifications Required: </strong> [extract certification requirements]</li>             <li><strong> Ø Education Required: </strong> [extract education requirements]</li>             <li><strong> Ø Company Vision: </strong> [extract company vision/mission if available]</li>             </ul>\n            Please extract the actual information from the job posting. Using the structure above, organize the output into a clean HTML bullet list format. If any information is not available in the job posting, use 'Not specified' for that item. Ensure the output is clean, well-structured, and uses proper HTML bullet list formatting. Maintain 1.2 line spacing. Do not show the word ```html in output."
        )
        job_summary = await call_ai_api(job_summary_prompt)
        job_summary = f"\n\n {job_summary}"

        # b. Resume Summary with Comparison Table (Module 3: Comparison & Scoring)
        resume_summary_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job summary:\n\n"
            f"{job_summary}\n\n"
            "Output a comparison table between the job_summary and the upload user resume. List in the table format with Four columns: Categories (list all the key requirements regarding position responsibilities, technical and soft skills, certifications, and educations from the job requirements, each key requirement in one line), Match Status (four status will be used: ✅ Strong (the item is also mentioned in the user's resume and very well-matched with what mentioned in job_summary_prompt) / 🔷 Moderate-strong (the item is also mentioned in the user's resume and closely matched with what mentioned in job_summary_prompt)/⚠️ Partial (the item is kind of mentioned in the user's resume and some parts matched with what mentioned in job_summary_prompt)/ ❌ Lack (the item is not clearly mentioned in the user's resume and only little bit or not match with what mentioned in job_summary_prompt)), Comments (very precise comment on how the user's experiences matches with the job requirement), and Match Weight (If the Match Status is Strong, assign number 1; If the Match Status is Moderate-Strong, assign number 0.8; If the Match Status is Partial, assign number 0.5; If the Match Status is Lack, assign number 0.1). Make sure to output the table in HTML format, with <table>, <tr>, <th>, <td> tags, and do not add any explanation or extra text. The table should be styled to look clean and modern. Only output the table in HTML format, with <table>, <tr>, <th>, <td> tags, and do not add any explanation or extra text. The table should be styled to look clean and modern. Below the table, based on the Match Weight column from job_summary comparison table, calculates the percentage of the matching score. The calculation formulas are: Sum of total Match Weight numbers = sum of all numbers in the Match Weight column; Count of total Match Weight numbers = count of all numbers in the Match Weight column; Match Score (%) =(Sum of total Match Weight numbers)/(Count of total Match Weight numbers). Return the final calculation results of Sum of total Match Weight numbers, Count of total Match Weight numbers, and Match Score as the final percentage number, rounded to two decimal places. No extra text, do not show ``` symbols or word html in output. "
        )
        resume_summary = await call_ai_api(resume_summary_prompt)
        print("resume_summary raw output:", resume_summary)
        resume_summary = f"\n\n{resume_summary}"

        # Match Score extraction (PRESERVED — identical regex logic)
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

        # c. Match Score
        try:
            match_score = float(match_score_test.strip().replace("%", ""))
        except Exception:
            match_score = match_score_test

        # d. Tailored Resume Summary (Module 3 sub-task 3)
        tailored_resume_summary_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job content:\n\n"
            f"{job_text}\n\n"
            "Provide a revised one-paragraph summary based on the original summary in resume_text (the user's resume). If the user's resume does not have a summary or highlight section, write a new summary as the revised summary. Make sure this summary highlights the user's key skills and work experiences and makes it more closely match the job requirements in job_text. Please limit the overall summary to 1700 characters. The output should be in HTML format and should maintain a simple, modern style. Write this paragraph in the first person. Maintain 1.2 line spacing. Do not show the word ```html in output."
        )
        tailored_resume_summary = await call_ai_api(tailored_resume_summary_prompt)
        tailored_resume_summary = f"\n{tailored_resume_summary}"

        # e. Tailored Work Experience (Module 3 sub-task 4)
        tailored_work_experience_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job content:\n\n"
            f"{job_text}\n\n"
            "Find the latest work experiences from the resume and modify them to better match the job requirements. Format the output as a clean HTML unordered list with no more than 7 bullet points:              <ul>             <li>     Ø  [revised work experience bullet 1]</li>             <li>     Ø  [revised work experience bullet 2]</li>             <li>     Ø  [revised work experience bullet 3]</li>             <li>     Ø  [revised work experience bullet 4]</li>             <li>     Ø  [revised work experience bullet 5]</li>             <li>     Ø  [revised work experience bullet 6]</li>             <li>     Ø  [revised work experience bullet 7]</li>             </ul>             Please provide the actual revised work experience content. Organize the output into a clean HTML bullet list using the structure above. Return the result wrapped inside triple backticks and identify the language as HTML. Focus on the most recent and relevant experiences that align with the job requirements. Keep each bullet point concise and impactful. Make sure there are line breaks between each paragraph. Ensure the output uses proper HTML bullet list formatting. Maintain 1.2 line spacing.  Do not show the word ```html in output."
        )
        tailored_work_experience_html = await call_ai_api(tailored_work_experience_prompt)

        # f. Cover Letter (Module 3 sub-task 5)
        cover_letter_prompt = (
            "Read the following resume content:\n\n"
            f"{resume_text}\n\n"
            "And the following job content:\n\n"
            f"{job_text}\n\n"
            "Provide a formal cover letter for the job application. The job position and the company name in the cover letter for applying should be the same as what being used in the job_text. The cover letter should show the user's key strengths and highlight the user's best fit skills and experiences according to the job posting in job_text, then express the user's passions for the position, and express appreciation for a future interview opportunity. The overall tone of the cover letter should be confident, honest, and professional. The cover letters should be written in the first person. Only output in HTML format, using <p> and <br> tags for formatting. Make sure there are line breaks between each paragraph. Do not output markdown or plain text. Do not show ```html in output. "
        )
        cover_letter = await call_ai_api(cover_letter_prompt)
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
# Main Analysis Endpoint (PRESERVED — identical logic)
# ============================================================================
@app.post("/api/compare")
async def compare(job_text: str = Form(...), resume: UploadFile = File(...), uid: str = Form(None)):
    try:
        # 1. Check user permissions
        if uid:
            user_status = UserStatus(uid)
            can_gen, reason = user_status.can_generate()
            
            if not can_gen:
                error_messages = {
                    "trial_used": "Your free trial is finished. Please upgrade to continue using MatchWise!",
                    "subscription_limit_reached": "You have reached your monthly scan limit. Please upgrade your plan or wait for next month.",
                    "subscription_expired": "Your subscription has expired. Please renew to continue."
                }
                return JSONResponse(
                    status_code=403, 
                    content={"error": error_messages.get(reason, "Access denied")}
                )
        
        # 2. Parse resume file (Module 2: Resume Parsing)
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
        
        # 3. Run AI analysis (now uses Groq → Gemini → OpenRouter)
        result = await compare_texts(job_text, resume_text)
        
        # 4. Update user status
        if uid:
            user_status = UserStatus(uid)
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


# ============================================================================
# Stripe Payment Endpoints (PRESERVED — Module 5)
# ============================================================================
@app.post("/api/create-checkout-session")
async def create_checkout_session(uid: str = Form(...), price_id: str = Form(...), mode: str = Form(...)):
    try:
        # Use env var for frontend URL, with fallback
        frontend_url = os.getenv("FRONTEND_URL", "https://matchwise-ai.vercel.app")
        success_url = f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/cancel"
        
        if mode == "payment":
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"uid": uid}
            )
        elif mode == "subscription":
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
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


@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print("⚠️  Webhook signature verification failed.", e)
        return {"status": "error", "message": str(e)}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        uid = session["metadata"].get("uid")
        price_id = None

        try:
            # For one-time payment (mode: payment)
            if session.get("mode") == "payment":
                line_items = stripe.checkout.Session.list_line_items(session["id"], limit=1)
                if line_items and line_items["data"]:
                    price_id = line_items["data"][0]["price"]["id"]

            # For subscription
            elif session.get("mode") == "subscription" and session.get("subscription"):
                subscription = stripe.Subscription.retrieve(session["subscription"])
                price_id = subscription["items"]["data"][0]["price"]["id"]

            if uid and price_id:
                user_status = UserStatus(uid)
                
                if price_id == "price_1RnBbcE6OOEHr6Zo6igE1U8B":
                    # $2 one-time payment — 1 scan
                    user_status.user_ref.set({
                        "isUpgraded": True,
                        "planType": "one_time",
                        "scanLimit": 1,
                        "scansUsed": 0,
                        "lastScanMonth": datetime.now().strftime("%Y-%m")
                    }, merge=True)
                    print(f"✅ User {uid} upgraded to one-time plan")
                    
                elif price_id == "price_1RnBehE6OOEHr6Zo4QLLJZTg":
                    # $6/month subscription — 30 scans/month
                    now = datetime.utcnow()
                    user_status.user_ref.set({
                        "isUpgraded": True,
                        "planType": "basic",
                        "scanLimit": 30,
                        "scansUsed": 0,
                        "subscriptionStart": now.isoformat(),
                        "subscriptionEnd": (now + timedelta(days=30)).isoformat()
                    }, merge=True)
                    print(f"✅ User {uid} upgraded to basic subscription")
                    
                elif price_id == "price_1RnBgPE6OOEHr6Zo9EFmgyA5":
                    # $15/month subscription — 180 scans/month
                    now = datetime.utcnow()
                    user_status.user_ref.set({
                        "isUpgraded": True,
                        "planType": "pro",
                        "scanLimit": 180,
                        "scansUsed": 0,
                        "subscriptionStart": now.isoformat(),
                        "subscriptionEnd": (now + timedelta(days=30)).isoformat()
                    }, merge=True)
                    print(f"✅ User {uid} upgraded to pro subscription")
                else:
                    print(f"⚠️ Unknown price_id: {price_id}")
            else:
                print(f"⚠️ Missing uid or price_id: uid={uid}, price_id={price_id}")
                
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        print(f"📝 Subscription cancelled: {subscription['id']}")
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        print(f"❌ Payment failed for invoice: {invoice['id']}")
    
    return {"status": "success"}


# ============================================================================
# Utility Endpoints (PRESERVED)
# ============================================================================
@app.get("/")
def root():
    return {"message": "MatchWise AI v2 Backend API is running!"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "ai_architecture": "groq-gemini-openrouter"}

@app.post("/api/user/use-trial")
async def use_trial(request: Request):
    data = await request.json()
    uid = data.get("uid") or request.query_params.get("uid")
    return JSONResponse({"success": True, "message": "Trial used."})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
