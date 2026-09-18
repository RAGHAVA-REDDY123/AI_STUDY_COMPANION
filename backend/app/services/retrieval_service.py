import logging
import time
import uuid
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.models.observability import RetrievalLog
from app.services.ai.context import get_current_ai_context
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class RetrievalService:
    """
    Project-Scoped Hybrid Retrieval Service.
    Enforces strict project isolation at the database layer before top-K selection,
    combining pgvector HNSW cosine search with PostgreSQL Full-Text Search.
    Records comprehensive RAG observability telemetry to retrieval_logs.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        project_id: UUID,
        query: str,
        top_k: int = 20,
        final_k: int = 6,
        confidence_threshold: float = 0.35,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Retrieves project-isolated chunks using hybrid search.
        Returns:
            (top_candidates, has_sufficient_evidence)
        """
        if not query or not query.strip():
            return [], False

        start_time = time.time()
        ctx = get_current_ai_context()
        req_id = request_id or (ctx.request_id if ctx else f"ret_{uuid.uuid4().hex[:12]}")
        u_id = user_id or (ctx.user_id if ctx else None)

        # 1. Generate query embedding (strictly 384 dimensions)
        emb_start = time.time()
        query_embeddings = await embedding_service.get_embeddings([query])
        query_vec = query_embeddings[0]

        # 2. Vector Semantic Search (strictly project-filtered in SQL)
        vector_sql = text("""
            SELECT 
                id, 
                material_id, 
                page_number, 
                chunk_index, 
                COALESCE(section_title, 'General') AS section_title, 
                COALESCE(document_title, 'Material Notes') AS document_title, 
                content,
                1 - (embedding <=> :query_embedding) AS vector_similarity
            FROM document_chunks
            WHERE project_id = CAST(:project_id AS uuid)
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :query_embedding ASC
            LIMIT :top_k;
        """)

        vector_result = await self.db.execute(
            vector_sql,
            {
                "project_id": str(project_id),
                "query_embedding": query_vec,
                "top_k": top_k
            }
        )
        vector_rows = vector_result.mappings().all()

        # 3. PostgreSQL Full-Text Search (strictly project-filtered in SQL)
        fts_sql = text("""
            SELECT 
                id, 
                material_id, 
                page_number, 
                chunk_index, 
                COALESCE(section_title, 'General') AS section_title, 
                COALESCE(document_title, 'Material Notes') AS document_title, 
                content,
                ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', :query_text)) AS fts_rank
            FROM document_chunks
            WHERE project_id = CAST(:project_id AS uuid)
              AND to_tsvector('english', content) @@ plainto_tsquery('english', :query_text)
            ORDER BY fts_rank DESC
            LIMIT :top_k;
        """)

        fts_result = await self.db.execute(
            fts_sql,
            {
                "project_id": str(project_id),
                "query_text": query,
                "top_k": top_k
            }
        )
        fts_rows = fts_result.mappings().all()
        retrieval_latency_ms = int((time.time() - emb_start) * 1000)

        # 4. Reciprocal Rank Fusion (RRF) Merge & Rerank
        rerank_start = time.time()
        rrf_scores: dict[str, dict[str, Any]] = {}
        rrf_k = 60.0

        for rank, row in enumerate(vector_rows):
            cid = str(row["id"])
            if cid not in rrf_scores:
                rrf_scores[cid] = {
                    "id": cid,
                    "material_id": str(row["material_id"]),
                    "page_number": row["page_number"],
                    "chunk_index": row["chunk_index"],
                    "section_title": row["section_title"],
                    "document_title": row["document_title"],
                    "content": row["content"],
                    "vector_similarity": float(row["vector_similarity"]),
                    "fts_rank": 0.0,
                    "rrf_score": 0.0
                }
            rrf_scores[cid]["rrf_score"] += 1.0 / (rrf_k + rank + 1.0)

        for rank, row in enumerate(fts_rows):
            cid = str(row["id"])
            if cid not in rrf_scores:
                rrf_scores[cid] = {
                    "id": cid,
                    "material_id": str(row["material_id"]),
                    "page_number": row["page_number"],
                    "chunk_index": row["chunk_index"],
                    "section_title": row["section_title"],
                    "document_title": row["document_title"],
                    "content": row["content"],
                    "vector_similarity": 0.0,
                    "fts_rank": float(row["fts_rank"]),
                    "rrf_score": 0.0
                }
            rrf_scores[cid]["fts_rank"] = float(row["fts_rank"])
            rrf_scores[cid]["rrf_score"] += 1.0 / (rrf_k + rank + 1.0)

        merged_candidates = list(rrf_scores.values())
        merged_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        top_candidates = merged_candidates[:final_k]
        reranking_latency_ms = int((time.time() - rerank_start) * 1000)

        # 5. Evaluate Evidence Grounding Confidence
        best_sim = max((c["vector_similarity"] for c in top_candidates), default=0.0)
        best_fts = max((c["fts_rank"] for c in top_candidates), default=0.0)

        has_sufficient_evidence = bool(
            top_candidates and (best_sim >= confidence_threshold or best_fts > 0.05)
        )

        # 6. Observability: Record Retrieval Log
        try:
            retrieval_log = RetrievalLog(
                request_id=req_id,
                project_id=project_id,
                user_id=u_id,
                query=query[:500],
                retrieval_method="hybrid_rrf",
                top_k=top_k,
                final_k=final_k,
                retrieved_chunk_ids=[c["id"] for c in top_candidates],
                similarity_scores={c["id"]: round(c["rrf_score"], 4) for c in top_candidates},
                retrieval_latency_ms=retrieval_latency_ms,
                reranking_latency_ms=reranking_latency_ms,
                final_chunk_ids=[c["id"] for c in top_candidates],
                has_sufficient_evidence=has_sufficient_evidence,
                retrieval_version=settings.RETRIEVAL_VERSION
            )
            self.db.add(retrieval_log)
            # Flush to get log ID if needed, commit is managed by transaction/caller
            await self.db.flush()
        except Exception as e:
            logger.warning(f"[RetrievalService] Failed to record retrieval log: {e}")

        return top_candidates, has_sufficient_evidence
