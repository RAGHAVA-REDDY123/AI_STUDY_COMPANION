import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, JSON, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base

class RecommendationAction(str, enum.Enum):
    REVIEW_MATERIAL = "REVIEW_MATERIAL"
    TAKE_QUIZ = "TAKE_QUIZ"
    REVISE_CONCEPT = "REVISE_CONCEPT"

class RecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Uuid, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    reasoning = Column(Text, nullable=False)
    action_type = Column(Enum(RecommendationAction), nullable=False)
    target_payload = Column(JSON, default=dict, nullable=False)  # {material_id, page_number} or {concept_id}
    status = Column(Enum(RecommendationStatus), default=RecommendationStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="recommendations")
