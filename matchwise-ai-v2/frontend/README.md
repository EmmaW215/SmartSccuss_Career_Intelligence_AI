# MatchWise AI v2.0

AI-powered resume optimization platform that analyzes job postings, compares them against your resume, generates match scores, tailored summaries, work experience suggestions, and cover letters.

## Architecture

```
Frontend (Vercel)              Backend (Render)
─────────────────              ────────────────────────
Vite + React 19                FastAPI (Python 3.9+)
TypeScript                     Uvicorn (ASGI server)
Tailwind CSS (CDN)             aiohttp (async HTTP)
Firebase Auth (Client SDK)     Firebase Admin SDK (Firestore)
Stripe.js                      Stripe Python SDK
                               PyPDF2 / python-docx
                               BeautifulSoup4
                               ─────────────────────
                               AI Fallback Chain:
                               1. Groq (Llama 3.3 70B) — Free
                               2. Gemini 2.5 Flash — Free/Low
                               3. OpenRouter :free models — Free
```

## Quick Start (Frontend)

```bash
# 1. Clone and install
git clone https://github.com/EmmaW215/matchwise-ai_New_For_SmartSuccessAI.git
cd matchwise-ai_New_For_SmartSuccessAI
npm install

# 2. Create .env.local from template
cp .env.example .env.local
# Edit .env.local with your actual Firebase + Stripe keys

# 3. Run locally
npm run dev
# Opens at http://localhost:3000
```

## Deployment

**Frontend → Vercel:**
- Connect this repo to Vercel
- Framework: Vite | Build: `npm run build` | Output: `dist`
- Add all `VITE_*` env vars from `.env.example`

**Backend → Render:**
- Already deployed at: `https://resume-matcher-backend-rrrw.onrender.com`
- Add `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` in Render env vars
- Update `FRONTEND_URL` to your new Vercel domain

## Modules

| Module | Description |
|--------|-------------|
| 1. Job Parsing | AI extracts structured job requirements from pasted text |
| 2. Resume Parsing | PDF/DOCX upload with drag-drop support |
| 3. Comparison & Scoring | Match table, score, tailored summary, work experience, cover letter |
| 4. Auth & Access | Firebase Auth (Google Sign-in) + Firestore user status |
| 5. Stripe Payments | 3 tiers: $2 one-time, $6/mo basic, $15/mo pro |
| 6. Visitor Counter | Placeholder for future backend integration |

## License

MIT
