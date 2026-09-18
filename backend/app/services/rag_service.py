"""
Deprecated: rag_service.py is replaced by app.services.retrieval_service.RetrievalService.
Provided for backwards compatibility.
"""
from app.services.retrieval_service import RetrievalService

# Alias for backwards compatibility
RAGService = RetrievalService

__all__ = ["RetrievalService", "RAGService"]
