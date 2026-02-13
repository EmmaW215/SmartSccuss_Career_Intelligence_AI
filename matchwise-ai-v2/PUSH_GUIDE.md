# MatchWise AI v2 — Push & Deploy Guide

## 📦 Package Contents

```
matchwise-ai-v2/
├── frontend/                    ← Push to: EmmaW215/matchwise-ai_New_For_SmartSuccessAI
│   ├── .env.example             ★ NEW — env var template
│   ├── .gitignore               ★ UPDATED — includes .env.local
│   ├── App.tsx                  ★ FIXED — VITE_ env vars
│   ├── README.md                ★ UPDATED — v2 documentation
│   ├── firebase.ts              ★ FIXED — VITE_ env vars
│   ├── index.html               • UNCHANGED
│   ├── index.tsx                • UNCHANGED
│   ├── metadata.json            • UPDATED version to 2.0.0
│   ├── package.json             • UPDATED version to 2.0.0
│   ├── tsconfig.json            • UNCHANGED
│   ├── types.ts                 • UNCHANGED
│   ├── vite.config.ts           ★ FIXED — removed stale Gemini define block
│   ├── components/
│   │   ├── LoginModal.tsx       • UNCHANGED
│   │   ├── ResultsDisplay.tsx   • UNCHANGED
│   │   ├── UpgradeModal.tsx     • UNCHANGED
│   │   └── VisitorCounter.tsx   • UNCHANGED (placeholder for Module 6)
│   └── hooks/
│       └── useParentMessage.ts  ★ FIXED — import.meta.env.PROD
│
├── backend/                     ← Push to: your Render backend repo
│   ├── main.py                  ★ NEW — Groq→Gemini→OpenRouter AI chain
│   ├── requirements.txt         ★ UPDATED — removed openai, playwright
│   └── .env.example             ★ NEW — backend env var template
│
└── PUSH_GUIDE.md                ← This file (don't push)
```

★ = Modified/New files    • = Unchanged files

---

## 🚀 Step 1: Push Frontend to GitHub (5 min)

```bash
# Clone your existing repo (or navigate to your local copy)
git clone https://github.com/EmmaW215/matchwise-ai_New_For_SmartSuccessAI.git
cd matchwise-ai_New_For_SmartSuccessAI

# Copy ALL files from the frontend/ folder in this package,
# OVERWRITING existing files:
# - Copy frontend/.env.example → .env.example
# - Copy frontend/.gitignore → .gitignore
# - Copy frontend/App.tsx → App.tsx
# - Copy frontend/firebase.ts → firebase.ts
# - Copy frontend/vite.config.ts → vite.config.ts
# - Copy frontend/hooks/useParentMessage.ts → hooks/useParentMessage.ts
# - Copy frontend/README.md → README.md
# - Copy frontend/package.json → package.json
# - Copy frontend/metadata.json → metadata.json
# (All other files remain unchanged but are included for completeness)

# Commit and push
git add -A
git commit -m "v2.0.0: Migrate to Vite env vars, fix REACT_APP→VITE prefix"
git push origin main
```

---

## 🚀 Step 2: Create .env.local for Local Dev (2 min)

```bash
# In your frontend repo root:
cp .env.example .env.local

# Edit .env.local with YOUR actual values:
# VITE_FIREBASE_API_KEY=AIzaSy...         ← from Firebase Console
# VITE_FIREBASE_AUTH_DOMAIN=...
# VITE_FIREBASE_PROJECT_ID=...
# VITE_FIREBASE_STORAGE_BUCKET=...
# VITE_FIREBASE_MESSAGING_SENDER_ID=...
# VITE_FIREBASE_APP_ID=...
# VITE_BACKEND_URL=https://resume-matcher-backend-rrrw.onrender.com
# VITE_STRIPE_KEY=pk_test_51RnB7HE6OOEHr6Zo...
```

---

## 🚀 Step 3: Register Free AI Accounts & Get API Keys (15 min)

| Service | URL | Key Format |
|---------|-----|------------|
| **Groq** (Layer 1) | https://console.groq.com | `gsk_...` |
| **Google AI Studio** (Layer 2) | https://aistudio.google.com/apikey | `AIzaSy...` |
| **OpenRouter** (Layer 3) | https://openrouter.ai/keys | `sk-or-v1-...` |

---

## 🚀 Step 4: Update Render Backend (10 min)

### 4a. Push backend code
If your backend is in a separate repo:
```bash
cd your-render-backend-repo
# Replace main.py with backend/main.py from this package
# Replace requirements.txt with backend/requirements.txt from this package
git add -A
git commit -m "v2.0.0: Replace OpenAI/xAI/Mock with Groq/Gemini/OpenRouter"
git push origin main
# Render will auto-deploy
```

### 4b. Add environment variables in Render Dashboard
Go to: https://dashboard.render.com → Your service → Environment

**ADD these new variables:**
| Variable | Value |
|----------|-------|
| `GROQ_API_KEY` | `gsk_...` (from Step 3) |
| `GEMINI_API_KEY` | `AIzaSy...` (from Step 3) |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` (from Step 3) |
| `FRONTEND_URL` | `https://matchwise-ai-v2.vercel.app` |
| `ALLOWED_ORIGINS` | `https://matchwise-ai-v2.vercel.app,https://matchwise-ai.vercel.app` |

**KEEP these existing variables:**
- `STRIPE_SECRET_KEY` — keep as-is
- `STRIPE_WEBHOOK_SECRET` — keep as-is
- (serviceAccountKey.json — keep as-is)

**OPTIONAL: Remove old variables:**
- `OPENAI_API_KEY` — no longer needed
- `XAI_API_KEY` — no longer needed

---

## 🚀 Step 5: Deploy Frontend to Vercel (5 min)

1. Go to https://vercel.com/new
2. Import: `EmmaW215/matchwise-ai_New_For_SmartSuccessAI`
3. Framework Preset: **Vite**
4. Build Command: `npm run build`
5. Output Directory: `dist`
6. **Environment Variables** — add all from `.env.example`:
   - `VITE_FIREBASE_API_KEY` = your value
   - `VITE_FIREBASE_AUTH_DOMAIN` = your value
   - `VITE_FIREBASE_PROJECT_ID` = your value
   - `VITE_FIREBASE_STORAGE_BUCKET` = your value
   - `VITE_FIREBASE_MESSAGING_SENDER_ID` = your value
   - `VITE_FIREBASE_APP_ID` = your value
   - `VITE_BACKEND_URL` = `https://resume-matcher-backend-rrrw.onrender.com`
   - `VITE_STRIPE_KEY` = your Stripe publishable key
7. Deploy!

---

## 🚀 Step 6: Test (10 min)

### Quick Smoke Test:
1. ✅ Open your Vercel URL → page loads with MatchWise header
2. ✅ Paste a job description + upload a PDF resume → click Generate
3. ✅ Check Render logs for: `✅ AI Layer 1 SUCCESS: Groq`
4. ✅ All 6 results appear (Job Summary, Comparison Table, Score, Resume Summary, Work Experience, Cover Letter)
5. ✅ Google Sign-in works
6. ✅ Upgrade modal shows 3 pricing tiers

### Verify AI Fallback:
- Normal usage → Render logs should show "AI Layer 1 SUCCESS: Groq"
- If Groq is rate-limited → logs show "Layer 2: Gemini"
- If both fail → logs show "Layer 3: OpenRouter"

---

## 📊 Cost Summary

| Metric | Old | New |
|--------|-----|-----|
| Per-request cost | $0.004 (OpenAI) | **$0** (Groq free) |
| Free daily capacity | 0 | **~1,050 requests** |
| Overflow cost | $0.004/req | **$0.00075/req** (Gemini) |
| Cost reduction | — | **81% savings** |
