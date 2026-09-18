from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
from datetime import datetime
from app.models.conversation import MessageRole

class CitationItem(BaseModel):
    material_id: Optional[UUID] = None
    document_title: str
    page_number: int
    snippet: str

class MessageSend(BaseModel):
    content: str
    conversation_id: Optional[UUID] = None

class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    citations: list[dict[str, Any]] = []
    is_unsupported_refusal: bool
    tokens_used: int
    latency_ms: int
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    created_at: datetime
    messages: list[MessageOut] = []

    class Config:
        from_attributes = True
