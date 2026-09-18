from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.project import Project
from app.schemas.cheat_sheet import CheatSheetResponse
from app.services.cheat_sheet_service import CheatSheetService

router = APIRouter(prefix="/projects/{project_id}", tags=["Exam Revision & Cheat Sheet"])

@router.get("/cheat-sheet", response_model=CheatSheetResponse)
async def get_project_cheat_sheet(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Retrieves or generates a high-yield, personalized Exam Revision Cheat Sheet.
    Synthesizes project study notes, formulas, and the student's actual diagnosed misconceptions.
    """
    service = CheatSheetService(db)
    return await service.get_or_generate_cheat_sheet(project, current_user, force_regenerate=False)

@router.post("/cheat-sheet/regenerate", response_model=CheatSheetResponse)
async def regenerate_project_cheat_sheet(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Forces a fresh regeneration of the Exam Revision Cheat Sheet
    to incorporate the latest quiz mistakes, mastery updates, and newly ingested notes.
    """
    service = CheatSheetService(db)
    return await service.get_or_generate_cheat_sheet(project, current_user, force_regenerate=True)
