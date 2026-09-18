from typing import Any

class RetrievalEvaluator:
    """
    Evaluator for Project-Scoped Information Retrieval:
    - Recall@K: Did the retrieved set contain the relevant evidence?
    - Precision@K: How dense was the retrieved set with relevant chunks?
    - MRR (Mean Reciprocal Rank): Position of the highest ranked relevant chunk.
    - Calibrated Refusal: Did out-of-domain queries correctly yield has_sufficient_evidence = False?
    """

    def evaluate_case(
        self,
        case: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
        has_sufficient_evidence: bool,
        latency_ms: int = 0
    ) -> dict[str, Any]:
        should_have = case.get("should_have_evidence", True)

        # Negative / Out-of-Domain Retrieval Evaluation
        if not should_have:
            passed = not has_sufficient_evidence
            score = 1.0 if passed else 0.0
            return {
                "case_id": case["case_id"],
                "score": score,
                "passed": passed,
                "metrics": {
                    "refusal_accurate": passed,
                    "retrieved_count": len(retrieved_chunks),
                    "latency_ms": latency_ms
                },
                "failure_reason": None if passed else "Failed refusal: negative out-of-domain query returned false evidence flag."
            }

        # Positive Retrieval Evaluation
        target_doc = (case.get("target_document") or "").lower()
        target_kw = [kw.lower() for kw in case.get("target_keywords", [])]

        relevant_indices = []
        for idx, chunk in enumerate(retrieved_chunks):
            content = chunk.get("content", "").lower()
            doc_title = chunk.get("document_title", "").lower()

            doc_match = bool(target_doc and (target_doc in doc_title or doc_title in target_doc))
            kw_match = sum(1 for kw in target_kw if kw in content) >= max(1, len(target_kw) // 2)

            if doc_match or kw_match:
                relevant_indices.append(idx)

        k = len(retrieved_chunks) or 1
        relevant_count = len(relevant_indices)

        recall_at_k = 1.0 if relevant_count > 0 else 0.0
        precision_at_k = round(relevant_count / k, 4)
        mrr = round(1.0 / (relevant_indices[0] + 1), 4) if relevant_indices else 0.0

        overall_score = round(0.5 * recall_at_k + 0.3 * mrr + 0.2 * precision_at_k, 4)
        passed = recall_at_k >= 1.0 and has_sufficient_evidence

        return {
            "case_id": case["case_id"],
            "score": overall_score,
            "passed": passed,
            "metrics": {
                "recall_at_k": recall_at_k,
                "precision_at_k": precision_at_k,
                "mrr": mrr,
                "has_sufficient_evidence": has_sufficient_evidence,
                "first_relevant_rank": relevant_indices[0] + 1 if relevant_indices else None,
                "latency_ms": latency_ms
            },
            "failure_reason": None if passed else f"Target evidence not found in top-{k} candidates."
        }

retrieval_evaluator = RetrievalEvaluator()
