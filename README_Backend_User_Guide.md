<div align="center">
<img width="1762" height="1061" alt="image" src="https://github.com/user-attachments/assets/3fa9d693-dfa0-4898-9114-bf583e888d68" />
</div>


# SmartSuccess.AI Interview Backend - User Guide

> Complete guide to setting up, running, and deploying the SmartSuccess Interview Backend API

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
- [Usage Examples](#usage-examples)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## 🎯 Overview

The SmartSuccess Interview Backend is an AI-powered mock interview platform that provides three specialized interview types:

| Interview Type | Duration | Best For |
|---------------|----------|----------|
| **Screening** | 10-15 min | First impressions, basic communication skills |
| **Behavioral** | 25-30 min | STAR method, soft skills, past experiences |
| **Technical** | 45 min | AI/ML engineering, system design, coding skills |

### What This Backend Does

- 🤖 **AI-Powered Interviews**: Uses OpenAI GPT models to conduct realistic interviews
- 📝 **RAG-Enhanced Questions**: Personalizes questions based on your resume and job description
- 🎤 **Voice Support**: Transcribe speech and synthesize responses (Whisper + TTS)
- 📊 **Real-time Feedback**: Get instant evaluation and scoring after each response
- 🎯 **Specialized Question Banks**: Pre-trained questions optimized for each interview type

---

## ✨ Features

### Core Capabilities

- ✅ **Three Interview Types**: Screening, Behavioral (STAR), and Technical
- ✅ **Resume-Based Personalization**: Questions tailored to your background
- ✅ **Voice Integration**: Full voice-to-voice interview support
- ✅ **Session Management**: Track interview progress and history
- ✅ **Feedback System**: Detailed scoring and improvement suggestions
- ✅ **RESTful API**: Easy integration with any frontend

### Interview-Specific Features

**Screening Interview**
- Quick first impression assessment
- Communication skills evaluation
- Basic fit and motivation check
- 5 questions, 10-15 minutes

**Behavioral Interview**
- STAR method (Situation, Task, Action, Result) evaluation
- Competency-based questions
- Follow-up probing questions
- 6 questions with probing, 25-30 minutes

**Technical Interview**
- AI/ML engineering topics
- System design and architecture
- Practical coding scenarios
- 8 questions across multiple domains, 45 minutes

---

## 📦 Prerequisites

Before you begin, ensure you have:

1. **Python 3.11 or higher**
   ```bash
   python3 --version  # Should be 3.11+
   ```

2. **OpenAI API Key**
   - Sign up at [OpenAI Platform](https://platform.openai.com/)
   - Create an API key in your account settings
   - Keep it secure - you'll need it for configuration

3. **Git** (for cloning the repository)
   ```bash
   git --version
   ```

4. **Virtual Environment** (recommended)
   - Python's `venv` module (included with Python 3.11+)

---

## 🚀 Quick Start

Get the backend running in 5 minutes:

```bash
# 1. Navigate to backend directory
cd smartsuccess-interview-backend

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 6. Run the server
uvicorn app.main:app --reload
```

The API will be available at:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root Endpoint**: http://localhost:8000/

---

## 📥 Installation

### Step 1: Clone the Repository

If you haven't already:

```bash
git clone https://github.com/EmmaW215/SmartSccuss_Career_Intelligence_AI.git
cd SmartSccuss_Career_Intelligence_AI/smartsuccess-interview-backend
```

### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- OpenAI (AI services)
- Pydantic (data validation)
- And other required packages

### Step 4: Verify Installation

```bash
python -c "import fastapi; print('FastAPI installed successfully')"
python -c "import openai; print('OpenAI SDK installed successfully')"
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `smartsuccess-interview-backend` directory:

```bash
cp .env.example .env
```

Then edit `.env` with your settings:

#### Required Variables

```env
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

#### Optional Configuration

```env
# Environment
ENVIRONMENT=development  # or 'production'
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000

# CORS - Comma-separated list of allowed origins
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://your-frontend-domain.com

# AI Model Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Interview Limits
SCREENING_MAX_QUESTIONS=5
SCREENING_DURATION_MINUTES=15
BEHAVIORAL_MAX_QUESTIONS=6
BEHAVIORAL_DURATION_MINUTES=30
TECHNICAL_MAX_QUESTIONS=8
TECHNICAL_DURATION_MINUTES=45

# Voice Configuration
WHISPER_MODEL=whisper-1
TTS_MODEL=tts-1
TTS_VOICE=alloy
```

### Getting Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Click **Create new secret key**
5. Copy the key and paste it in your `.env` file
6. **Important**: Never commit your `.env` file to Git!

---

## 🏃 Running the Server

### Development Mode (with auto-reload)

```bash
uvicorn app.main:app --reload --port 8000
```

The `--reload` flag enables automatic restart when you change code.

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using Python Directly

```bash
python -m app.main
```

### Check Server Status

Visit http://localhost:8000/health in your browser or:

```bash
curl http://localhost:8000/health
```

You should see:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-23T12:00:00"
}
```

---

## 📚 API Documentation

### Interactive API Docs

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive documentation where you can test endpoints directly.

### Main Endpoints

#### Health Check
```
GET /health
GET /health/ready
GET /health/live
```

#### Screening Interview
```
POST /api/interview/screening/start
POST /api/interview/screening/message
GET  /api/interview/screening/session/{session_id}
GET  /api/interview/screening/questions
```

#### Behavioral Interview
```
POST /api/interview/behavioral/start
POST /api/interview/behavioral/message
GET  /api/interview/behavioral/session/{session_id}
GET  /api/interview/behavioral/star-guide
```

#### Technical Interview
```
POST /api/interview/technical/start
POST /api/interview/technical/message
GET  /api/interview/technical/session/{session_id}
GET  /api/interview/technical/domains
```

#### Voice Services
```
POST /api/voice/transcribe
POST /api/voice/synthesize
POST /api/voice/interview/{type}/voice-turn
```

---

## 💻 Usage Examples

### Example 1: Start a Screening Interview (Python)

```python
import httpx

# Start the interview
response = httpx.post(
    "http://localhost:8000/api/interview/screening/start",
    json={
        "user_id": "user_123",
        "resume_text": "Software Engineer with 5 years of experience...",
        "job_description": "Looking for a senior software engineer..."
    }
)

data = response.json()
session_id = data["session_id"]
greeting = data["greeting"]

print(f"Session ID: {session_id}")
print(f"Interviewer: {greeting}")

# Send your response
response = httpx.post(
    "http://localhost:8000/api/interview/screening/message",
    json={
        "session_id": session_id,
        "message": "Hello! I'm excited to be here..."
    }
)

result = response.json()
print(f"Question: {result['question']}")
print(f"Feedback: {result.get('feedback', 'No feedback yet')}")
```

### Example 2: Behavioral Interview (JavaScript/Frontend)

```javascript
// Start behavioral interview
const startInterview = async () => {
  const response = await fetch('http://localhost:8000/api/interview/behavioral/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: 'user_123',
      resume_text: resumeText,
      job_description: jobDescription
    })
  });
  
  const data = await response.json();
  return data.session_id;
};

// Send message
const sendMessage = async (sessionId, message) => {
  const response = await fetch('http://localhost:8000/api/interview/behavioral/message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      message: message
    })
  });
  
  return await response.json();
};

// Usage
const sessionId = await startInterview();
const result = await sendMessage(sessionId, "In my previous role, I led a team of 5 developers...");
console.log(result.question);
```

### Example 3: Using cURL

```bash
# Start interview
curl -X POST http://localhost:8000/api/interview/screening/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "resume_text": "Software Engineer...",
    "job_description": "Looking for..."
  }'

# Send message (replace SESSION_ID)
curl -X POST http://localhost:8000/api/interview/screening/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "message": "My response to the question"
  }'
```

### Example 4: Voice Interview

```python
import httpx

# Voice turn (transcribe + get response + synthesize)
with open("audio.wav", "rb") as audio_file:
    response = httpx.post(
        "http://localhost:8000/api/voice/interview/screening/voice-turn",
        files={"audio": audio_file},
        data={
            "session_id": "your_session_id"
        }
    )
    
result = response.json()
# Returns: transcribed_text, question, audio_url
```

---

## 🚢 Deployment

### Deploy to Render

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Connect to Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `smartsuccess-interview-backend` directory

3. **Configure Build Settings**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3

4. **Set Environment Variables**
   In Render dashboard, add:
   - `OPENAI_API_KEY` = your API key
   - `ALLOWED_ORIGINS` = your frontend URLs (comma-separated)
   - `ENVIRONMENT` = production

5. **Deploy!**
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Your API will be available at: `https://your-app.onrender.com`

### Deploy with Docker

```bash
# Build image
docker build -t smartsuccess-backend .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e ALLOWED_ORIGINS=http://localhost:3000 \
  smartsuccess-backend
```

### Environment Variables for Production

Make sure to set these in your deployment platform:

```env
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=https://your-frontend.com,https://your-other-domain.com
ENVIRONMENT=production
LLM_MODEL=gpt-4o-mini
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "API key must be set" Error

**Problem**: OpenAI API key not found

**Solution**:
```bash
# Check if .env file exists
ls -la .env

# Verify API key is set
grep OPENAI_API_KEY .env

# Make sure .env is in the correct location (smartsuccess-interview-backend/)
```

#### 2. Port Already in Use

**Problem**: `Address already in use`

**Solution**:
```bash
# Use a different port
uvicorn app.main:app --port 8001

# Or kill the process using port 8000
lsof -ti:8000 | xargs kill -9
```

#### 3. Module Not Found Errors

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 4. CORS Errors

**Problem**: Frontend can't connect to backend

**Solution**:
- Add your frontend URL to `ALLOWED_ORIGINS` in `.env`
- Restart the server after changing `.env`
- Check that CORS middleware is configured correctly

#### 5. Import Errors

**Problem**: `ImportError: cannot import name 'X'`

**Solution**:
```bash
# Make sure you're in the correct directory
cd smartsuccess-interview-backend

# Check Python path
python -c "import sys; print(sys.path)"
```

### Getting Help

- Check the API docs at `/docs` endpoint
- Review error messages in server logs
- Verify all environment variables are set
- Check OpenAI API key is valid and has credits

---

## 📁 Project Structure

```
smartsuccess-interview-backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── api/                    # API routes
│   │   └── routes/
│   │       ├── health.py       # Health check endpoints
│   │       ├── screening.py    # Screening interview API
│   │       ├── behavioral.py   # Behavioral interview API
│   │       ├── technical.py    # Technical interview API
│   │       └── voice.py        # Voice services API
│   │
│   ├── core/                   # Core services
│   │   ├── embedding_service.py    # Text embeddings
│   │   ├── vector_store.py         # Vector similarity search
│   │   └── voice_service.py         # Speech-to-text & TTS
│   │
│   ├── interview/              # Interview logic
│   │   ├── base_interview.py
│   │   ├── screening_interview.py
│   │   ├── behavioral_interview.py
│   │   └── technical_interview.py
│   │
│   ├── rag/                    # RAG services
│   │   ├── base_rag.py
│   │   ├── screening_rag.py
│   │   ├── behavioral_rag.py
│   │   └── technical_rag.py
│   │
│   ├── feedback/               # Feedback generation
│   │   ├── screening_feedback.py
│   │   ├── behavioral_feedback.py
│   │   └── technical_feedback.py
│   │
│   ├── prompts/                # Prompt templates
│   │   ├── screening_prompts.py
│   │   ├── behavioral_prompts.py
│   │   └── technical_prompts.py
│   │
│   └── models/                 # Data models (Pydantic)
│
├── data/                       # Question banks
│   ├── screening/questions.json
│   ├── behavioral/questions.json
│   └── technical/questions.json
│
├── tests/                      # Test files
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── Dockerfile                  # Docker configuration
├── render.yaml                 # Render deployment config
└── README.md                   # This file
```

---

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py
```

---

## 📝 License

MIT License

---

## 🤝 Support

For issues, questions, or contributions:
- Check the [GitHub Issues](https://github.com/EmmaW215/SmartSccuss_Career_Intelligence_AI/issues)
- Review the API documentation at `/docs` endpoint
- Ensure all prerequisites are met

---

**SmartSuccess.AI Interview Backend** - Making interview preparation smarter with AI 🤖

*Last updated: January 2024*
