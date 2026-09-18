import asyncio
from sqlalchemy import text
from app.core.database import engine, Base

async def run_migration():
    print("Running adaptive quiz schema migration...")
    async with engine.begin() as conn:
        # Create all newly defined tables e.g. quiz_mistakes
        await conn.run_sync(Base.metadata.create_all)

        # Alter quizzes table
        await conn.execute(text("""
            ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS completed_questions INTEGER DEFAULT 0;
        """))
        await conn.execute(text("""
            ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS overall_score DOUBLE PRECISION DEFAULT 0.0;
        """))

        # Alter questions table
        await conn.execute(text("""
            ALTER TABLE questions ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
        """))
        await conn.execute(text("""
            ALTER TABLE questions ADD COLUMN IF NOT EXISTS source_chunk_ids JSON DEFAULT '[]';
        """))
        await conn.execute(text("""
            ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_order INTEGER DEFAULT 1;
        """))
        await conn.execute(text("""
            ALTER TABLE questions ADD COLUMN IF NOT EXISTS expected_concepts JSON DEFAULT '[]';
        """))
        await conn.execute(text("""
            ALTER TABLE questions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'PENDING';
        """))

        # Alter question_answers table
        await conn.execute(text("""
            ALTER TABLE question_answers ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
        """))
        await conn.execute(text("""
            ALTER TABLE question_answers ADD COLUMN IF NOT EXISTS evaluation JSON DEFAULT '{}';
        """))
        await conn.execute(text("""
            ALTER TABLE question_answers ADD COLUMN IF NOT EXISTS feedback TEXT;
        """))

        # Alter concept_masteries table
        await conn.execute(text("""
            ALTER TABLE concept_masteries ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION DEFAULT 0.5;
        """))
        await conn.execute(text("""
            ALTER TABLE concept_masteries ADD COLUMN IF NOT EXISTS last_practiced_at TIMESTAMP WITH TIME ZONE;
        """))

        # Alter mastery_history_points table
        await conn.execute(text("""
            ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
        """))
        await conn.execute(text("""
            ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE;
        """))
        await conn.execute(text("""
            ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS quiz_id UUID REFERENCES quizzes(id) ON DELETE SET NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS quiz_question_id UUID REFERENCES questions(id) ON DELETE SET NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE mastery_history_points ADD COLUMN IF NOT EXISTS source VARCHAR(100) DEFAULT 'QUIZ';
        """))

    print("Adaptive quiz schema migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
