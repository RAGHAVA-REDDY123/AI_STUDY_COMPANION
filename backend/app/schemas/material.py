from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.models.material import MaterialStatus, ProcessingStage

class MaterialOut(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    file_size_bytes: int
    total_pages: int
    chunk_count: int = 0
    character_count: int = 0
    status: MaterialStatus
    current_stage: ProcessingStage = ProcessingStage.QUEUED
    processing_attempts: int = 0
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConceptOut(BaseModel):
    id: UUID
    project_id: UUID
    material_id: Optional[UUID]
    name: str
    description: str
    importance_score: float
    created_at: datetime

    class Config:
        from_attributes = True
