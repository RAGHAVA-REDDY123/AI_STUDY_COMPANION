# AI Usage Documentation

As required by Section 20 of the PRD, this document clearly distinguishes between:
1. **AI Used to Build the Product** (developer tooling, coding assistants, architecture design)
2. **AI Used by the Final Product** (runtime models, embeddings, prompts, schemas)

---

## 1. AI Used to Build the Product

| Tool / Assistant | Usage Area | Purpose | Impact on Velocity |
| :--- | :--- | :--- | :--- |
| **Antigravity / Gemini 3.8 Flash** | Architecture & Planning | End-to-end PRD analysis, relational schema design, flaw identification, and scaffolding. | Reduced design-to-architecture turnaround from 2 days to hours. |
| **Pydantic Schema Synthesis** | Backend Data Modeling | Formulating strongly typed JSON validation models for rubrics, quiz formats, and citations. | Guaranteed 100% schema alignment across client and server. |
| **FastAPI Boilerplate Generation** | API Controllers | Rapid generation of repetitive CRUD routers with type hints and async signatures. | Enabled focus on core business logic and AI evaluation. |

---

## 2. AI Used by the Final Product (Runtime Architecture)

| Component / Feature | Model / Provider | Input Context | Output Format | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Document Chunk Embeddings** | `BAAI/bge-small-en-v1.5` (384 dims) | Cleaned page text chunk (400 chars) | Dense float array `vector(384)` | Powers project-isolated cosine similarity vector search. |
| **Concept Extraction** | `gemini-2.5-flash` | Sample chunks from uploaded PDF | JSON (`ConceptExtractionPayload`) | Automatically extracts 5–15 atomic concepts covered in the PDF. |
| **Grounded AI Tutor** | `gemini-2.5-flash` | Top project chunks + learner weaknesses + chat history + user query | Streaming text with citations (`[Source: Doc — Page X]`) | Provides conversational tutoring strictly grounded in source notes. |
| **Unsupported Refusal** | `gemini-2.5-flash` | Chunks lacking evidence + user query | Plain text calibrated refusal | Rejects out-of-scope queries to eliminate hallucinations. |
| **Adaptive Quiz Generator** | `gemini-2.5-flash` | Weak concepts + mistake history + target PDF chunks | JSON (`QuizQuestionPayload`) | Generates targeted MCQs with distractor explanations and open-ended questions. |
| **Open-Ended Rubric Grader** | `gemini-2.5-flash` | Question prompt + correct reference + student explanation | JSON (`OpenEndedRubricEvaluation`) | Evaluates Understanding, Accuracy, Missing Concepts, and Analytical Reasoning. |
| **Recommendation Engine** | `gemini-2.5-flash` | Low-mastery concepts + mistake notes + PDF page map | JSON (`RecommendationPayload`) | Directs the student to specific pages and targeted actions (*“What should I do next?”*). |
