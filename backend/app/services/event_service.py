import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import ActivityEvent

logger = logging.getLogger(__name__)

class EventType:
    PROJECT_CREATED = "PROJECT_CREATED"
    MATERIAL_UPLOADED = "MATERIAL_UPLOADED"
    MATERIAL_PROCESSED = "MATERIAL_PROCESSED"
    TUTOR_INTERACTION = "TUTOR_INTERACTION"
    QUIZ_STARTED = "QUIZ_STARTED"
    QUIZ_COMPLETED = "QUIZ_COMPLETED"
    MASTERY_UPDATED = "MASTERY_UPDATED"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    RECOMMENDATION_EXECUTED = "RECOMMENDATION_EXECUTED"

class EventService:
    """
    Centralized event logger for learning actions and audit trail.
    Ensures safe, asynchronous, and non-blocking emission of activity events.
    """

    @staticmethod
    async def log_event(
        db: AsyncSession,
        user_id: UUID,
        event_type: str,
        project_id: Optional[UUID] = None,
        payload: Optional[dict[str, Any]] = None,
        auto_commit: bool = True
    ) -> Optional[ActivityEvent]:
        try:
            event = ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                event_type=event_type,
                payload=payload or {},
                created_at=datetime.now(timezone.utc)
            )
            db.add(event)
            if auto_commit:
                await db.commit()
            return event
        except Exception as e:
            logger.error(f"Failed to record activity event {event_type} for user {user_id}: {e}", exc_info=True)
            # Never let activity event logging crash the primary workflow
            return None

event_service = EventService()
