import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.api.v1.router import api_router

async def _apply_schema_updates():
    from app.core.database import Base, engine
    async with engine.begin() as conn:
        # 1. Create any missing tables (e.g. quiz_mistakes)
        await conn.run_sync(Base.metadata.create_all)
        
        # 2. Add any missing columns individually (asyncpg requires single statement per execute)
        alter_statements = [
            "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS completed_questions INTEGER DEFAULT 0;",
            "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS overall_score DOUBLE PRECISION DEFAULT 0.0;",
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;",
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS source_chunk_ids JSON DEFAULT '[]';",
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_order INTEGER DEFAULT 1;",
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS expected_concepts JSON DEFAULT '[]';",
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'PENDING';",
            "ALTER TABLE question_answers ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;",
            "ALTER TABLE question_answers ADD COLUMN IF NOT EXISTS evaluation JSON DEFAULT '{}';",
            "ALTER TABLE question_answers ADD COLUMN IF NOT EXISTS feedback TEXT;",
            "ALTER TABLE concept_masteries ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION DEFAULT 0.5;",
            "ALTER TABLE concept_masteries ADD COLUMN IF NOT EXISTS last_practiced_at TIMESTAMP WITH TIME ZONE;",
            "ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;",
            "ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE;",
            "ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS quiz_id UUID REFERENCES quizzes(id) ON DELETE SET NULL;",
            "ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS quiz_question_id UUID REFERENCES questions(id) ON DELETE SET NULL;",
            "ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS source VARCHAR(100) DEFAULT 'QUIZ';",
            "ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS request_id VARCHAR(64);",
            "ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS operation VARCHAR(64) DEFAULT 'generate_text';",
            "ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'gemini';",
            "ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS error_type VARCHAR(64);",
            "ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(64);",
            "ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS metadata_json JSON;",
            "ALTER TABLE ai_usage_logs ALTER COLUMN prompt_tokens DROP NOT NULL;",
            "ALTER TABLE ai_usage_logs ALTER COLUMN completion_tokens DROP NOT NULL;",
            "ALTER TABLE ai_usage_logs ALTER COLUMN total_tokens DROP NOT NULL;",
            "ALTER TABLE ai_usage_logs ALTER COLUMN estimated_cost_usd DROP NOT NULL;",
            "CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_request_id ON ai_usage_logs(request_id);",
            "CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_operation ON ai_usage_logs(operation);",
            "CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_error_type ON ai_usage_logs(error_type);"
        ]
        for stmt in alter_statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning] {stmt[:30]}...: {e}", flush=True)

    print("[Schema Migration] Database schema successfully synchronized with adaptive quiz & AI observability models.", flush=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure storage directory exists
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    
    # Auto-ensure database tables, pgvector extension, and seed admin user
    try:
        from app.core.init_db import init_db
        await init_db()
    except Exception as e:
        print(f"[Lifespan Startup Warning] Auto-init db: {e}", flush=True)

    # Auto-ensure relational tables and new columns exist
    try:
        await _apply_schema_updates()
    except Exception as e:
        print(f"[Lifespan Startup Error] Auto-migration check: {e}", flush=True)

    yield

    # Shutdown logic
    from app.core.database import engine
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "3.0-prototype"
    }

@app.get(f"{settings.API_V1_STR}/admin/sync-schema")
@app.post(f"{settings.API_V1_STR}/admin/sync-schema")
async def trigger_schema_sync():
    await _apply_schema_updates()
    return {"status": "success", "message": "Schema synchronized successfully"}

@app.get(f"{settings.API_V1_STR}/admin/init-database")
@app.post(f"{settings.API_V1_STR}/admin/init-database")
async def trigger_init_database():
    from app.core.init_db import init_db
    await init_db()
    await _apply_schema_updates()
    return {"status": "success", "message": "Database initialized, pgvector extension enabled, and seed data created successfully"}

