import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector as PgVector

from app.core.database import Base
from app.core.config import settings

class AsyncpgVector(PgVector):
    """
    Subclasses pgvector.sqlalchemy.Vector to ensure that when using asyncpg
    with register_vector, Python lists/ndarrays are passed directly to the driver
    rather than being stringified into '[0.1, 0.2]' which causes asyncpg's
    native vector codec to reject the input with 'expected list or ndarray'.
    """
    def bind_processor(self, dialect):
        if dialect.driver == "asyncpg":
            def process(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    clean = value.strip("[]")
                    return [float(x.strip()) for x in clean.split(",") if x.strip()]
                return list(value)
            return process
        return super().bind_processor(dialect)

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if hasattr(value, "to_list"):
                return value.to_list()
            if hasattr(value, "tolist"):
                return value.tolist()
            if hasattr(value, "to_numpy"):
                return list(value.to_numpy())
            if isinstance(value, str):
                clean = value.strip("[]")
                return [float(x.strip()) for x in clean.split(",") if x.strip()]
            try:
                return list(value)
            except Exception:
                return value
        return process

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    material_id = Column(Uuid, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)  # Grounding anchor for citations
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=True)
    document_title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)
    token_count = Column(Integer, nullable=False)
    embedding = Column(AsyncpgVector(settings.EMBEDDING_DIMENSION), nullable=True)  # Strict 384-dim pgvector
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("material_id", "chunk_index", name="uq_material_chunk_index"),
        Index("idx_document_chunks_project_id", "project_id"),
        Index(
            "idx_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )

    material = relationship("Material", back_populates="chunks")
