import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(Uuid, ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    importance_score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_concept_name"),
    )

    project = relationship("Project", back_populates="concepts")
    masteries = relationship("ConceptMastery", back_populates="concept", cascade="all, delete-orphan")
