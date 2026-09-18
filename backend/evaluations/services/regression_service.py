from typing import Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.observability import AIEvaluationRun, AIEvaluationResult

class RegressionService:
    """
    Regression Analysis Service.
    Compares two evaluation runs across prompt versions, models, retrieval configurations,
    and granular test case scores to detect regressions and improvements.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compare_runs(self, run_a_id: UUID, run_b_id: UUID) -> dict[str, Any]:
        stmt_a = (
            select(AIEvaluationRun)
            .where(AIEvaluationRun.id == run_a_id)
            .options(selectinload(AIEvaluationRun.results))
        )
        stmt_b = (
            select(AIEvaluationRun)
            .where(AIEvaluationRun.id == run_b_id)
            .options(selectinload(AIEvaluationRun.results))
        )

        run_a = (await self.db.execute(stmt_a)).scalar_one_or_none()
        run_b = (await self.db.execute(stmt_b)).scalar_one_or_none()

        if not run_a or not run_b:
            raise ValueError("One or both evaluation runs not found.")

        # Aggregate Metrics Comparison
        metrics_a = run_a.metrics or {}
        metrics_b = run_b.metrics or {}

        metrics_diff = {}
        all_metric_keys = set(metrics_a.keys()).union(set(metrics_b.keys()))
        for k in all_metric_keys:
            val_a = metrics_a.get(k, 0.0)
            val_b = metrics_b.get(k, 0.0)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diff = round(float(val_b) - float(val_a), 4)
                metrics_diff[k] = {
                    "baseline": val_a,
                    "target": val_b,
                    "delta": diff,
                    "is_regression": diff < -0.02
                }

        # Granular Case-by-Case Comparison
        results_a = {r.case_id: r for r in run_a.results}
        results_b = {r.case_id: r for r in run_b.results}

        regressed_cases = []
        improved_cases = []
        unchanged_cases = []

        for case_id, res_b in results_b.items():
            res_a = results_a.get(case_id)
            score_b = float(res_b.score)
            score_a = float(res_a.score) if res_a else 0.0
            delta = round(score_b - score_a, 4)

            item = {
                "case_id": case_id,
                "feature": res_b.feature,
                "baseline_score": score_a,
                "target_score": score_b,
                "delta": delta,
                "baseline_passed": res_a.passed if res_a else False,
                "target_passed": res_b.passed,
                "target_failure_reason": res_b.failure_reason
            }

            if delta < -0.05 or (res_a and res_a.passed and not res_b.passed):
                regressed_cases.append(item)
            elif delta > 0.05 or (res_a and not res_a.passed and res_b.passed):
                improved_cases.append(item)
            else:
                unchanged_cases.append(item)

        return {
            "baseline_run": {
                "id": str(run_a.id),
                "name": run_a.run_name,
                "model": run_a.model,
                "prompt_version": run_a.prompt_version,
                "retrieval_version": run_a.retrieval_version,
                "passed_cases": run_a.passed_cases,
                "total_cases": run_a.total_cases,
                "created_at": run_a.created_at.isoformat()
            },
            "target_run": {
                "id": str(run_b.id),
                "name": run_b.run_name,
                "model": run_b.model,
                "prompt_version": run_b.prompt_version,
                "retrieval_version": run_b.retrieval_version,
                "passed_cases": run_b.passed_cases,
                "total_cases": run_b.total_cases,
                "created_at": run_b.created_at.isoformat()
            },
            "has_regression": len(regressed_cases) > 0,
            "metrics_diff": metrics_diff,
            "regressed_cases": regressed_cases,
            "improved_cases": improved_cases,
            "unchanged_cases_count": len(unchanged_cases)
        }
