# SmartSuccess.AI Interview Backend

> AI-powered mock interview platform with specialized interview types

## 🚀 Overview

This backend provides three specialized mock interview services:

| Interview Type | Duration | Focus |
|---------------|----------|-------|
| **Screening** | 10-15 min | First impression, communication, basic fit |
| **Behavioral** | 25-30 min | STAR method, soft skills, past behavior |
| **Technical** | 45 min | AI/ML engineering, system design, practical experience |

## ✨ Features

### Core Features
- 🎯 **Pre-trained Question Banks** - Optimized questions for each interview type
- 🧠 **RAG-powered Personalization** - Questions tailored to resume/JD
- ⭐ **STAR Method Evaluation** - Structured behavioral assessment
- 🔊 **Voice Support** - Whisper ASR + OpenAI TTS
- 📊 **Real-time Feedback** - Instant evaluation and scoring

### Interview Types

#### Screening Interview
- First impression assessment
- Communication skills evaluation
- Motivation and basic fit
- 5 questions, 10-15 minutes

#### Behavioral Interview (STAR Method)
- Situation, Task, Action, Result evaluation
- Competency assessment
- Follow-up questions for incomplete responses
- 6 questions with probing, 25-30 minutes

#### Technical Interview
- AI/ML engineering topics
- System design and architecture
- Practical experience validation
- 8 questions across multiple domains, 45 minutes

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **AI Services**: OpenAI (GPT-4, Whisper, TTS)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector Store**: In-memory NumPy-based
- **Deployment**: Render

## 📁 Project Structure

```
smartsuccess-interview-backend/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration management
│   │
│   ├── core/                      # Core services
│   │   ├── embedding_service.py   # Text → Vector embeddings
│   │   ├── vector_store.py        # In-memory similarity search
│   │   └── voice_service.py       # Whisper ASR + TTS
│   │
│   ├── interview/                 # Interview services
│   │   ├── base_interview.py      # Base interview class
│   │   ├── screening_interview.py # Screening implementation
│   │   ├── behavioral_interview.py# STAR method implementation
│   │   └── technical_interview.py # Technical implementation
│   │
│   ├── rag/                       # RAG services
│   │   ├── base_rag.py            # Base RAG class
│   │   ├── screening_rag.py       # Screening questions
│   │   ├── behavioral_rag.py      # Behavioral questions
│   │   └── technical_rag.py       # Technical questions
│   │
│   ├── feedback/                  # Feedback services
│   │   ├── screening_feedback.py  # First impression scoring
│   │   ├── behavioral_feedback.py # STAR scoring
│   │   └── technical_feedback.py  # Technical scoring
│   │
│   ├── prompts/                   # Prompt templates
│   │   ├── screening_prompts.py
│   │   ├── behavioral_prompts.py
│   │   └── technical_prompts.py
│   │
│   ├── models/                    # Data models
│   │   └── __init__.py            # Pydantic models
│   │
│   └── api/                       # API routes
│       └── routes/
│           ├── health.py
│           ├── screening.py
│           ├── behavioral.py
│           ├── technical.py
│           └── voice.py
│
├── data/                          # Pre-trained question banks
│   ├── screening/questions.json
│   ├── behavioral/questions.json
│   └── technical/questions.json
│
├── tests/                         # Test files
├── requirements.txt
├── render.yaml                    # Render deployment config
├── Dockerfile
├── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API Key

### Local Development

1. **Clone and setup**
```bash
cd smartsuccess-interview-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the server**
```bash
uvicorn app.main:app --reload --port 8000
```

4. **Access the API**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Deploy to Render

1. Push code to GitHub
2. Connect repository to Render
3. Set environment variables in Render dashboard:
   - `OPENAI_API_KEY`
   - `ALLOWED_ORIGINS`
4. Deploy!

## 📡 API Endpoints

### Health
- `GET /health` - Health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

### Screening Interview
- `POST /api/interview/screening/start` - Start session
- `POST /api/interview/screening/message` - Send message
- `GET /api/interview/screening/session/{id}` - Get session
- `GET /api/interview/screening/questions` - List questions

### Behavioral Interview
- `POST /api/interview/behavioral/start` - Start session
- `POST /api/interview/behavioral/message` - Send message
- `GET /api/interview/behavioral/session/{id}` - Get session
- `GET /api/interview/behavioral/star-guide` - STAR method guide

### Technical Interview
- `POST /api/interview/technical/start` - Start session
- `POST /api/interview/technical/message` - Send message
- `GET /api/interview/technical/session/{id}` - Get session
- `GET /api/interview/technical/domains` - List domains

### Voice
- `POST /api/voice/transcribe` - Audio to text
- `POST /api/voice/synthesize` - Text to audio
- `POST /api/voice/interview/{type}/voice-turn` - Full voice turn

## 📝 API Usage Example

### Start a Screening Interview

```python
import httpx

# Start session
response = httpx.post(
    "http://localhost:8000/api/interview/screening/start",
    json={
        "user_id": "user123",
        "resume_text": "Your resume text...",  # Optional
        "job_description": "Job description..."  # Optional
    }
)
data = response.json()
session_id = data["session_id"]
print(data["greeting"])

# Send response
response = httpx.post(
    "http://localhost:8000/api/interview/screening/message",
    json={
        "session_id": session_id,
        "message": "I'm a software engineer with 5 years of experience..."
    }
)
print(response.json())
```

### JavaScript/Frontend Example

```javascript
// Start behavioral interview
const startResponse = await fetch('/api/interview/behavioral/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user123',
    resume_text: resumeText,
    job_description: jobDescription
  })
});
const { session_id, greeting } = await startResponse.json();

// Send message
const messageResponse = await fetch('/api/interview/behavioral/message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: session_id,
    message: userInput
  })
});
const result = await messageResponse.json();
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `ALLOWED_ORIGINS` | Yes | localhost | CORS origins |
| `LLM_MODEL` | No | gpt-4o-mini | LLM model |
| `EMBEDDING_MODEL` | No | text-embedding-3-small | Embedding model |
| `SCREENING_MAX_QUESTIONS` | No | 5 | Max screening questions |
| `BEHAVIORAL_MAX_QUESTIONS` | No | 6 | Max behavioral questions |
| `TECHNICAL_MAX_QUESTIONS` | No | 8 | Max technical questions |

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📄 License

MIT License

---

**SmartSuccess.AI Interview Backend** - Making interview preparation smarter with AI
