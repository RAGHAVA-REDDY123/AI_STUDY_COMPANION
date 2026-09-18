import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.observability import AIUsageLog
from app.services.ai.context import AIRequestContext, get_current_ai_context
from app.services.ai.cost_calculator import cost_calculator
from app.services.ai.error_handler import AIErrorHandler, AIErrorType, AIException
from app.services.ai.provider import AIProvider, GeminiProvider

logger = logging.getLogger(__name__)

class AIService:
    """
    Centralized AIService Orchestrator.
    Decouples application domains (Tutor, Quiz, Assessment, Recommendations) from
    specific LLM provider implementations. Manages request contexts, token tracking,
    latency recording, cost calculation, and persistent database telemetry.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or GeminiProvider()

    async def log_usage(
        self,
        db: Optional[AsyncSession],
        feature: str,
        operation: str,
        latency_ms: int,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        status_code: str = "SUCCESS",
        error_type: Optional[str] = None,
        error_details: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        model_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        metadata_json: Optional[dict[str, Any]] = None
    ) -> None:
        """Persists AI request observability log to PostgreSQL."""
        if not settings.AI_LOGGING_ENABLED:
            return

        ctx = get_current_ai_context()
        req_id = request_id or (ctx.request_id if ctx else None)
        u_id = user_id or (ctx.user_id if ctx else None)
        p_id = project_id or (ctx.project_id if ctx else None)
        model = model_name or (ctx.model if ctx else self.provider.model_name)
        prov = provider_name or (ctx.provider if ctx else self.provider.provider_name)
        p_ver = prompt_version or (ctx.prompt_version if ctx else None)
        meta = metadata_json or (ctx.metadata if ctx else None)

        cost = cost_calculator.calculate_cost(
            provider=prov,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        ) if settings.AI_COST_TRACKING_ENABLED else None

        usage_log = AIUsageLog(
            request_id=req_id,
            user_id=u_id,
            project_id=p_id,
            feature=feature.upper(),
            operation=operation,
            provider=prov,
            model_name=model,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=cost,
            status_code=status_code,
            error_type=error_type,
            error_details=AIErrorHandler.sanitize_error_detail(error_details) if error_details else None,
            prompt_version=p_ver,
            metadata_json=meta
        )

        try:
            if db:
                db.add(usage_log)
                await db.commit()
            else:
                async with AsyncSessionLocal() as session:
                    session.add(usage_log)
                    await session.commit()
        except Exception as e:
            logger.warning(f"[AIService] Failed to persist AI telemetry log: {e}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        db: Optional[AsyncSession] = None,
        feature: str = "GENERAL",
        operation: str = "generate_text",
        **kwargs
    ) -> dict[str, Any]:
        start = time.time()
        ctx = get_current_ai_context()
        try:
            res = await self.provider.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                **kwargs
            )
            latency_ms = int((time.time() - start) * 1000)

            await self.log_usage(
                db=db,
                feature=feature,
                operation=operation,
                latency_ms=latency_ms,
                input_tokens=res.get("input_tokens"),
                output_tokens=res.get("output_tokens"),
                total_tokens=res.get("total_tokens"),
                status_code="SUCCESS"
            )
            return res

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            err_type, _, user_msg = AIErrorHandler.classify_exception(e)
            raw_err = getattr(e, "raw_error", str(e))

            await self.log_usage(
                db=db,
                feature=feature,
                operation=operation,
                latency_ms=latency_ms,
                status_code="FAILED",
                error_type=err_type.value if hasattr(err_type, "value") else str(err_type),
                error_details=raw_err
            )
            raise AIException(
                message=user_msg,
                error_type=err_type,
                raw_error=raw_err
            ) from e

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.provider.generate_stream(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs
        ):
            yield chunk

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        feature: str = "STRUCTURED",
        operation: str = "generate_structured",
        **kwargs
    ) -> dict[str, Any]:
        start = time.time()
        try:
            res = await self.provider.generate_structured(
                prompt=prompt,
                system_instruction=system_instruction,
                schema=schema,
                **kwargs
            )
            latency_ms = int((time.time() - start) * 1000)

            await self.log_usage(
                db=db,
                feature=feature,
                operation=operation,
                latency_ms=latency_ms,
                input_tokens=res.get("input_tokens"),
                output_tokens=res.get("output_tokens"),
                total_tokens=res.get("total_tokens"),
                status_code="SUCCESS"
            )
            return res.get("data", {})

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            err_type, _, user_msg = AIErrorHandler.classify_exception(e)
            raw_err = getattr(e, "raw_error", str(e))

            await self.log_usage(
                db=db,
                feature=feature,
                operation=operation,
                latency_ms=latency_ms,
                status_code="FAILED",
                error_type=err_type.value if hasattr(err_type, "value") else str(err_type),
                error_details=raw_err
            )
            raise AIException(
                message=user_msg,
                error_type=err_type,
                raw_error=raw_err
            ) from e

ai_service = AIService()
