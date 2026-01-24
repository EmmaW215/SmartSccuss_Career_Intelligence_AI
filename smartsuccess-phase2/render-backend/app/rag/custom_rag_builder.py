"""
Custom RAG Builder
Builds personalized interview questions from user documents
Works with GPU server for full features, falls back to simplified mode
"""

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from app.services.llm_service import get_llm_service
from app.services.gpu_client import get_gpu_client
from app.rag.question_bank import (
    get_questions_for_type, 
    SCREENING_QUESTIONS, 
    BEHAVIORAL_QUESTIONS, 
    TECHNICAL_QUESTIONS
)


@dataclass
class UserDocument:
    """Processed user document"""
    filename: str
    content: str
    doc_type: str  # resume, job_description, other
    
    
@dataclass  
class CustomRAGResult:
    """Result from building custom RAG"""
    user_id: str
    profile: Dict[str, Any]
    questions: List[Dict[str, Any]]
    success: bool
    provider: str  # "gpu" or "render"
    error: Optional[str] = None


class CustomRAGBuilder:
    """
    Builds personalized RAG for customize interviews
    
    Full Mode (GPU available):
    - Vector store with user documents
    - LLM-based profile extraction
    - Personalized question selection
    
    Simplified Mode (GPU unavailable):
    - Keyword-based profile extraction
    - Standard question selection
    """
    
    PROFILE_EXTRACTION_PROMPT = """Analyze these documents and extract a candidate profile.

DOCUMENTS:
{documents}

Extract as JSON:
{{
    "name": "name if found",
    "current_role": "current/recent job title",
    "years_experience": "estimated years",
    "technical_skills": ["skill1", "skill2"],
    "industries": ["industry1"],
    "education": ["degree/cert"],
    "key_achievements": ["achievement1"],
    "career_level": "junior/mid/senior/lead",
    "job_target": {{
        "title": "target job from JD",
        "key_requirements": ["req1", "req2"]
    }},
    "strengths": ["strength vs JD"],
    "gaps": ["gap vs JD"]
}}

Return ONLY valid JSON."""

    QUESTION_CUSTOMIZATION_PROMPT = """Customize these interview questions for this candidate.

CANDIDATE PROFILE:
{profile}

QUESTIONS TO CUSTOMIZE:
{questions}

For each question, create a personalized version that:
1. References candidate's specific experience/skills
2. Probes areas relevant to the target job
3. Allows candidate to showcase strengths
4. Explores potential gaps

Return JSON array:
[
    {{
        "original_id": "question id",
        "category": "screening/behavioral/technical",
        "original_question": "original text",
        "customized_question": "personalized version",
        "why_this_question": "brief rationale",
        "order": 1
    }}
]

Return ONLY valid JSON array."""

    def __init__(self):
        self.llm_service = get_llm_service()
        self.gpu_client = get_gpu_client()
    
    async def build(
        self,
        user_id: str,
        files: List[Dict[str, Any]]
    ) -> CustomRAGResult:
        """
        Build custom RAG from user documents
        
        Args:
            user_id: User identifier
            files: List of file dicts with 'filename', 'content', 'content_type'
            
        Returns:
            CustomRAGResult with profile and questions
        """
        # Check GPU availability for full RAG
        gpu_status = await self.gpu_client.check_health()
        
        if gpu_status.get("available") and gpu_status.get("services", {}).get("rag", True):
            try:
                return await self._build_full(user_id, files)
            except Exception as e:
                print(f"Full RAG build failed, falling back: {e}")
        
        # Simplified build (always works)
        return await self._build_simplified(user_id, files)
    
    async def _build_full(
        self,
        user_id: str,
        files: List[Dict[str, Any]]
    ) -> CustomRAGResult:
        """Full RAG build using GPU server"""
        try:
            # Call GPU server to build RAG
            result = await self.gpu_client.build_custom_rag(user_id, files)
            
            return CustomRAGResult(
                user_id=user_id,
                profile=result.get("profile", {}),
                questions=result.get("questions", []),
                success=True,
                provider="gpu"
            )
        except Exception as e:
            raise Exception(f"GPU RAG build failed: {e}")
    
    async def _build_simplified(
        self,
        user_id: str,
        files: List[Dict[str, Any]]
    ) -> CustomRAGResult:
        """Simplified build without GPU (Render-only)"""
        try:
            # Process documents
            documents = self._process_documents(files)
            
            # Extract profile using LLM
            profile = await self._extract_profile(documents)
            
            # Select and customize questions
            questions = await self._select_questions(profile)
            
            return CustomRAGResult(
                user_id=user_id,
                profile=profile,
                questions=questions,
                success=True,
                provider="render"
            )
        except Exception as e:
            # Final fallback - standard questions
            return CustomRAGResult(
                user_id=user_id,
                profile={"career_level": "mid"},
                questions=self._get_standard_questions(),
                success=True,
                provider="render",
                error=f"Used standard questions due to: {e}"
            )
    
    def _process_documents(
        self,
        files: List[Dict[str, Any]]
    ) -> List[UserDocument]:
        """Process and classify uploaded files"""
        documents = []
        
        for file_info in files:
            filename = file_info.get("filename", "unknown")
            content = file_info.get("content", "")
            
            # Handle bytes content
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            # Detect document type
            doc_type = self._detect_type(filename, content)
            
            documents.append(UserDocument(
                filename=filename,
                content=content[:5000],  # Limit for LLM context
                doc_type=doc_type
            ))
        
        return documents
    
    def _detect_type(self, filename: str, content: str) -> str:
        """Detect document type"""
        fname_lower = filename.lower()
        content_lower = content.lower()
        
        # Check filename
        if any(w in fname_lower for w in ["resume", "cv", "curriculum"]):
            return "resume"
        if any(w in fname_lower for w in ["job", "jd", "description", "posting"]):
            return "job_description"
        
        # Check content
        resume_words = ["experience", "education", "skills", "employment", "work history"]
        jd_words = ["requirements", "responsibilities", "qualifications", "we are looking", "must have"]
        
        resume_score = sum(1 for w in resume_words if w in content_lower)
        jd_score = sum(1 for w in jd_words if w in content_lower)
        
        if resume_score > jd_score:
            return "resume"
        elif jd_score > resume_score:
            return "job_description"
        
        return "other"
    
    async def _extract_profile(
        self,
        documents: List[UserDocument]
    ) -> Dict[str, Any]:
        """Extract profile using LLM"""
        # Combine documents
        docs_text = "\n\n---\n\n".join([
            f"[{doc.doc_type.upper()}] {doc.filename}:\n{doc.content}"
            for doc in documents
        ])
        
        prompt = self.PROFILE_EXTRACTION_PROMPT.format(documents=docs_text)
        
        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse JSON
            return self._parse_json(response)
            
        except Exception as e:
            print(f"Profile extraction error: {e}")
            return self._extract_profile_keywords(documents)
    
    def _extract_profile_keywords(
        self,
        documents: List[UserDocument]
    ) -> Dict[str, Any]:
        """Keyword-based profile extraction (fallback)"""
        profile = {
            "technical_skills": [],
            "job_target": {},
            "career_level": "mid"
        }
        
        # Common technical skills
        tech_keywords = [
            "python", "java", "javascript", "typescript", "sql", "aws", "gcp", "azure",
            "machine learning", "ai", "llm", "rag", "fastapi", "react", "docker", 
            "kubernetes", "langchain", "tensorflow", "pytorch", "node", "go", "rust"
        ]
        
        for doc in documents:
            content_lower = doc.content.lower()
            
            # Extract skills
            for skill in tech_keywords:
                if skill in content_lower and skill not in profile["technical_skills"]:
                    profile["technical_skills"].append(skill)
            
            # Extract job title from JD
            if doc.doc_type == "job_description":
                lines = doc.content.split("\n")[:10]
                for line in lines:
                    line = line.strip()
                    if 5 < len(line) < 100:
                        if any(w in line.lower() for w in ["engineer", "developer", "manager", "analyst", "scientist"]):
                            profile["job_target"]["title"] = line
                            break
        
        return profile
    
    async def _select_questions(
        self,
        profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Select and customize questions"""
        # Get base questions
        base_questions = []
        
        # 3 screening
        base_questions.extend([
            {"id": q["id"], "category": "screening", "question": q["question"]}
            for q in SCREENING_QUESTIONS[:3]
        ])
        
        # 3 behavioral
        base_questions.extend([
            {"id": q["id"], "category": "behavioral", "question": q["question"]}
            for q in BEHAVIORAL_QUESTIONS[:3]
        ])
        
        # 4 technical
        base_questions.extend([
            {"id": q["id"], "category": "technical", "question": q["question"]}
            for q in TECHNICAL_QUESTIONS[:4]
        ])
        
        # Try to customize with LLM
        try:
            return await self._customize_questions(profile, base_questions)
        except Exception as e:
            print(f"Question customization failed: {e}")
            # Return base questions with order
            return [
                {
                    "original_id": q["id"],
                    "category": q["category"],
                    "customized_question": q["question"],
                    "order": i + 1
                }
                for i, q in enumerate(base_questions)
            ]
    
    async def _customize_questions(
        self,
        profile: Dict[str, Any],
        questions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Customize questions using LLM"""
        questions_text = "\n".join([
            f"{i+1}. [{q['category']}] {q['question']}"
            for i, q in enumerate(questions)
        ])
        
        prompt = self.QUESTION_CUSTOMIZATION_PROMPT.format(
            profile=json.dumps(profile, indent=2),
            questions=questions_text
        )
        
        response = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.5,
            max_tokens=2500
        )
        
        customized = self._parse_json(response, default=[])
        
        if not customized:
            raise Exception("Failed to parse customized questions")
        
        return customized
    
    def _get_standard_questions(self) -> List[Dict[str, Any]]:
        """Get standard questions (final fallback)"""
        questions = []
        order = 1
        
        for q in SCREENING_QUESTIONS[:3]:
            questions.append({
                "original_id": q["id"],
                "category": "screening",
                "customized_question": q["question"],
                "order": order
            })
            order += 1
        
        for q in BEHAVIORAL_QUESTIONS[:3]:
            questions.append({
                "original_id": q["id"],
                "category": "behavioral",
                "customized_question": q["question"],
                "order": order
            })
            order += 1
        
        for q in TECHNICAL_QUESTIONS[:4]:
            questions.append({
                "original_id": q["id"],
                "category": "technical",
                "customized_question": q["question"],
                "order": order
            })
            order += 1
        
        return questions
    
    def _parse_json(
        self,
        text: str,
        default: Any = None
    ) -> Any:
        """Parse JSON from LLM response"""
        if default is None:
            default = {}
        
        try:
            # Clean up response
            text = text.strip()
            
            # Extract JSON from markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            # Find JSON
            text = text.strip()
            
            # Try to find JSON object or array
            if text.startswith("{"):
                end = text.rfind("}") + 1
                text = text[:end]
            elif text.startswith("["):
                end = text.rfind("]") + 1
                text = text[:end]
            
            return json.loads(text)
            
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            print(f"JSON parse error: {e}")
            return default


# Singleton
_builder_instance: Optional[CustomRAGBuilder] = None


def get_custom_rag_builder() -> CustomRAGBuilder:
    """Get singleton CustomRAGBuilder instance"""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = CustomRAGBuilder()
    return _builder_instance
