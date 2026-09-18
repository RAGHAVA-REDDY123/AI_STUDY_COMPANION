# AI Study Companion – AI-Powered Learning & Growth Workspace

> **Version:** 3.0 (Candidate Challenge Edition)  
> **Target:** Production-Grade Full-Stack AI Learning Companion Prototype  
> **Role:** Full Stack AI Engineer  
> **Primary Evaluation Goal:** Continuous Closed Learning Loop without losing context  

The **AI Study Companion** is a persistent, contextual, and measurable learning workspace designed to help users understand, practice, measure, and continuously improve a skill or area of knowledge. 

Rather than a collection of disconnected AI features, the platform integrates learning materials, an AI Tutor, adaptive assessments, concept mastery, growth analysis, recommendations, analytics, persistent learning context, and intelligent background workflows into **one connected feedback loop**:

```
Create Space ➔ Create Project ➔ Add Material (PDF) ➔ Async Ingestion & OCR ➔ Learn with AI Tutor (Multi-turn + Citations)
                                                                                       │
                                                                                       ▼
Continue Learning  Actionable Recommendations  Growth Analysis  Concept Mastery  Adaptive Quiz & Rubric Evaluation
```

---

## Table of Contents
1. [Core Features & PRD Compliance](#core-features--prd-compliance)
2. [Architectural Highlights](#architectural-highlights)
3. [Repository Structure](#repository-structure)
4. [Quickstart Setup](#quickstart-setup)
   - [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
   - [Option B: Local Manual Setup](#option-b-local-manual-setup)
5. [Default Demo Credentials](#default-demo-credentials)
6. [Testing & AI Evaluation Benchmark Suite](#testing--ai-evaluation-benchmark-suite)
7. [The 10-Step Core Learning Loop Walkthrough](#the-10-step-core-learning-loop-walkthrough)
8. [API & SSE Endpoints Reference](#api--sse-endpoints-reference)
9. [Documentation Deliverables (PRD §20)](#documentation-deliverables-prd-20)

---

## Core Features & PRD Compliance

| Feature Area | PRD Section | Implementation Details |
| :--- | :--- | :--- |
| **Spaces & Projects** | §3, §4 | Multi-tenant organization. Spaces represent broad disciplines; Projects represent focused learning goals with strict tenant isolation. |
| **PDF Ingestion & OCR** | §5 | Asynchronous ingestion pipeline (`QUEUED` ➔ `PROCESSING` ➔ `READY`/`FAILED`), PyMuPDF text & structure parsing, Tesseract OCR fallback, pgvector HNSW embeddings, and SHA-256 deduplication. |
| **Grounded AI Tutor** | §6, §7 | Token-by-token SSE streaming via Google Gemini. Combines Project Knowledge + Conversation History + Learner Weaknesses. |
| **In-Browser Original PDF Viewer** | §7 | Built-in PDF reader that anchors directly to `#page=X` with a dedicated **Grounded Evidence Proof Callout Banner** highlighting verbatim cited text. |
| **Calibrated Refusal** | §7 | Explicit prompt boundary isolation (`<context_evidence>`). Out-of-scope or adversarial queries trigger a calibrated refusal ("Insufficient Evidence") with zero hallucinations. |
| **Structured Tool Calling** | §8 | Controlled capabilities (`check_concept_mastery`, `search_study_materials`, `trigger_remedial_quiz`, `record_learner_preference`) with real-time UI execution widgets in chat. |
| **Adaptive Quiz & Assessment** | §9 | Dynamic MCQ and Open-Ended questions. Adaptive selection targets weak concepts rather than simplistic "wrong $\rightarrow$ easy". |
| **Pedagogical Rubric Grader** | §9 | Multi-factor AI grading across 4 cognitive dimensions: *Understanding*, *Accuracy*, *Reasoning*, and *Missing Concepts*. |
| **Mastery & Growth Trajectory** | §10 | Estimated mastery percentages (0–100%) categorized into 3 growth states: **Improving**, **Stable**, and **Requiring Attention**. |
| **Actionable Recommendations** | §10 | Direct answers to *"What should I do next?"* with 1-click targeted remedial quizzes and links to supporting PDF pages. |
| **Persistent Learner Context** | §11 | Persistent `LearnerContext` tracking goals, preferences, known strengths, known weaknesses, and diagnosed misconceptions across sessions. |
| **Analytics & Event Logging** | §12 | Recharts visualizations for mastery progress and quiz score velocity, paired with full-spectrum `ActivityEvent` audit logs. |
| **Background Workflows** | §13 | Asynchronous Celery/FastAPI workers for document processing, quiz evaluation, and the **Repeated-Mistake Remediation Workflow** (auto-diagnoses misconceptions on $\ge 2$ consecutive errors). |
| **AI Observability & Cost Tracking** | §14 | Real-time database telemetry logging model, latency (ms), tokens, estimated USD costs, failure classifications, and prompt versions. |
| **Admin Operations Portal** | §16 | Platform-level monitoring of users, spaces, projects, activity feeds with filters, AI telemetry & cost breakdowns, and live evaluation benchmarks. |
| **Exam Revision & Cheat Sheet Generator** | §10, §18, §21 | **Standout Feature:** Hyper-dense, personalized revision study sheet synthesizing actual student mistake history (`QuizMistake`), examiner trap warnings, cited core formulas with 1-click original PDF jumping, real-time concept mastery indicators, rapid-fire Q&A, and print-to-PDF export. |

---

## Architectural Highlights

```text
                                  +---------------------------------------+
                                  |         Next.js 14 Web Client         |
                                  | (TypeScript, Tailwind, Recharts, SSE) |
                                  +---------------------------------------+
                                                      │
                                                      ▼
+──────────────────────────────────────────────────────────────────────────────────────────────────────────+
│                                            FastAPI Backend API                                           │
│  ├── Auth & Tenancy (JWT, Role Guards, Strict Project Isolation via verify_project_access)              │
│  ├── REST Endpoints (/spaces, /projects, /materials, /quiz, /mastery, /recommendations, /analytics)    │
│  ├── SSE Streaming Tutor (/tutor/chat with token stream, tool calling, and live citations)              │
│  └── Admin Operations (/admin/overview, /admin/activity, /admin/evaluations/benchmarks)                  │
+──────────────────────────────────────────────────────────────────────────────────────────────────────────+
                         │                                                    │
                         ▼                                                    ▼
+──────────────────────────────────────────────────+  +──────────────────────────────────────────────────+
│             PostgreSQL 16 + pgvector             │  │            Asynchronous Worker Pool              │
│  ├── users, spaces, projects, materials          │  │  ├── PDF parsing, chunking & OCR                 │
│  ├── document_chunks (HNSW vector_cosine_ops)    │  │  ├── BGE-small embedding generation              │
│  ├── concepts, concept_masteries, quizzes        │  │  ├── Concept extraction via Gemini                │
│  ├── learner_contexts, quiz_mistakes             │  │  ├── Repeated-Mistake cognitive diagnosis        │
│  └── ai_usage_logs, activity_events              │  │  └── Celery + Redis (FastAPI task fallback)      │
+──────────────────────────────────────────────────+  +──────────────────────────────────────────────────+
```

1. **Strict Multi-Tenant Isolation:** All database queries enforce `WHERE project_id = CAST(:project_id AS uuid)`. Embeddings, conversation history, and mastery data never leak across projects.
2. **Context-Aware Multi-Turn Tutor:** Recent conversation turns are injected under `<conversation_history>`, allowing natural follow-up questions (e.g. *"Can you give an analogy for that?"*) while maintaining factual grounding.
3. **Double-Vetted Citations:** The backend cross-references all LLM citations (`[Source: Title — Page X]`) against actual retrieved chunk metadata to guarantee zero fabricated page numbers.
4. **Resilient AI Engineering:** Built on a unified `AIProvider` interface with bounded exponential backoff retries, rate-limit classification, and fallback execution.

---

## Repository Structure

```
AI_PROF_ASSIGNMENT/
├── backend/
│   ├── app/
│   │   ├── api/v1/             # REST controllers (auth, spaces, materials, tutor, quiz, admin)
│   │   ├── core/               # App config, database sessions, JWT security, initial seed
│   │   ├── models/             # SQLAlchemy ORM models (User, Space, Project, Material, Chunk, Mastery, etc.)
│   │   ├── schemas/            # Pydantic validation & response schemas
│   │   ├── services/           # Core domain logic:
│   │   │   ├── tutor_service.py        # Streaming Tutor orchestration & multi-turn memory
│   │   │   ├── tutor_tools.py          # Structured tool execution engine
│   │   │   ├── retrieval_service.py    # Hybrid pgvector + BM25 keyword search
│   │   │   ├── citation_service.py     # Citation validation & proof verification
│   │   │   ├── remediation_service.py  # Repeated-mistake background diagnosis
│   │   │   └── quiz/                   # Adaptive engine, question generator & rubric evaluator
│   │   ├── ai/                 # Gemini API client, pricing calculator, prompt repository
│   │   └── workers/            # Celery tasks & async ingestion pipeline
│   ├── evaluations/            # Automated AI benchmark suite:
│   │   ├── datasets/           # Curated test cases (tutor, retrieval, assessment, recommendations)
│   │   ├── services/           # Precision, Recall@K, Groundedness & Rubric evaluators
│   │   └── runners/            # CLI evaluation runner (run_evaluations.py)
│   ├── storage/                # Isolated document filesystem storage
│   ├── tests/                  # Pytest test suite (isolation, RAG, quiz, observability)
│   ├── Dockerfile              # Container definition for backend
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js App Router:
│   │   │   ├── (auth)/         # Login & Register views
│   │   │   └── (dashboard)/    # Dashboard, Spaces, Projects, Tutor, Quiz, Mastery, Admin
│   │   ├── components/         # Reusable UI (DocumentViewerModal, Recharts graphs, Navbar)
│   │   ├── lib/                # API client & auth token interceptors
│   │   └── types/              # TypeScript domain types & API contracts
│   └── package.json            # Node.js dependencies
├── docs/                       # PRD Deliverables Documentation:
│   ├── ARCHITECTURE.md         # Full architectural decision records & diagrams
│   ├── AI_USAGE.md             # AI used to build vs AI embedded in the product
│   ├── PROMPTS.md              # Complete log of production system prompts
│   ├── EVALUATION.md           # Benchmark methodologies, scoring formulas & results
│   └── LIMITATIONS.md          # Known limitations & future roadmap
├── docker-compose.yml          # Multi-container orchestration (PostgreSQL, Redis, Backend, Worker, Frontend)
└── README.md                   # Project overview & documentation (this file)
```

---

## Quickstart Setup

### Option A: Docker Compose (Recommended)

Run the entire platform with PostgreSQL (pgvector), Redis, FastAPI backend, background worker, and Next.js frontend in one command:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/ai-study-companion.git
   cd ai-study-companion
   ```

2. **Configure environment variables:**
   Create a root `.env` or set `GEMINI_API_KEY`:
   ```bash
   # On Linux/macOS
   export GEMINI_API_KEY="your-gemini-api-key"

   # On Windows (PowerShell)
   $env:GEMINI_API_KEY="your-gemini-api-key"
   ```

3. **Build and start services:**
   ```bash
   docker compose up --build
   ```

4. **Access the Application:**
   - **Frontend Web UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Local Manual Setup

#### 1. Prerequisites
- **Python:** 3.11 or higher
- **Node.js:** 18.x or higher with `npm`
- **PostgreSQL:** 16 with `pgvector` extension enabled
- **Redis:** (Optional, uses background tasks fallback if unavailable)

#### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY and DATABASE_URL

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend Setup
```bash
cd frontend

# Install Node packages
npm install

# Configure environment
cp .env.example .env.local

# Run Next.js development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Default Demo Credentials

The database auto-seeds both administrator and learner demo accounts on initial startup:

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Learner** | `learner@aiprof.com` | `Learner123!` | Spaces, Projects, Materials, Tutor, Quizzes, Mastery, Analytics |
| **Administrator** | `admin@aiprof.com` | `AdminPassword123!` | Full Learner Access + Admin Operations Portal (`/admin`) |

---

## Testing & AI Evaluation Benchmark Suite

### 1. Backend Automated Tests (Pytest)
Run the full test suite verifying project data isolation, RAG security boundaries, citation verification, and adaptive quiz engines:
```bash
cd backend
python -m pytest tests/ -v
```

### 2. AI Evaluation Benchmark Runner (PRD §14 & §20)
Execute the curated AI benchmark suite across Groundedness, Citation Correctness, Recall@K, and Rubric Grading:
```bash
cd backend

# Run all benchmark suites
python -m evaluations.runners.run_evaluations --type all

# Or run a specific benchmark domain:
python -m evaluations.runners.run_evaluations --type tutor
python -m evaluations.runners.run_evaluations --type retrieval
python -m evaluations.runners.run_evaluations --type assessment
python -m evaluations.runners.run_evaluations --type recommendation
```
*Benchmark runs and metrics are persisted to the database and can be inspected live in the Admin Portal under `/admin`.*

### 3. Frontend Build & Typecheck
Ensure all TypeScript interfaces and Next.js routes compile with zero warnings:
```bash
cd frontend
npx tsc --noEmit
npm run build
```

---

## The 10-Step Core Learning Loop Walkthrough

Experience the complete, unbroken learning loop as defined by PRD Section 19:

1. **Create Space & Project:**
   - Log in as `learner@aiprof.com`.
   - Create a Space (e.g., *"Deep Learning & AI Engineering"*).
   - Create a Project (e.g., *"Neural Optimization & Backpropagation"* with learning goal *"Master gradient descent algorithms"*).
2. **Upload Learning Material:**
   - Navigate to **Materials** tab and upload a PDF.
   - Watch the real-time status pill transition from `QUEUED` ➔ `PROCESSING` ➔ `READY`.
   - Inspect the extracted atomic concepts automatically discovered from your document.
3. **Chat with AI Tutor:**
   - Open the **AI Tutor** tab.
   - Ask: *"How does gradient descent update neural network weights?"*
   - Watch the response stream token-by-token with clickable citation badges (e.g., `Original PDF • Page 14`).
4. **Inspect Original PDF Citation:**
   - Click the citation badge or the Inspect Drawer link.
   - The in-browser **Document Viewer Modal** opens directly to **Page 14 of the authentic PDF** with the exact supporting passage highlighted in the Grounded Proof Banner.
5. **Test Multi-Turn Conversational Context:**
   - Follow up with: *"Can you give me an analogy for that?"*
   - Notice the Tutor retains context from the previous turn, explaining the analogy without re-prompting.
6. **Test Calibrated Refusal (Zero Hallucinations):**
   - Ask an out-of-scope question: *"How do I bake a chocolate cake?"*
   - The Tutor immediately triggers a calibrated refusal: *"I couldn't find enough information about this in your project materials..."*
7. **Trigger Structured Tool Calling:**
   - Click the prompt chip **"🎯 Check Mastery & Quiz Me"** or type: *"Check my mastery on optimization and test me."*
   - The Tutor executes `check_concept_mastery` and `trigger_remedial_quiz`, rendering an interactive concept status card and a 1-click **Launch Quiz →** CTA widget directly in chat.
8. **Take Adaptive Assessment (MCQ & Open-Ended):**
   - Click **Launch Quiz** or navigate to **Quiz**.
   - Answer the adaptive multiple-choice question.
   - For open-ended questions, type your analytical explanation.
   - The AI evaluates your answer across *Understanding*, *Accuracy*, *Reasoning*, and *Missing Concepts*, returning qualitative formative feedback.
9. **Inspect Mastery Trajectory & Recommendations:**
   - Navigate to **Mastery & Growth**.
   - View your animated concept mastery progress bars (0–100%).
   - See concepts classified into **Improving**, **Stable**, or **Requiring Attention**.
   - Inspect the **Actionable Recommendation Hero**: *"What should I do next?"* with direct buttons to launch targeted quizzes or open cited PDF pages.
10. **Admin Operational Monitoring:**
    - Log out and log in as `admin@aiprof.com` (or click **Admin Portal** in the header).
    - Inspect platform-wide activity feeds, filter by event type, review AI token usage and USD costs, inspect individual learner journeys, and trigger automated evaluation benchmark runs.

---

## API & SSE Endpoints Reference

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/login` | OAuth2 password token generation (JWT) |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch active user session profile |
| **Spaces** | `GET`, `POST` | `/api/v1/spaces` | List and create broad learning spaces |
| **Projects** | `GET`, `POST` | `/api/v1/spaces/{id}/projects` | List and create scoped learning projects |
| **Projects** | `GET` | `/api/v1/projects/{id}/summary` | Retrieve dashboard KPI summary & active recommendation |
| **Materials** | `POST` | `/api/v1/projects/{id}/materials` | Asynchronously upload & enqueue PDF ingestion |
| **Materials** | `GET` | `/api/v1/projects/{id}/materials/{m_id}/raw` | Stream authentic PDF bytes for iframe viewing (`?token=...`) |
| **Tutor** | `POST` | `/api/v1/projects/{id}/tutor/chat` | SSE streaming chat with citations & tool calls |
| **Quiz** | `POST` | `/api/v1/projects/{id}/quizzes` | Generate adaptive MCQ / open-ended quiz |
| **Quiz** | `POST` | `/api/v1/projects/{id}/quizzes/{q_id}/evaluate` | Formative rubric evaluation of student answers |
| **Mastery** | `GET` | `/api/v1/projects/{id}/mastery` | Estimated concept mastery levels & growth trajectories |
| **Recommendations** | `GET` | `/api/v1/projects/{id}/recommendations` | Active next-step recommendations |
| **Analytics** | `GET` | `/api/v1/projects/{id}/analytics` | Project Recharts mastery and quiz trends |
| **Analytics** | `GET` | `/api/v1/analytics/global` | Global platform-wide analytics & leaderboard |
| **Admin** | `GET` | `/api/v1/admin/overview` | Platform health, AI costs, and aggregate stats |
| **Admin** | `GET` | `/api/v1/admin/activity` | Filterable platform-wide audit event feed |
| **Admin** | `POST` | `/api/v1/admin/evaluations/benchmark` | Trigger automated AI benchmark suite |

---

## Documentation Deliverables (PRD §20)

Comprehensive technical documentation is maintained in the [`docs/`](file:///d:/AI-ML/AI_PROF_ASSIGNMENT/docs/) directory in accordance with Section 20 of the PRD:

* [**ARCHITECTURE.md**](file:///d:/AI-ML/AI_PROF_ASSIGNMENT/docs/ARCHITECTURE.md): System architecture, modular monolith design, RAG pipeline, and relational schemas.
* [**AI_USAGE.md**](file:///d:/AI-ML/AI_PROF_ASSIGNMENT/docs/AI_USAGE.md): Distinction between AI used to build the product vs. runtime models embedded in the product.
* [**PROMPTS.md**](file:///d:/AI-ML/AI_PROF_ASSIGNMENT/docs/PROMPTS.md): Production system prompts for the Tutor, concept extraction, rubric evaluations, and repeated-mistake diagnosis.
* [**EVALUATION.md**](file:///d:/AI-ML/AI_PROF_ASSIGNMENT/docs/EVALUATION.md): Scoring formulas (Groundedness %, Citation Precision, Recall@K, MRR), curated test datasets, and regression testing.
* [**LIMITATIONS.md**](file:///d:/AI-ML/AI_PROF_ASSIGNMENT/docs/LIMITATIONS.md): Known prototype limitations and future engineering roadmap.

---

## License & Attribution
Developed for the **AI.Prof Candidate Challenge v3.0**. Built with modern full-stack AI engineering principles: context first, grounded evidence, persistent learning continuity, and complete observability.
