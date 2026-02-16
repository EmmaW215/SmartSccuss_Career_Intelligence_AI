"""
Multi-Domain Technical Interview Configuration
FIX: D-T1 (Sprint 1) — Hardcoded AI/ML questions now expand to 5 domains
FIX: D-T2 (Sprint 3) — Dynamic first question based on detected domain

Domain detection uses JD keyword matching ($0 cost, no LLM required).
Falls back to AI/ML domain if no JD or no match.
"""

from typing import Dict, List, Optional


# ============================================================
# Domain-Specific Question Banks
# ============================================================

DOMAIN_QUESTION_BANKS: Dict[str, Dict] = {
    "ai_ml": {
        "label": "AI/ML Engineering",
        "domains": [
            "python_engineering", "llm_frameworks", "rag_architecture",
            "ml_production", "model_training", "cloud_deployment"
        ],
        "opener": (
            "To start, what programming languages and ML frameworks "
            "do you work with most frequently?"
        ),
        "fallback_questions": [
            "Walk me through how you'd architect an LLM-powered application from scratch.",
            "How do you approach building a RAG system? What are the key design decisions?",
            "Describe your experience deploying ML models to production. What challenges did you face?",
            "How do you evaluate and compare different LLM models for a specific use case?",
            "Tell me about a data pipeline you've built. How did you ensure data quality?",
            "How would you design a system for fine-tuning an LLM on custom data?",
            "What's your approach to handling model versioning and A/B testing in production?",
            "Explain how you'd build a conversational AI agent with memory and tool use.",
        ]
    },
    "frontend": {
        "label": "Frontend Engineering",
        "domains": [
            "javascript_typescript", "react_vue_angular", "css_design_systems",
            "performance_optimization", "testing", "accessibility"
        ],
        "opener": (
            "To start, which frontend frameworks and tools are you most "
            "experienced with?"
        ),
        "fallback_questions": [
            "Walk me through how you'd architect a complex single-page application.",
            "How do you approach state management in large frontend applications?",
            "Describe your strategy for optimizing web application performance.",
            "How do you ensure cross-browser compatibility and responsive design?",
            "What's your testing strategy for frontend components? Unit, integration, E2E?",
            "How do you handle authentication and authorization in a frontend app?",
            "Describe how you'd implement a design system for a growing organization.",
            "How do you approach accessibility (a11y) in your frontend work?",
        ]
    },
    "backend": {
        "label": "Backend Engineering",
        "domains": [
            "api_design", "database_optimization", "distributed_systems",
            "auth", "caching", "microservices"
        ],
        "opener": (
            "To start, what backend technologies and architectures are you "
            "most comfortable with?"
        ),
        "fallback_questions": [
            "How would you design a RESTful API for a high-traffic service?",
            "Describe your approach to database schema design and optimization.",
            "How do you handle distributed transactions across microservices?",
            "What caching strategies have you used, and when would you choose each?",
            "Walk me through how you'd design a rate limiting system.",
            "How do you approach error handling and logging in a production backend?",
            "Describe a time you had to scale a backend service. What was your approach?",
            "How do you handle data migrations in a production database without downtime?",
        ]
    },
    "devops": {
        "label": "DevOps/SRE",
        "domains": [
            "ci_cd", "container_orchestration", "infrastructure_as_code",
            "monitoring", "security", "cloud_platforms"
        ],
        "opener": (
            "To start, walk me through your typical infrastructure and "
            "deployment stack."
        ),
        "fallback_questions": [
            "How would you design a CI/CD pipeline for a microservices architecture?",
            "Describe your experience with container orchestration (Kubernetes, Docker Swarm, etc.).",
            "How do you approach infrastructure as code? What tools do you prefer and why?",
            "Walk me through your monitoring and alerting strategy for production systems.",
            "How do you handle secrets management in your deployment pipeline?",
            "Describe how you'd implement blue-green or canary deployments.",
            "What's your approach to disaster recovery and high availability?",
            "How do you handle security patching and vulnerability management at scale?",
        ]
    },
    "data_engineering": {
        "label": "Data Engineering",
        "domains": [
            "etl_pipelines", "data_warehousing", "stream_processing",
            "data_quality", "sql_optimization", "orchestration"
        ],
        "opener": (
            "To start, what data processing tools and platforms do you "
            "work with regularly?"
        ),
        "fallback_questions": [
            "How would you design an ETL pipeline for processing terabytes of daily data?",
            "Describe your approach to data warehouse design (star schema, snowflake, etc.).",
            "How do you handle real-time stream processing? What tools have you used?",
            "What strategies do you use to ensure data quality in your pipelines?",
            "Walk me through a complex SQL optimization you've performed.",
            "How do you handle schema evolution in a data pipeline?",
            "Describe your experience with workflow orchestration tools (Airflow, Dagster, etc.).",
            "How do you approach data governance and data cataloging?",
        ]
    }
}


# ============================================================
# Domain Detection from Job Description
# ============================================================

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "ai_ml": [
        "machine learning", "ai ", "artificial intelligence", "llm",
        "nlp", "natural language", "deep learning", "rag",
        "ml engineer", "data scientist", "computer vision",
        "neural network", "tensorflow", "pytorch", "langchain",
        "hugging face", "generative ai", "prompt engineer"
    ],
    "frontend": [
        "frontend", "front-end", "front end", "react", "vue",
        "angular", "next.js", "nuxt", "ui developer", "ux engineer",
        "javascript developer", "typescript", "css", "tailwind",
        "web developer", "ui/ux"
    ],
    "backend": [
        "backend", "back-end", "back end", "api", "microservices",
        "server-side", "java developer", "go developer", "rust",
        "node.js developer", "django", "flask", "fastapi",
        "spring boot", "express.js"
    ],
    "devops": [
        "devops", "sre", "site reliability", "infrastructure",
        "kubernetes", "docker", "ci/cd", "platform engineer",
        "cloud engineer", "aws", "azure", "gcp", "terraform",
        "ansible", "jenkins"
    ],
    "data_engineering": [
        "data engineer", "etl", "data pipeline", "airflow",
        "spark", "warehouse", "data platform", "databricks",
        "snowflake", "bigquery", "kafka", "data architect"
    ]
}


def detect_domain_from_jd(job_context: Optional[Dict] = None) -> str:
    """
    Detect technical domain from job description keywords.
    
    Cost: $0 — pure keyword matching, no LLM calls.
    
    Args:
        job_context: Dict with 'job_description' and/or 'job_title' keys
        
    Returns:
        Domain key string (e.g., 'ai_ml', 'frontend', 'backend')
    """
    if not job_context:
        return "ai_ml"
    
    jd_text = " ".join([
        job_context.get("job_description", ""),
        job_context.get("job_title", ""),
        str(job_context.get("required_skills", "")),
    ]).lower()
    
    if not jd_text.strip():
        return "ai_ml"
    
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw in jd_text)
    
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "ai_ml"


def get_domain_opener(domain: str) -> str:
    """Get the opening question for a detected domain."""
    bank = DOMAIN_QUESTION_BANKS.get(domain, DOMAIN_QUESTION_BANKS["ai_ml"])
    return bank["opener"]


def get_domain_fallback_questions(domain: str) -> List[str]:
    """Get fallback question list for a domain."""
    bank = DOMAIN_QUESTION_BANKS.get(domain, DOMAIN_QUESTION_BANKS["ai_ml"])
    return bank["fallback_questions"]


# ============================================================
# Competency Configuration (for Behavioral — FIX C-B3)
# ============================================================

TARGET_COMPETENCIES = [
    "problem_solving", "teamwork", "adaptability",
    "leadership", "time_management", "growth_mindset"
]

QUESTION_COMPETENCY_MAP: Dict[int, str] = {
    0: "teamwork",
    1: "problem_solving",
    2: "leadership",
    3: "adaptability",
    4: "time_management",
    5: "growth_mindset"
}


# ============================================================
# STAR Coaching Templates (for Behavioral — FIX C-B2)
# ============================================================

STAR_COACHING_TEMPLATES: Dict[str, str] = {
    "situation": (
        "You've described what you did well, but I'd love more context. "
        "Could you set the scene — what was the specific situation or challenge?"
    ),
    "task": (
        "Great context! What specifically was your responsibility or goal "
        "in that situation?"
    ),
    "action": (
        "I can see the situation clearly. Now, what specific steps did YOU take? "
        "Walk me through your personal actions."
    ),
    "result": (
        "You've explained your approach well. What was the outcome? "
        "Any measurable results or lessons learned?"
    )
}


# ============================================================
# Screening Criteria (FIX B-S3 — text-appropriate criteria)
# ============================================================

SCREENING_CRITERIA = {
    "communication_clarity": "How clearly and coherently did the candidate express their thoughts?",
    "relevance": "How directly did the response address the question asked?",
    "specificity": "Did the candidate provide concrete examples, numbers, or details?",
    "professionalism": "Was the tone and language appropriate for a professional interview?",
    "self_awareness": "Did the candidate demonstrate honest self-reflection and awareness?"
}
