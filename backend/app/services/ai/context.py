import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

@dataclass
class AIRequestContext:
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    feature: str = "general"
    operation: str = "generate_text"
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    prompt_version: Optional[str] = None
    retrieval_version: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

_current_context: ContextVar[Optional[AIRequestContext]] = ContextVar("current_ai_context", default=None)

def get_current_ai_context() -> Optional[AIRequestContext]:
    return _current_context.get()

def set_current_ai_context(ctx: Optional[AIRequestContext]) -> None:
    _current_context.set(ctx)

class ai_request_scope:
    """Context manager for scoping an AI operation to a unified request_id and tracing context."""
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        feature: str = "general",
        operation: str = "generate_text",
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        prompt_version: Optional[str] = None,
        retrieval_version: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ):
        self.ctx = AIRequestContext(
            request_id=request_id or f"req_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            project_id=project_id,
            feature=feature,
            operation=operation,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            retrieval_version=retrieval_version,
            metadata=metadata or {}
        )
        self.token = None

    def __enter__(self) -> AIRequestContext:
        self.token = _current_context.set(self.ctx)
        return self.ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            _current_context.reset(self.token)
