"""
Dashboard Endpoints
User interview history and statistics
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.session_store import InterviewStatus


router = APIRouter()


@router.get("/history/{user_id}")
async def get_interview_history(
    request: Request,
    user_id: str,
    limit: int = 10,
    status: Optional[str] = None
):
    """Get user's interview history"""
    session_store = request.app.state.session_store
    
    status_filter = None
    if status:
        try:
            status_filter = InterviewStatus(status)
        except ValueError:
            pass
    
    sessions = session_store.get_user_sessions(
        user_id=user_id,
        limit=limit,
        status=status_filter
    )
    
    history = []
    for session in sessions:
        history.append({
            "session_id": session.session_id,
            "interview_type": session.interview_type,
            "status": session.status.value,
            "questions_answered": len(session.responses),
            "total_questions": len(session.questions),
            "voice_enabled": session.voice_enabled,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None
        })
    
    return {
        "user_id": user_id,
        "total_interviews": len(history),
        "interviews": history
    }


@router.get("/stats/{user_id}")
async def get_user_stats(
    request: Request,
    user_id: str
):
    """Get user's interview statistics"""
    session_store = request.app.state.session_store
    
    all_sessions = session_store.get_user_sessions(user_id=user_id, limit=100)
    
    completed = [s for s in all_sessions if s.status == InterviewStatus.COMPLETED]
    
    by_type = {}
    for session in all_sessions:
        itype = session.interview_type
        if itype not in by_type:
            by_type[itype] = {"total": 0, "completed": 0}
        by_type[itype]["total"] += 1
        if session.status == InterviewStatus.COMPLETED:
            by_type[itype]["completed"] += 1
    
    return {
        "user_id": user_id,
        "total_interviews": len(all_sessions),
        "completed_interviews": len(completed),
        "in_progress": len([s for s in all_sessions if s.status == InterviewStatus.IN_PROGRESS]),
        "by_type": by_type,
        "completion_rate": len(completed) / len(all_sessions) * 100 if all_sessions else 0
    }


@router.get("/session/{session_id}/feedback")
async def get_session_feedback(
    request: Request,
    session_id: str
):
    """Get detailed feedback for a completed session"""
    session_store = request.app.state.session_store
    
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Compile feedback from session
    feedback = {
        "session_id": session_id,
        "interview_type": session.interview_type,
        "status": session.status.value,
        "questions_answered": len(session.responses),
        "total_questions": len(session.questions),
        "responses": [],
        "feedback_hints": session.feedback_hints
    }
    
    for i, response in enumerate(session.responses):
        feedback["responses"].append({
            "question_index": i,
            "question": response.get("question", {}).get("question", ""),
            "user_response": response.get("user_response", ""),
            "ai_response": response.get("ai_response", "")
        })
    
    # Calculate simple scores based on hints
    good_count = sum(1 for h in session.feedback_hints if h.get("quality") == "good")
    fair_count = sum(1 for h in session.feedback_hints if h.get("quality") == "fair")
    needs_improvement = sum(1 for h in session.feedback_hints if h.get("quality") == "needs_improvement")
    
    total_hints = len(session.feedback_hints)
    if total_hints > 0:
        feedback["estimated_score"] = {
            "good_responses": good_count,
            "fair_responses": fair_count,
            "needs_improvement": needs_improvement,
            "estimated_percentage": round((good_count * 100 + fair_count * 70 + needs_improvement * 40) / total_hints, 1)
        }
    
    return feedback


@router.get("/session/{session_id}/transcript")
async def get_session_transcript(
    request: Request,
    session_id: str
):
    """Get full transcript of an interview session"""
    session_store = request.app.state.session_store
    
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    transcript = []
    
    for i, response in enumerate(session.responses):
        question = response.get("question", {})
        transcript.append({
            "type": "question",
            "index": i,
            "content": question.get("question", ""),
            "category": question.get("category", "")
        })
        transcript.append({
            "type": "user_response",
            "index": i,
            "content": response.get("user_response", "")
        })
        transcript.append({
            "type": "ai_response",
            "index": i,
            "content": response.get("ai_response", "")
        })
    
    return {
        "session_id": session_id,
        "interview_type": session.interview_type,
        "transcript": transcript,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None
    }


@router.delete("/session/{session_id}")
async def delete_session(
    request: Request,
    session_id: str
):
    """Delete a session"""
    session_store = request.app.state.session_store
    
    success = session_store.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"deleted": True, "session_id": session_id}
