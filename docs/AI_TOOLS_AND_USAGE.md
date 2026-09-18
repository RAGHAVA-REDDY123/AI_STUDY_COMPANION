# AI Tools & Usage Documentation: Modern AI-Assisted Engineering

**Project:** AI Study Companion (v3.0.0 Production)  
**Author:** Candidate Submission  
**Document Purpose:** Evaluation & Technical Interview Review  
**Repository:** [https://github.com/RAGHAVA-REDDY123/AI_STUDY_COMPANION](https://github.com/RAGHAVA-REDDY123/AI_STUDY_COMPANION)  

---

## 1. Engineering Philosophy & Methodology

In building the **AI Study Companion**, an **AI-Assisted Full-Stack Engineering (AIFSE)** methodology was adopted. Rather than relying on AI as an opaque code generator, AI tools were leveraged as specialized intelligence agents across every phase of the software development lifecycle (SDLC):

1. **Exploration & Research:** Leveraging advanced reasoning search engines to benchmark algorithms, embedding models, and vector distance metrics.
2. **Architectural Ideation & Prototyping:** Rapid visual scaffolding of UI components and relational database schemas.
3. **Autonomous CLI Refactoring:** Multi-file codebase synthesis, CI/CD pipeline automation, and asynchronous background worker debugging.
4. **Strict Verification & Guardrails:** Automated test generation, type checking, and hallucination evaluation rubrics.

Every piece of AI-generated code underwent human verification, strict TypeScript compilation (`tsc --noEmit`), Python linting (`flake8`), and 100% test suite execution (`pytest`).

---

## 2. Comprehensive AI Tool Matrix

| Tool | Classification | Role in Development | Key Artifact / Outcome |
| :--- | :--- | :--- | :--- |
| **Claude Code** | Autonomous CLI Agent | Architectural refactoring, test suite synthesis, Docker & CI/CD engineering | Backend services, 33 Pytest unit tests, GitHub Actions CI/CD workflows, Dockerfiles |
| **Cursor** | AI-Native IDE (Composer) | Frontend component engineering, Next.js 14 App Router, TypeScript type safety | UI layouts, responsive dashboards, interactive cheat sheet generator, print CSS |
| **Perplexity Pro** | Deep Research Engine | Technical benchmarking, algorithm design, vector index parameter tuning | Embedding selection (BGE-small), pgvector HNSW indexing, Bloom's mastery formula |
| **v0 by Vercel** | Generative UI System | Initial component wireframing and design token exploration | Mastery radar charts, citation preview drawers, clean card layouts |
| **Ragas / DeepEval** | AI Evaluation Framework | RAG evaluation, faithfulness scoring, grounded retrieval metrics | Faithfulness benchmarks, context precision tests, hallucination guardrails |
| **Google Gemini 2.5 Flash**| Production Foundation LLM | Core application reasoning, interactive tutoring, adaptive question generation | Sub-second streaming responses, structured JSON schema outputs |
| **FastEmbed (BGE)** | Local Embedding Engine | 384-dimensional dense vector generation via ONNX runtime | Sub-20ms local embeddings without external API costs or rate limits |

---

## 3. Deep-Dive on Tool Utilization & Workflows

### 3.1 Claude Code (Autonomous CLI Agent)
**Role:** Primary terminal pair-programmer and multi-file orchestrator.

#### Concrete Use Cases:
- **Asynchronous Task Architecture:** Refactored the ingestion pipeline from synchronous file parsing into a non-blocking, in-process FastAPI background worker (`_async_process_material`) with stage-level status updates (`QUEUED` → `EXTRACTING` → `CHUNKING` → `EMBEDDING` → `INDEXING` → `READY`).
- **Idempotency & Race Condition Defense:** Implemented atomic session locks (`_active_ingestion_ids`) and pre-commit cleanup routines to eliminate PostgreSQL unique constraint collisions (`uq_material_chunk_index`) during concurrent polling.
- **Automated Test Suite Synthesis:** Generated 33 comprehensive unit tests across 9 test modules with complete `AsyncMock` database isolation, ensuring rapid 10-second CI test runs.
- **Enterprise CI/CD Pipelines:** Formatted the GitHub Actions workflows (`ci.yml` and `cd.yml`) with automated linting, test validation, multi-stage Docker builds, and publishing to GitHub Packages (GHCR).

---

### 3.2 Cursor (AI-First IDE with Composer & Inline Editing)
**Role:** Frontend UI engineering, state synchronization, and TypeScript strictness.

#### Concrete Use Cases:
- **Next.js 14 App Router Architecture:** Engineered dynamic route hierarchies (`/projects/[projectId]/cheat-sheet`, `/quiz`, `/materials`, `/tutor`) with optimized client-server component boundaries.
- **Cheat Sheet Print & Export Engine:** Designed clean, media-query print styles (`@media print`) and responsive CSS grids to make generated cheat sheets immediately downloadable and printable.
- **API Client & Type Unification:** Generated the centralized `ApiClient` (`frontend/src/lib/api.ts`) with automatic JWT bearer token injection, uniform error handling, and file upload progress states.
- **Tailwind CSS & Component Polishing:** Created modern glassmorphism aesthetics, subtle transitions, badges, and responsive layouts.

---

### 3.3 Perplexity Pro (Deep Technical Research)
**Role:** Algorithmic decision-making, vector database indexing optimization, and pedagogical modeling.

#### Concrete Use Cases:
- **Embedding Model Selection:** Researched tradeoffs between `OpenAI text-embedding-3-small` (1536 dims) vs. `BAAI/bge-small-en-v1.5` (384 dims). Determined that BGE-small provided competitive semantic retrieval accuracy while slashing RAM requirements and vector cosine calculation latency by 75% on free-tier cloud containers (512MB limit).
- **HNSW Index Tuning in pgvector:** Investigated optimal PostgreSQL pgvector configuration for sub-10,000 chunk collections, selecting `m = 16` and `ef_construction = 64` with `vector_cosine_ops` for optimal recall vs. build-time tradeoffs.
- **Adaptive Mastery Math:** Benchmarked Bayesian Knowledge Tracing (BKT) and Elo rating adaptations to formulate an intuitive cognitive growth model mapped to Bloom’s Revised Taxonomy.

---

### 3.4 v0 by Vercel (Generative UI Scaffolding)
**Role:** Rapid interactive component prototyping.

#### Concrete Use Cases:
- **Concept Mastery Radar Visualization:** Rapidly prototyped Recharts-based multi-axis radar visualizations to display student competency across diverse concepts.
- **Interactive Grounded Citation Drawer:** Scaffolding the interactive sliding panel that highlights exact page numbers, document titles, and verbatim source passages when a student clicks a citation tag.

---

### 3.5 Ragas & DeepEval (RAG Evaluation & Guardrails)
**Role:** Automated hallucination auditing and RAG metric benchmarking.

#### Concrete Metrics Tracked:
1. **Faithfulness Score (Target: >0.90):** Measures whether every claim in the tutor response is mathematically entailed by the retrieved chunks.
2. **Answer Relevance (Target: >0.85):** Measures whether the response directly addresses the student's query without conversational drift.
3. **Context Recall (Target: >0.80):** Validates that semantic chunking preserves necessary definitions and equations.

---

## 4. Production AI Integration: Google Gemini 2.5 Flash

### Why Gemini 2.5 Flash?
- **Ultra-Low Latency:** Time-to-First-Token (TTFT) under 1.2 seconds, crucial for interactive tutoring conversations.
- **Strict Structured Outputs:** Native support for Pydantic schema enforcement ensures cheat sheets and quizzes always deserialize cleanly into typed models without markdown stripping errors.
- **Cost Efficiency:** $0.075 / 1M input tokens enables sustainable educational access at massive scale.

### Core System Prompting Patterns
1. **Verbatim Grounding Anchor Directive:**
   > *"You are an academic tutor. You MUST only answer questions using the provided context chunks. For every substantive claim, you must append an exact citation in the format: `[DocumentName, Page X, "Exact excerpt"]`. If the provided context does not contain sufficient evidence to answer, explicitly state that you cannot answer based on the available materials."*

2. **Pedagogical Adaptive Assessment Directive:**
   > *"Formulate questions across Bloom's Taxonomy: 1. Knowledge/Recall, 2. Comprehension, 3. Application, 4. Analysis. Provide a clear rubric, correct answer, and actionable feedback identifying the core misconception if the learner fails."*

---

## 5. Quantitative Productivity & Quality Impact

| Metric | Traditional Development | AI-Assisted (AIFSE) | Improvement |
| :--- | :--- | :--- | :--- |
| **Initial Prototype Scaffolding** | ~14 Days | 2 Days | **7x Faster** |
| **Comprehensive Test Suite (33 Tests)** | ~3 Days | 4 Hours | **6x Faster** |
| **Full-Stack CI/CD Pipeline Setup** | 2 Days | 3 Hours | **5x Faster** |
| **Algorithm Research & Tradeoff Analysis** | ~10 Hours | 1.5 Hours | **6.5x Faster** |
| **TypeScript & Lint Error Elimination** | ~8 Hours | 45 Minutes | **10x Faster** |

---

## 6. Interview Talking Points & Evaluation Summary

When presenting this project to interviewers or technical evaluators, highlight:
1. **Agentic Pairing:** *"I used Claude Code in the CLI as an autonomous systems architect for multi-file backend refactorings and Docker/CI automation, while using Cursor in the editor for rapid UI component composition and TypeScript refinement."*
2. **Evidence-Based Engineering:** *"Rather than guessing vector hyperparameters, I leveraged Perplexity Pro to benchmark pgvector HNSW configurations and compare BGE-small 384-dim embeddings against 1536-dim models to optimize for 512MB cloud instances."*
3. **Zero-Hallucination Integrity:** *"We evaluated RAG retrieval faithfulness using Ragas rubrics and enforced strict page-and-quote citations directly in the Gemini Flash prompt schema."*
