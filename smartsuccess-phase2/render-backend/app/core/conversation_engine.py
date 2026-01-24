"""
Conversation Engine - Makes AI speak like a real person

Features:
- Natural language responses (not robotic)
- Adaptive follow-up questions
- Context-aware transitions
- Emotion/tone awareness
- Speech-optimized output

Uses Gemini/OpenAI for processing, outputs speech-ready text
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.services.llm_service import get_llm_service


class InterviewPhase(Enum):
    NOT_STARTED = "not_started"
    GREETING = "greeting"
    IN_PROGRESS = "in_progress"
    FOLLOW_UP = "follow_up"
    CLOSING = "closing"
    COMPLETED = "completed"


@dataclass
class ConversationContext:
    """Maintains conversation state for a session"""
    session_id: str
    user_id: str
    interview_type: str
    phase: InterviewPhase = InterviewPhase.NOT_STARTED
    current_question_index: int = 0
    questions_asked: List[str] = field(default_factory=list)
    user_responses: List[str] = field(default_factory=list)
    ai_responses: List[str] = field(default_factory=list)
    feedback_hints: List[Dict] = field(default_factory=list)
    user_profile: Optional[Dict] = None
    job_context: Optional[Dict] = None
    started_at: datetime = field(default_factory=datetime.now)
    follow_up_count: int = 0
    max_follow_ups: int = 2


class ConversationEngine:
    """
    Natural conversation engine for human-like interview experience
    
    Makes AI interviewer sound like a real person:
    1. Natural greetings
    2. Acknowledgments before questions
    3. Adaptive follow-ups
    4. Smooth transitions
    5. Speech-optimized (no markdown)
    """
    
    INTERVIEWER_PERSONA = """You are Alex, an experienced and friendly interviewer.

PERSONALITY:
- Warm and encouraging, but professional
- Acknowledge what the candidate says before moving on
- Use natural transitions: "That's interesting...", "I see...", "Great point..."
- Occasionally ask brief clarifying questions
- Show genuine interest in responses
- Speak conversationally, not robotically

VOICE STYLE (responses will be spoken aloud):
- Use contractions: I'm, you're, that's, it's, don't
- Keep sentences short (5-15 words ideal)
- Add natural pauses with "..." where appropriate
- NO bullet points, lists, or formatting
- NO asterisks, headers, or markdown
- Write as natural spoken sentences only

IMPORTANT: Sound like a real person, not a script reader."""

    RESPONSE_FORMAT = """\
Respond in JSON format:
{
    "acknowledgment": "Brief reaction (1 sentence, optional)",
    "transition": "Bridge to next topic (1 sentence, optional)",
    "next_content": "Your question or response",
    "tone": "friendly|curious|impressed|neutral|encouraging",
    "needs_follow_up": true/false,
    "follow_up_reason": "reason if needs_follow_up is true"
}

Rules:
- Total spoken text under 80 words
- Be conversational, not robotic
- acknowledgment + transition + next_content = what you say"""

    def __init__(self):
        self.llm_service = get_llm_service()
        self.contexts: Dict[str, ConversationContext] = {}
    
    def create_context(
        self,
        session_id: str,
        user_id: str,
        interview_type: str,
        user_profile: Optional[Dict] = None,
        job_context: Optional[Dict] = None
    ) -> ConversationContext:
        """Create new conversation context"""
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            interview_type=interview_type,
            user_profile=user_profile,
            job_context=job_context
        )
        self.contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get existing conversation context"""
        return self.contexts.get(session_id)
    
    def delete_context(self, session_id: str) -> bool:
        """Delete conversation context"""
        if session_id in self.contexts:
            del self.contexts[session_id]
            return True
        return False
    
    async def generate_greeting(
        self,
        context: ConversationContext,
        user_name: Optional[str] = None
    ) -> str:
        """Generate natural greeting based on interview type"""
        greetings = {
            "screening": self._screening_greeting(user_name),
            "behavioral": self._behavioral_greeting(user_name),
            "technical": self._technical_greeting(user_name),
            "customize": self._customize_greeting(user_name, context)
        }
        
        greeting = greetings.get(context.interview_type, greetings["screening"])
        context.phase = InterviewPhase.GREETING
        context.ai_responses.append(greeting)
        
        return greeting
    
    def _screening_greeting(self, name: Optional[str]) -> str:
        n = f" {name}" if name else ""
        return (
            f"Hi{n}! I'm Alex, and I'll be your interviewer today. "
            f"Thanks for taking the time to chat with me. "
            f"This is just a quick 10-15 minute conversation so I can learn a bit about you. "
            f"There are no trick questions here... I just want to get to know you better. "
            f"Ready? Great! So... tell me a little about yourself."
        )
    
    def _behavioral_greeting(self, name: Optional[str]) -> str:
        n = f" {name}" if name else ""
        return (
            f"Hey{n}, great to meet you! I'm Alex. "
            f"Today we'll spend about 25-30 minutes diving into your past experiences. "
            f"I'll ask about specific situations you've faced... and I'd love real examples. "
            f"The more specific, the better. Don't worry about making things sound perfect... "
            f"I'm more interested in how you actually handled things. "
            f"Let's jump in... Tell me about a time when you faced a real challenge at work."
        )
    
    def _technical_greeting(self, name: Optional[str]) -> str:
        n = f" {name}" if name else ""
        return (
            f"Hi{n}! I'm Alex, one of the technical interviewers. "
            f"We've got about 45 minutes together, and I'm looking forward to learning about "
            f"your technical experience. Feel free to think out loud and ask clarifying questions. "
            f"I'm more interested in how you approach problems than perfect answers. "
            f"So... let's start. Tell me about the most complex system you've built or worked on."
        )
    
    def _customize_greeting(self, name: Optional[str], context: ConversationContext) -> str:
        n = f" {name}" if name else ""
        job = ""
        if context.job_context and context.job_context.get("title"):
            job = f" for the {context.job_context['title']} position"
        
        return (
            f"Welcome{n}! I'm Alex, and I'm excited to have this personalized interview with you. "
            f"I've reviewed the materials you shared and prepared questions tailored to your background{job}. "
            f"We'll cover 3 screening questions, 3 behavioral questions, and 4 technical questions. "
            f"This should take about 45 minutes. Take your time... there's no rush. "
            f"Ready? Let's begin..."
        )
    
    async def process_response(
        self,
        context: ConversationContext,
        user_response: str,
        next_question: str
    ) -> Dict[str, Any]:
        """
        Process user response and generate natural AI reply
        
        Returns:
            Dict with: ai_response, tone, needs_follow_up, feedback_hint
        """
        context.user_responses.append(user_response)
        context.phase = InterviewPhase.IN_PROGRESS
        
        # Build conversation history
        history = self._build_history(context)
        
        prompt = f"""{self.INTERVIEWER_PERSONA}

CONVERSATION SO FAR:
{history}

CANDIDATE'S LATEST RESPONSE:
"{user_response}"

NEXT PLANNED QUESTION (adapt this naturally):
"{next_question}"

{self.RESPONSE_FORMAT}"""

        try:
            llm_response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.8,
                max_tokens=400
            )
            
            result = self._parse_response(llm_response, next_question)
            
            # Build spoken response
            parts = []
            if result.get("acknowledgment"):
                parts.append(result["acknowledgment"])
            if result.get("transition"):
                parts.append(result["transition"])
            parts.append(result["next_content"])
            
            ai_response = " ".join(parts)
            
            # Update context
            context.ai_responses.append(ai_response)
            context.questions_asked.append(next_question)
            
            # Handle follow-up
            if result.get("needs_follow_up") and context.follow_up_count < context.max_follow_ups:
                context.phase = InterviewPhase.FOLLOW_UP
                context.follow_up_count += 1
            else:
                context.current_question_index += 1
                context.follow_up_count = 0
            
            # Generate feedback hint
            feedback_hint = await self._generate_feedback_hint(user_response)
            if feedback_hint:
                context.feedback_hints.append(feedback_hint)
            
            return {
                "ai_response": ai_response,
                "tone": result.get("tone", "neutral"),
                "needs_follow_up": result.get("needs_follow_up", False),
                "follow_up_reason": result.get("follow_up_reason"),
                "feedback_hint": feedback_hint,
                "question_index": context.current_question_index
            }
            
        except Exception as e:
            print(f"Conversation engine error: {e}")
            # Fallback
            fallback = f"I see. Thanks for sharing that. {next_question}"
            context.ai_responses.append(fallback)
            context.questions_asked.append(next_question)
            context.current_question_index += 1
            
            return {
                "ai_response": fallback,
                "tone": "neutral",
                "needs_follow_up": False,
                "feedback_hint": None,
                "question_index": context.current_question_index
            }
    
    async def generate_follow_up(
        self,
        context: ConversationContext,
        user_response: str,
        reason: str
    ) -> str:
        """Generate natural follow-up question"""
        prompt = f"""{self.INTERVIEWER_PERSONA}

The candidate's response needs clarification.
Response: "{user_response[:300]}"
Reason: {reason}

Generate a brief, natural follow-up (1-2 sentences).
Be encouraging, not critical. Sound curious.

Respond with ONLY the follow-up question."""

        try:
            follow_up = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=100
            )
            
            follow_up = follow_up.strip()
            context.ai_responses.append(follow_up)
            return follow_up
        except Exception:
            default = "Could you tell me a bit more about that?"
            context.ai_responses.append(default)
            return default
    
    async def generate_closing(
        self,
        context: ConversationContext,
        is_early_stop: bool = False
    ) -> str:
        """Generate natural interview closing"""
        context.phase = InterviewPhase.CLOSING
        
        if is_early_stop:
            closing = (
                "No problem at all! We can stop here. "
                "Thanks so much for your time today... I really enjoyed our conversation. "
                "Your feedback will be ready shortly on the dashboard. "
                "Is there anything you'd like to ask me before we wrap up?"
            )
        else:
            closing = (
                "And that brings us to the end! Thank you so much... "
                "I really enjoyed learning about your experience. "
                "Your detailed feedback is being prepared... "
                "you'll see your scores and insights on the dashboard in just a moment. "
                "Great job today!"
            )
        
        context.ai_responses.append(closing)
        context.phase = InterviewPhase.COMPLETED
        return closing
    
    def _build_history(self, context: ConversationContext) -> str:
        """Build conversation history (last 3 exchanges)"""
        history = []
        pairs = list(zip(context.questions_asked, context.user_responses))
        
        for i, (q, r) in enumerate(pairs[-3:], 1):
            history.append(f"Q{i}: {q}")
            history.append(f"A{i}: {r[:200]}...")
        
        return "\n".join(history) if history else "No previous exchanges."
    
    def _parse_response(self, response: str, fallback_question: str) -> Dict:
        """Parse LLM JSON response with fallback"""
        try:
            text = response.strip()
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                text = text[start:end]
            
            result = json.loads(text)
            
            if not result.get("next_content"):
                result["next_content"] = fallback_question
            
            return result
        except (json.JSONDecodeError, IndexError, ValueError):
            clean = response.strip()
            if len(clean) > 200:
                clean = fallback_question
            
            return {
                "acknowledgment": "",
                "transition": "",
                "next_content": clean if clean else fallback_question,
                "tone": "neutral",
                "needs_follow_up": False
            }
    
    async def _generate_feedback_hint(self, response: str) -> Optional[Dict]:
        """Generate quick feedback hint for UI"""
        if len(response) < 20:
            return {"hint": "Response was quite brief", "quality": "needs_improvement"}
        
        prompt = f"""Analyze this interview response briefly.
Response: {response[:400]}

Rate: good, fair, or needs_improvement
Provide a 1-sentence hint.

Format: {{"hint": "your hint", "quality": "good|fair|needs_improvement"}}
Respond with ONLY JSON."""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=80
            )
            
            text = result.strip()
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                return json.loads(text[start:end])
        except Exception:
            pass
        
        return None
    
    def get_session_summary(self, context: ConversationContext) -> Dict:
        """Get summary of conversation session"""
        return {
            "session_id": context.session_id,
            "interview_type": context.interview_type,
            "phase": context.phase.value,
            "questions_asked": len(context.questions_asked),
            "duration_seconds": (datetime.now() - context.started_at).total_seconds(),
            "feedback_hints": context.feedback_hints
        }


# Singleton
_engine_instance: Optional[ConversationEngine] = None


def get_conversation_engine() -> ConversationEngine:
    """Get singleton conversation engine"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ConversationEngine()
    return _engine_instance
