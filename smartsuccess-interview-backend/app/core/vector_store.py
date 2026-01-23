"""
Vector Store for SmartSuccess Interview Backend
In-memory vector database with cosine similarity search

Features:
- Pure NumPy implementation (no external dependencies)
- Collection-based organization (per user/session)
- Metadata filtering support
- Top-k similarity search
"""

import numpy as np
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class VectorDocument:
    """A document with its embedding and metadata"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """Result from a similarity search"""
    document: VectorDocument
    score: float  # Similarity score (0-1, higher is better)
    distance: float  # Distance (0-2, lower is better)


class VectorStore:
    """
    In-memory vector store with cosine similarity search
    
    Usage:
        store = VectorStore()
        store.add_documents("user_123", documents)
        results = store.search("user_123", query_embedding, k=5)
    """
    
    def __init__(self):
        # Collections organized by collection_id (e.g., user_id, session_id)
        self.collections: Dict[str, List[VectorDocument]] = {}
    
    def create_collection(self, collection_id: str) -> None:
        """Create a new collection if it doesn't exist"""
        if collection_id not in self.collections:
            self.collections[collection_id] = []
    
    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection and all its documents"""
        if collection_id in self.collections:
            del self.collections[collection_id]
            return True
        return False
    
    def add_document(
        self,
        collection_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a single document to a collection
        
        Returns:
            Document ID
        """
        self.create_collection(collection_id)
        
        doc_id = str(uuid.uuid4())
        document = VectorDocument(
            id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        
        self.collections[collection_id].append(document)
        return doc_id
    
    def add_documents(
        self,
        collection_id: str,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple documents to a collection
        
        Args:
            collection_id: Collection identifier
            documents: List of dicts with 'content', 'embedding', and optional 'metadata'
            
        Returns:
            List of document IDs
        """
        self.create_collection(collection_id)
        
        doc_ids = []
        for doc in documents:
            doc_id = self.add_document(
                collection_id=collection_id,
                content=doc["content"],
                embedding=doc["embedding"],
                metadata=doc.get("metadata", {})
            )
            doc_ids.append(doc_id)
        
        return doc_ids
    
    def search(
        self,
        collection_id: str,
        query_embedding: List[float],
        k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents using cosine similarity
        
        Args:
            collection_id: Collection to search
            query_embedding: Query vector
            k: Number of results to return
            metadata_filter: Optional filter on metadata fields
            
        Returns:
            List of SearchResult objects, sorted by similarity (highest first)
        """
        if collection_id not in self.collections:
            return []
        
        documents = self.collections[collection_id]
        
        # Apply metadata filter if provided
        if metadata_filter:
            documents = [
                doc for doc in documents
                if self._matches_filter(doc.metadata, metadata_filter)
            ]
        
        if not documents:
            return []
        
        # Convert to numpy for efficient computation
        query_vec = np.array(query_embedding)
        
        # Calculate similarities
        results = []
        for doc in documents:
            doc_vec = np.array(doc.embedding)
            similarity = self._cosine_similarity(query_vec, doc_vec)
            distance = 1 - similarity
            
            results.append(SearchResult(
                document=doc,
                score=similarity,
                distance=distance
            ))
        
        # Sort by score (descending) and return top k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
    
    def get_document(
        self,
        collection_id: str,
        document_id: str
    ) -> Optional[VectorDocument]:
        """Get a specific document by ID"""
        if collection_id not in self.collections:
            return None
        
        for doc in self.collections[collection_id]:
            if doc.id == document_id:
                return doc
        
        return None
    
    def get_all_documents(
        self,
        collection_id: str,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[VectorDocument]:
        """Get all documents in a collection, optionally filtered"""
        if collection_id not in self.collections:
            return []
        
        documents = self.collections[collection_id]
        
        if metadata_filter:
            documents = [
                doc for doc in documents
                if self._matches_filter(doc.metadata, metadata_filter)
            ]
        
        return documents
    
    def count_documents(self, collection_id: str) -> int:
        """Count documents in a collection"""
        if collection_id not in self.collections:
            return 0
        return len(self.collections[collection_id])
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        # Handle zero vectors
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def _matches_filter(
        self,
        metadata: Dict[str, Any],
        filter_dict: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches all filter conditions"""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            
            # Handle list values (any match)
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            # Direct equality
            elif metadata[key] != value:
                return False
        
        return True
    
    def clear_all(self) -> None:
        """Clear all collections (use with caution)"""
        self.collections.clear()


# Singleton instance for shared use
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the singleton vector store instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
