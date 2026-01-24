"""
GPU RAG Service
Custom RAG building with GPU-accelerated embeddings

Cost: $0 (self-hosted)
Features: Document processing, embedding generation, question customization
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional

import torch


class RAGService:
    """
    GPU-accelerated RAG builder for custom interviews
    
    Pipeline:
    1. Document processing (PDF, TXT, MD, DOCX)
    2. Profile extraction
    3. Embedding generation (GPU-accelerated)
    4. Question selection and customization
    """
    
    # Standard questions for customization
    SCREENING_QUESTIONS = [
        {"id": "scr_1", "question": "Tell me about yourself."},
        {"id": "scr_2", "question": "Why are you interested in this role?"},
        {"id": "scr_3", "question": "What are your greatest strengths?"}
    ]
    
    BEHAVIORAL_QUESTIONS = [
        {"id": "beh_1", "question": "Tell me about a time when you faced a significant challenge at work."},
        {"id": "beh_2", "question": "Describe a situation where you had to work with a difficult team member."},
        {"id": "beh_3", "question": "Tell me about a time when you had to learn something new quickly."}
    ]
    
    TECHNICAL_QUESTIONS = [
        {"id": "tech_1", "question": "Walk me through the most complex system you've built."},
        {"id": "tech_2", "question": "How do you approach debugging difficult problems?"},
        {"id": "tech_3", "question": "Explain a recent technology you learned and applied."},
        {"id": "tech_4", "question": "How do you ensure code quality in your projects?"}
    ]
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedding_model = None
        self.llm = None
        
        self._load_models()
    
    def _load_models(self):
        """Load embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            
            print(f"Loading embedding model on {self.device}...")
            self.embedding_model = SentenceTransformer(
                'all-MiniLM-L6-v2',
                device=self.device
            )
            print("Embedding model loaded")
            
        except ImportError:
            print("WARNING: sentence-transformers not installed")
            self.embedding_model = None
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            self.embedding_model = None
    
    async def build(
        self,
        user_id: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build custom RAG from user documents
        
        Args:
            user_id: User identifier
            files: List of file dicts with filename, content, content_type
            
        Returns:
            Dict with profile and customized questions
        """
        # Process documents
        documents = await self._process_documents(files)
        
        # Extract profile
        profile = await self._extract_profile(documents)
        
        # Generate embeddings (if model available)
        if self.embedding_model:
            embeddings = await self._generate_embeddings(documents)
        
        # Select and customize questions
        questions = await self._customize_questions(profile, documents)
        
        return {
            "profile": profile,
            "questions": questions,
            "document_count": len(documents)
        }
    
    async def _process_documents(
        self,
        files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process uploaded documents"""
        documents = []
        
        for file_info in files:
            filename = file_info.get("filename", "unknown")
            content = file_info.get("content", b"")
            content_type = file_info.get("content_type", "")
            
            # Decode content
            if isinstance(content, bytes):
                # Try to extract text
                text = await self._extract_text(content, filename, content_type)
            else:
                text = content
            
            # Detect document type
            doc_type = self._detect_doc_type(filename, text)
            
            documents.append({
                "filename": filename,
                "text": text[:10000],  # Limit text length
                "doc_type": doc_type
            })
        
        return documents
    
    async def _extract_text(
        self,
        content: bytes,
        filename: str,
        content_type: str
    ) -> str:
        """Extract text from file content"""
        # PDF
        if filename.lower().endswith('.pdf') or 'pdf' in content_type:
            return await self._extract_pdf_text(content)
        
        # DOCX
        if filename.lower().endswith('.docx'):
            return await self._extract_docx_text(content)
        
        # Plain text
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content.decode('latin-1', errors='ignore')
    
    async def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(stream=content, filetype="pdf")
            text_parts = []
            
            for page in doc:
                text_parts.append(page.get_text())
            
            doc.close()
            return "\n".join(text_parts)
            
        except ImportError:
            return "[PDF content - PyMuPDF not installed]"
        except Exception as e:
            return f"[PDF extraction error: {e}]"
    
    async def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            import docx
            import io
            
            doc = docx.Document(io.BytesIO(content))
            text_parts = []
            
            for para in doc.paragraphs:
                text_parts.append(para.text)
            
            return "\n".join(text_parts)
            
        except ImportError:
            return "[DOCX content - python-docx not installed]"
        except Exception as e:
            return f"[DOCX extraction error: {e}]"
    
    def _detect_doc_type(self, filename: str, text: str) -> str:
        """Detect document type"""
        fname_lower = filename.lower()
        text_lower = text.lower()
        
        if any(w in fname_lower for w in ["resume", "cv"]):
            return "resume"
        if any(w in fname_lower for w in ["job", "jd", "description"]):
            return "job_description"
        
        resume_words = ["experience", "education", "skills", "employment"]
        jd_words = ["requirements", "responsibilities", "qualifications"]
        
        resume_score = sum(1 for w in resume_words if w in text_lower)
        jd_score = sum(1 for w in jd_words if w in text_lower)
        
        if resume_score > jd_score:
            return "resume"
        elif jd_score > resume_score:
            return "job_description"
        
        return "other"
    
    async def _extract_profile(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract candidate profile from documents"""
        profile = {
            "technical_skills": [],
            "soft_skills": [],
            "industries": [],
            "education": [],
            "career_level": "mid",
            "job_target": {}
        }
        
        # Technical skill keywords
        tech_skills = [
            "python", "java", "javascript", "typescript", "go", "rust", "c++",
            "sql", "nosql", "mongodb", "postgresql", "mysql",
            "aws", "gcp", "azure", "docker", "kubernetes",
            "react", "vue", "angular", "node", "fastapi", "django", "flask",
            "machine learning", "deep learning", "ai", "llm", "rag", "nlp",
            "tensorflow", "pytorch", "langchain", "openai",
            "git", "ci/cd", "agile", "scrum"
        ]
        
        for doc in documents:
            text_lower = doc["text"].lower()
            
            # Extract technical skills
            for skill in tech_skills:
                if skill in text_lower and skill not in profile["technical_skills"]:
                    profile["technical_skills"].append(skill)
            
            # Extract job title from JD
            if doc["doc_type"] == "job_description":
                lines = doc["text"].split("\n")[:15]
                for line in lines:
                    line = line.strip()
                    if 10 < len(line) < 100:
                        job_keywords = ["engineer", "developer", "manager", "scientist", "analyst", "architect"]
                        if any(w in line.lower() for w in job_keywords):
                            profile["job_target"]["title"] = line
                            break
        
        # Estimate career level
        skills_count = len(profile["technical_skills"])
        if skills_count > 10:
            profile["career_level"] = "senior"
        elif skills_count > 5:
            profile["career_level"] = "mid"
        else:
            profile["career_level"] = "junior"
        
        return profile
    
    async def _generate_embeddings(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Any]:
        """Generate embeddings for documents"""
        if self.embedding_model is None:
            return []
        
        texts = [doc["text"][:1000] for doc in documents]  # Limit text length
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.embedding_model.encode,
            texts
        )
        
        return embeddings.tolist()
    
    async def _customize_questions(
        self,
        profile: Dict[str, Any],
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Customize questions based on profile"""
        questions = []
        order = 1
        
        # Screening questions (customized based on profile)
        for q in self.SCREENING_QUESTIONS:
            customized = self._customize_single_question(q, profile, "screening")
            customized["order"] = order
            questions.append(customized)
            order += 1
        
        # Behavioral questions
        for q in self.BEHAVIORAL_QUESTIONS:
            customized = self._customize_single_question(q, profile, "behavioral")
            customized["order"] = order
            questions.append(customized)
            order += 1
        
        # Technical questions (based on skills)
        for q in self.TECHNICAL_QUESTIONS:
            customized = self._customize_single_question(q, profile, "technical")
            customized["order"] = order
            questions.append(customized)
            order += 1
        
        return questions
    
    def _customize_single_question(
        self,
        question: Dict[str, Any],
        profile: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """Customize a single question"""
        original = question["question"]
        customized = original
        
        # Add skill references for technical questions
        if category == "technical" and profile.get("technical_skills"):
            top_skills = profile["technical_skills"][:3]
            if "system" in original.lower() or "complex" in original.lower():
                skills_text = ", ".join(top_skills)
                customized = f"{original} Particularly interested in your work with {skills_text}."
        
        # Add job context
        job_title = profile.get("job_target", {}).get("title", "")
        if job_title and "role" in original.lower():
            customized = original.replace("this role", f"the {job_title} position")
        
        return {
            "original_id": question["id"],
            "category": category,
            "original_question": original,
            "customized_question": customized,
            "why_this_question": f"Relevant for {profile.get('career_level', 'mid')}-level candidate"
        }
