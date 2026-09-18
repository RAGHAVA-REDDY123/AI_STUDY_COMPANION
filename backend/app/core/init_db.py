import asyncio
from sqlalchemy import select, text
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.space import Space
from app.models.project import Project
from app.models.concept import Concept
from app.models.mastery import ConceptMastery, GrowthState
from app.models.chunk import DocumentChunk
from app.models.material import Material

async def init_db():
    print(f"Initializing PostgreSQL database with pgvector ({settings.EMBEDDING_DIMENSION}-dim)...")
    async with engine.begin() as conn:
        # 1. Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # 2. Create all relational tables
        await conn.run_sync(Base.metadata.create_all)
        # 3. Ensure HNSW index exists on document_chunks.embedding
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
            ON document_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """))

    print("PostgreSQL tables and pgvector HNSW index initialized successfully.")

    async with AsyncSessionLocal() as db:
        # 1. Seed Superuser Admin
        stmt_admin = select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
        admin_user = (await db.execute(stmt_admin)).scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                password_hash=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                full_name="AI.Prof System Administrator",
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            print(f"Created initial admin user: {settings.FIRST_SUPERUSER_EMAIL}")

        # 2. Seed Demo Learner
        demo_email = "learner@aiprof.com"
        stmt_learner = select(User).where(User.email == demo_email)
        demo_learner = (await db.execute(stmt_learner)).scalar_one_or_none()
        if not demo_learner:
            demo_learner = User(
                email=demo_email,
                password_hash=get_password_hash("Learner123!"),
                full_name="Alex Mercer (Candidate)",
                role=UserRole.LEARNER
            )
            db.add(demo_learner)
            await db.flush()

            # Seed Sample Space
            demo_space = Space(
                user_id=demo_learner.id,
                name="Machine Learning & Deep Learning",
                description="Core theoretical foundations and practical architectures.",
                visual_tag="ai-engineering"
            )
            db.add(demo_space)
            await db.flush()

            # Seed Sample Project
            demo_project = Project(
                space_id=demo_space.id,
                user_id=demo_learner.id,
                name="Backpropagation & Neural Optimization",
                description="Mastering gradient computation, activation functions, and regularization.",
                learning_goal="Understand multi-layer perceptron gradients, avoid vanishing gradients, and compare optimizer convergence."
            )
            db.add(demo_project)
            await db.flush()

            # Seed Sample Concepts
            concepts = [
                Concept(
                    project_id=demo_project.id,
                    name="Backpropagation & Chain Rule",
                    description="Iterative application of calculus chain rule to calculate loss gradients with respect to parameters.",
                    importance_score=0.95
                ),
                Concept(
                    project_id=demo_project.id,
                    name="Vanishing Gradient Problem",
                    description="Phenomenon in deep networks where gradient signals diminish exponentially in early layers with saturating activations.",
                    importance_score=0.88
                ),
                Concept(
                    project_id=demo_project.id,
                    name="Adam & Momentum Optimizers",
                    description="Adaptive learning rate optimization methods maintaining moving averages of past gradients.",
                    importance_score=0.82
                )
            ]
            db.add_all(concepts)
            await db.flush()

            # Seed Initial Mastery
            mastery1 = ConceptMastery(
                project_id=demo_project.id,
                concept_id=concepts[0].id,
                user_id=demo_learner.id,
                mastery_score=78.5,
                trend_state=GrowthState.IMPROVING,
                total_attempts=3,
                successful_attempts=2
            )
            mastery2 = ConceptMastery(
                project_id=demo_project.id,
                concept_id=concepts[1].id,
                user_id=demo_learner.id,
                mastery_score=42.0,
                trend_state=GrowthState.REQUIRING_ATTENTION,
                total_attempts=2,
                successful_attempts=0,
                consecutive_mistakes=2
            )
            mastery3 = ConceptMastery(
                project_id=demo_project.id,
                concept_id=concepts[2].id,
                user_id=demo_learner.id,
                mastery_score=65.0,
                trend_state=GrowthState.STABLE,
                total_attempts=1,
                successful_attempts=1
            )
            db.add_all([mastery1, mastery2, mastery3])
            print("Created demo learner, space, project, concepts, and initial mastery metrics.")

        await db.commit()
    print("Local database initialization completed successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
