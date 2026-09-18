from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.project import Project
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.tutor import ConversationOut, MessageSend, MessageOut
from app.services.tutor_service import TutorService

from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/projects/{project_id}/tutor", tags=["AI Tutor"])

@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.project_id == project.id,
            Conversation.user_id == current_user.id
        )
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/chat")
async def chat_with_tutor(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    msg_in: MessageSend,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    CRITICAL PRD REQUIREMENT: Grounded AI with Citations and Unsupported-Question Handling.
    Dispatches to TutorService which performs project-isolated vector retrieval,
    evaluates evidence confidence, and streams back grounded tokens with exact page citations.
    """
    tutor_svc = TutorService(db)
    
    # Return streaming response using Server-Sent Events (SSE)
    return StreamingResponse(
        tutor_svc.generate_grounded_response_stream(
            project=project,
            user=current_user,
            query=msg_in.content,
            conversation_id=msg_in.conversation_id
        ),
        media_type="text/event-stream"
    )
