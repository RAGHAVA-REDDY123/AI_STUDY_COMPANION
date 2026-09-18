from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.space import Space
from app.schemas.project import SpaceCreate, SpaceOut

router = APIRouter(prefix="/spaces", tags=["Spaces"])

@router.get("", response_model=list[SpaceOut])
async def list_spaces(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Space).where(Space.user_id == current_user.id).order_by(Space.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=SpaceOut, status_code=status.HTTP_201_CREATED)
async def create_space(
    space_in: SpaceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    new_space = Space(
        user_id=current_user.id,
        name=space_in.name,
        description=space_in.description,
        visual_tag=space_in.visual_tag or "default"
    )
    db.add(new_space)
    await db.commit()
    await db.refresh(new_space)
    return new_space

@router.get("/{space_id}", response_model=SpaceOut)
async def get_space(
    space_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await db.execute(stmt)).scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    return space
