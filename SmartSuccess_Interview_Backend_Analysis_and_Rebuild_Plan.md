# SmartSuccess.AI Interview Backend - Analysis & Rebuild Plan

**Document Date:** January 23, 2026  
**Purpose:** Analyze existing RAG backend and plan rebuild for new SmartSccuss_Career_Intelligence_AI project

---

## Part 1: Existing Backend Analysis (Original SmartSuccess.AI)

### ✅ CONFIRMED: Pre-RAG Coding EXISTS in Original Project

Based on my analysis of your GitHub repository and past conversation history, **YES, you DO have a complete Pre-RAG system** already built in the original SmartSuccess.AI project.

### Current Backend Architecture

```
SmartSuccess.AI/
└── resume-matcher-backend/
    ├── main.py                      # FastAPI entry point
    ├── requirements.txt             # Python dependencies
    │
    ├── services/                    # ✅ COMPLETE RAG LAYER
    │   ├── __init__.py
    │   ├── embedding_service.py     # ✅ Text → Vector (xAI/OpenAI)
    │   ├── vector_store.py          # ✅ In-memory vector DB (NumPy)
    │   ├── rag_service.py           # ✅ RAG query logic
    │   ├── interview_service.py     # ✅ Interview state machine
    │   └── feedback_service.py      # ✅ STAR scoring & analysis
    │
    ├── models/                      # ✅ Data models
    │   ├── schemas.py               # Pydantic models
    │   └── feedback_models.py       # Feedback rubrics
    │
    └── prompts/                     # ✅ Prompt templates
        ├── interview_prompts.py     # Question templates
        └── feedback_prompts.py      # Scoring prompts
```

### Service Layer Summary

| Service | Status | Description |
|---------|--------|-------------|
| `EmbeddingService` | ✅ Complete | xAI → OpenAI fallback, batch processing, section-aware chunking |
| `VectorStore` | ✅ Complete | Pure NumPy cosine similarity, in-memory storage, metadata filtering |
| `RAGService` | ✅ Complete | Context building from resume/JD, technical & soft-skill retrieval |
| `InterviewService` | ✅ Complete | State machine: GREETING → MENU → SELF_INTRO/TECHNICAL/SOFT_SKILL |
| `FeedbackService` | ✅ Complete | STAR method scoring, LLM-based feedback generation |

### Current Interview State Machine

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CURRENT STATE MACHINE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   GREETING ──[ready]──► MENU ──[choice]──► SELF_INTRO ──┐              │
│                           │                              │              │
│                           ├──[choice]──► TECHNICAL ─────┤              │
│                           │                              │              │
│                           └──[choice]──► SOFT_SKILL ────┴──► MENU      │
│                                                                         │
│   Note: All sections share same prompts/questions (NOT optimized)      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 🚨 Current Limitations (Need to Fix in New Project)

1. **Single Interview Flow** - No dedicated pages for Screening/Behavioral/Technical
2. **Generic Prompts** - Same prompt templates for all interview types
3. **No Pre-trained Question Bank** - Questions generated on-the-fly only
4. **Limited Voice Support** - Basic voice integration, not optimized
5. **No Interview-Type-Specific Evaluation** - Same STAR rubric for all types

---

## Part 2: New Project Frontend Structure

### SmartSccuss_Career_Intelligence_AI (Vercel Deployed)

```
SmartSccuss_Career_Intelligence_AI/
├── components/                      # UI components
├── contexts/                        # React contexts
├── services/                        # Frontend services
├── views/                           # Page views
│   └── (Expected: ScreeningView, BehavioralView, TechnicalView)
├── App.tsx                          # Main app
├── index.tsx                        # Entry point
├── types.ts                         # TypeScript types
└── AI_Skills_Lab_Complete_Design_Plan.md
```

**Deployed URL:** https://smart-sccuss-career-intelligence-ai.vercel.app

---

## Part 3: Rebuild Plan for Three Interview Types

### 🎯 Goal: Specialized RAG + Voice for Each Interview Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│               NEW INTERVIEW ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │   SCREENING    │  │  BEHAVIORAL    │  │  TECHNICAL     │            │
│  │   INTERVIEW    │  │  INTERVIEW     │  │  INTERVIEW     │            │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘            │
│          │                   │                   │                      │
│          ▼                   ▼                   ▼                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │ Screening RAG  │  │ Behavioral RAG │  │ Technical RAG  │            │
│  │ Question Bank  │  │ Question Bank  │  │ Question Bank  │            │
│  │ (Pre-trained)  │  │ (Pre-trained)  │  │ (Pre-trained)  │            │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘            │
│          │                   │                   │                      │
│          └───────────────────┼───────────────────┘                      │
│                              │                                          │
│                              ▼                                          │
│                    ┌──────────────────┐                                 │
│                    │   Shared Core    │                                 │
│                    │  - EmbeddingService                                │
│                    │  - VectorStore                                     │
│                    │  - Voice Service                                   │
│                    │  - Session Manager                                 │
│                    └──────────────────┘                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Detailed Implementation Plan

### Phase 1: Backend Foundation Refactor (Week 1)

#### 1.1 New Project Structure

```
smartsuccess-interview-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI entry point
│   ├── config.py                        # Environment configuration
│   │
│   ├── core/                            # Core services (REUSE from original)
│   │   ├── __init__.py
│   │   ├── embedding_service.py         # ✅ REUSE & ENHANCE
│   │   ├── vector_store.py              # ✅ REUSE
│   │   └── voice_service.py             # 🆕 NEW - Whisper ASR + TTS
│   │
│   ├── interview/                       # 🆕 NEW - Interview-specific services
│   │   ├── __init__.py
│   │   ├── base_interview.py            # Base interview class
│   │   ├── screening_interview.py       # Screening-specific logic
│   │   ├── behavioral_interview.py      # Behavioral-specific logic
│   │   └── technical_interview.py       # Technical-specific logic
│   │
│   ├── rag/                             # 🆕 NEW - Specialized RAG
│   │   ├── __init__.py
│   │   ├── base_rag_service.py          # Base RAG class
│   │   ├── screening_rag.py             # Screening question bank
│   │   ├── behavioral_rag.py            # Behavioral question bank
│   │   ├── technical_rag.py             # Technical question bank
│   │   └── question_banks/              # Pre-trained question data
│   │       ├── screening_questions.json
│   │       ├── behavioral_questions.json
│   │       └── technical_questions.json
│   │
│   ├── feedback/                        # 🆕 NEW - Type-specific feedback
│   │   ├── __init__.py
│   │   ├── base_feedback.py             # Base feedback class
│   │   ├── screening_feedback.py        # First impression scoring
│   │   ├── behavioral_feedback.py       # STAR method scoring
│   │   └── technical_feedback.py        # Technical accuracy scoring
│   │
│   ├── prompts/                         # 🆕 NEW - Optimized prompts
│   │   ├── __init__.py
│   │   ├── screening_prompts.py
│   │   ├── behavioral_prompts.py
│   │   └── technical_prompts.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── question.py
│   │   └── feedback.py
│   │
│   └── api/                             # API routes
│       ├── __init__.py
│       ├── routes/
│       │   ├── screening.py
│       │   ├── behavioral.py
│       │   ├── technical.py
│       │   └── voice.py
│       └── dependencies.py
│
├── data/                                # Pre-trained question banks
│   ├── screening/
│   ├── behavioral/
│   └── technical/
│
├── requirements.txt
├── Dockerfile
└── render.yaml
```

---

### Phase 2: Pre-trained RAG Question Banks (Week 1-2)

#### 2.1 Screening Interview Question Bank

```json
// data/screening/questions.json
{
  "category": "screening",
  "purpose": "First impression assessment",
  "duration_minutes": 15,
  "questions": [
    {
      "id": "SCR-001",
      "type": "self_introduction",
      "question": "Tell me about yourself.",
      "evaluation_criteria": ["communication_clarity", "relevance", "confidence"],
      "follow_ups": [
        "What aspects of your background are most relevant to this role?",
        "How would you summarize your career journey in one sentence?"
      ],
      "difficulty": "basic"
    },
    {
      "id": "SCR-002",
      "type": "motivation",
      "question": "Why are you interested in this role?",
      "evaluation_criteria": ["company_research", "role_understanding", "enthusiasm"],
      "follow_ups": [
        "What specifically about our company attracted you?",
        "How does this role align with your career goals?"
      ],
      "difficulty": "basic"
    },
    {
      "id": "SCR-003",
      "type": "transition",
      "question": "Why did you leave (or are considering leaving) your last job?",
      "evaluation_criteria": ["professionalism", "honesty", "growth_mindset"],
      "follow_ups": [
        "What would have made you stay longer?",
        "What did you learn from that experience?"
      ],
      "difficulty": "intermediate"
    },
    {
      "id": "SCR-004",
      "type": "fit_assessment",
      "question": "Why do you think you are the best fit for this role?",
      "evaluation_criteria": ["self_awareness", "skill_matching", "value_proposition"],
      "follow_ups": [
        "What unique skills do you bring that others might not?",
        "How would you describe your working style?"
      ],
      "difficulty": "intermediate"
    },
    {
      "id": "SCR-005",
      "type": "situational",
      "question": "What would you do if you were assigned a task you've never done before?",
      "evaluation_criteria": ["problem_solving", "resourcefulness", "adaptability"],
      "follow_ups": [
        "Can you give an example of when this happened?",
        "How do you typically approach learning new skills?"
      ],
      "difficulty": "intermediate"
    }
  ],
  "evaluation_rubric": {
    "communication_skills": {
      "weight": 0.3,
      "criteria": ["clarity", "conciseness", "confidence"]
    },
    "basic_fit": {
      "weight": 0.3,
      "criteria": ["role_understanding", "motivation", "availability"]
    },
    "judgment": {
      "weight": 0.2,
      "criteria": ["practical_thinking", "values_alignment"]
    },
    "first_impression": {
      "weight": 0.2,
      "criteria": ["professionalism", "enthusiasm", "preparation"]
    }
  }
}
```

#### 2.2 Behavioral Interview Question Bank

```json
// data/behavioral/questions.json
{
  "category": "behavioral",
  "purpose": "Assess soft skills and past behavior",
  "duration_minutes": 30,
  "method": "STAR",
  "question_categories": {
    "teamwork": [
      {
        "id": "BEH-TW-001",
        "question": "Tell me about a challenge you faced working in a team.",
        "star_prompts": {
          "situation": "Describe the team context and the challenge",
          "task": "What was your specific role and responsibility?",
          "action": "What steps did you take to address the challenge?",
          "result": "What was the outcome and what did you learn?"
        },
        "evaluation_criteria": ["collaboration", "conflict_resolution", "communication"],
        "difficulty": "intermediate"
      },
      {
        "id": "BEH-TW-002",
        "question": "How do you handle people conflict in a team?",
        "star_prompts": {
          "situation": "Describe a specific conflict situation",
          "task": "What role did you play in resolving it?",
          "action": "What specific steps did you take?",
          "result": "How was the conflict resolved?"
        },
        "evaluation_criteria": ["emotional_intelligence", "diplomacy", "problem_solving"],
        "difficulty": "advanced"
      }
    ],
    "problem_solving": [
      {
        "id": "BEH-PS-001",
        "question": "Describe a time when you had to solve a complex problem with limited information.",
        "star_prompts": {
          "situation": "What was the problem and what information was missing?",
          "task": "What was expected of you?",
          "action": "How did you gather information and approach the solution?",
          "result": "What was the outcome?"
        },
        "evaluation_criteria": ["analytical_thinking", "resourcefulness", "decision_making"],
        "difficulty": "advanced"
      }
    ],
    "leadership": [
      {
        "id": "BEH-LD-001",
        "question": "Tell me about a time you led a project or initiative.",
        "star_prompts": {
          "situation": "What was the project context?",
          "task": "What was your leadership role?",
          "action": "How did you lead the team?",
          "result": "What were the outcomes?"
        },
        "evaluation_criteria": ["initiative", "influence", "accountability"],
        "difficulty": "advanced"
      }
    ],
    "deadline_management": [
      {
        "id": "BEH-DL-001",
        "question": "How would you handle a deadline conflict in a project?",
        "star_prompts": {
          "situation": "Describe a situation with conflicting deadlines",
          "task": "What was at stake?",
          "action": "How did you prioritize and manage?",
          "result": "What was the outcome?"
        },
        "evaluation_criteria": ["prioritization", "time_management", "stakeholder_communication"],
        "difficulty": "intermediate"
      }
    ],
    "product_ownership": [
      {
        "id": "BEH-PO-001",
        "question": "What approach would you take on Product Ownership in an Agile environment?",
        "follow_up_topics": ["backlog_management", "stakeholder_alignment", "sprint_planning"],
        "evaluation_criteria": ["agile_knowledge", "prioritization", "customer_focus"],
        "difficulty": "advanced"
      }
    ]
  },
  "evaluation_rubric": {
    "star_method_adherence": {
      "weight": 0.25,
      "scoring": {
        "5": "All STAR components clearly addressed",
        "4": "Most components addressed with minor gaps",
        "3": "Some components missing or unclear",
        "2": "Major gaps in structure",
        "1": "No STAR structure followed"
      }
    },
    "teamwork": {
      "weight": 0.2,
      "criteria": ["collaboration", "conflict_resolution", "communication"]
    },
    "problem_solving": {
      "weight": 0.2,
      "criteria": ["analytical_thinking", "creativity", "decision_making"]
    },
    "leadership_attitude": {
      "weight": 0.2,
      "criteria": ["initiative", "accountability", "influence"]
    },
    "logic_structure": {
      "weight": 0.15,
      "criteria": ["coherence", "completeness", "relevance"]
    }
  }
}
```

#### 2.3 Technical Interview Question Bank

```json
// data/technical/questions.json
{
  "category": "technical",
  "purpose": "Assess technical skills and knowledge",
  "duration_minutes": 45,
  "domains": {
    "ai_engineering": [
      {
        "id": "TECH-AI-001",
        "question": "Would you consider yourself an expert-level Python engineer? Can you share examples of complex systems you've built with Python?",
        "expected_topics": ["architecture", "scalability", "best_practices"],
        "evaluation_criteria": ["depth_of_knowledge", "practical_experience", "code_quality"],
        "difficulty": "intermediate"
      },
      {
        "id": "TECH-AI-002",
        "question": "Which agent or LLM frameworks have you used? (LangChain, LangGraph, LlamaIndex, AutoGen, CrewAI)",
        "expected_topics": ["framework_comparison", "use_cases", "limitations"],
        "evaluation_criteria": ["breadth_of_experience", "framework_understanding", "practical_application"],
        "difficulty": "intermediate"
      },
      {
        "id": "TECH-AI-003",
        "question": "Have you built or worked with LLM-based autonomous agents before? Can you briefly describe one example?",
        "expected_topics": ["agent_architecture", "tool_calling", "memory_management"],
        "evaluation_criteria": ["hands_on_experience", "system_design", "problem_solving"],
        "difficulty": "advanced"
      }
    ],
    "system_architecture": [
      {
        "id": "TECH-SA-001",
        "question": "Walk through the architecture of a RAG or GenAI system you designed. How did data ingestion, embedding, vector storage, retrieval, and generation work end to end?",
        "expected_topics": ["data_pipeline", "embedding_strategy", "retrieval_optimization", "generation_quality"],
        "evaluation_criteria": ["system_thinking", "technical_depth", "trade_off_analysis"],
        "difficulty": "advanced"
      },
      {
        "id": "TECH-SA-002",
        "question": "Have you implemented authentication, access control, or security mechanisms for AI/ML systems or agent workflows?",
        "expected_topics": ["security_patterns", "authorization", "data_protection"],
        "evaluation_criteria": ["security_awareness", "implementation_experience", "best_practices"],
        "difficulty": "intermediate"
      }
    ],
    "ml_production": [
      {
        "id": "TECH-ML-001",
        "question": "Describe a machine learning system you built and operated in production. What was your role across the full lifecycle—from data ingestion and model training to deployment, monitoring, and iteration?",
        "expected_topics": ["mlops", "monitoring", "model_versioning", "deployment"],
        "evaluation_criteria": ["end_to_end_experience", "operational_maturity", "problem_solving"],
        "difficulty": "advanced"
      },
      {
        "id": "TECH-ML-002",
        "question": "How have you designed and managed data pipelines for large, noisy, real-world datasets? How did you handle missing data, outliers, schema consistency, and data validation?",
        "expected_topics": ["data_quality", "pipeline_design", "error_handling"],
        "evaluation_criteria": ["data_engineering_skills", "robustness", "scalability"],
        "difficulty": "advanced"
      }
    ],
    "cloud_deployment": [
      {
        "id": "TECH-CD-001",
        "question": "What is your hands-on experience deploying and operating ML systems on cloud platforms? Which services did you use, and why?",
        "expected_topics": ["GCP", "AWS", "Azure", "service_selection", "cost_optimization"],
        "evaluation_criteria": ["cloud_expertise", "service_knowledge", "practical_decisions"],
        "difficulty": "intermediate"
      }
    ],
    "debugging_troubleshooting": [
      {
        "id": "TECH-DB-001",
        "question": "Recount a time when a deployed model failed to meet expectations in production. What was your root-cause analysis process, and what steps did you take to diagnose and implement the final fix?",
        "expected_topics": ["debugging_methodology", "monitoring", "iteration"],
        "evaluation_criteria": ["problem_solving", "systematic_approach", "learning_from_failure"],
        "difficulty": "advanced"
      }
    ],
    "concept_explanation": [
      {
        "id": "TECH-CE-001",
        "question": "Explain how Agentic Workflows work and when you would use them.",
        "key_concepts": ["agent_coordination", "tool_use", "planning", "execution"],
        "difficulty": "intermediate"
      },
      {
        "id": "TECH-CE-002",
        "question": "Explain how RAG Architecture works and its key components.",
        "key_concepts": ["retrieval", "augmentation", "generation", "vector_db"],
        "difficulty": "intermediate"
      },
      {
        "id": "TECH-CE-003",
        "question": "Explain how MCP (Model Context Protocol) works.",
        "key_concepts": ["context_management", "protocol_design", "integration"],
        "difficulty": "advanced"
      }
    ]
  },
  "evaluation_rubric": {
    "technical_accuracy": {
      "weight": 0.35,
      "criteria": ["correctness", "depth", "precision"]
    },
    "practical_experience": {
      "weight": 0.25,
      "criteria": ["hands_on_examples", "real_world_application", "lessons_learned"]
    },
    "system_thinking": {
      "weight": 0.20,
      "criteria": ["architecture_understanding", "trade_offs", "scalability"]
    },
    "communication_clarity": {
      "weight": 0.20,
      "criteria": ["explanation_quality", "structure", "technical_vocabulary"]
    }
  }
}
```

---

### Phase 3: Specialized Interview Services (Week 2)

#### 3.1 Base Interview Class (Reusable)

```python
# app/interview/base_interview.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class InterviewPhase(Enum):
    NOT_STARTED = "not_started"
    GREETING = "greeting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@dataclass
class InterviewSession:
    session_id: str
    user_id: str
    interview_type: str  # "screening", "behavioral", "technical"
    phase: InterviewPhase = InterviewPhase.NOT_STARTED
    current_question_index: int = 0
    messages: List[Dict] = field(default_factory=list)
    questions_asked: List[str] = field(default_factory=list)
    responses: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Optional context from MatchWise
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    matchwise_analysis: Optional[Dict] = None

class BaseInterviewService(ABC):
    """Base class for all interview types"""
    
    def __init__(self, rag_service, voice_service, feedback_service):
        self.rag_service = rag_service
        self.voice_service = voice_service
        self.feedback_service = feedback_service
        self.sessions: Dict[str, InterviewSession] = {}
    
    @abstractmethod
    async def get_greeting(self) -> str:
        """Return interview-type-specific greeting"""
        pass
    
    @abstractmethod
    async def get_next_question(self, session: InterviewSession) -> str:
        """Get next question based on interview type and context"""
        pass
    
    @abstractmethod
    async def evaluate_response(self, session: InterviewSession, response: str) -> Dict:
        """Evaluate response using type-specific criteria"""
        pass
    
    @abstractmethod
    def get_duration_limit(self) -> int:
        """Return interview duration in minutes"""
        pass
    
    async def create_session(self, user_id: str, **kwargs) -> InterviewSession:
        """Create a new interview session"""
        session_id = f"{self.interview_type}_{user_id}_{datetime.utcnow().timestamp()}"
        session = InterviewSession(
            session_id=session_id,
            user_id=user_id,
            interview_type=self.interview_type,
            resume_text=kwargs.get("resume_text"),
            job_description=kwargs.get("job_description"),
            matchwise_analysis=kwargs.get("matchwise_analysis")
        )
        self.sessions[session_id] = session
        return session
    
    async def process_message(self, session_id: str, user_message: str) -> Dict:
        """Process user message and return response"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Record user message
        session.messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Evaluate response
        evaluation = await self.evaluate_response(session, user_message)
        session.responses.append({
            "question_index": session.current_question_index,
            "response": user_message,
            "evaluation": evaluation
        })
        
        # Get next question or complete
        session.current_question_index += 1
        
        if self._should_complete(session):
            session.phase = InterviewPhase.COMPLETED
            session.completed_at = datetime.utcnow()
            return {
                "type": "completion",
                "message": await self._get_completion_message(session),
                "summary": await self.feedback_service.generate_session_summary(session)
            }
        
        next_question = await self.get_next_question(session)
        session.questions_asked.append(next_question)
        session.messages.append({
            "role": "assistant",
            "content": next_question,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "type": "question",
            "message": next_question,
            "question_number": session.current_question_index,
            "evaluation": evaluation
        }
    
    def _should_complete(self, session: InterviewSession) -> bool:
        """Check if interview should complete"""
        max_questions = self._get_max_questions()
        return session.current_question_index >= max_questions
    
    @abstractmethod
    def _get_max_questions(self) -> int:
        """Return max questions for this interview type"""
        pass
    
    @abstractmethod
    async def _get_completion_message(self, session: InterviewSession) -> str:
        """Return interview-specific completion message"""
        pass
```

#### 3.2 Screening Interview Service

```python
# app/interview/screening_interview.py

from .base_interview import BaseInterviewService, InterviewSession

class ScreeningInterviewService(BaseInterviewService):
    """
    Screening Interview - First Impression Assessment
    Duration: 10-20 minutes
    Focus: Self-introduction, motivation, basic fit
    """
    
    interview_type = "screening"
    
    async def get_greeting(self) -> str:
        return """Welcome to your Screening Interview! 🎯

I'm your AI interviewer today. This is a brief 10-15 minute conversation where I'll get to know you better and understand your interest in this role.

We'll cover:
• A quick self-introduction
• Your motivation for this role
• Why you're the right fit

Remember, this is like a first conversation - be yourself and speak naturally!

Let's begin. Please tell me about yourself."""

    async def get_next_question(self, session: InterviewSession) -> str:
        # Use RAG to get personalized questions if resume/JD available
        if session.resume_text or session.job_description:
            return await self.rag_service.get_personalized_screening_question(
                session, 
                session.current_question_index
            )
        
        # Fallback to pre-trained questions
        return await self.rag_service.get_screening_question(
            session.current_question_index
        )
    
    async def evaluate_response(self, session: InterviewSession, response: str) -> Dict:
        return await self.feedback_service.evaluate_screening_response(
            question=session.questions_asked[-1] if session.questions_asked else "Tell me about yourself",
            response=response,
            criteria=["communication_clarity", "relevance", "confidence", "professionalism"]
        )
    
    def get_duration_limit(self) -> int:
        return 15  # 15 minutes
    
    def _get_max_questions(self) -> int:
        return 5  # 5 screening questions
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        return """Thank you for completing the Screening Interview! 🎉

You've given me a great first impression. I've noted your background, motivation, and how you'd fit with this role.

Your feedback summary is being prepared. In a real interview process, this would be the first step before moving to behavioral or technical rounds.

Great job!"""
```

#### 3.3 Behavioral Interview Service

```python
# app/interview/behavioral_interview.py

from .base_interview import BaseInterviewService, InterviewSession

class BehavioralInterviewService(BaseInterviewService):
    """
    Behavioral Interview - STAR Method Assessment
    Duration: 25-30 minutes
    Focus: Past behavior as predictor of future performance
    """
    
    interview_type = "behavioral"
    
    STAR_FOLLOW_UPS = {
        "situation": "Can you describe the specific situation or context in more detail?",
        "task": "What exactly was your role and responsibility in this situation?",
        "action": "What specific actions did you take? Walk me through the steps.",
        "result": "What was the outcome? How did you measure success?"
    }
    
    async def get_greeting(self) -> str:
        return """Welcome to your Behavioral Interview! 💼

This is a 25-30 minute session where we'll explore how you've handled real situations in the past.

I'll be using the STAR method:
• **S**ituation - Describe the context
• **T**ask - Explain your responsibility  
• **A**ction - Detail what you did
• **R**esult - Share the outcome

Tips for success:
✓ Use specific examples from your experience
✓ Focus on YOUR actions, not the team's
✓ Quantify results when possible

Let's start with a teamwork question:

Tell me about a challenge you faced working in a team. How did you handle it?"""

    async def get_next_question(self, session: InterviewSession) -> str:
        # Check if we need STAR follow-up
        if self._needs_star_followup(session):
            missing_component = self._get_missing_star_component(session)
            return self.STAR_FOLLOW_UPS.get(missing_component, await self._get_new_question(session))
        
        return await self._get_new_question(session)
    
    async def _get_new_question(self, session: InterviewSession) -> str:
        if session.resume_text or session.job_description:
            return await self.rag_service.get_personalized_behavioral_question(
                session,
                session.current_question_index
            )
        return await self.rag_service.get_behavioral_question(
            session.current_question_index
        )
    
    def _needs_star_followup(self, session: InterviewSession) -> bool:
        if not session.responses:
            return False
        last_eval = session.responses[-1].get("evaluation", {})
        star_scores = last_eval.get("star_breakdown", {})
        return any(score < 3 for score in star_scores.values())
    
    def _get_missing_star_component(self, session: InterviewSession) -> str:
        if not session.responses:
            return "situation"
        last_eval = session.responses[-1].get("evaluation", {})
        star_scores = last_eval.get("star_breakdown", {})
        for component in ["situation", "task", "action", "result"]:
            if star_scores.get(component, 5) < 3:
                return component
        return "action"  # Default
    
    async def evaluate_response(self, session: InterviewSession, response: str) -> Dict:
        return await self.feedback_service.evaluate_behavioral_response(
            question=session.questions_asked[-1] if session.questions_asked else "",
            response=response,
            star_method=True
        )
    
    def get_duration_limit(self) -> int:
        return 30  # 30 minutes
    
    def _get_max_questions(self) -> int:
        return 6  # 6 behavioral questions with potential follow-ups
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        return """Excellent! You've completed the Behavioral Interview! 🌟

I've assessed your responses using the STAR method across several competency areas:
• Teamwork & Collaboration
• Problem-Solving
• Leadership & Initiative
• Communication

Your detailed feedback with STAR scores is being generated. 

In a real interview, your specific examples and the way you structured your answers would be key factors in the evaluation.

Well done!"""
```

#### 3.4 Technical Interview Service

```python
# app/interview/technical_interview.py

from .base_interview import BaseInterviewService, InterviewSession

class TechnicalInterviewService(BaseInterviewService):
    """
    Technical Interview - Skills Assessment
    Duration: 45-60 minutes
    Focus: Technical knowledge, problem-solving, system design
    """
    
    interview_type = "technical"
    
    # Technical domains to cover
    DOMAINS = [
        "ai_engineering",
        "system_architecture", 
        "ml_production",
        "cloud_deployment",
        "debugging_troubleshooting",
        "concept_explanation"
    ]
    
    async def get_greeting(self) -> str:
        return """Welcome to your Technical Interview! 🔧

This is a 45-minute deep-dive into your technical skills and experience.

We'll cover:
• AI/ML Engineering concepts
• System architecture and design
• Production ML experience
• Cloud deployment
• Problem-solving and debugging

Feel free to:
✓ Ask clarifying questions
✓ Think out loud
✓ Draw on your real project experience
✓ Discuss trade-offs and alternatives

Let's start:

Would you consider yourself an expert-level Python engineer? Can you share examples of complex systems you've built with Python?"""

    async def get_next_question(self, session: InterviewSession) -> str:
        # Rotate through technical domains
        domain_index = session.current_question_index % len(self.DOMAINS)
        current_domain = self.DOMAINS[domain_index]
        
        if session.resume_text or session.matchwise_analysis:
            # Personalized questions based on resume skills
            return await self.rag_service.get_personalized_technical_question(
                session,
                domain=current_domain,
                skills=self._extract_skills(session)
            )
        
        return await self.rag_service.get_technical_question(
            domain=current_domain,
            question_index=session.current_question_index
        )
    
    def _extract_skills(self, session: InterviewSession) -> List[str]:
        if session.matchwise_analysis:
            return session.matchwise_analysis.get("matched_skills", [])
        return []
    
    async def evaluate_response(self, session: InterviewSession, response: str) -> Dict:
        return await self.feedback_service.evaluate_technical_response(
            question=session.questions_asked[-1] if session.questions_asked else "",
            response=response,
            domain=self.DOMAINS[session.current_question_index % len(self.DOMAINS)],
            criteria=["technical_accuracy", "depth", "practical_experience", "communication"]
        )
    
    def get_duration_limit(self) -> int:
        return 45  # 45 minutes
    
    def _get_max_questions(self) -> int:
        return 8  # 8 technical questions
    
    async def _get_completion_message(self, session: InterviewSession) -> str:
        return """You've completed the Technical Interview! 🚀

I've assessed your technical abilities across:
• AI/ML Engineering
• System Architecture
• Production Experience
• Cloud Deployment
• Problem-Solving

Your detailed technical scorecard is being generated, including:
- Technical accuracy ratings
- Depth of knowledge assessment
- Practical experience evaluation
- Areas for improvement

Great technical discussion!"""
```

---

### Phase 4: Optimized Prompts for Each Interview Type (Week 2-3)

#### 4.1 Screening Interview Prompts

```python
# app/prompts/screening_prompts.py

SCREENING_SYSTEM_PROMPT = """You are an experienced HR screening interviewer conducting a brief 10-15 minute phone screen.

Your role:
- Assess first impressions and communication skills
- Understand candidate's motivation and basic fit
- Keep questions conversational and approachable
- Evaluate professionalism and enthusiasm

Interview style:
- Friendly but professional
- Ask follow-up questions when answers are vague
- Keep answers focused (1-2 minutes ideal)
- Note any red flags diplomatically

You are NOT testing technical skills - that comes later.
Focus on: Communication, Motivation, Basic Fit, Professionalism
"""

SCREENING_QUESTION_GENERATION = """Based on the candidate's resume and job description, generate a relevant screening question.

Resume highlights: {resume_summary}
Job requirements: {job_requirements}
Questions already asked: {asked_questions}

Generate ONE screening question that:
1. Is appropriate for a 10-15 minute phone screen
2. Assesses communication skills or motivation
3. Is NOT deeply technical
4. Builds on previous conversation naturally

Question:"""

SCREENING_EVALUATION_PROMPT = """Evaluate this screening interview response.

Question: {question}
Response: {response}

Evaluate on these criteria (1-5 scale):
1. Communication Clarity - How clearly did they express themselves?
2. Relevance - Did they answer the question directly?
3. Confidence - Did they sound confident without being arrogant?
4. Professionalism - Was the tone appropriate?
5. Enthusiasm - Did they show genuine interest?

Provide:
- Scores for each criterion
- One strength observed
- One area for improvement
- Overall first impression (Positive/Neutral/Concerning)

Response format (JSON):
{
  "scores": {...},
  "strength": "...",
  "improvement": "...",
  "first_impression": "..."
}"""
```

#### 4.2 Behavioral Interview Prompts

```python
# app/prompts/behavioral_prompts.py

BEHAVIORAL_SYSTEM_PROMPT = """You are an expert behavioral interviewer using the STAR method.

Your role:
- Assess past behavior as a predictor of future performance
- Probe for specific examples and details
- Evaluate competencies: teamwork, problem-solving, leadership, communication
- Guide candidates to provide complete STAR responses

STAR Method:
- Situation: Context and background
- Task: Candidate's specific responsibility
- Action: What they specifically did (not the team)
- Result: Outcome with metrics if possible

Interview techniques:
- Use follow-up questions to complete incomplete STAR responses
- Probe for "I" statements (what THEY did, not "we")
- Ask for quantifiable results when possible
- Note if candidate takes accountability vs. blames others
"""

BEHAVIORAL_STAR_EVALUATION = """Evaluate this behavioral interview response using STAR method.

Question: {question}
Response: {response}

STAR Analysis (1-5 for each component):

1. Situation (1-5):
   - Was the context clearly described?
   - Was it a real, specific example?
   
2. Task (1-5):
   - Was their role clearly defined?
   - Did they own the responsibility?

3. Action (1-5):
   - Did they describe THEIR specific actions?
   - Were the steps logical and detailed?
   - Did they say "I" not just "we"?

4. Result (1-5):
   - Was there a clear outcome?
   - Were results quantified if possible?
   - Did they reflect on learnings?

Competency Assessment:
- Primary competency demonstrated: 
- Secondary competency:
- Missing competency indicator:

Response format (JSON):
{
  "star_breakdown": {
    "situation": {"score": X, "notes": "..."},
    "task": {"score": X, "notes": "..."},
    "action": {"score": X, "notes": "..."},
    "result": {"score": X, "notes": "..."}
  },
  "overall_star_score": X,
  "competencies": {...},
  "strengths": [...],
  "growth_areas": [...],
  "follow_up_needed": "situation|task|action|result|none"
}"""

BEHAVIORAL_FOLLOWUP_PROMPT = """The candidate's response was missing the {missing_component} component.

Original question: {question}
Their response: {response}

Generate a natural follow-up question to elicit the {missing_component}:
- For 'situation': Ask for more context/background
- For 'task': Ask what specifically was their responsibility
- For 'action': Ask what specific steps THEY took
- For 'result': Ask about the outcome and impact

Follow-up question:"""
```

#### 4.3 Technical Interview Prompts

```python
# app/prompts/technical_prompts.py

TECHNICAL_SYSTEM_PROMPT = """You are a senior technical interviewer assessing AI/ML engineering candidates.

Your role:
- Assess technical depth and breadth
- Evaluate practical, hands-on experience
- Test system design and architecture thinking
- Understand problem-solving approach

Domains to cover:
1. AI/ML Engineering (LLMs, RAG, Agents, Fine-tuning)
2. System Architecture (Scalability, Design patterns)
3. Production ML (MLOps, Monitoring, Deployment)
4. Cloud Platforms (GCP, AWS, Azure)
5. Data Engineering (Pipelines, Quality, ETL)

Interview approach:
- Start with experience-based questions
- Probe deeper on interesting points
- Ask "why" behind technical decisions
- Discuss trade-offs and alternatives
- Allow candidates to think aloud
"""

TECHNICAL_QUESTION_GENERATION = """Generate a technical interview question for this AI/ML engineering candidate.

Domain: {domain}
Candidate skills from resume: {skills}
Difficulty level: {difficulty}
Questions already asked: {asked_questions}

The question should:
1. Be specific to the domain
2. Allow candidate to draw from their experience
3. Test both knowledge and practical application
4. Have follow-up potential

Question:"""

TECHNICAL_EVALUATION_PROMPT = """Evaluate this technical interview response.

Domain: {domain}
Question: {question}
Response: {response}

Evaluation criteria (1-5 scale):

1. Technical Accuracy (1-5):
   - Are the facts and concepts correct?
   - Any misconceptions or errors?

2. Depth of Knowledge (1-5):
   - Surface-level or deep understanding?
   - Can they explain the "why" behind concepts?

3. Practical Experience (1-5):
   - Did they reference real projects?
   - Do examples sound authentic?

4. System Thinking (1-5):
   - Do they consider trade-offs?
   - Can they see the bigger picture?

5. Communication Clarity (1-5):
   - Can they explain complex concepts clearly?
   - Is the answer structured?

Response format (JSON):
{
  "scores": {
    "technical_accuracy": {"score": X, "notes": "..."},
    "depth_of_knowledge": {"score": X, "notes": "..."},
    "practical_experience": {"score": X, "notes": "..."},
    "system_thinking": {"score": X, "notes": "..."},
    "communication_clarity": {"score": X, "notes": "..."}
  },
  "overall_technical_score": X,
  "key_strengths": [...],
  "knowledge_gaps": [...],
  "follow_up_topics": [...],
  "hire_signal": "strong|moderate|weak|no"
}"""
```

---

### Phase 5: Voice Integration Enhancement (Week 3)

#### 5.1 Voice Service (Reuse + Enhance)

```python
# app/core/voice_service.py

import os
from typing import Optional, Tuple
from openai import AsyncOpenAI
import httpx

class VoiceService:
    """
    Voice service for speech-to-text and text-to-speech
    Uses Whisper for ASR and OpenAI TTS
    """
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.whisper_model = "whisper-1"
        self.tts_model = "tts-1"
        self.tts_voice = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
    
    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """
        Transcribe audio to text using Whisper
        
        Args:
            audio_data: Audio file bytes (mp3, wav, webm, etc.)
            language: ISO language code
        
        Returns:
            Transcribed text
        """
        try:
            transcript = await self.openai_client.audio.transcriptions.create(
                model=self.whisper_model,
                file=("audio.webm", audio_data, "audio/webm"),
                language=language,
                response_format="text"
            )
            return transcript.strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            raise
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesize text to speech using OpenAI TTS
        
        Args:
            text: Text to synthesize
            voice: Voice option (default: alloy)
        
        Returns:
            Audio bytes (mp3 format)
        """
        try:
            response = await self.openai_client.audio.speech.create(
                model=self.tts_model,
                voice=voice or self.tts_voice,
                input=text
            )
            return response.content
        except Exception as e:
            print(f"TTS error: {e}")
            raise
    
    async def transcribe_and_respond(
        self, 
        audio_data: bytes,
        process_callback,  # Function to process transcribed text
        language: str = "en"
    ) -> Tuple[str, str, bytes]:
        """
        Full voice pipeline: transcribe → process → synthesize
        
        Returns:
            (transcribed_text, response_text, response_audio)
        """
        # Step 1: Transcribe user audio
        user_text = await self.transcribe(audio_data, language)
        
        # Step 2: Process the text (interview service callback)
        response_text = await process_callback(user_text)
        
        # Step 3: Synthesize response
        response_audio = await self.synthesize(response_text)
        
        return user_text, response_text, response_audio
```

---

### Phase 6: API Routes (Week 3)

```python
# app/api/routes/interview_routes.py

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io

from app.interview.screening_interview import ScreeningInterviewService
from app.interview.behavioral_interview import BehavioralInterviewService
from app.interview.technical_interview import TechnicalInterviewService
from app.core.voice_service import VoiceService

router = APIRouter(prefix="/api/interview", tags=["interview"])

# Request/Response models
class StartSessionRequest(BaseModel):
    user_id: str
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    matchwise_analysis: Optional[dict] = None

class MessageRequest(BaseModel):
    session_id: str
    message: str

class SessionResponse(BaseModel):
    session_id: str
    greeting: str
    interview_type: str

# Dependency injection for services
def get_screening_service():
    return ScreeningInterviewService(...)

def get_behavioral_service():
    return BehavioralInterviewService(...)

def get_technical_service():
    return TechnicalInterviewService(...)

def get_voice_service():
    return VoiceService()

# ==================== SCREENING INTERVIEW ====================

@router.post("/screening/start", response_model=SessionResponse)
async def start_screening_interview(
    request: StartSessionRequest,
    service: ScreeningInterviewService = Depends(get_screening_service)
):
    """Start a new screening interview session"""
    session = await service.create_session(
        user_id=request.user_id,
        resume_text=request.resume_text,
        job_description=request.job_description
    )
    greeting = await service.get_greeting()
    
    return SessionResponse(
        session_id=session.session_id,
        greeting=greeting,
        interview_type="screening"
    )

@router.post("/screening/message")
async def screening_message(
    request: MessageRequest,
    service: ScreeningInterviewService = Depends(get_screening_service)
):
    """Process a message in screening interview"""
    return await service.process_message(request.session_id, request.message)

# ==================== BEHAVIORAL INTERVIEW ====================

@router.post("/behavioral/start", response_model=SessionResponse)
async def start_behavioral_interview(
    request: StartSessionRequest,
    service: BehavioralInterviewService = Depends(get_behavioral_service)
):
    """Start a new behavioral interview session"""
    session = await service.create_session(
        user_id=request.user_id,
        resume_text=request.resume_text,
        job_description=request.job_description
    )
    greeting = await service.get_greeting()
    
    return SessionResponse(
        session_id=session.session_id,
        greeting=greeting,
        interview_type="behavioral"
    )

@router.post("/behavioral/message")
async def behavioral_message(
    request: MessageRequest,
    service: BehavioralInterviewService = Depends(get_behavioral_service)
):
    """Process a message in behavioral interview"""
    return await service.process_message(request.session_id, request.message)

# ==================== TECHNICAL INTERVIEW ====================

@router.post("/technical/start", response_model=SessionResponse)
async def start_technical_interview(
    request: StartSessionRequest,
    service: TechnicalInterviewService = Depends(get_technical_service)
):
    """Start a new technical interview session"""
    session = await service.create_session(
        user_id=request.user_id,
        resume_text=request.resume_text,
        job_description=request.job_description,
        matchwise_analysis=request.matchwise_analysis
    )
    greeting = await service.get_greeting()
    
    return SessionResponse(
        session_id=session.session_id,
        greeting=greeting,
        interview_type="technical"
    )

@router.post("/technical/message")
async def technical_message(
    request: MessageRequest,
    service: TechnicalInterviewService = Depends(get_technical_service)
):
    """Process a message in technical interview"""
    return await service.process_message(request.session_id, request.message)

# ==================== VOICE ENDPOINTS ====================

@router.post("/voice/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    voice_service: VoiceService = Depends(get_voice_service)
):
    """Transcribe audio to text"""
    audio_data = await audio.read()
    text = await voice_service.transcribe(audio_data)
    return {"text": text}

@router.post("/voice/synthesize")
async def synthesize_speech(
    text: str,
    voice: Optional[str] = "alloy",
    voice_service: VoiceService = Depends(get_voice_service)
):
    """Synthesize text to speech"""
    audio_data = await voice_service.synthesize(text, voice)
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=response.mp3"}
    )

@router.post("/{interview_type}/voice")
async def voice_interview_turn(
    interview_type: str,
    session_id: str,
    audio: UploadFile = File(...),
    voice_service: VoiceService = Depends(get_voice_service)
):
    """
    Full voice interview turn:
    1. Transcribe user audio
    2. Process through interview service
    3. Synthesize response
    4. Return both text and audio
    """
    # Get appropriate service
    service_map = {
        "screening": get_screening_service(),
        "behavioral": get_behavioral_service(),
        "technical": get_technical_service()
    }
    service = service_map.get(interview_type)
    if not service:
        raise HTTPException(status_code=400, detail=f"Unknown interview type: {interview_type}")
    
    # Process voice turn
    audio_data = await audio.read()
    
    async def process_callback(text: str):
        result = await service.process_message(session_id, text)
        return result.get("message", "")
    
    user_text, response_text, response_audio = await voice_service.transcribe_and_respond(
        audio_data, process_callback
    )
    
    return {
        "user_transcript": user_text,
        "assistant_response": response_text,
        "audio_url": f"/api/interview/audio/{session_id}/latest"  # Or return base64
    }
```

---

## Part 5: Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| **Week 1** | Foundation | New project structure, Core services migrated, Question banks created |
| **Week 2** | Interview Services | 3 interview services implemented, Specialized RAG for each type |
| **Week 3** | Prompts & Voice | Optimized prompts, Voice integration, API routes |
| **Week 4** | Integration & Testing | Frontend integration, End-to-end testing, Deploy to Render |

---

## Part 6: What to REUSE vs BUILD NEW

### ✅ REUSE from Original SmartSuccess.AI

| Component | Status | Notes |
|-----------|--------|-------|
| `embedding_service.py` | Reuse 90% | Add batch processing optimization |
| `vector_store.py` | Reuse 100% | Works well for session-based storage |
| `feedback_service.py` | Reuse 70% | Add type-specific evaluation methods |
| Voice integration pattern | Reuse 80% | Enhance with streaming |

### 🆕 BUILD NEW

| Component | Reason |
|-----------|--------|
| Interview type classes | Need specialized logic for each type |
| Pre-trained question banks | New JSON data files |
| Type-specific prompts | Optimized for each interview purpose |
| Type-specific RAG services | Different retrieval strategies |
| New API routes | Separate endpoints for each type |

---

## Part 7: Next Steps

1. **Confirm this plan meets your requirements**
2. **I'll create the complete backend code package** for the new project
3. **Deploy to Render** with new endpoints
4. **Connect to your Vercel frontend**

Would you like me to proceed with creating the full implementation code?
