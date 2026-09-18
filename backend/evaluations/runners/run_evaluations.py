import argparse
import asyncio
import sys

from app.core.database import AsyncSessionLocal, engine
from evaluations.services.evaluation_service import EvaluationService

async def main():
    parser = argparse.ArgumentParser(description="Run AI Evaluation Benchmarks")
    parser.add_argument(
        "--type",
        choices=["tutor", "retrieval", "assessment", "recommendation", "all"],
        default="all",
        help="Evaluation suite to run"
    )
    parser.add_argument("--name", type=str, default=None, help="Optional run label")
    args = parser.parse_args()

    suite_mapping = {
        "tutor": "TUTOR",
        "retrieval": "RETRIEVAL",
        "assessment": "ASSESSMENT",
        "recommendation": "RECOMMENDATION",
        "all": "FULL_SUITE"
    }
    suite_type = suite_mapping.get(args.type, "FULL_SUITE")

    print(f"\n=======================================================")
    print(f"[RUN] Launching AI Evaluation Suite: {suite_type}")
    print(f"=======================================================\n")

    async with AsyncSessionLocal() as db:
        service = EvaluationService(db)
        eval_run = await service.run_suite(suite_type=suite_type, run_name=args.name)

        print(f"Run ID:        {eval_run.id}")
        print(f"Run Name:      {eval_run.run_name}")
        print(f"Model:         {eval_run.model}")
        print(f"Total Cases:   {eval_run.total_cases}")
        print(f"Passed:        {eval_run.passed_cases}")
        print(f"Failed:        {eval_run.failed_cases}")
        print(f"\n--- Summary Metrics ---")
        for k, v in (eval_run.metrics or {}).items():
            print(f"  {k:25}: {v}")
        print(f"\nStatus:        {eval_run.status}")
        print(f"=======================================================\n")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
