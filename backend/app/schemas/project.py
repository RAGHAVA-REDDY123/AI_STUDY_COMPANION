from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class SpaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    visual_tag: Optional[str] = "default"

class SpaceOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    visual_tag: str
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    learning_goal: str

class ProjectOut(BaseModel):
    id: UUID
    space_id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    learning_goal: str
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectSummaryOut(BaseModel):
    id: UUID
    name: str
    learning_goal: str
    total_materials: int
    total_concepts: int
    average_mastery: float
    active_recommendation: Optional[dict] = None
