"""
Centralized AI Service Adapter (Legacy Compatibility Layer).
Proxies calls to the robust app.services.ai provider infrastructure.
"""
from collections.abc import AsyncGenerator
from typing import Any, Optional
from app.services.ai import ai_service, GeminiProvider

class LLMService:
    def __init__(self):
        self.ai = ai_service
        self.provider = self.ai.provider

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        return await self.provider.generate_text(prompt, system_instruction=system_instruction, **kwargs)

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.provider.generate_stream(prompt, system_instruction=system_instruction, **kwargs):
            yield chunk

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        res = await self.provider.generate_structured(prompt, system_instruction=system_instruction, **kwargs)
        return res.get("data", {})

llm_service = LLMService()

__all__ = ["GeminiProvider", "LLMService", "llm_service"]
