"""
Screening Interview API Routes
First impression assessment endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from app.models import (
    StartSessionRequest,
    StartSessionResponse,
    MessageRequest,
    MessageResponse
)
from app.interview.screening_interview import (
    ScreeningInterviewService,
    get_screening_interview_service
)

router = APIRouter(
    prefix="/api/interview/screening",
    tags=["screening"]
)


def get_service(http_request: Request = None) -> ScreeningInterviewService:
    """Get screening interview service instance"""
    # Phase 2: Get session_store from app state if available
    session_store = None
    if http_request:
        session_store = getattr(http_request.app.state, 'session_store', None)
    return get_screening_interview_service(session_store=session_store)


@router.post("/start", response_model=StartSessionResponse)
async def start_screening_interview(request: StartSessionRequest, http_request: Request):
    """
    Start a new screening interview session
    
    - **user_id**: Unique identifier for the user
    - **resume_text**: Optional resume content for personalization
    - **job_description**: Optional job description for context
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
        
        # Record first question
        first_question = "Please tell me about yourself."
        session.questions_asked.append(first_question)
        
        return StartSessionResponse(
            session_id=session.session_id,
            interview_type="screening",
            greeting=greeting,
            duration_limit_minutes=service.duration_limit_minutes,
            max_questions=service.max_questions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=MessageResponse)
async def send_screening_message(request: MessageRequest, http_request: Request):
    """
    Send a message in the screening interview
    
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
async def get_screening_session(session_id: str, http_request: Request):
    """Get screening session details"""
    service = get_service(http_request)
    
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "interview_type": session.interview_type.value,
        "phase": session.phase.value,
        "current_question_index": session.current_question_index,
        "total_questions": len(session.questions_asked),
        "total_responses": len(session.responses),
        "created_at": session.created_at.isoformat(),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None
    }


@router.delete("/session/{session_id}")
async def delete_screening_session(session_id: str):
    """Delete a screening session"""
    service = get_service()
    
    if service.delete_session(session_id):
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )


@router.get("/questions")
async def get_screening_questions():
    """Get list of available screening questions"""
    from app.rag.screening_rag import get_screening_rag_service
    
    rag_service = get_screening_rag_service()
    questions = rag_service.get_all_questions()
    
    return {
        "interview_type": "screening",
        "total_questions": len(questions),
        "questions": [
            {
                "id": q.get("id", f"SCR-{i+1:03d}"),
                "type": q.get("type", "general"),
                "question": q.get("question", ""),
                "difficulty": q.get("difficulty", "intermediate")
            }
            for i, q in enumerate(questions)
        ]
    }
