"""
Behavioral Interview API Routes
STAR method assessment endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models import (
    StartSessionRequest,
    StartSessionResponse,
    MessageRequest,
    MessageResponse
)
from app.interview.behavioral_interview import (
    BehavioralInterviewService,
    get_behavioral_interview_service
)

router = APIRouter(
    prefix="/api/interview/behavioral",
    tags=["behavioral"]
)


def get_service() -> BehavioralInterviewService:
    """Get behavioral interview service instance"""
    return get_behavioral_interview_service()


@router.post("/start", response_model=StartSessionResponse)
async def start_behavioral_interview(request: StartSessionRequest):
    """
    Start a new behavioral interview session
    
    Uses STAR method (Situation, Task, Action, Result) for assessment.
    
    - **user_id**: Unique identifier for the user
    - **resume_text**: Optional resume content for personalization
    - **job_description**: Optional job description for context
    """
    service = get_service()
    
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
        first_question = "Tell me about a challenge you faced working in a team. How did you handle it?"
        session.questions_asked.append(first_question)
        
        return StartSessionResponse(
            session_id=session.session_id,
            interview_type="behavioral",
            greeting=greeting,
            duration_limit_minutes=service.duration_limit_minutes,
            max_questions=service.max_questions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=MessageResponse)
async def send_behavioral_message(request: MessageRequest):
    """
    Send a message in the behavioral interview
    
    Responses are evaluated using the STAR method.
    Follow-up questions may be asked if STAR components are missing.
    
    - **session_id**: Session identifier from start endpoint
    - **message**: User's response text
    """
    service = get_service()
    
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
async def get_behavioral_session(session_id: str):
    """Get behavioral session details including STAR scores"""
    service = get_service()
    
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    # Calculate aggregate STAR scores
    star_totals = {"situation": [], "task": [], "action": [], "result": []}
    for resp in session.responses:
        eval_data = resp.get("evaluation", {})
        star_scores = eval_data.get("star_scores", {})
        for key in star_totals:
            if key in star_scores:
                star_totals[key].append(star_scores[key])
    
    star_averages = {}
    for key, scores in star_totals.items():
        star_averages[key] = round(sum(scores) / len(scores), 2) if scores else 0
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "interview_type": session.interview_type.value,
        "phase": session.phase.value,
        "current_question_index": session.current_question_index,
        "total_questions": len(session.questions_asked),
        "total_responses": len(session.responses),
        "star_scores": star_averages,
        "created_at": session.created_at.isoformat(),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None
    }


@router.delete("/session/{session_id}")
async def delete_behavioral_session(session_id: str):
    """Delete a behavioral session"""
    service = get_service()
    
    if service.delete_session(session_id):
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )


@router.get("/questions")
async def get_behavioral_questions():
    """Get list of available behavioral questions by category"""
    from app.rag.behavioral_rag import get_behavioral_rag_service
    
    rag_service = get_behavioral_rag_service()
    
    # Get questions organized by category
    questions_by_category = rag_service.questions_by_category
    
    result = {
        "interview_type": "behavioral",
        "method": "STAR",
        "categories": {}
    }
    
    for category, questions in questions_by_category.items():
        result["categories"][category] = [
            {
                "id": q.get("id", ""),
                "type": q.get("type", ""),
                "question": q.get("question", ""),
                "difficulty": q.get("difficulty", "intermediate"),
                "competencies": q.get("competencies", [])
            }
            for q in questions
        ]
    
    return result


@router.get("/star-guide")
async def get_star_guide():
    """Get STAR method explanation and tips"""
    return {
        "method": "STAR",
        "components": {
            "S": {
                "name": "Situation",
                "description": "Describe the context and background",
                "tips": [
                    "Set the scene clearly",
                    "Include relevant details",
                    "Be specific about when and where"
                ]
            },
            "T": {
                "name": "Task",
                "description": "Explain your specific responsibility",
                "tips": [
                    "Clarify YOUR role specifically",
                    "Explain what was expected of you",
                    "Distinguish your task from the team's goal"
                ]
            },
            "A": {
                "name": "Action",
                "description": "Detail what YOU specifically did",
                "tips": [
                    "Use 'I' not 'we'",
                    "Be detailed about your steps",
                    "Explain your reasoning"
                ]
            },
            "R": {
                "name": "Result",
                "description": "Share the outcome with metrics if possible",
                "tips": [
                    "Quantify results when possible",
                    "Include what you learned",
                    "Connect to the original goal"
                ]
            }
        }
    }
