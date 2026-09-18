# Architecture Documentation — AI Engineering, Observability & Evaluation

## 1. Architectural Philosophy & Strategy

The **AI Study Companion** is structured as a **modular monolith** with asynchronous worker execution and a decoupled **AI Engineering & Observability Layer**. This architecture ensures that AI interactions are treated as resilient engineering systems rather than arbitrary API calls.

```text
TutorService / QuizService / AssessmentService / RecommendationService
                                 |
                                 v
                       AIRequestContext (Unified request_id)
                                 |
                                 v
                             AIService
                                 |
                                 v
                        AIProvider Interface
                                 |
                                 v
               +-----------------+-----------------+
               |                                   |
               v                                   v
        GeminiProvider                      CostCalculator
  (Bounded 429 Backoff)                 (Configured Pricing)
               |                                   |
               +-----------------+-----------------+
                                 |
                                 v
                       PostgreSQL Telemetry
                (ai_usage_logs, retrieval_logs)
```

---

## 2. Key Architectural Decisions

### Decision 1: Centralized AI Provider Abstraction (`app/services/ai/`)
* **Rationale:** Business logic services (Tutor, Quiz, Assessment) depend on the abstract `AIProvider` interface rather than Google Gemini SDK details.
* **Benefits:** Enables swapping models, testing offline with deterministic mocks, and enforcing system-wide error handling and telemetry.

### Decision 2: Centralized AI Request Correlation (`request_id`)
* **Rationale:** Complex workflows (e.g. Tutor query -> project retrieval -> LLM generation -> citation verification) share a unified `request_id` (e.g. `req_abc123`).
* **Traceability:** Facilitates investigation into latency bottlenecks (retrieval ms vs generation ms) and failure points.

### Decision 3: Zero Fabricated Metrics
* **Tokens & Cost:** Tokens are recorded only when exposed by `usageMetadata`. If unexposed, database records `NULL` rather than invented counts.
* **Cost Tracking:** The `CostCalculator` computes estimated USD using configurable pricing per 1,000,000 tokens for Gemini 2.5 Flash, Gemini 1.5 Pro, and local embeddings.

### Decision 4: Resilient HTTP 429 Rate-Limit & Failure Classification
* **Classifications:** `RATE_LIMIT` (429), `QUOTA_EXCEEDED`, `AUTHENTICATION_ERROR`, `TIMEOUT`, `PROVIDER_ERROR` (5xx), `STRUCTURED_OUTPUT_ERROR`, `NETWORK_ERROR`.
* **Bounded Retries:** Exponential backoff schedule (2.0s, 5.0s, 10.0s) with randomized jitter.
* **Privacy:** Redacts API keys and secrets from logs and presents sanitized user-facing messages.

### Decision 5: Strict Project-Isolated RAG Observability
* **Requirement:** Project A's materials must never leak into Project B's context.
* **Mechanism:** Every vector and keyword query enforces:
  ```sql
  WHERE document_chunks.project_id = CAST(:project_id AS uuid)
  ```
* **Retrieval Telemetry:** Records `query`, `top_k`, `retrieved_chunk_ids`, `similarity_scores`, `retrieval_latency_ms`, `reranking_latency_ms`, and `has_sufficient_evidence` in `retrieval_logs`.

---

## 3. Persistent Database Observability Schema

### `ai_usage_logs`
* `id`: UUID Primary Key
* `request_id`: Indexed correlation ID
* `user_id`, `project_id`: Tenant references
* `feature`, `operation`: Categorization (`TUTOR`, `QUIZ`, `ASSESSMENT`, `RECOMMENDATION`, `DOCUMENT`)
* `provider`, `model_name`: Provider details (`gemini`, `gemini-2.5-flash`)
* `prompt_tokens`, `completion_tokens`, `total_tokens`: Token metrics (NULL if unexposed)
* `latency_ms`: Operational duration
* `estimated_cost_usd`: Configured USD cost estimate
* `status_code`: `SUCCESS` or `FAILED`
* `error_type`, `error_details`: Sanitized failure logs
* `prompt_version`, `metadata_json`: Versioning and structured metrics

### `retrieval_logs`
* `id`: UUID Primary Key
* `request_id`, `project_id`, `user_id`: Scoped correlation
* `query`, `retrieval_method`: Query and algorithm (`hybrid_rrf`)
* `top_k`, `final_k`: Candidate counts
* `retrieved_chunk_ids`, `similarity_scores`: Diagnostic rankings
* `retrieval_latency_ms`, `reranking_latency_ms`: Split latencies
* `has_sufficient_evidence`: Refusal threshold indicator
* `retrieval_version`: Algorithm version (`hybrid_rrf_v1.0_bge384`)

### `ai_evaluation_runs` & `ai_evaluation_results`
* Records evaluation suite runs, aggregate scores, Groundedness %, Citation Correctness %, Recall@5, MRR, and per-case inputs/outputs for regression analysis.
