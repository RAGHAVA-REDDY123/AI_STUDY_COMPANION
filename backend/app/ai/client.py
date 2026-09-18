"""
Compatibility adapter:
Legacy app.ai.client is refactored into dedicated services:
- app.services.llm_service.llm_service (Gemini 2.5 Flash)
- app.services.embedding_service.embedding_service (BGE-small 384-dimensional embeddings)
"""
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service

class AIClientAdapter:
    @property
    def model(self):
        return llm_service.provider.model

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return await embedding_service.get_embeddings(texts)

ai_client = AIClientAdapter()

__all__ = ["ai_client", "AIClientAdapter"]
