"""
Base RAG Service for SmartSuccess Interview Backend
Provides common functionality for specialized RAG services
"""

import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.embedding_service import EmbeddingService
from app.core.vector_store import VectorStore, get_vector_store
from app.config import settings


class BaseRAGService(ABC):
    """
    Base class for interview-specific RAG services
    
    Provides:
    - Question bank loading and management
    - Resume/JD context building
    - Personalized question generation
    """
    
    def __init__(self, interview_type: str):
        self.interview_type = interview_type
        self.embedding_service = EmbeddingService()
        self.vector_store = get_vector_store()
        
        # Load question bank
        self.question_bank = self._load_question_bank()
        
        # Collection prefix for this interview type
        self.collection_prefix = f"{interview_type}_rag"
    
    def _load_question_bank(self) -> Dict[str, Any]:
        """Load the question bank JSON for this interview type"""
        # Try multiple possible paths
        possible_paths = [
            Path(settings.data_dir) / self.interview_type / "questions.json",
            Path("data") / self.interview_type / "questions.json",
            Path(__file__).parent.parent.parent / "data" / self.interview_type / "questions.json",
        ]
        
        for path in possible_paths:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        
        print(f"Warning: Could not load question bank for {self.interview_type}")
        return {"questions": [], "evaluation_rubric": {}}
    
    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all questions from the question bank"""
        questions = self.question_bank.get("questions", [])
        
        # Some question banks organize by category
        if not questions and "question_categories" in self.question_bank:
            for category_questions in self.question_bank["question_categories"].values():
                questions.extend(category_questions)
        
        return questions
    
    def get_question_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get a specific question by index"""
        questions = self.get_all_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None
    
    def get_evaluation_rubric(self) -> Dict[str, Any]:
        """Get the evaluation rubric for this interview type"""
        return self.question_bank.get("evaluation_rubric", {})
    
    async def build_user_context(
        self,
        user_id: str,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None
    ) -> str:
        """
        Build context from resume and job description
        Store in vector store for retrieval
        
        Returns:
            Collection ID for the user's context
        """
        collection_id = f"{self.collection_prefix}_{user_id}"
        
        # Clear existing context for this user
        self.vector_store.delete_collection(collection_id)
        
        documents = []
        
        # Process resume
        if resume_text:
            chunks = self.embedding_service.chunk_text_by_sections(
                resume_text, source="resume"
            )
            for chunk_text, metadata in chunks:
                embedding = await self.embedding_service.embed_text(chunk_text)
                documents.append({
                    "content": chunk_text,
                    "embedding": embedding,
                    "metadata": {
                        "source": metadata.source,
                        "section": metadata.section,
                        "type": "resume"
                    }
                })
        
        # Process job description
        if job_description:
            chunks = self.embedding_service.chunk_text_by_sections(
                job_description, source="job_description"
            )
            for chunk_text, metadata in chunks:
                embedding = await self.embedding_service.embed_text(chunk_text)
                documents.append({
                    "content": chunk_text,
                    "embedding": embedding,
                    "metadata": {
                        "source": metadata.source,
                        "section": metadata.section,
                        "type": "job_description"
                    }
                })
        
        # Add to vector store
        if documents:
            self.vector_store.add_documents(collection_id, documents)
        
        return collection_id
    
    async def query_context(
        self,
        user_id: str,
        query: str,
        source_filter: Optional[str] = None,
        k: int = 4
    ) -> str:
        """
        Query the user's context for relevant information
        
        Args:
            user_id: User identifier
            query: Search query
            source_filter: Optional filter ("resume" or "job_description")
            k: Number of results
            
        Returns:
            Concatenated relevant context
        """
        collection_id = f"{self.collection_prefix}_{user_id}"
        
        # Check if collection exists
        if self.vector_store.count_documents(collection_id) == 0:
            return ""
        
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query)
        
        # Build metadata filter
        metadata_filter = None
        if source_filter:
            metadata_filter = {"type": source_filter}
        
        # Search
        results = self.vector_store.search(
            collection_id=collection_id,
            query_embedding=query_embedding,
            k=k,
            metadata_filter=metadata_filter
        )
        
        if not results:
            return ""
        
        # Format context
        context_parts = []
        for result in results:
            source = result.document.metadata.get("source", "unknown").upper()
            section = result.document.metadata.get("section", "")
            section_str = f" - {section}" if section else ""
            context_parts.append(f"[{source}{section_str}]: {result.document.content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    async def get_resume_context(self, user_id: str) -> str:
        """Get context specifically from the resume"""
        return await self.query_context(
            user_id,
            "skills experience education projects achievements",
            source_filter="resume",
            k=4
        )
    
    async def get_job_context(self, user_id: str) -> str:
        """Get context specifically from the job description"""
        return await self.query_context(
            user_id,
            "requirements responsibilities qualifications skills",
            source_filter="job_description",
            k=4
        )
    
    @abstractmethod
    async def get_question(self, index: int) -> str:
        """Get a question by index - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def get_personalized_question(
        self,
        session,
        index: int
    ) -> str:
        """Get a personalized question based on context - implemented by subclasses"""
        pass
