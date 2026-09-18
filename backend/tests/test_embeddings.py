import pytest
from app.core.config import settings
from app.services.embedding_service import embedding_service

@pytest.mark.asyncio
async def test_embedding_dimension_strictly_384():
    """Verify generated embeddings have strictly 384 dimensions matching BGE-small configuration."""
    texts = [
        "Backpropagation applies the chain rule recursively.",
        "Gradient descent minimizes empirical risk.",
        "A transformer model relies on multi-head self-attention mechanisms."
    ]

    embeddings = await embedding_service.get_embeddings(texts)

    assert len(embeddings) == len(texts)
    for emb in embeddings:
        assert isinstance(emb, list)
        assert len(emb) == 384, f"Expected 384 dimensions, got {len(emb)}"
        assert len(emb) == settings.EMBEDDING_DIMENSION
        # Ensure values are non-zero normalized floats
        assert any(v != 0.0 for v in emb)

def test_invalid_embedding_dimension_rejected():
    """Verify that vector dimensions other than 384 are strictly rejected."""
    valid_384 = [0.05] * 384
    assert embedding_service.validate_embedding_dimension(valid_384) is True

    # Legacy 1536 vector must be rejected
    invalid_1536 = [0.01] * 1536
    assert embedding_service.validate_embedding_dimension(invalid_1536) is False

    # Short vector must be rejected
    invalid_short = [0.1] * 128
    assert embedding_service.validate_embedding_dimension(invalid_short) is False

@pytest.mark.asyncio
async def test_embedding_caching_behavior():
    """Verify identical text produces identical cached embeddings without duplicate computation."""
    sample = "Batch normalization stabilizes layer activation distributions."
    
    emb1 = await embedding_service.get_embeddings([sample])
    emb2 = await embedding_service.get_embeddings([sample])
    
    assert emb1[0] == emb2[0]
    key = embedding_service._get_cache_key(sample)
    assert key in embedding_service._cache
