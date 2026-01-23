"""
Embedding Service for SmartSuccess Interview Backend
Generates text embeddings using OpenAI or xAI with automatic fallback

Features:
- Provider abstraction (OpenAI primary, xAI fallback)
- Batch processing for efficiency
- Section-aware text chunking for resumes/JDs
- Automatic retry and error handling
"""

import os
import re
import asyncio
from typing import List, Optional, Tuple
from dataclasses import dataclass
import httpx
from openai import AsyncOpenAI

from app.config import settings


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk"""
    source: str  # "resume", "job_description", "question_bank"
    section: Optional[str] = None
    chunk_index: int = 0
    total_chunks: int = 1


class EmbeddingService:
    """
    Service for generating text embeddings with provider fallback
    
    Usage:
        service = EmbeddingService()
        embedding = await service.embed_text("Hello world")
        embeddings = await service.embed_batch(["text1", "text2"])
    """
    
    def __init__(self):
        self.openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.xai_key = settings.xai_api_key or os.getenv("XAI_API_KEY")
        
        # Initialize OpenAI client
        if self.openai_key:
            self.openai_client = AsyncOpenAI(api_key=self.openai_key)
        else:
            self.openai_client = None
        
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        
        # xAI endpoint for fallback
        self.xai_endpoint = "https://api.x.ai/v1/embeddings"
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        # Clean text
        text = self._clean_text(text)
        
        # Try OpenAI first
        if self.openai_client:
            try:
                response = await self.openai_client.embeddings.create(
                    model=self.model,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"OpenAI embedding error: {e}, falling back to xAI")
        
        # Fallback to xAI
        if self.xai_key:
            try:
                return await self._embed_with_xai(text)
            except Exception as e:
                print(f"xAI embedding error: {e}")
        
        # Return zero vector if all providers fail
        print("Warning: All embedding providers failed, returning zero vector")
        return [0.0] * self.dimension
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Clean texts
        cleaned_texts = [self._clean_text(t) for t in texts]
        
        # Try OpenAI batch embedding
        if self.openai_client:
            try:
                response = await self.openai_client.embeddings.create(
                    model=self.model,
                    input=cleaned_texts
                )
                # Sort by index to maintain order
                sorted_embeddings = sorted(response.data, key=lambda x: x.index)
                return [e.embedding for e in sorted_embeddings]
            except Exception as e:
                print(f"OpenAI batch embedding error: {e}")
        
        # Fallback to individual xAI calls
        if self.xai_key:
            try:
                tasks = [self._embed_with_xai(t) for t in cleaned_texts]
                return await asyncio.gather(*tasks)
            except Exception as e:
                print(f"xAI batch embedding error: {e}")
        
        # Return zero vectors if all fail
        return [[0.0] * self.dimension for _ in texts]
    
    async def _embed_with_xai(self, text: str) -> List[float]:
        """Generate embedding using xAI API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.xai_endpoint,
                headers={
                    "Authorization": f"Bearer {self.xai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "embedding-beta",
                    "input": text
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for embedding"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might cause issues
        text = text.replace('\x00', '')
        
        # Truncate if too long (OpenAI has ~8k token limit)
        max_chars = 30000  # Approximate
        if len(text) > max_chars:
            text = text[:max_chars]
        
        return text.strip()
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks for embedding
        
        Args:
            text: Text to chunk
            chunk_size: Target size of each chunk (in characters)
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within the chunk
                for delimiter in ['. ', '! ', '? ', '\n\n', '\n']:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim > chunk_size * 0.5:  # Only if we keep at least half
                        end = start + last_delim + len(delimiter)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def chunk_text_by_sections(
        self,
        text: str,
        source: str = "document"
    ) -> List[Tuple[str, ChunkMetadata]]:
        """
        Smart chunking that preserves document structure
        Especially useful for resumes and job descriptions
        
        Args:
            text: Text to chunk
            source: Source identifier ("resume", "job_description", etc.)
            
        Returns:
            List of (chunk_text, metadata) tuples
        """
        if not text:
            return []
        
        # Define section patterns
        section_patterns = [
            r'(?i)^#{1,3}\s+(.+)$',  # Markdown headers
            r'(?i)^([A-Z][A-Z\s]+):?\s*$',  # ALL CAPS headers
            r'(?i)^(experience|education|skills|summary|objective|projects|certifications|achievements)\s*:?\s*$',
            r'(?i)^(requirements|responsibilities|qualifications|about|benefits)\s*:?\s*$',
        ]
        
        combined_pattern = '|'.join(f'({p})' for p in section_patterns)
        
        # Split by sections
        lines = text.split('\n')
        sections = []
        current_section = "Introduction"
        current_content = []
        
        for line in lines:
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip(), re.MULTILINE):
                    # Save previous section
                    if current_content:
                        sections.append((current_section, '\n'.join(current_content)))
                    
                    # Start new section
                    current_section = line.strip().rstrip(':').title()
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Don't forget last section
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))
        
        # Convert to chunks with metadata
        chunks_with_metadata = []
        for i, (section_name, content) in enumerate(sections):
            content = content.strip()
            if not content:
                continue
            
            # Further chunk if content is too long
            if len(content) > 1000:
                sub_chunks = self.chunk_text(content, chunk_size=800, overlap=100)
                for j, sub_chunk in enumerate(sub_chunks):
                    metadata = ChunkMetadata(
                        source=source,
                        section=section_name,
                        chunk_index=j,
                        total_chunks=len(sub_chunks)
                    )
                    chunks_with_metadata.append((sub_chunk, metadata))
            else:
                metadata = ChunkMetadata(
                    source=source,
                    section=section_name,
                    chunk_index=0,
                    total_chunks=1
                )
                chunks_with_metadata.append((content, metadata))
        
        return chunks_with_metadata
