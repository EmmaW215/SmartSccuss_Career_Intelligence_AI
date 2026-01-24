# SmartSuccess.AI Interview Backend - Phase 2

## 🎯 Overview

Cost-optimized AI interview platform with natural conversation capabilities.

**Monthly Cost: $0-10** (vs. original $55-75)

```
┌─────────────────────────────────────────────────────────────────┐
│                  ARCHITECTURE OVERVIEW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Render Free ($0)        GPU Server (自托管)      Gemini ($0-8) │
│  ┌──────────────┐       ┌──────────────┐       ┌────────────┐  │
│  │ 轻量 API     │ ◄───► │ Whisper STT  │       │ 2.0 Flash  │  │
│  │ 问题库       │       │ XTTS TTS     │ ◄───► │ 1.5 Flash  │  │
│  │ Session 管理 │       │ Custom RAG   │       │ (对话处理)  │  │
│  │ 文字备用模式 │       │ Embeddings   │       └────────────┘  │
│  └──────────────┘       └──────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| Render Free | $0 | Lightweight API, 512MB RAM |
| Gemini API | $0-8 | Free tier: 1500 req/day |
| GPU Server | Electricity | Self-hosted Whisper + XTTS |
| Edge-TTS | $0 | Free Microsoft TTS fallback |
| **Total** | **$0-10/month** | |

## 🚀 Quick Start

### 1. Deploy to Render (FREE)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Or manually:

```bash
# Clone and deploy
cd render-backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Configure Environment

```bash
# Copy example env
cp .env.example .env

# Set your Gemini API key (FREE at https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_key_here

# Optional: GPU server URL
GPU_SERVER_URL=http://your-gpu:8001
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Start screening interview
curl -X POST http://localhost:8000/api/interview/screening/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "user_name": "Emma"}'
```

## 📁 Project Structure

```
smartsuccess-phase2/
├── render-backend/           # Render Free deployment
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── config.py        # Configuration
│   │   ├── core/
│   │   │   └── conversation_engine.py  # Natural AI conversations
│   │   ├── services/
│   │   │   ├── llm_service.py         # Gemini/OpenAI integration
│   │   │   ├── gpu_client.py          # GPU server client
│   │   │   └── session_store.py       # In-memory sessions
│   │   ├── rag/
│   │   │   ├── question_bank.py       # Pre-built questions
│   │   │   └── custom_rag_builder.py  # Custom RAG
│   │   ├── feedback/
│   │   │   └── feedback_generator.py  # Interview feedback
│   │   └── api/routes/
│   │       ├── screening.py
│   │       ├── behavioral.py
│   │       ├── technical.py
│   │       ├── customize.py
│   │       ├── voice.py
│   │       └── dashboard.py
│   ├── requirements.txt
│   ├── render.yaml
│   └── .env.example
│
├── gpu-server/              # Self-hosted GPU (optional)
│   ├── main.py
│   ├── services/
│   │   ├── whisper_service.py  # STT
│   │   ├── tts_service.py      # XTTS
│   │   └── rag_service.py      # RAG building
│   └── requirements.txt
│
└── frontend-components/     # React components
    ├── components/
    │   └── interview/
    │       └── InterviewVoicePanel.tsx
    ├── hooks/
    │   ├── useMicrophone.ts
    │   ├── useAudioPlayer.ts
    │   └── useInterviewSession.ts
    └── services/
        └── interviewApi.ts
```

## 🎤 Interview Types

### 1. Screening Interview
- 5 questions, ~15 minutes
- Basic fit and motivation
- Route: `/api/interview/screening`

### 2. Behavioral Interview
- 6 questions, ~30 minutes
- STAR method evaluation
- Route: `/api/interview/behavioral`

### 3. Technical Interview
- 8 questions, ~45 minutes
- System design, coding, problem-solving
- Route: `/api/interview/technical`

### 4. Customize Interview (Requires GPU)
- 10 questions, ~45 minutes
- Personalized from uploaded documents
- Route: `/api/interview/customize`

## 🔧 API Reference

### Start Interview
```http
POST /api/interview/{type}/start
Content-Type: application/json

{
  "user_id": "string",
  "user_name": "string (optional)",
  "voice_enabled": true
}
```

### Submit Response
```http
POST /api/interview/{type}/respond
Content-Type: application/json

{
  "session_id": "string",
  "user_response": "string"
}
```

### Voice Services
```http
# Transcribe audio
POST /api/voice/transcribe
Content-Type: multipart/form-data
audio: <file>
language: "en"

# Synthesize speech
POST /api/voice/synthesize
Content-Type: application/json
{
  "text": "Hello, this is Alex.",
  "voice": "professional"
}
```

## 💡 Graceful Degradation

| GPU Status | Voice | Custom RAG | Standard Interviews |
|------------|-------|------------|---------------------|
| ✅ Online | High-quality | ✅ Full | ✅ Voice + Text |
| ❌ Offline | Edge-TTS | ❌ Disabled | ✅ Text only |

## 🔒 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Gemini API key (free tier) |
| `GPU_SERVER_URL` | No | Self-hosted GPU server URL |
| `OPENAI_API_KEY` | No | Emergency fallback |
| `ENVIRONMENT` | No | `production` or `development` |

## 📈 LLM Provider Priority

1. **Gemini 2.0 Flash** - FREE (1500 req/day)
2. **Gemini 1.5 Flash** - $0.075/1M tokens
3. **GPT-4o-mini** - $0.15/1M tokens (emergency)

## 🖥️ GPU Server Setup (Optional)

```bash
cd gpu-server

# Install dependencies (requires CUDA)
pip install -r requirements.txt

# Run server
uvicorn main:app --host 0.0.0.0 --port 8001
```

Required GPU: NVIDIA with 8GB+ VRAM (RTX 3070 or better)

## 🛠️ Development

```bash
# Install dependencies
cd render-backend
pip install -r requirements.txt

# Run with hot reload
uvicorn app.main:app --reload --port 8000

# Test
pytest tests/
```

## 📝 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request
