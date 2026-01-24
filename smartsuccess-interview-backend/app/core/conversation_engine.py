"""
Conversation Engine (Phase 2 - Optional Enhancement)
Makes AI speak like a real person with natural conversation flow

Features:
- Natural language responses (not robotic)
- Adaptive follow-up questions
- Context-aware transitions
- Emotion/tone awareness
- Speech-optimized output

Only used when use_conversation_engine=True in config
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.config import settings
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
        # Only initialize if conversation engine is enabled
        if not settings.use_conversation_engine:
            raise Exception("Conversation engine is disabled in config")
        
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
            f"You can let me know whenever you want to stop the interview, just say 'stop' or 'end' and I'll stop the interview."
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
            f"You can let me know whenever you want to stop the interview, just say 'stop' or 'end' and I'll stop the interview."
            f"Now, let's jump in... Tell me about a time when you faced a real challenge at work."
        )
    
    def _technical_greeting(self, name: Optional[str]) -> str:
        n = f" {name}" if name else ""
        return (
            f"Hi{n}! I'm Alex, one of the technical interviewers. "
            f"We've got about 45 minutes together, and I'm looking forward to learning about. "
            f"your technical experience. Feel free to think out loud and ask clarifying questions. "
            f"You can let me know whenever you want to stop the interview, just say 'stop' or 'end' and I'll stop the interview."
            f"I'm more interested in how you approach problems than perfect answers. "
            f"So... let's start. Tell me about the most complex system you've built or worked on."
        )
    
    def _customize_greeting(self, name: Optional[str], context: ConversationContext) -> str:
        return (
            "Welcome to have this Interview with me here! 🎯 "
            "I'm your AI interviewer today. "
            "This is a 45-minute deep-dive into your personal technical and soft skills, according to your own experience. "
            "We'll cover: 3 Screening questions, 3 soft skill questions, and 4 technical questions. "
            "You can let me know whenever you want to stop the interview, just say 'stop' or 'end' and I'll stop the interview."
            "Now, please tell me know a little bit more about you: "
            "Before we start, please send me your latest resume, the job descriptions which you'd like to apply right now, and any of the other information you think I should know about you here in attachment."
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
            Dict with: ai_response, tone, needs_follow_up, feedback_hint, is_complete
        """
        # Check if user wants to end interview early
        user_lower = user_response.lower().strip()
        end_keywords = ['stop', 'end', 'finish', 'done', "that's all", 'that is all', 'i\'m done', 'i am done']
        if any(keyword in user_lower for keyword in end_keywords):
            # Generate closing message
            closing = await self.generate_closing(context)
            context.phase = InterviewPhase.COMPLETED
            return {
                "ai_response": closing,
                "tone": "friendly",
                "needs_follow_up": False,
                "feedback_hint": None,
                "question_index": context.current_question_index,
                "is_complete": True,
                "should_end": True
            }
        
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
    
    async def generate_closing(self, context: ConversationContext) -> str:
        """
        Generate closing message when interview ends (naturally or early)
        
        Provides a warm, professional closing and mentions report generation
        """
        questions_answered = len(context.user_responses)
        total_questions = len(context.questions_asked) if context.questions_asked else 10
        
        # Build summary of what was covered
        summary_parts = []
        if questions_answered > 0:
            summary_parts.append(f"we covered {questions_answered} question{'s' if questions_answered > 1 else ''}")
        
        # Generate personalized closing based on interview type
        if context.interview_type == "screening":
            closing = (
                f"Thank you so much for your time today! "
                f"I really enjoyed our conversation and learning more about you. "
                f"Your feedback report is being generated now, and you'll be able to review it in your dashboard. "
                f"Great job, and best of luck with your job search!"
            )
        elif context.interview_type == "behavioral":
            closing = (
                f"Thanks for sharing those experiences with me! "
                f"I appreciate you taking the time to walk through those situations. "
                f"Your detailed feedback report is being prepared, and you can access it from your dashboard. "
                f"Keep up the great work!"
            )
        elif context.interview_type == "technical":
            closing = (
                f"Excellent work today! "
                f"I really enjoyed discussing your technical background and approach to problem-solving. "
                f"Your comprehensive feedback report is being generated, and you'll find it in your dashboard. "
                f"Thanks again for your time!"
            )
        else:  # customize
            closing = (
                f"Thank you for completing this interview! "
                f"I've gathered great insights about your skills and experience. "
                f"Your personalized feedback report is being generated now, and you can view it in your dashboard. "
                f"Best of luck with your applications!"
            )
        
        return closing


# Singleton
_engine_instance: Optional[ConversationEngine] = None


def get_conversation_engine() -> Optional[ConversationEngine]:
    """Get singleton conversation engine (returns None if disabled)"""
    global _engine_instance
    
    # Check if enabled
    if not settings.use_conversation_engine:
        return None
    
    if _engine_instance is None:
        try:
            _engine_instance = ConversationEngine()
        except Exception as e:
            print(f"Failed to initialize conversation engine: {e}")
            return None
    return _engine_instance
