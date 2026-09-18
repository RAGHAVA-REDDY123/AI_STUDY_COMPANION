# AI Study Companion: Enterprise Architecture & System Design Documentation

**Document Version:** 3.0.0  
**Target Audience:** Evaluators, Technical Architects, Engineering Interviewers  
**System Status:** Production Ready (Live on Render & Vercel)  
**Repository:** [https://github.com/RAGHAVA-REDDY123/AI_STUDY_COMPANION](https://github.com/RAGHAVA-REDDY123/AI_STUDY_COMPANION)  

---

## 1. Executive Summary

The **AI Study Companion** is an enterprise-grade, grounded educational copilot designed to help students and professionals master complex domains without cognitive overload or AI hallucination risks. 

Unlike generic chatbot wrappers, this system implements:
1. **Strict Contextual Grounding (RAG)**: Zero unsourced claims; every response is anchored to page-level citations and direct document quotes.
2. **Project-Level Security Isolation**: Total multi-tenant isolation ensuring study materials from Project A can never leak into Project B.
3. **Adaptive Cognitive Mastery**: Bayesian-inspired knowledge tracing evaluating learner mastery across Bloom’s Revised Taxonomy.
4. **Exam Revision & Synthesis Engine**: Algorithmic generation of four-pillar study cheat sheets with printable exports.
5. **Full-Stack Observability**: Real-time token accounting, latency percentiles, error categorization, and cost analytics.

---

## 2. High-Level Architecture Overview

The system follows a clean, decoupled **3-Tier Cloud Architecture**:

```
+-------------------------------------------------------------------------+
|                         PRESENTATION LAYER                              |
|   Next.js 14 App Router | React 18 | Tailwind CSS | Recharts | Lucide  |
|   Hosted on Vercel Global Edge Network (HTTP/2, CDN, Edge Caching)      |
+-------------------------------------------------------------------------+
                                     │
                             RESTful JSON / HTTPS
                                     ▼
+-------------------------------------------------------------------------+
|                        APPLICATION & AI SERVICE LAYER                   |
|   FastAPI (Python 3.11 Async) | Uvicorn | Pydantic v2 | Celery/Redis   |
|   Hosted on Render Cloud Web Service (Linux Container)                  |
|                                                                         |
|   ┌─────────────────────┐  ┌──────────────────────┐  ┌──────────────┐  |
|   │ Ingestion & Chunking│  │ Hybrid Retrieval RAG │  │ Master Engine│  |
|   └─────────────────────┘  └──────────────────────┘  └──────────────┘  |
|   ┌─────────────────────┐  ┌──────────────────────┐  ┌──────────────┐  |
|   │ Cheat Sheet Synthesizer│ Adaptive Quiz Gen    │  │ Observability│  |
|   └─────────────────────┘  └──────────────────────┘  └──────────────┘  |
+-------------------------------------------------------------------------+
                    │                                 │
     pgvector Cosine (SQLAlchemy)           Google Gemini Flash API
                    ▼                                 ▼
+------------------------------------+  +--------------------------------+
|          PERSISTENCE LAYER         |  |        FOUNDATION AI MODEL     |
| PostgreSQL 16 + pgvector Extension |  | Gemini 2.5 Flash (Google AI)   |
| HNSW Cosine Vector Index (384-dim) |  | Structured JSON & Grounded RAG |
| Relational Store + Audit Logs      |  | Sub-second Token Streaming     |
+------------------------------------+  +--------------------------------+
```

---

## 3. Core Subsystems & Technical Workflows

### 3.1 Document Ingestion & Vector Indexing Pipeline

When a user uploads a PDF study document, the system triggers an asynchronous, stage-tracked ingestion workflow:

```
[PDF Upload] 
     │
     ▼
[SHA-256 Checksum] ──── Duplicate? ──► [Instant Reference Reuse]
     │ (New File)
     ▼
[PyMuPDF Page Extractor] ──► Extracts text, preserves page numbers & layout
     │
     ▼
[Semantic Sliding Window Chunking]
     ├─ Target: 400 tokens (~1600 characters)
     ├─ Overlap: 50 tokens (preserves context across boundaries)
     └─ Metadata: section_title, page_number, document_title, content_hash
     │
     ▼
[FastEmbed / BGE-small Embedding Engine] ──► 384-Dimensional Dense Vectors
     │
     ▼
[PostgreSQL Bulk Upsert] ──► document_chunks table
     ├─ Unique Constraint: uq_material_chunk_index (material_id, chunk_index)
     └─ HNSW Cosine Index: vector_cosine_ops (m=16, ef_construction=64)
     │
     ▼
[Concept Extraction & Seeding] ──► Auto-generates initial Knowledge Nodes
     │
     ▼
[Material Status: READY] ──► Emits Activity Event
```

#### Key Engineering Invariants:
- **Idempotency Guarantee**: If a document is re-uploaded or re-processed, previous chunks are purged atomically in the transaction before new chunks are committed.
- **Race Condition Prevention**: Active ingestion tracking (`_active_ingestion_ids`) ensures concurrent API requests never spawn duplicate ingestion workers for the same document.

---

### 3.2 Grounded AI Tutor with Interactive Citations

The AI Tutor implements strict retrieval-augmented generation to ensure zero hallucinations:

```
[Learner Question] ("Explain Backpropagation")
     │
     ▼
[384-Dim Query Embedding] (BAAI/bge-small-en-v1.5)
     │
     ▼
[Isolated Cosine Similarity Search in pgvector]
     └─ SQL Filter: WHERE project_id = :project_id
     └─ ORDER BY embedding <=> query_embedding ASC LIMIT 5
     │
     ▼
[Grounding Context Assembly]
     └─ Extracts [DocName, Page #, Exact Text Snippets]
     │
     ▼
[Grounded Prompt Injection]
     └─ Prompt enforces: "Cite exact page numbers. If evidence is absent, state unknown."
     │
     ▼
[Gemini 2.5 Flash Inference]
     │
     ▼
[Structured Response with Citations]
     └─ "Backpropagation applies chain rule... [ML_Notes.pdf, Page 14]"
     │
     ▼
[Telemetry Logging] ──► ai_usage_logs (prompt_tokens, completion_tokens, latency_ms)
```

---

### 3.3 Adaptive Assessment & Mastery Engine

Knowledge mastery is continuously updated based on interactive quiz outcomes across **Bloom's Taxonomy**:

```
           [Quiz Attempt Submitted]
                      │
                      ▼
        [Answer Semantic Evaluation]
   (Score: 0.0 to 1.0, Confidence, Feedback)
                      │
                      ▼
       [Bayesian Knowledge Updating]
                      │
     ┌────────────────┴────────────────┐
     ▼                                 ▼
[Success]                          [Failure]
mastery_score += (100 - score)*0.15   mastery_score -= (score)*0.20
consecutive_mistakes = 0           consecutive_mistakes += 1
     │                                 │
     └────────────────┬────────────────┘
                      │
                      ▼
         [Growth Trend Classification]
   ├─ score >= 75% AND improving ──► IMPROVING
   ├─ 50% <= score < 75% ──────────► STABLE
   └─ score < 50% OR mistakes >= 2 ► REQUIRING_ATTENTION
                      │
                      ▼
       [Automated Smart Recommendations]
  "Your mastery in 'Vanishing Gradient' dropped to 42%. 
   Review ML_Notes.pdf (Page 8) and retake assessment."
```

---

### 3.4 Exam Revision & Cheat Sheet Generation Engine

Synthesizes high-density, multi-document knowledge into an exam-ready summary:

```
[Generate Cheat Sheet Request]
     │
     ▼
[Aggregate High-Importance Concepts & Grounded Chunks]
     │
     ▼
[Structured Synthesis Prompt (Gemini 2.5 Flash)]
     ├─ Pillar 1: Core Architectural Summary (100-150 words)
     ├─ Pillar 2: Critical Formulas & Formal Definitions
     ├─ Pillar 3: High-Yield Memory Anchors (Mnemonics & Key Contrasts)
     └─ Pillar 4: Common Traps, Anti-patterns & Exam Pitfalls
     │
     ▼
[Pydantic JSON Validation] (CheatSheetContent Schema)
     │
     ▼
[Persistence in PostgreSQL] (cheat_sheets table)
     │
     ▼
[Interactive Frontend View + One-Click Print CSS Engine]
```

---

## 4. Database Schema & Data Dictionary

The PostgreSQL database enforces relational integrity, foreign key cascades, and pgvector embeddings:

| Table Name | Primary Purpose | Key Constraints & Indexes |
| :--- | :--- | :--- |
| `users` | User credentials, roles, and profiles | `email UNIQUE`, `role IN ('ADMIN', 'LEARNER', 'VIEWER')` |
| `spaces` | High-level learning subject workspaces | `user_id FK -> users(id)` |
| `projects` | Isolated study projects with specific goals | `space_id FK`, `user_id FK` |
| `materials` | Uploaded PDFs with pipeline stage status | `project_id FK`, `file_hash INDEX`, `status` |
| `document_chunks` | 384-dim embedded text fragments | `uq_material_chunk_index`, `HNSW cosine index` |
| `concepts` | Granular knowledge nodes | `project_id FK`, `importance_score` |
| `concept_masteries`| Estimated mastery score & growth state | `(project_id, concept_id, user_id) UNIQUE` |
| `mastery_history_points` | Audit trail of mastery changes over time | `concept_id FK`, `created_at INDEX` |
| `quizzes` | Adaptive quiz sessions | `project_id FK`, `score`, `status` |
| `questions` | Generated questions across Bloom levels | `quiz_id FK`, `difficulty`, `taxonomy_level` |
| `question_answers` | Student submissions and AI evaluations | `question_id FK`, `is_correct`, `score` |
| `cheat_sheets` | Synthesized exam revision sheets | `project_id FK`, `user_id FK`, `JSON content` |
| `ai_usage_logs` | Token accounting and observability | `request_id INDEX`, `operation INDEX`, `created_at` |
| `background_jobs`| Async worker job status & retry tracking | `idempotency_key UNIQUE`, `status` |

---

## 5. Security & Isolation Architecture

### 5.1 Multi-Tenant Project Isolation
To prevent cross-project context pollution:
- Every query to `document_chunks` mandates `WHERE project_id = :project_id`.
- Verified in continuous integration by unit test:
  `test_project_a_never_leaks_project_b_chunks()` which proves that semantically closer chunks in Project B are mathematically impossible to retrieve when querying Project A.

### 5.2 Authentication & Credential Security
- **Algorithm**: HMAC-SHA256 (HS256) JWT Access Tokens with 24-hour expiration.
- **Password Hashing**: Direct `bcrypt` with unique cryptographic salting (`bcrypt.gensalt()`).
- **Authorization**: Role-Based Access Control (`UserRole.ADMIN`, `UserRole.LEARNER`, `UserRole.VIEWER`) verified via FastAPI dependency injection guards.

---

## 6. Continuous Integration, Deployment & Infrastructure

### 6.1 CI/CD Pipeline Workflow (GitHub Actions)
```
[Git Push to main]
        │
        ├──► Job 1: Backend CI (Ubuntu Latest)
        │     ├─ flake8 strict lint check (E9, F63, F7, F82)
        │     └─ pytest test suite (33/33 tests passed in isolation)
        │
        ├──► Job 2: Frontend CI (Ubuntu Latest)
        │     ├─ npx tsc --noEmit (strict typecheck)
        │     └─ npm run build (production Next.js standalone bundle)
        │
        └──► Job 3: Continuous Delivery (CD)
              ├─ Docker build backend -> Publish to GHCR
              └─ Docker build frontend -> Publish to GHCR
```

### 6.2 Cloud Production Hosting
- **Backend API**: Hosted on **Render** (Docker runtime, Python 3.11, Uvicorn, Asyncpg, PostgreSQL 16 + pgvector).
- **Frontend App**: Hosted on **Vercel** (Next.js 14 Standalone, Global Edge Network, HTTPS/SSL).
- **AI Engine**: Google Cloud Vertex/Gemini 2.5 Flash API with token streaming and retry backoff.

---

## 7. Architectural Decisions & Tradeoffs

| Decision | Alternative Considered | Rationale for Selection |
| :--- | :--- | :--- |
| **pgvector on PostgreSQL** | Pinecone / Qdrant / Weaviate | Keeps relational metadata (projects, users, citations) in the same ACID-compliant database, eliminating dual-write synchronization hazards. |
| **FastEmbed (BGE-small-en-v1.5)** | OpenAI text-embedding-3-small | 384 dimensions provide 4x lower memory and faster cosine distance calculation than 1536-dim vectors with zero API token cost. |
| **Next.js 14 App Router** | Vite SPA / Create React App | Server-Side Rendering (SSR) for initial loads, automatic route code-splitting, and native Vercel Edge performance. |
| **Direct Asyncpg Driver** | Psycopg2 / Synchronous drivers | Native asyncio driver enables non-blocking database queries supporting hundreds of concurrent requests on a single worker instance. |
