"""
Dashboard Endpoints (Phase 2 - Optional)
User interview history and statistics

Note: This is an optional feature. Only works when Phase 2 session store is enabled.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.session_store import InterviewStatus, SessionStore
from app.services.session_adapter import convert_base_session_to_store

# Import interview services for fallback
try:
    from app.interview.screening_interview import get_screening_interview_service
    from app.interview.behavioral_interview import get_behavioral_interview_service
    from app.interview.technical_interview import get_technical_interview_service
    INTERVIEW_SERVICES_AVAILABLE = True
except ImportError:
    INTERVIEW_SERVICES_AVAILABLE = False


router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"]
)


def get_session_store(request: Request) -> Optional[SessionStore]:
    """Get session store from app state (if available)"""
    return getattr(request.app.state, 'session_store', None)


@router.get("/history/{user_id}")
async def get_interview_history(
    request: Request,
    user_id: str,
    limit: int = 10,
    status: Optional[str] = None
):
    """Get user's interview history from SessionStore and BaseInterviewService"""
    session_store = get_session_store(request)
    history = []
    
    # Get from SessionStore if available
    if session_store:
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
    
    # Also get from BaseInterviewService if available
    if INTERVIEW_SERVICES_AVAILABLE:
        for service_getter in [get_screening_interview_service, get_behavioral_interview_service, get_technical_interview_service]:
            try:
                service = service_getter()
                for session_id, base_session in service.sessions.items():
                    if base_session.user_id == user_id:
                        # Check status filter
                        if status:
                            if status == "completed" and base_session.phase.value != "completed":
                                continue
                            elif status == "in_progress" and base_session.phase.value != "in_progress":
                                continue
                        
                        # Check if already in history
                        if any(h["session_id"] == session_id for h in history):
                            continue
                        
                        history.append({
                            "session_id": base_session.session_id,
                            "interview_type": base_session.interview_type.value.lower().replace(" interview", ""),
                            "status": "completed" if base_session.phase.value == "completed" else "in_progress",
                            "questions_answered": len(base_session.responses),
                            "total_questions": len(base_session.questions_asked),
                            "voice_enabled": False,
                            "created_at": base_session.created_at.isoformat(),
                            "completed_at": base_session.completed_at.isoformat() if base_session.completed_at else None
                        })
            except Exception as e:
                print(f"Error getting sessions from service: {e}")
                continue
    
    # Sort by created_at descending and limit
    history.sort(key=lambda x: x["created_at"], reverse=True)
    history = history[:limit]
    
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
    """Get user's interview statistics from SessionStore and BaseInterviewService"""
    session_store = get_session_store(request)
    all_sessions_list = []
    
    # Get from SessionStore if available
    if session_store:
        store_sessions = session_store.get_user_sessions(user_id=user_id, limit=100)
        all_sessions_list.extend(store_sessions)
    
    # Also get from BaseInterviewService if available
    if INTERVIEW_SERVICES_AVAILABLE:
        for service_getter in [get_screening_interview_service, get_behavioral_interview_service, get_technical_interview_service]:
            try:
                service = service_getter()
                for session_id, base_session in service.sessions.items():
                    if base_session.user_id == user_id:
                        # Convert to StoreSession format for consistency
                        if session_store:
                            store_session = convert_base_session_to_store(base_session, session_store)
                            # Check if not already in list
                            if not any(s.session_id == store_session.session_id for s in all_sessions_list):
                                all_sessions_list.append(store_session)
                        else:
                            # Create temporary entry
                            from app.services.session_store import InterviewSession as StoreSession, InterviewStatus
                            from app.models import InterviewPhase
                            
                            status_map = {
                                InterviewPhase.COMPLETED: InterviewStatus.COMPLETED,
                                InterviewPhase.IN_PROGRESS: InterviewStatus.IN_PROGRESS,
                                InterviewPhase.GREETING: InterviewStatus.PENDING
                            }
                            temp_status = status_map.get(base_session.phase, InterviewStatus.PENDING)
                            
                            temp_session = StoreSession(
                                session_id=base_session.session_id,
                                user_id=base_session.user_id,
                                interview_type=base_session.interview_type.value.lower().replace(" interview", ""),
                                status=temp_status,
                                current_question_index=base_session.current_question_index,
                                questions=[],
                                responses=[],
                                feedback_hints=[],
                                created_at=base_session.created_at,
                                started_at=base_session.started_at,
                                completed_at=base_session.completed_at,
                                last_activity=base_session.created_at,
                                voice_enabled=False,
                                voice_provider="none"
                            )
                            all_sessions_list.append(temp_session)
            except Exception as e:
                print(f"Error getting stats from service: {e}")
                continue
    
    completed = [s for s in all_sessions_list if s.status == InterviewStatus.COMPLETED]
    
    by_type = {}
    for session in all_sessions_list:
        itype = session.interview_type
        if itype not in by_type:
            by_type[itype] = {"total": 0, "completed": 0}
        by_type[itype]["total"] += 1
        if session.status == InterviewStatus.COMPLETED:
            by_type[itype]["completed"] += 1
    
    return {
        "user_id": user_id,
        "total_interviews": len(all_sessions_list),
        "completed_interviews": len(completed),
        "in_progress": len([s for s in all_sessions_list if s.status == InterviewStatus.IN_PROGRESS]),
        "by_type": by_type,
        "completion_rate": len(completed) / len(all_sessions_list) * 100 if all_sessions_list else 0
    }


@router.get("/session/{session_id}/feedback")
async def get_session_feedback(
    request: Request,
    session_id: str
):
    """Get detailed feedback for a completed session"""
    session_store = get_session_store(request)
    if not session_store:
        raise HTTPException(status_code=503, detail="Session store not available")
    
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
            "question": response.get("question", {}).get("question", "") if isinstance(response.get("question"), dict) else "",
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


@router.get("/session/{session_id}/report")
async def generate_interview_report(
    request: Request,
    session_id: str
):
    """Generate comprehensive interview report for a completed session
    
    Supports both SessionStore (Phase 2) and BaseInterviewService sessions
    """
    session_store = get_session_store(request)
    session = None
    is_from_store = False
    
    # Try to get from SessionStore first
    if session_store:
        session = session_store.get_session(session_id)
        is_from_store = True
    
    # Fallback: Try to get from BaseInterviewService
    if not session and INTERVIEW_SERVICES_AVAILABLE:
        # Determine interview type from session_id
        if session_id.startswith("screening_"):
            service = get_screening_interview_service()
        elif session_id.startswith("behavioral_"):
            service = get_behavioral_interview_service()
        elif session_id.startswith("technical_"):
            service = get_technical_interview_service()
        else:
            service = None
        
        if service:
            base_session = service.get_session(session_id)
            if base_session:
                # Convert to StoreSession format
                if session_store:
                    session = convert_base_session_to_store(base_session, session_store)
                else:
                    # Create a temporary StoreSession-like object
                    from app.services.session_store import InterviewSession as StoreSession, InterviewStatus
                    from app.models import InterviewPhase
                    
                    # Map phase to status
                    status_map = {
                        InterviewPhase.COMPLETED: InterviewStatus.COMPLETED,
                        InterviewPhase.IN_PROGRESS: InterviewStatus.IN_PROGRESS,
                        InterviewPhase.GREETING: InterviewStatus.PENDING
                    }
                    status = status_map.get(base_session.phase, InterviewStatus.PENDING)
                    
                    # Convert questions and responses
                    questions = [{"question": q, "question_index": i, "category": "general"} 
                               for i, q in enumerate(base_session.questions_asked)]
                    responses = []
                    for resp in base_session.responses:
                        responses.append({
                            "question_index": resp.get("question_index", 0),
                            "question": {"question": resp.get("question", "")},
                            "user_response": resp.get("response", ""),
                            "ai_response": "",
                            "timestamp": resp.get("timestamp", "")
                        })
                    
                    # Extract AI responses from messages
                    ai_messages = [msg for msg in base_session.messages if msg.get("role") == "assistant"]
                    for i, response in enumerate(responses):
                        if i < len(ai_messages):
                            responses[i]["ai_response"] = ai_messages[i].get("content", "")
                    
                    # Convert evaluations to feedback hints
                    feedback_hints = []
                    for resp in base_session.responses:
                        evaluation = resp.get("evaluation", {})
                        if evaluation:
                            score = evaluation.get("score", 3.0)
                            if score >= 4.0:
                                quality = "good"
                            elif score >= 2.5:
                                quality = "fair"
                            else:
                                quality = "needs_improvement"
                            feedback_hints.append({
                                "hint": evaluation.get("feedback", ""),
                                "quality": quality
                            })
                    
                    # Create temporary StoreSession
                    session = StoreSession(
                        session_id=base_session.session_id,
                        user_id=base_session.user_id,
                        interview_type=base_session.interview_type.value.lower().replace(" interview", ""),
                        status=status,
                        current_question_index=base_session.current_question_index,
                        questions=questions,
                        responses=responses,
                        feedback_hints=feedback_hints,
                        created_at=base_session.created_at,
                        started_at=base_session.started_at,
                        completed_at=base_session.completed_at,
                        last_activity=base_session.completed_at or base_session.started_at or base_session.created_at,
                        voice_enabled=False,
                        voice_provider="none"
                    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if completed
    if session.status != InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail="Report can only be generated for completed interviews"
        )
    
    # Compile comprehensive report
    report = {
        "session_id": session_id,
        "user_id": session.user_id,
        "interview_type": session.interview_type,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "duration_minutes": None,
        "questions_answered": len(session.responses),
        "total_questions": len(session.questions),
        "conversation_history": [],
        "responses_summary": [],
        "feedback_analysis": {
            "good_responses": 0,
            "fair_responses": 0,
            "needs_improvement": 0,
            "overall_score": 0
        },
        "strengths": [],
        "areas_for_improvement": [],
        "recommendations": []
    }
    
    # Calculate duration
    if session.created_at and session.completed_at:
        duration = (session.completed_at - session.created_at).total_seconds() / 60
        report["duration_minutes"] = round(duration, 1)
    
    # Build conversation history
    for i, response in enumerate(session.responses):
        question = response.get("question", {})
        if isinstance(question, dict):
            question_text = question.get("question", "")
        else:
            question_text = str(question) if question else ""
        
        report["conversation_history"].append({
            "question_index": i + 1,
            "question": question_text,
            "user_response": response.get("user_response", ""),
            "ai_response": response.get("ai_response", ""),
            "timestamp": response.get("timestamp")
        })
        
        report["responses_summary"].append({
            "question": question_text[:100] + "..." if len(question_text) > 100 else question_text,
            "user_response_length": len(response.get("user_response", "")),
            "has_feedback": response.get("feedback_hint") is not None
        })
    
    # Analyze feedback hints
    good_count = sum(1 for h in session.feedback_hints if h.get("quality") == "good")
    fair_count = sum(1 for h in session.feedback_hints if h.get("quality") == "fair")
    needs_improvement = sum(1 for h in session.feedback_hints if h.get("quality") == "needs_improvement")
    
    total_hints = len(session.feedback_hints)
    if total_hints > 0:
        overall_score = round((good_count * 100 + fair_count * 70 + needs_improvement * 40) / total_hints, 1)
        report["feedback_analysis"] = {
            "good_responses": good_count,
            "fair_responses": fair_count,
            "needs_improvement": needs_improvement,
            "overall_score": overall_score
        }
        
        # Generate recommendations based on feedback
        if needs_improvement > good_count:
            report["recommendations"].append("Focus on providing more detailed and specific examples in your responses")
            report["recommendations"].append("Practice structuring your answers with clear context and outcomes")
        if fair_count > good_count:
            report["recommendations"].append("Work on being more concise while maintaining clarity")
            report["recommendations"].append("Consider preparing STAR method responses for behavioral questions")
        
        # Extract strengths and improvements from feedback hints
        for hint in session.feedback_hints:
            hint_text = hint.get("hint", "")
            if hint.get("quality") == "good" and hint_text:
                report["strengths"].append(hint_text)
            elif hint.get("quality") == "needs_improvement" and hint_text:
                report["areas_for_improvement"].append(hint_text)
    
    # Limit lists to top items
    report["strengths"] = report["strengths"][:5]
    report["areas_for_improvement"] = report["areas_for_improvement"][:5]
    report["recommendations"] = report["recommendations"][:5] if report["recommendations"] else [
        "Continue practicing to improve your interview skills",
        "Review your responses and identify areas for improvement",
        "Consider doing more mock interviews to build confidence"
    ]
    
    return report
