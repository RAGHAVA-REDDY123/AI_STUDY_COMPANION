from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.models.mastery import GrowthState

class ConceptMasteryOut(BaseModel):
    id: UUID
    concept_id: UUID
    concept_name: str
    mastery_score: float
    trend_state: GrowthState
    total_attempts: int
    consecutive_mistakes: int
    last_assessed_at: Optional[datetime]

    class Config:
        from_attributes = True

class ProjectGrowthSummaryOut(BaseModel):
    improving: list[ConceptMasteryOut] = []
    stable: list[ConceptMasteryOut] = []
    requiring_attention: list[ConceptMasteryOut] = []
