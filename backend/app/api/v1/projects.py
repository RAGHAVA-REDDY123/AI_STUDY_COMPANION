from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.space import Space
from app.models.project import Project
from app.models.material import Material
from app.models.concept import Concept
from app.models.mastery import ConceptMastery
from app.models.recommendation import Recommendation, RecommendationStatus
from app.schemas.project import ProjectCreate, ProjectOut, ProjectSummaryOut

router = APIRouter(tags=["Projects"])

@router.get("/spaces/{space_id}/projects", response_model=list[ProjectOut])
async def list_projects_for_space(
    space_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Project).where(
        Project.space_id == space_id,
        Project.user_id == current_user.id
    ).order_by(Project.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/spaces/{space_id}/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    space_id: UUID,
    project_in: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Verify Space belongs to user
    stmt_space = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await db.execute(stmt_space)).scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")

    new_project = Project(
        space_id=space_id,
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        learning_goal=project_in.learning_goal
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    from app.services.event_service import event_service, EventType
    await event_service.log_event(
        db=db,
        user_id=current_user.id,
        project_id=new_project.id,
        event_type=EventType.PROJECT_CREATED,
        payload={"project_name": new_project.name, "learning_goal": new_project.learning_goal}
    )

    return new_project

@router.get("/projects/{project_id}/summary", response_model=ProjectSummaryOut)
async def get_project_summary(
    project: Annotated[Project, Depends(verify_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Aggregate counts for materials & concepts
    mat_count = (await db.execute(
        select(func.count(Material.id)).where(Material.project_id == project.id)
    )).scalar() or 0

    concept_count = (await db.execute(
        select(func.count(Concept.id)).where(Concept.project_id == project.id)
    )).scalar() or 0

    avg_mastery = (await db.execute(
        select(func.avg(ConceptMastery.mastery_score)).where(ConceptMastery.project_id == project.id)
    )).scalar() or 0.0

    # Fetch top pending recommendation
    rec_stmt = select(Recommendation).where(
        Recommendation.project_id == project.id,
        Recommendation.status == RecommendationStatus.PENDING
    ).order_by(Recommendation.created_at.desc()).limit(1)
    rec = (await db.execute(rec_stmt)).scalar_one_or_none()

    rec_data = None
    if rec:
        rec_data = {
            "id": str(rec.id),
            "title": rec.title,
            "reasoning": rec.reasoning,
            "action_type": rec.action_type.value,
            "target_payload": rec.target_payload
        }

    return {
        "id": project.id,
        "name": project.name,
        "learning_goal": project.learning_goal,
        "total_materials": mat_count,
        "total_concepts": concept_count,
        "average_mastery": round(float(avg_mastery), 1),
        "active_recommendation": rec_data
    }
