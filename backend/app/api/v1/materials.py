import hashlib
import os
import uuid
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user, verify_project_access
from app.models.user import User
from app.models.project import Project
from app.models.material import Material, MaterialStatus, ProcessingStage
from app.models.concept import Concept
from app.schemas.material import MaterialOut, ConceptOut

router = APIRouter(prefix="/projects/{project_id}", tags=["Materials & Knowledge"])

def dispatch_ingestion(material_id: UUID, background_tasks: BackgroundTasks) -> None:
    """Dispatches processing directly via FastAPI async background task for reliable, in-process execution."""
    from app.workers.tasks import _async_process_material
    background_tasks.add_task(_async_process_material, material_id)

@router.get("/materials", response_model=list[MaterialOut])
async def list_materials(
    project: Annotated[Project, Depends(verify_project_access)],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Material).where(Material.project_id == project.id).order_by(Material.created_at.desc())
    result = await db.execute(stmt)
    materials = result.scalars().all()

    # Auto-process any materials currently waiting in QUEUED
    for m in materials:
        if m.status == MaterialStatus.QUEUED:
            dispatch_ingestion(m.id, background_tasks)

    return materials

@router.post("/materials/{material_id}/retry", response_model=MaterialOut)
@router.post("/materials/{material_id}/process", response_model=MaterialOut)
@router.get("/materials/{material_id}/retry", response_model=MaterialOut)
@router.get("/materials/{material_id}/process", response_model=MaterialOut)
async def retry_material_processing(
    material_id: UUID,
    project: Annotated[Project, Depends(verify_project_access)],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Material).where(Material.id == material_id, Material.project_id == project.id)
    material = (await db.execute(stmt)).scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Reset status and stage so frontend immediately sees QUEUED
    material.status = MaterialStatus.QUEUED
    material.current_stage = ProcessingStage.QUEUED
    material.error_message = None
    await db.commit()
    await db.refresh(material)

    dispatch_ingestion(material.id, background_tasks)
    return material

@router.get("/materials/{material_id}/status", response_model=MaterialOut)
async def get_material_status(
    material_id: UUID,
    project: Annotated[Project, Depends(verify_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Query material processing status and current stage."""
    stmt = select(Material).where(Material.id == material_id, Material.project_id == project.id)
    material = (await db.execute(stmt)).scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material

@router.post("/materials", response_model=MaterialOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_material(
    project: Annotated[Project, Depends(verify_project_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for prototype ingestion"
        )

    # Read content & compute hash
    content = await file.read()
    file_size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate upload in this project
    dup_stmt = select(Material).where(
        Material.project_id == project.id,
        Material.file_hash == file_hash
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        if existing.status == MaterialStatus.READY:
            return existing
        # If it was previously stuck or failed, re-enqueue and return
        dispatch_ingestion(existing.id, background_tasks)
        return existing

    # Save to disk
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    saved_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(settings.STORAGE_DIR, saved_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    new_material = Material(
        project_id=project.id,
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_hash=file_hash,
        file_size_bytes=file_size,
        status=MaterialStatus.QUEUED,
        current_stage=ProcessingStage.QUEUED
    )
    db.add(new_material)
    await db.commit()
    await db.refresh(new_material)

    from app.services.event_service import event_service, EventType
    await event_service.log_event(
        db=db,
        user_id=current_user.id,
        project_id=project.id,
        event_type=EventType.MATERIAL_UPLOADED,
        payload={"filename": new_material.filename, "file_size_bytes": new_material.file_size_bytes}
    )

    dispatch_ingestion(new_material.id, background_tasks)

    return new_material

@router.post("/materials/{material_id}/retry", response_model=MaterialOut)
async def retry_material_processing(
    material_id: UUID,
    project: Annotated[Project, Depends(verify_project_access)],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Material).where(Material.id == material_id, Material.project_id == project.id)
    material = (await db.execute(stmt)).scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    material.status = MaterialStatus.QUEUED
    material.current_stage = ProcessingStage.QUEUED
    material.error_message = None
    await db.commit()
    await db.refresh(material)

    dispatch_ingestion(material.id, background_tasks)
    return material

@router.get("/concepts", response_model=list[ConceptOut])
async def list_concepts(
    project: Annotated[Project, Depends(verify_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    stmt = select(Concept).where(Concept.project_id == project.id).order_by(Concept.importance_score.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/materials/{material_id}/raw")
async def get_raw_material_pdf(
    material_id: UUID,
    project: Annotated[Project, Depends(verify_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Streams raw PDF file for in-browser PDF viewers and citation jumping.
    """
    from fastapi.responses import FileResponse
    stmt = select(Material).where(Material.id == material_id, Material.project_id == project.id)
    material = (await db.execute(stmt)).scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    if not os.path.exists(material.file_path):
        raise HTTPException(status_code=404, detail="Material file not found on disk")

    return FileResponse(
        path=material.file_path,
        media_type="application/pdf",
        filename=material.filename,
        headers={
            "Content-Disposition": f"inline; filename=\"{material.filename}\"",
            "Content-Security-Policy": "frame-ancestors 'self' http://localhost:3000 http://127.0.0.1:3000 *;",
            "X-Frame-Options": "ALLOWALL",
        }
    )

@router.get("/materials/{material_id}/reader")
async def get_material_reader_pages(
    material_id: UUID,
    project: Annotated[Project, Depends(verify_project_access)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Fast JSON reader endpoint returning page-by-page text chunks for instant in-browser citation jumping.
    """
    from collections import defaultdict
    from app.models.chunk import DocumentChunk

    stmt = select(Material).where(Material.id == material_id, Material.project_id == project.id)
    material = (await db.execute(stmt)).scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    chunk_stmt = select(DocumentChunk).where(
        DocumentChunk.material_id == material_id,
        DocumentChunk.project_id == project.id
    ).order_by(DocumentChunk.page_number.asc(), DocumentChunk.chunk_index.asc())
    chunks = (await db.execute(chunk_stmt)).scalars().all()

    pages_dict = defaultdict(list)
    for c in chunks:
        pages_dict[c.page_number].append({
            "chunk_id": str(c.id),
            "section_title": c.section_title or "General",
            "content": c.content,
            "token_count": c.token_count
        })

    pages = []
    for p_num in sorted(pages_dict.keys()):
        pages.append({
            "page_number": p_num,
            "chunks": pages_dict[p_num]
        })

    return {
        "material_id": str(material.id),
        "filename": material.filename,
        "total_pages": material.total_pages or len(pages) or 1,
        "pages": pages
    }

