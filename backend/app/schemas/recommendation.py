from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
from datetime import datetime
from app.models.recommendation import RecommendationAction, RecommendationStatus

class RecommendationOut(BaseModel):
    id: UUID
    project_id: UUID
    concept_id: Optional[UUID]
    title: str
    reasoning: str
    action_type: RecommendationAction
    target_payload: dict[str, Any]
    status: RecommendationStatus
    created_at: datetime

    class Config:
        from_attributes = True
