"""
GPU RAG Service
Custom RAG building with GPU-accelerated embeddings + ChromaDB persistence

Cost: $0 (self-hosted)
Features: Document processing, embedding generation, question customization, persistent storage
"""

import os
import json
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

import torch

logger = logging.getLogger("gpu.rag")


# Persistent storage path
CHROMA_PERSIST_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")
)
PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "profiles")


class RAGService:
    """
    GPU-accelerated RAG builder for custom interviews
    
    Pipeline:
    1. Document processing (PDF, TXT, MD, DOCX)
    2. Profile extraction
    3. Embedding generation (GPU-accelerated) + ChromaDB persistence
    4. Question selection and customization
    
    Data persists across GPU Server restarts via ChromaDB and JSON profiles.
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
        self.chroma_client = None
        
        self._load_models()
        self._init_chromadb()
    
    def _load_models(self):
        """Load embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info("Loading embedding model (all-MiniLM-L6-v2) on %s...", self.device)
            t0 = time.perf_counter()
            self.embedding_model = SentenceTransformer(
                'all-MiniLM-L6-v2',
                device=self.device
            )
            logger.info("Embedding model loaded in %.1fs", time.perf_counter() - t0)
            
        except ImportError:
            logger.error("sentence-transformers not installed — embeddings unavailable")
            self.embedding_model = None
        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)
            self.embedding_model = None
    
    def _init_chromadb(self):
        """Initialize ChromaDB with persistent storage"""
        try:
            import chromadb
            
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            os.makedirs(PROFILES_DIR, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            logger.info("ChromaDB initialized (persist: %s)", CHROMA_PERSIST_DIR)
            
        except ImportError:
            logger.warning("DEGRADATION: chromadb not installed — using in-memory only")
            self.chroma_client = None
        except Exception as e:
            logger.error("Failed to initialize ChromaDB: %s", e)
            self.chroma_client = None
    
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
        t_total = time.perf_counter()
        
        # Process documents
        t0 = time.perf_counter()
        documents = await self._process_documents(files)
        logger.debug("Document processing — %.0fms | %d files → %d docs",
                      (time.perf_counter() - t0) * 1000, len(files), len(documents))
        
        # Extract profile
        t0 = time.perf_counter()
        profile = await self._extract_profile(documents)
        logger.debug("Profile extraction — %.0fms | skills=%d level=%s",
                      (time.perf_counter() - t0) * 1000,
                      len(profile.get("technical_skills", [])),
                      profile.get("career_level"))
        
        # Generate embeddings and store in ChromaDB
        rag_id = None
        if self.embedding_model:
            t0 = time.perf_counter()
            embeddings = await self._generate_embeddings(documents)
            logger.debug("Embedding generation — %.0fms | %d vectors",
                          (time.perf_counter() - t0) * 1000, len(embeddings))
            
            t0 = time.perf_counter()
            rag_id = await self._store_in_chromadb(user_id, documents, embeddings)
            logger.debug("ChromaDB storage — %.0fms | collection=%s",
                          (time.perf_counter() - t0) * 1000, rag_id)
        
        # Select and customize questions
        t0 = time.perf_counter()
        questions = await self._customize_questions(profile, documents)
        logger.debug("Question customization — %.0fms | %d questions",
                      (time.perf_counter() - t0) * 1000, len(questions))
        
        # Save profile to disk for persistence
        self._save_profile(user_id, profile, questions)
        
        total_ms = (time.perf_counter() - t_total) * 1000
        logger.info(
            "RAG build pipeline — %.0fms total | user=%s docs=%d questions=%d",
            total_ms, user_id, len(documents), len(questions),
        )
        
        return {
            "profile": profile,
            "questions": questions,
            "document_count": len(documents),
            "rag_id": rag_id
        }
    
    async def _store_in_chromadb(
        self,
        user_id: str,
        documents: List[Dict[str, Any]],
        embeddings: List[Any]
    ) -> Optional[str]:
        """Store document embeddings in ChromaDB for persistent retrieval"""
        if self.chroma_client is None:
            return None
        
        try:
            collection_name = f"user_{user_id.replace('-', '_')[:50]}"
            
            # Delete existing collection for this user (rebuild)
            try:
                self.chroma_client.delete_collection(collection_name)
            except Exception:
                pass
            
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"user_id": user_id, "created_at": datetime.now().isoformat()}
            )
            
            # Add documents with embeddings
            ids = []
            docs = []
            metadatas = []
            embs = []
            
            for i, doc in enumerate(documents):
                doc_id = f"{user_id}_doc_{i}"
                ids.append(doc_id)
                docs.append(doc["text"][:5000])  # ChromaDB text limit
                metadatas.append({
                    "filename": doc["filename"],
                    "doc_type": doc["doc_type"],
                    "user_id": user_id
                })
                if i < len(embeddings):
                    embs.append(embeddings[i])
            
            if embs:
                collection.add(
                    ids=ids,
                    documents=docs,
                    metadatas=metadatas,
                    embeddings=embs
                )
            else:
                collection.add(
                    ids=ids,
                    documents=docs,
                    metadatas=metadatas
                )
            
            logger.info("Stored %d documents in ChromaDB for user %s", len(ids), user_id)
            return collection_name
            
        except Exception as e:
            logger.error("ChromaDB storage error: %s", e)
            return None
    
    def _save_profile(
        self,
        user_id: str,
        profile: Dict[str, Any],
        questions: List[Dict[str, Any]]
    ):
        """Save profile and questions to disk for persistence"""
        try:
            os.makedirs(PROFILES_DIR, exist_ok=True)
            
            profile_path = os.path.join(PROFILES_DIR, f"{user_id}.json")
            data = {
                "user_id": user_id,
                "profile": profile,
                "questions": questions,
                "created_at": datetime.now().isoformat()
            }
            
            with open(profile_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("Profile saved — %s", profile_path)
        except Exception as e:
            logger.error("Failed to save profile for user %s: %s", user_id, e)
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a previously saved user profile"""
        try:
            profile_path = os.path.join(PROFILES_DIR, f"{user_id}.json")
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Failed to load profile for user %s: %s", user_id, e)
        return None
    
    async def query_documents(
        self,
        user_id: str,
        query: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Query stored documents for a user using semantic search"""
        if self.chroma_client is None or self.embedding_model is None:
            return []
        
        try:
            collection_name = f"user_{user_id.replace('-', '_')[:50]}"
            collection = self.chroma_client.get_collection(collection_name)
            
            # Generate query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None,
                lambda: self.embedding_model.encode([query]).tolist()[0]
            )
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, collection.count())
            )
            
            documents = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None
                    })
            
            return documents
            
        except Exception as e:
            logger.error("ChromaDB query error for user %s: %s", user_id, e)
            return []
    
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
