# AI Evaluation Methodology, Benchmarks & Regression Testing

This document details the evaluation architecture, curated benchmark datasets, scoring formulas, and regression testing capabilities of the **AI Study Companion**.

---

## 1. System Architecture

The evaluation system treats AI as an engineering system with clear input/output assertions, metrics calculation, and regression prevention:

```text
evaluations/
├── datasets/
│   ├── tutor_cases.json           # 12 curated test cases (factual, multi-doc, refusal, citations)
│   ├── retrieval_cases.json       # 12 curated cases (queries, target docs, Recall@K, MRR)
│   ├── assessment_cases.json      # 10 curated cases (MCQ schema, rubric evaluation, adaptivity)
│   └── recommendation_cases.json  # 10 curated cases (learner state alignment, actionability)
├── services/
│   ├── tutor_evaluator.py         # Groundedness, accuracy keyword overlap, citation validation
│   ├── retrieval_evaluator.py     # Recall@K, Precision@K, Mean Reciprocal Rank (MRR)
│   ├── assessment_evaluator.py    # Schema reliability, rubric grading quality, adaptive transitions
│   ├── recommendation_evaluator.py# Targeted weak-concept alignment, actionability, non-generic scoring
│   ├── evaluation_service.py      # Benchmark runner and PostgreSQL persistence
│   └── regression_service.py      # Run-to-run regression analysis and metric delta detection
└── runners/
    └── run_evaluations.py         # CLI runner for local and CI/CD execution
```

---

## 2. Evaluation Dimensions & Formulas

### 2.1 Tutor Evaluation
* **Accuracy:** Keyword recall against authoritative curriculum definitions:
  $$\text{Accuracy} = \frac{|\text{Matched Keywords}|}{|\text{Expected Keywords}|}$$
* **Citation Correctness:** Validated by `CitationService.validate_citations_detailed()` against actual retrieved chunks:
  $$\text{Citation Correctness} = \frac{|\text{Verified Citations}|}{|\text{Total Extracted Citations}|}$$
* **Groundedness:** Synthesis of accuracy and evidence citation grounding:
  $$\text{Groundedness} = 0.6 \times \text{Accuracy} + 0.4 \times \text{Citation Correctness}$$
* **Unsupported Question Refusal:** For questions outside project materials or adversarial injections:
  - Asserts presence of calibrated refusal signature: *"I cannot find sufficient evidence in your uploaded project notes..."*
  - Asserts complete absence of hallucinated domain content or leaked tokens.

### 2.2 Retrieval Evaluation
* **Recall@K:** Fraction of relevant evidence retrieved in top $K$ candidates ($K=5$):
  $$\text{Recall@K} = \frac{|\text{Relevant Chunks in Top K}|}{|\text{All Relevant Chunks}|}$$
* **Precision@K:** Proportion of top $K$ retrieved items that are relevant.
* **MRR (Mean Reciprocal Rank):** Evaluates ranking quality:
  $$\text{MRR} = \frac{1}{\text{rank of first relevant chunk}}$$
* **Project Isolation:** Enforces `WHERE project_id = CAST(:project_id AS uuid)`. Cross-project chunks in retrieved set is strictly 0.

### 2.3 Assessment Evaluation
* **Structured Output Reliability:** Pydantic schema validation for MCQ choices, correct answers, and 4-factor open-ended rubrics (Understanding, Accuracy, Relevance, Reasoning).
* **Adaptive Behavior:** Verification of difficulty transitions based on performance history and mastery levels.

### 2.4 Recommendation Evaluation
* **Alignment:** Recommends `REVIEW_MATERIAL` targeting specific weak concepts when mastery $< 60\%$.
* **Actionability:** Clear verbs and page references rather than generic placeholders.

---

## 3. Regression Testing

The `RegressionService` compares two runs (Run A vs Run B) across prompt and retrieval versions:

* **Prompt Versioning:** `tutor_v1.0`, `quiz_gen_v2.0`, `assessment_rubric_v1.0`
* **Retrieval Versioning:** `hybrid_rrf_v1.0_bge384`
* **Regression Alert:** Triggered if aggregate Groundedness, Recall@5, or Pass Rate decreases by $> 2\%$ or if previously passing cases fail.

---

## 4. How to Run Evaluations

### Via CLI:
```bash
cd backend
# Run all benchmark suites:
python -m evaluations.runners.run_evaluations --type all

# Run specific suite:
python -m evaluations.runners.run_evaluations --type tutor
python -m evaluations.runners.run_evaluations --type retrieval
python -m evaluations.runners.run_evaluations --type assessment
python -m evaluations.runners.run_evaluations --type recommendation
```

### Via Admin Dashboard:
1. Log in as Admin (`admin@aiprof.com`).
2. Navigate to `/admin`.
3. Click the **Evaluation & Regression Studio** tab.
4. Click **Run Full Benchmark Suite** to trigger a live run.
5. Select Run A and Run B in the dropdowns and click **Detect Regressions** to inspect score deltas.
