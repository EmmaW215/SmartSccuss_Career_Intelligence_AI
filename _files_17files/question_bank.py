"""
Question Bank Loader (Phase 2 - Enhanced)
Lightweight question bank for Phase 2 features (customize interview)

FIX: D-T1 — Integrated with domain_config.py for multi-domain technical questions
FIX: C-B3 — Added competency metadata to behavioral questions
FIX: B-S3 — Added text-appropriate evaluation criteria to screening questions

Note: Existing RAG services use their own question sources
This is used for Phase 2 customize interview feature AND as fallback for Phase 1
"""

from typing import Dict, List, Optional

# FIX: D-T1 — Import multi-domain config for technical questions
try:
    from .domain_config import (
        DOMAIN_QUESTION_BANKS,
        detect_domain_from_jd,
        DOMAIN_OPENERS,
        TARGET_COMPETENCIES,
        QUESTION_COMPETENCY_MAP,
    )
    HAS_DOMAIN_CONFIG = True
except ImportError:
    HAS_DOMAIN_CONFIG = False


# ──────────────────────────────────────────────
# Screening Questions
# FIX: B-S3 — evaluation_criteria now text-appropriate
#   (replaced "body_language", "eye_contact" with "specificity", "self_awareness")
# ──────────────────────────────────────────────
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
        "evaluation_criteria": ["research", "enthusiasm", "fit"]  # FIX: B-S3
    },
    {
        "id": "scr_3",
        "question": "What are your greatest strengths?",
        "category": "self_assessment",
        "follow_up_prompts": ["Can you give me an example?"],
        "evaluation_criteria": ["self_awareness", "relevance", "specificity"]  # FIX: B-S3
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
    },
]


# ──────────────────────────────────────────────
# Behavioral Questions
# FIX: C-B3 — Added "competency" field to each question for coverage tracking
# ──────────────────────────────────────────────
BEHAVIORAL_QUESTIONS = [
    {
        "id": "beh_1",
        "question": "Tell me about a time when you faced a significant challenge at work. How did you handle it?",
        "category": "problem_solving",
        "competency": "problem_solving",  # FIX: C-B3
        "star_method": True,
        "follow_up_prompts": ["What was the outcome?", "What did you learn?"],
        "evaluation_criteria": ["situation", "task", "action", "result"]
    },
    {
        "id": "beh_2",
        "question": "Describe a situation where you had to work with a difficult team member.",
        "category": "teamwork",
        "competency": "teamwork",  # FIX: C-B3
        "star_method": True,
        "follow_up_prompts": ["How did you resolve the conflict?"],
        "evaluation_criteria": ["empathy", "communication", "resolution"]
    },
    {
        "id": "beh_3",
        "question": "Tell me about a time when you had to learn something new quickly.",
        "category": "adaptability",
        "competency": "adaptability",  # FIX: C-B3
        "star_method": True,
        "follow_up_prompts": ["What resources did you use?"],
        "evaluation_criteria": ["learning_agility", "resourcefulness", "application"]
    },
    {
        "id": "beh_4",
        "question": "Describe a project where you took initiative beyond your normal responsibilities.",
        "category": "leadership",
        "competency": "leadership",  # FIX: C-B3
        "star_method": True,
        "follow_up_prompts": ["What motivated you to step up?"],
        "evaluation_criteria": ["initiative", "impact", "ownership"]
    },
    {
        "id": "beh_5",
        "question": "Tell me about a time when you had to meet a tight deadline.",
        "category": "time_management",
        "competency": "time_management",  # FIX: C-B3
        "star_method": True,
        "follow_up_prompts": ["How did you prioritize?"],
        "evaluation_criteria": ["planning", "execution", "stress_management"]
    },
    {
        "id": "beh_6",
        "question": "Describe a situation where you received critical feedback. How did you respond?",
        "category": "growth_mindset",
        "competency": "growth_mindset",  # FIX: C-B3
        "star_method": True,
        "follow_up_prompts": ["What changes did you make?"],
        "evaluation_criteria": ["receptiveness", "action", "growth"]
    },
]


# ──────────────────────────────────────────────
# Technical Questions (generic fallback)
# FIX: D-T1 — These are used ONLY when domain_config is unavailable
#   or when domain cannot be detected. Prefer DOMAIN_QUESTION_BANKS.
# ──────────────────────────────────────────────
TECHNICAL_QUESTIONS = [
    {
        "id": "tech_1",
        "question": "Walk me through the most complex technical system you've built or significantly contributed to.",
        "category": "system_design",
        "difficulty": "intermediate",  # FIX: D-T5
        "follow_up_prompts": ["What were the main challenges?", "How did you scale it?"],
        "evaluation_criteria": ["complexity", "architecture", "trade_offs"]
    },
    {
        "id": "tech_2",
        "question": "How do you approach debugging a difficult problem that you've never seen before?",
        "category": "debugging",
        "difficulty": "intermediate",  # FIX: D-T5
        "follow_up_prompts": ["Can you give a specific example?"],
        "evaluation_criteria": ["methodology", "tools", "persistence"]
    },
    {
        "id": "tech_3",
        "question": "Explain a recent technology or framework you learned. How did you apply it?",
        "category": "learning",
        "difficulty": "basic",  # FIX: D-T5
        "follow_up_prompts": ["What resources helped most?"],
        "evaluation_criteria": ["depth", "application", "enthusiasm"]
    },
    {
        "id": "tech_4",
        "question": "How do you ensure code quality in your projects?",
        "category": "quality",
        "difficulty": "intermediate",  # FIX: D-T5
        "follow_up_prompts": ["What testing strategies do you use?"],
        "evaluation_criteria": ["practices", "tools", "consistency"]
    },
    {
        "id": "tech_5",
        "question": "Describe your experience with cloud services or infrastructure.",
        "category": "infrastructure",
        "difficulty": "intermediate",  # FIX: D-T5
        "follow_up_prompts": ["How do you handle deployment?"],
        "evaluation_criteria": ["breadth", "depth", "practical_experience"]
    },
    {
        "id": "tech_6",
        "question": "How do you handle technical disagreements with teammates?",
        "category": "collaboration",
        "difficulty": "basic",  # FIX: D-T5
        "follow_up_prompts": ["Give me an example."],
        "evaluation_criteria": ["communication", "openness", "resolution"]
    },
    {
        "id": "tech_7",
        "question": "What's your approach to designing for scalability?",
        "category": "architecture",
        "difficulty": "advanced",  # FIX: D-T5
        "follow_up_prompts": ["What patterns do you prefer?"],
        "evaluation_criteria": ["knowledge", "trade_offs", "experience"]
    },
    {
        "id": "tech_8",
        "question": "How do you stay current with new technologies and industry trends?",
        "category": "growth",
        "difficulty": "basic",  # FIX: D-T5
        "follow_up_prompts": ["What have you learned recently?"],
        "evaluation_criteria": ["curiosity", "methods", "application"]
    },
]


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def load_all_question_banks() -> Dict[str, List[Dict]]:
    """Load all question banks"""
    return {
        "screening": SCREENING_QUESTIONS,
        "behavioral": BEHAVIORAL_QUESTIONS,
        "technical": TECHNICAL_QUESTIONS,
    }


def get_questions_for_type(interview_type: str) -> List[Dict]:
    """Get questions for a specific interview type"""
    banks = load_all_question_banks()
    return banks.get(interview_type, [])


# FIX: D-T1 — Domain-aware technical question selection
def get_domain_technical_questions(domain: str) -> List[Dict]:
    """
    Get technical questions for a specific domain from DOMAIN_QUESTION_BANKS.

    Falls back to generic TECHNICAL_QUESTIONS if domain_config is unavailable
    or the domain is not recognized.
    """
    if not HAS_DOMAIN_CONFIG:
        return TECHNICAL_QUESTIONS

    bank = DOMAIN_QUESTION_BANKS.get(domain)
    if not bank:
        return TECHNICAL_QUESTIONS

    # Convert domain_config format → question_bank format
    questions = []
    for idx, q_text in enumerate(bank["questions"]):
        questions.append({
            "id": f"{domain}_{idx + 1}",
            "question": q_text,
            "category": domain,
            "difficulty": "intermediate",
            "follow_up_prompts": [],
            "evaluation_criteria": ["technical_accuracy", "depth", "practical_experience"],
        })
    return questions


# FIX: C-B3 — Competency-aware behavioral question retrieval
def get_behavioral_by_competency(competency: str) -> Optional[Dict]:
    """Return the first behavioral question matching a target competency."""
    for q in BEHAVIORAL_QUESTIONS:
        if q.get("competency") == competency:
            return q
    return None


def get_uncovered_competencies(covered: set) -> List[str]:
    """
    Return competencies that have NOT yet been covered.
    Uses TARGET_COMPETENCIES from domain_config if available,
    otherwise falls back to the competencies defined in BEHAVIORAL_QUESTIONS.
    """
    if HAS_DOMAIN_CONFIG:
        all_competencies = TARGET_COMPETENCIES
    else:
        all_competencies = [q["competency"] for q in BEHAVIORAL_QUESTIONS if "competency" in q]

    return [c for c in all_competencies if c not in covered]


def select_customize_questions(
    profile: Optional[Dict] = None,
    screening_count: int = 3,
    behavioral_count: int = 3,
    technical_count: int = 4,
    job_context: Optional[Dict] = None,
) -> List[Dict]:
    """
    Select and order questions for customize interview.

    FIX: D-T1 — Uses detected domain for technical question selection
    FIX: C-B3 — Ensures competency coverage for behavioral questions
    """
    selected: List[Dict] = []

    # ── Screening ─────────────────────────────
    screening = get_questions_for_type("screening")
    selected.extend(screening[:screening_count])

    # ── Behavioral (competency-aware) ─────────
    # FIX: C-B3 — Pick one question per unique competency first
    behavioral = get_questions_for_type("behavioral")
    competency_picked: set = set()
    behavioral_selected: List[Dict] = []

    for q in behavioral:
        comp = q.get("competency", "")
        if comp and comp not in competency_picked and len(behavioral_selected) < behavioral_count:
            behavioral_selected.append(q)
            competency_picked.add(comp)

    # Fill remaining slots sequentially if needed
    for q in behavioral:
        if len(behavioral_selected) >= behavioral_count:
            break
        if q not in behavioral_selected:
            behavioral_selected.append(q)

    selected.extend(behavioral_selected)

    # ── Technical (domain-aware) ──────────────
    # FIX: D-T1 — Detect domain from job context or profile
    detected_domain = "ai_ml"  # default
    if HAS_DOMAIN_CONFIG and job_context:
        detected_domain = detect_domain_from_jd(job_context)
    elif HAS_DOMAIN_CONFIG and profile and profile.get("job_target"):
        detected_domain = detect_domain_from_jd({"job_title": profile["job_target"]})

    technical = get_domain_technical_questions(detected_domain)

    # Try to match technical questions to profile skills if available
    if profile and profile.get("technical_skills"):
        # Prioritize questions whose category overlaps with skills
        skills_lower = {s.lower() for s in profile["technical_skills"]}
        scored = []
        for q in technical:
            relevance = sum(
                1 for s in skills_lower
                if s in q.get("question", "").lower() or s in q.get("category", "").lower()
            )
            scored.append((relevance, q))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected.extend([q for _, q in scored[:technical_count]])
    else:
        selected.extend(technical[:technical_count])

    # Add order numbers
    for i, q in enumerate(selected):
        q["order"] = i + 1

    return selected
