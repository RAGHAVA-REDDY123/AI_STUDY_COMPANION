import hashlib
import math
from typing import Optional
from app.core.config import settings

class EmbeddingService:
    """
    Centralized Embedding Service for BGE-small (384 dimensions).
    Enforces batch generation, strict dimension validation, and content-hash caching.
    """

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self._cache: dict[str, list[float]] = {}
        self._model = None

    def _get_cache_key(self, text: str) -> str:
        return hashlib.sha256(f"{text}:{self.model_name}".encode("utf-8")).hexdigest()

    def _load_model(self):
        if self._model is not None:
            return self._model

        # Attempt 1: fastembed (Fast, CPU-optimized ONNX runtime, lightweight)
        try:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)
            return self._model
        except Exception:
            pass

        # Attempt 2: sentence_transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            return self._model
        except Exception:
            pass

        return None

    def _generate_deterministic_vector(self, text: str) -> list[float]:
        """
        Deterministic, non-zero normalized 384-dimensional fallback pseudo-embedding.
        Ensures consistent 384 dimensions if native models are offline/uninstalled.
        """
        vec = [0.001] * self.dimension
        tokens = [w.lower().strip() for w in text.split() if len(w) > 1]
        if not tokens:
            tokens = [text.lower().strip() if text.strip() else "general"]

        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            vec[idx] += 1.0
            vec[(idx + 1) % self.dimension] += 0.5
            vec[(idx - 1) % self.dimension] += 0.5

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            return [v / norm for v in vec]
        return [1.0 / math.sqrt(self.dimension)] * self.dimension

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Batched embedding generation with strict 384-dim validation and content-hash caching.
        """
        if not texts:
            return []

        results: list[Optional[list[float]]] = [None] * len(texts)
        texts_to_generate: list[tuple[int, str]] = []

        # 1. Check cache
        for idx, text in enumerate(texts):
            key = self._get_cache_key(text)
            if key in self._cache:
                results[idx] = self._cache[key]
            else:
                texts_to_generate.append((idx, text))

        if texts_to_generate:
            model = self._load_model()
            batch_texts = [item[1] for item in texts_to_generate]
            generated_vectors: list[list[float]] = []

            if model is not None:
                try:
                    # Check if fastembed TextEmbedding
                    if hasattr(model, "embed"):
                        embeddings_gen = model.embed(batch_texts)
                        for emb in embeddings_gen:
                            generated_vectors.append(list(map(float, emb)))
                    elif hasattr(model, "encode"):
                        embs = model.encode(batch_texts, show_progress_bar=False)
                        for emb in embs:
                            generated_vectors.append(list(map(float, emb)))
                except Exception as e:
                    print(f"[EmbeddingService Error] Native model generation failed: {e}. Using deterministic fallback.", flush=True)
                    generated_vectors = [self._generate_deterministic_vector(t) for t in batch_texts]
            else:
                generated_vectors = [self._generate_deterministic_vector(t) for t in batch_texts]

            # 2. Validate dimensions and populate cache
            for (orig_idx, orig_text), vec in zip(texts_to_generate, generated_vectors):
                # Strict dimension validation
                if len(vec) != self.dimension:
                    raise ValueError(
                        f"CRITICAL EMBEDDING ERROR: Expected vector dimension {self.dimension}, "
                        f"but got {len(vec)}. Model configuration must match {self.dimension} dimensions."
                    )
                key = self._get_cache_key(orig_text)
                self._cache[key] = vec
                results[orig_idx] = vec

        # Final assertion: all vectors must be exactly 384 dims
        final_embeddings: list[list[float]] = []
        for r in results:
            assert r is not None and len(r) == self.dimension, f"Vector failed {self.dimension}-dim check"
            final_embeddings.append(r)

        return final_embeddings

    def validate_embedding_dimension(self, vector: list[float]) -> bool:
        """Validates that an embedding has strictly 384 dimensions."""
        return isinstance(vector, list) and len(vector) == self.dimension

embedding_service = EmbeddingService()
