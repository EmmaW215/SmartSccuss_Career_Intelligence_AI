"""
Technical Interview API Routes
AI/ML Engineering skills assessment endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from app.models import (
    StartSessionRequest,
    StartSessionResponse,
    MessageRequest,
    MessageResponse
)
from app.interview.technical_interview import (
    TechnicalInterviewService,
    get_technical_interview_service
)

router = APIRouter(
    prefix="/api/interview/technical",
    tags=["technical"]
)


def get_service(http_request: Request = None) -> TechnicalInterviewService:
    """Get technical interview service instance"""
    # Phase 2: Get session_store from app state if available
    session_store = None
    if http_request:
        session_store = getattr(http_request.app.state, 'session_store', None)
    return get_technical_interview_service(session_store=session_store)


@router.post("/start", response_model=StartSessionResponse)
async def start_technical_interview(request: StartSessionRequest, http_request: Request):
    """
    Start a new technical interview session
    
    Covers AI/ML engineering topics including:
    - Python engineering
    - LLM frameworks (LangChain, LangGraph, etc.)
    - RAG architecture
    - ML production systems
    - Cloud deployment
    
    - **user_id**: Unique identifier for the user
    - **resume_text**: Optional resume for personalized questions
    - **job_description**: Optional job description for context
    - **matchwise_analysis**: Optional MatchWise analysis with skill gaps
    """
    service = get_service(http_request)
    
    try:
        session = await service.create_session(
            user_id=request.user_id,
            resume_text=request.resume_text,
            job_description=request.job_description,
            matchwise_analysis=request.matchwise_analysis
        )
        
        greeting = await service.get_greeting()
        
        # Record greeting as first message
        session.messages.append({
            "role": "assistant",
            "content": greeting,
            "timestamp": session.created_at.isoformat()
        })
        
        # Record first question (embedded in greeting)
        first_question = "Would you consider yourself an expert-level Python engineer? Can you share examples of complex systems you've built with Python?"
        session.questions_asked.append(first_question)
        
        return StartSessionResponse(
            session_id=session.session_id,
            interview_type="technical",
            greeting=greeting,
            duration_limit_minutes=service.duration_limit_minutes,
            max_questions=service.max_questions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=MessageResponse)
async def send_technical_message(request: MessageRequest, http_request: Request):
    """
    Send a message in the technical interview
    
    Responses are evaluated for:
    - Technical accuracy
    - Depth of knowledge
    - Practical experience
    - System thinking
    - Communication clarity
    
    - **session_id**: Session identifier from start endpoint
    - **message**: User's response text
    """
    service = get_service(http_request)
    
    session = service.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found"
        )
    
    try:
        response = await service.process_message(
            session_id=request.session_id,
            user_message=request.message
        )
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_technical_session(session_id: str, http_request: Request):
    """Get technical session details including scores by domain"""
    service = get_service(http_request)
    
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    # Calculate aggregate scores
    score_categories = {
        "technical_accuracy": [],
        "depth_of_knowledge": [],
        "practical_experience": [],
        "system_thinking": [],
        "communication_clarity": []
    }
    
    domains_covered = []
    hire_signals = []
    
    for resp in session.responses:
        eval_data = resp.get("evaluation", {})
        
        for key in score_categories:
            if key in eval_data:
                score_categories[key].append(eval_data[key])
        
        if eval_data.get("domain"):
            domains_covered.append(eval_data["domain"])
        
        if eval_data.get("hire_signal"):
            hire_signals.append(eval_data["hire_signal"])
    
    score_averages = {}
    for key, scores in score_categories.items():
        score_averages[key] = round(sum(scores) / len(scores), 2) if scores else 0
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "interview_type": session.interview_type.value,
        "phase": session.phase.value,
        "current_question_index": session.current_question_index,
        "total_questions": len(session.questions_asked),
        "total_responses": len(session.responses),
        "scores": score_averages,
        "domains_covered": list(set(domains_covered)),
        "hire_signals": hire_signals,
        "created_at": session.created_at.isoformat(),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None
    }


@router.delete("/session/{session_id}")
async def delete_technical_session(session_id: str):
    """Delete a technical session"""
    service = get_service()
    
    if service.delete_session(session_id):
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )


@router.get("/questions")
async def get_technical_questions():
    """Get list of available technical questions by domain"""
    from app.rag.technical_rag import get_technical_rag_service
    
    rag_service = get_technical_rag_service()
    
    # Get questions organized by domain
    questions_by_domain = rag_service.questions_by_domain
    
    result = {
        "interview_type": "technical",
        "domains": {}
    }
    
    for domain, questions in questions_by_domain.items():
        result["domains"][domain] = [
            {
                "id": q.get("id", ""),
                "type": q.get("type", ""),
                "question": q.get("question", ""),
                "difficulty": q.get("difficulty", "intermediate"),
                "expected_topics": q.get("expected_topics", []),
                "key_concepts": q.get("key_concepts", [])
            }
            for q in questions
        ]
    
    return result


@router.get("/domains")
async def get_technical_domains():
    """Get list of technical domains covered"""
    from app.rag.technical_rag import get_technical_rag_service
    
    rag_service = get_technical_rag_service()
    
    return {
        "domains": rag_service.get_available_domains(),
        "descriptions": {
            "python_engineering": "Python development, architecture, and best practices",
            "llm_frameworks": "LangChain, LangGraph, LlamaIndex, AutoGen, CrewAI",
            "rag_architecture": "RAG systems, embeddings, vector stores, retrieval",
            "ml_production": "MLOps, model deployment, monitoring, data pipelines",
            "cloud_deployment": "GCP, AWS, Azure, scaling, cost optimization",
            "security": "Authentication, authorization, data protection",
            "integration": "API design, external system integration",
            "debugging": "Problem-solving, root cause analysis",
            "model_training": "Fine-tuning, LoRA, hyperparameters",
            "concept_explanation": "Technical concept understanding"
        }
    }
