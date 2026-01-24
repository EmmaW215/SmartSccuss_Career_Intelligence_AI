"""
Question Bank Loader
Loads interview questions from JSON files
Lightweight for Render Free tier
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path


# Question data embedded for portability
SCREENING_QUESTIONS = [
    {
        "id": "scr_1",
        "question": "Tell me about yourself.",
        "category": "introduction",
        "follow_up_prompts": ["What made you choose this career path?"],
        "evaluation_criteria": ["relevance", "communication", "structure"]
    },
    {
        "id": "scr_2",
        "question": "Why are you interested in this role?",
        "category": "motivation",
        "follow_up_prompts": ["What specifically excites you about this opportunity?"],
        "evaluation_criteria": ["research", "enthusiasm", "fit"]
    },
    {
        "id": "scr_3",
        "question": "What are your greatest strengths?",
        "category": "self_assessment",
        "follow_up_prompts": ["Can you give me an example?"],
        "evaluation_criteria": ["self_awareness", "relevance", "examples"]
    },
    {
        "id": "scr_4",
        "question": "Where do you see yourself in five years?",
        "category": "career_goals",
        "follow_up_prompts": ["How does this role fit into that plan?"],
        "evaluation_criteria": ["ambition", "realism", "alignment"]
    },
    {
        "id": "scr_5",
        "question": "Why are you leaving your current position?",
        "category": "transition",
        "follow_up_prompts": ["What would make you stay at a company long-term?"],
        "evaluation_criteria": ["professionalism", "honesty", "forward_looking"]
    }
]

BEHAVIORAL_QUESTIONS = [
    {
        "id": "beh_1",
        "question": "Tell me about a time when you faced a significant challenge at work. How did you handle it?",
        "category": "problem_solving",
        "star_method": True,
        "follow_up_prompts": ["What was the outcome?", "What did you learn?"],
        "evaluation_criteria": ["situation", "task", "action", "result"]
    },
    {
        "id": "beh_2",
        "question": "Describe a situation where you had to work with a difficult team member.",
        "category": "teamwork",
        "star_method": True,
        "follow_up_prompts": ["How did you resolve the conflict?"],
        "evaluation_criteria": ["empathy", "communication", "resolution"]
    },
    {
        "id": "beh_3",
        "question": "Tell me about a time when you had to learn something new quickly.",
        "category": "adaptability",
        "star_method": True,
        "follow_up_prompts": ["What resources did you use?"],
        "evaluation_criteria": ["learning_agility", "resourcefulness", "application"]
    },
    {
        "id": "beh_4",
        "question": "Describe a project where you took initiative beyond your normal responsibilities.",
        "category": "leadership",
        "star_method": True,
        "follow_up_prompts": ["What motivated you to step up?"],
        "evaluation_criteria": ["initiative", "impact", "ownership"]
    },
    {
        "id": "beh_5",
        "question": "Tell me about a time when you had to meet a tight deadline.",
        "category": "time_management",
        "star_method": True,
        "follow_up_prompts": ["How did you prioritize?"],
        "evaluation_criteria": ["planning", "execution", "stress_management"]
    },
    {
        "id": "beh_6",
        "question": "Describe a situation where you received critical feedback. How did you respond?",
        "category": "growth_mindset",
        "star_method": True,
        "follow_up_prompts": ["What changes did you make?"],
        "evaluation_criteria": ["receptiveness", "action", "growth"]
    }
]

TECHNICAL_QUESTIONS = [
    {
        "id": "tech_1",
        "question": "Walk me through the most complex technical system you've built or significantly contributed to.",
        "category": "system_design",
        "follow_up_prompts": ["What were the main challenges?", "How did you scale it?"],
        "evaluation_criteria": ["complexity", "architecture", "trade_offs"]
    },
    {
        "id": "tech_2",
        "question": "How do you approach debugging a difficult problem that you've never seen before?",
        "category": "debugging",
        "follow_up_prompts": ["Can you give a specific example?"],
        "evaluation_criteria": ["methodology", "tools", "persistence"]
    },
    {
        "id": "tech_3",
        "question": "Explain a recent technology or framework you learned. How did you apply it?",
        "category": "learning",
        "follow_up_prompts": ["What resources helped most?"],
        "evaluation_criteria": ["depth", "application", "enthusiasm"]
    },
    {
        "id": "tech_4",
        "question": "How do you ensure code quality in your projects?",
        "category": "quality",
        "follow_up_prompts": ["What testing strategies do you use?"],
        "evaluation_criteria": ["practices", "tools", "consistency"]
    },
    {
        "id": "tech_5",
        "question": "Describe your experience with cloud services or infrastructure.",
        "category": "infrastructure",
        "follow_up_prompts": ["How do you handle deployment?"],
        "evaluation_criteria": ["breadth", "depth", "practical_experience"]
    },
    {
        "id": "tech_6",
        "question": "How do you handle technical disagreements with teammates?",
        "category": "collaboration",
        "follow_up_prompts": ["Give me an example."],
        "evaluation_criteria": ["communication", "openness", "resolution"]
    },
    {
        "id": "tech_7",
        "question": "What's your approach to designing for scalability?",
        "category": "architecture",
        "follow_up_prompts": ["What patterns do you prefer?"],
        "evaluation_criteria": ["knowledge", "trade_offs", "experience"]
    },
    {
        "id": "tech_8",
        "question": "How do you stay current with new technologies and industry trends?",
        "category": "growth",
        "follow_up_prompts": ["What have you learned recently?"],
        "evaluation_criteria": ["curiosity", "methods", "application"]
    }
]


def load_all_question_banks() -> Dict[str, List[Dict]]:
    """Load all question banks"""
    return {
        "screening": SCREENING_QUESTIONS,
        "behavioral": BEHAVIORAL_QUESTIONS,
        "technical": TECHNICAL_QUESTIONS
    }


def get_questions_for_type(interview_type: str) -> List[Dict]:
    """Get questions for a specific interview type"""
    banks = load_all_question_banks()
    return banks.get(interview_type, [])


def get_question_by_id(question_id: str) -> Optional[Dict]:
    """Get a specific question by ID"""
    banks = load_all_question_banks()
    
    for questions in banks.values():
        for q in questions:
            if q["id"] == question_id:
                return q
    
    return None


def select_questions(
    interview_type: str,
    count: int,
    categories: Optional[List[str]] = None
) -> List[Dict]:
    """Select questions for an interview"""
    questions = get_questions_for_type(interview_type)
    
    if categories:
        questions = [q for q in questions if q.get("category") in categories]
    
    return questions[:count]


def select_customize_questions(
    profile: Dict,
    screening_count: int = 3,
    behavioral_count: int = 3,
    technical_count: int = 4
) -> List[Dict]:
    """Select and order questions for customize interview"""
    selected = []
    
    # Screening questions
    screening = get_questions_for_type("screening")
    selected.extend(screening[:screening_count])
    
    # Behavioral questions
    behavioral = get_questions_for_type("behavioral")
    selected.extend(behavioral[:behavioral_count])
    
    # Technical questions
    technical = get_questions_for_type("technical")
    
    # Try to match technical questions to profile skills
    skills = profile.get("technical_skills", [])
    if skills:
        # Prioritize relevant questions (simplified matching)
        selected.extend(technical[:technical_count])
    else:
        selected.extend(technical[:technical_count])
    
    # Add order numbers
    for i, q in enumerate(selected):
        q["order"] = i + 1
    
    return selected
