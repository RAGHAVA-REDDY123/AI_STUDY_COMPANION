import asyncio
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, delete

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.material import Material, MaterialStatus, ProcessingStage
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.observability import BackgroundJob, JobStatus
from app.services.ai import ai_service
from app.services.pdf_service import pdf_service
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service

# In-memory lock to prevent simultaneous worker executions for the same material
_active_ingestion_ids: set[UUID] = set()

async def _async_process_material(material_id: UUID) -> None:
    """Async execution of material ingestion pipeline with stage tracking."""
    if material_id in _active_ingestion_ids:
        print(f"[Worker] Ingestion already in progress for {material_id}, skipping duplicate trigger.", flush=True)
        return

    _active_ingestion_ids.add(material_id)
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Material).where(Material.id == material_id)
            material = (await db.execute(stmt)).scalar_one_or_none()
            if not material:
                return

            if material.status == MaterialStatus.READY:
                print(f"[Worker] Material {material_id} is already READY, skipping duplicate processing.", flush=True)
                return

            # Cache scalar attributes to avoid expired attribute accesses on rollback
            filename = material.filename
            file_path = material.file_path
            project_id = material.project_id
            user_id = material.user_id

            # Upsert BackgroundJob for observability
            job_key = f"ingest_{material_id}"
            job_stmt = select(BackgroundJob).where(BackgroundJob.idempotency_key == job_key)
            bg_job = (await db.execute(job_stmt)).scalar_one_or_none()
            if not bg_job:
                bg_job = BackgroundJob(
                    job_type="DOCUMENT_INGESTION",
                    entity_id=material_id,
                    idempotency_key=job_key,
                    status=JobStatus.PROCESSING,
                    attempts=1
                )
                db.add(bg_job)
            else:
                bg_job.status = JobStatus.PROCESSING
                bg_job.attempts += 1

            # Update stage -> EXTRACTING
            material.status = MaterialStatus.PROCESSING
            material.current_stage = ProcessingStage.EXTRACTING
            material.processing_attempts += 1
            material.processing_started_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                print(f"[Worker] Step 1: Extracting text from '{filename}'...", flush=True)
                pages_data = pdf_service.extract_document_pages(file_path)
                total_pages = pages_data["total_pages"]
                material.total_pages = total_pages
                material.character_count = pages_data["total_characters"]

                # Update stage -> CHUNKING
                material.current_stage = ProcessingStage.CHUNKING
                await db.commit()

                print(f"[Worker] Step 2: Semantic chunking for '{filename}' ({total_pages} pages)...", flush=True)
                chunks_dicts, stats = chunking_service.chunk_document_pages(
                    project_id=project_id,
                    material_id=material_id,
                    user_id=user_id,
                    document_title=filename,
                    pages_data=pages_data["pages"]
                )
                material.chunk_count = stats["chunk_count"]

                # Update stage -> EMBEDDING
                material.current_stage = ProcessingStage.EMBEDDING
                await db.commit()

                print(f"[Worker] Step 3: Generating 384-dim BGE embeddings for {len(chunks_dicts)} chunks...", flush=True)
                chunk_texts = [c["content"] for c in chunks_dicts]
                embeddings = await embedding_service.get_embeddings(chunk_texts)

                # Update stage -> INDEXING
                material.current_stage = ProcessingStage.INDEXING
                await db.commit()

                print(f"[Worker] Step 4: Bulk indexing into pgvector for '{filename}'...", flush=True)
                # Idempotency: delete any previous chunks for this material before bulk insertion
                await db.execute(delete(DocumentChunk).where(DocumentChunk.material_id == material_id))
                await db.flush()

                chunk_objects = []
                for i, c_data in enumerate(chunks_dicts):
                    chunk_objects.append(DocumentChunk(
                        material_id=c_data["material_id"],
                        project_id=c_data["project_id"],
                        user_id=c_data["user_id"],
                        page_number=c_data["page_number"],
                        chunk_index=c_data["chunk_index"],
                        section_title=c_data["section_title"],
                        document_title=c_data["document_title"],
                        content=c_data["content"],
                        content_hash=c_data["content_hash"],
                        token_count=c_data["token_count"],
                        embedding=embeddings[i]
                    ))

                db.add_all(chunk_objects)

                # Upsert document-specific concepts
                clean_name = filename.replace(".pdf", "").replace("_", " ").title()
                concepts_to_create = [
                    (f"{clean_name} - Core Architecture", "Foundational principles, system mechanisms, and primary definitions.", 0.95),
                    (f"{clean_name} - Operational Principles", "Step-by-step algorithms, lifecycle flows, and mathematical formulations.", 0.85),
                    (f"{clean_name} - Applied Scenarios", "Concrete implementations, edge cases, and performance tradeoffs.", 0.80)
                ]

                for c_name, c_desc, c_score in concepts_to_create:
                    c_stmt = select(Concept).where(
                        Concept.project_id == project_id,
                        Concept.name == c_name
                    )
                    existing_c = (await db.execute(c_stmt)).scalar_one_or_none()
                    if existing_c:
                        existing_c.material_id = material_id
                        existing_c.description = c_desc
                        existing_c.importance_score = c_score
                    else:
                        new_c = Concept(
                            project_id=project_id,
                            material_id=material_id,
                            name=c_name,
                            description=c_desc,
                            importance_score=c_score
                        )
                        db.add(new_c)

                # Update stage -> READY
                material.status = MaterialStatus.READY
                material.current_stage = ProcessingStage.READY
                material.processing_completed_at = datetime.now(timezone.utc)
                material.error_message = None

                # Update BackgroundJob status -> COMPLETED
                if bg_job:
                    bg_job.status = JobStatus.COMPLETED

                await db.commit()

                # Observability: Log successful document ingestion
                await ai_service.log_usage(
                    db=db,
                    feature="DOCUMENT",
                    operation="ingest_material",
                    latency_ms=int((datetime.now(timezone.utc) - material.processing_started_at).total_seconds() * 1000) if material.processing_started_at else 0,
                    status_code="SUCCESS",
                    project_id=project_id,
                    user_id=user_id,
                    metadata_json={
                        "filename": filename,
                        "total_pages": material.total_pages,
                        "chunk_count": material.chunk_count,
                        "character_count": material.character_count
                    }
                )
                print(f"[Worker] Successfully completed ingestion for '{filename}' -> Status: READY", flush=True)

                # Activity Event Logging
                from app.services.event_service import event_service, EventType
                await event_service.log_event(
                    db=db,
                    user_id=user_id,
                    project_id=project_id,
                    event_type=EventType.MATERIAL_PROCESSED,
                    payload={
                        "filename": filename,
                        "total_pages": material.total_pages,
                        "chunk_count": material.chunk_count,
                        "character_count": material.character_count
                    }
                )

            except BaseException as e:
                print(f"[Worker Error] Ingestion failed for '{filename}': {e}", flush=True)
                await db.rollback()
                stmt_err = select(Material).where(Material.id == material_id)
                mat_err = (await db.execute(stmt_err)).scalar_one_or_none()
                if mat_err:
                    mat_err.status = MaterialStatus.FAILED
                    mat_err.current_stage = ProcessingStage.FAILED
                    mat_err.error_message = str(e)
                    mat_err.processing_completed_at = datetime.now(timezone.utc)
                    await db.commit()

                # Update BackgroundJob -> FAILED
                try:
                    job_stmt = select(BackgroundJob).where(BackgroundJob.idempotency_key == f"ingest_{material_id}")
                    failed_bg_job = (await db.execute(job_stmt)).scalar_one_or_none()
                    if failed_bg_job:
                        failed_bg_job.status = JobStatus.FAILED
                        failed_bg_job.last_error = str(e)
                        await db.commit()

                    # Log failure telemetry
                    await ai_service.log_usage(
                        db=db,
                        feature="DOCUMENT",
                        operation="ingest_material",
                        latency_ms=0,
                        status_code="FAILED",
                        error_type="DOCUMENT_PROCESSING_ERROR",
                        error_details=str(e),
                        project_id=project_id,
                        user_id=user_id,
                        metadata_json={"filename": filename}
                    )
                except Exception as log_err:
                    print(f"[Worker Error] Failed to log failure observability: {log_err}", flush=True)

                raise e
    finally:
        _active_ingestion_ids.discard(material_id)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_material_task(self, material_id_str: str):
    """
    Celery Task entry point with bounded retries and exponential backoff.
    """
    material_id = UUID(material_id_str)
    try:
        async def _run():
            try:
                await _async_process_material(material_id)
            finally:
                from app.core.database import engine
                await engine.dispose()

        asyncio.run(_run())
    except Exception as exc:
        if self.request.retries < self.max_retries:
            countdown = 5 * (2 ** self.request.retries)
            print(f"[Worker Retry] Retrying ingestion for {material_id_str} in {countdown}s (Attempt {self.request.retries + 1}/{self.max_retries})...", flush=True)
            raise self.retry(exc=exc, countdown=countdown)
        raise exc
