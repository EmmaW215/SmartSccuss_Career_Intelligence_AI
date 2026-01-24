"""
Customize Interview Endpoints
Requires GPU server for Custom RAG building
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
import base64

from app.rag.question_bank import select_customize_questions
from app.services.session_store import InterviewStatus
from app.services.gpu_client import get_gpu_client
from app.core.conversation_engine import get_conversation_engine


router = APIRouter()


class StartCustomInterviewRequest(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    voice_enabled: bool = False


class SubmitResponseRequest(BaseModel):
    session_id: str
    user_response: str


@router.post("/upload")
async def upload_documents(
    request: Request,
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload documents for custom RAG building
    Requires GPU server to be online
    """
    gpu_client = get_gpu_client()
    status = await gpu_client.check_health()
    
    if not status.get("available"):
        raise HTTPException(
            status_code=503,
            detail="Custom interview requires GPU server. Please ensure GPU server is running or try standard interview types."
        )
    
    # Process uploaded files
    processed_files = []
    for file in files:
        content = await file.read()
        
        # Validate file size (max 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 10MB limit"
            )
        
        # Detect content type
        content_type = file.content_type or "application/octet-stream"
        
        # For text files, decode content
        if content_type.startswith("text/") or file.filename.endswith(('.txt', '.md')):
            try:
                text_content = content.decode('utf-8')
            except:
                text_content = content.decode('latin-1')
            processed_files.append({
                "filename": file.filename,
                "content": text_content,
                "content_type": content_type
            })
        else:
            # Binary files (PDF, DOCX) - send as base64
            processed_files.append({
                "filename": file.filename,
                "content": content,  # bytes
                "content_type": content_type
            })
    
    # Build custom RAG on GPU
    try:
        rag_result = await gpu_client.build_custom_rag(
            user_id=user_id,
            files=processed_files
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "files_processed": len(processed_files),
            "profile": rag_result.get("profile", {}),
            "selected_questions": rag_result.get("questions", []),
            "rag_id": rag_result.get("rag_id")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build custom RAG: {str(e)}"
        )


@router.post("/start")
async def start_customize_interview(
    request: Request,
    body: StartCustomInterviewRequest,
    profile: Optional[dict] = None,
    rag_id: Optional[str] = None
):
    """Start a custom interview (after upload/build)"""
    session_store = request.app.state.session_store
    conversation_engine = get_conversation_engine()
    gpu_client = get_gpu_client()
    
    # Check GPU availability
    status = await gpu_client.check_health()
    
    # If we have a profile, use it; otherwise use default questions
    if profile:
        questions = select_customize_questions(profile)
    else:
        # Fallback to standard mix
        questions = select_customize_questions({})
    
    job_context = None
    if profile and profile.get("job_target"):
        job_context = profile["job_target"]
    
    session = session_store.create_session(
        user_id=body.user_id,
        interview_type="customize",
        questions=questions,
        voice_enabled=body.voice_enabled and status.get("available", False),
        custom_profile=profile,
        custom_rag_id=rag_id
    )
    
    context = conversation_engine.create_context(
        session_id=session.session_id,
        user_id=body.user_id,
        interview_type="customize",
        user_profile=profile,
        job_context=job_context
    )
    
    greeting = await conversation_engine.generate_greeting(
        context=context,
        user_name=body.user_name
    )
    
    session_store.update_session(
        session.session_id,
        status=InterviewStatus.IN_PROGRESS
    )
    
    return {
        "session_id": session.session_id,
        "greeting": greeting,
        "total_questions": len(questions),
        "voice_enabled": session.voice_enabled,
        "interview_type": "customize",
        "profile_used": profile is not None,
        "gpu_available": status.get("available", False)
    }


@router.post("/respond")
async def submit_response(
    request: Request,
    body: SubmitResponseRequest
):
    """Submit a response and get next question"""
    session_store = request.app.state.session_store
    conversation_engine = get_conversation_engine()
    
    session = session_store.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.interview_type != "customize":
        raise HTTPException(status_code=400, detail="Invalid interview type")
    
    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Interview not in progress")
    
    context = conversation_engine.get_context(body.session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Conversation context not found")
    
    if session.current_question_index >= len(session.questions):
        closing = await conversation_engine.generate_closing(context)
        session_store.complete_session(body.session_id)
        return {
            "ai_response": closing,
            "is_complete": True,
            "session_id": body.session_id
        }
    
    next_q = session.questions[session.current_question_index]
    next_question = next_q.get("customized_question") or next_q.get("question", "Tell me more.")
    
    result = await conversation_engine.process_response(
        context=context,
        user_response=body.user_response,
        next_question=next_question
    )
    
    session_store.add_response(
        session_id=body.session_id,
        question_index=session.current_question_index,
        user_response=body.user_response,
        ai_response=result["ai_response"],
        feedback_hint=result.get("feedback_hint")
    )
    
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
    
    # Get category of current question
    current_q = session.questions[result["question_index"]] if result["question_index"] < len(session.questions) else None
    category = current_q.get("category", "general") if current_q else None
    
    return {
        "ai_response": result["ai_response"],
        "tone": result.get("tone", "neutral"),
        "feedback_hint": result.get("feedback_hint"),
        "current_question": result["question_index"],
        "total_questions": len(session.questions),
        "current_category": category,
        "is_complete": False,
        "session_id": body.session_id
    }


@router.post("/end")
async def end_interview(request: Request, session_id: str):
    """End interview early"""
    session_store = request.app.state.session_store
    conversation_engine = get_conversation_engine()
    
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = conversation_engine.get_context(session_id)
    closing = await conversation_engine.generate_closing(context, is_early_stop=True) if context else "Thank you for your time."
    
    session_store.complete_session(session_id)
    
    return {
        "closing_message": closing,
        "session_id": session_id,
        "questions_answered": len(session.responses)
    }


@router.get("/session/{session_id}")
async def get_session_info(request: Request, session_id: str):
    """Get session information"""
    session_store = request.app.state.session_store
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.get("/gpu-status")
async def check_gpu_status():
    """Check if GPU server is available for custom interviews"""
    gpu_client = get_gpu_client()
    status = await gpu_client.check_health(force=True)
    
    return {
        "available": status.get("available", False),
        "services": status.get("services", {}),
        "latency_ms": status.get("latency_ms"),
        "message": "GPU server is ready for custom interviews" if status.get("available") else "GPU server offline. Standard interviews still available."
    }
