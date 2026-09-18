from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class RetrievalCandidate(BaseModel):
    chunk_id: UUID
    material_id: UUID
    page_number: int
    chunk_index: int
    section_title: str
    document_title: str
    content: str
    vector_similarity: float
    fts_rank: float
    rrf_score: float

class GroundedCitation(BaseModel):
    document_title: str
    page_number: int
    section_title: Optional[str] = None
    snippet: str
    is_verified: bool = True
