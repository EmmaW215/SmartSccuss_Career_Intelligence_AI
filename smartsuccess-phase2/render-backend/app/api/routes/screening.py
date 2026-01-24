"""
Screening Interview Endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.rag.question_bank import get_questions_for_type
from app.services.session_store import SessionStatus
from app.core.conversation_engine import get_conversation_engine


router = APIRouter()


class StartInterviewRequest(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    voice_enabled: bool = False


class SubmitResponseRequest(BaseModel):
    session_id: str
    user_response: str


class StartInterviewResponse(BaseModel):
    session_id: str
    greeting: str
    total_questions: int
    voice_enabled: bool
    audio_url: Optional[str] = None


@router.post("/start", response_model=StartInterviewResponse)
async def start_screening_interview(
    request: Request,
    body: StartInterviewRequest
):
    """Start a new screening interview"""
    session_store = request.app.state.session_store
    conversation_engine = get_conversation_engine()
    
    # Get questions
    questions = get_questions_for_type("screening")
    
    # Create session
    session = session_store.create_session(
        user_id=body.user_id,
        interview_type="screening",
        questions=questions,
        voice_enabled=body.voice_enabled
    )
    
    # Create conversation context
    context = conversation_engine.create_context(
        session_id=session.session_id,
        user_id=body.user_id,
        interview_type="screening"
    )
    
    # Generate greeting
    greeting = await conversation_engine.generate_greeting(
        context=context,
        user_name=body.user_name
    )
    
    # Update session status
    session_store.update_session(
        session.session_id,
        status=SessionStatus.IN_PROGRESS
    )
    
    audio_url = None
    if body.voice_enabled:
        # TTS would be handled separately via /api/voice/synthesize
        pass
    
    return StartInterviewResponse(
        session_id=session.session_id,
        greeting=greeting,
        total_questions=len(questions),
        voice_enabled=body.voice_enabled,
        audio_url=audio_url
    )


@router.post("/respond")
async def submit_response(
    request: Request,
    body: SubmitResponseRequest
):
    """Submit a response and get next question"""
    session_store = request.app.state.session_store
    conversation_engine = get_conversation_engine()
    
    # Get session
    session = session_store.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Interview not in progress")
    
    # Get conversation context
    context = conversation_engine.get_context(body.session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Conversation context not found")
    
    # Check if interview is complete
    if session.current_question_index >= len(session.questions):
        closing = await conversation_engine.generate_closing(context)
        session_store.complete_session(body.session_id)
        
        return {
            "ai_response": closing,
            "is_complete": True,
            "session_id": body.session_id
        }
    
    # Get next question
    next_q = session.questions[session.current_question_index]
    next_question = next_q.get("question", "Tell me more.")
    
    # Process response with conversation engine
    result = await conversation_engine.process_response(
        context=context,
        user_response=body.user_response,
        next_question=next_question
    )
    
    # Save response to session
    session_store.add_response(
        session_id=body.session_id,
        question_index=session.current_question_index,
        user_response=body.user_response,
        ai_response=result["ai_response"],
        feedback_hint=result.get("feedback_hint")
    )
    
    # Check completion
    is_complete = result["question_index"] >= len(session.questions)
    
    if is_complete:
        closing = await conversation_engine.generate_closing(context)
        session_store.complete_session(body.session_id)
        
        return {
            "ai_response": closing,
            "is_complete": True,
            "feedback_hint": result.get("feedback_hint"),
            "session_id": body.session_id
        }
    
    return {
        "ai_response": result["ai_response"],
        "tone": result.get("tone", "neutral"),
        "feedback_hint": result.get("feedback_hint"),
        "current_question": result["question_index"],
        "total_questions": len(session.questions),
        "is_complete": False,
        "session_id": body.session_id
    }


@router.post("/end")
async def end_interview(
    request: Request,
    session_id: str
):
    """End interview early and get feedback"""
    session_store = request.app.state.session_store
    conversation_engine = get_conversation_engine()
    
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = conversation_engine.get_context(session_id)
    
    if context:
        closing = await conversation_engine.generate_closing(context, is_early_stop=True)
    else:
        closing = "Thank you for your time. Your feedback is being prepared."
    
    session_store.complete_session(session_id)
    
    return {
        "closing_message": closing,
        "session_id": session_id,
        "questions_answered": len(session.responses),
        "total_questions": len(session.questions)
    }


@router.get("/session/{session_id}")
async def get_session_info(
    request: Request,
    session_id: str
):
    """Get session information"""
    session_store = request.app.state.session_store
    
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()
