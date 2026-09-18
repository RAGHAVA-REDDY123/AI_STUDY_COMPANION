import pytest
from app.services.ai.context import AIRequestContext, ai_request_scope, get_current_ai_context
from app.services.ai.cost_calculator import CostCalculator
from app.services.ai.error_handler import AIErrorHandler, AIErrorType, AIException
from app.services.citation_service import citation_service

def test_request_context_propagation():
    """Verify AIRequestContext generates valid request_id and scopes correctly."""
    with ai_request_scope(feature="TUTOR", operation="generate_stream", model="gemini-2.5-flash") as ctx:
        assert ctx.request_id.startswith("req_")
        assert ctx.feature == "TUTOR"
        assert ctx.model == "gemini-2.5-flash"
        
        active_ctx = get_current_ai_context()
        assert active_ctx is not None
        assert active_ctx.request_id == ctx.request_id

    # Outside scope, context resets
    assert get_current_ai_context() is None

def test_cost_calculator_accuracy():
    """Verify CostCalculator uses exact model rates and returns None if unexposed."""
    # 1. Gemini 2.5 Flash: $0.075 / 1M in, $0.30 / 1M out
    # 1,000,000 in + 1,000,000 out = $0.375
    cost = CostCalculator.calculate_cost(
        provider="gemini",
        model="gemini-2.5-flash",
        input_tokens=1_000_000,
        output_tokens=1_000_000
    )
    assert cost == 0.375000

    # 2. Typical query: 1,000 input, 250 output
    # (1000 * 0.075 + 250 * 0.30) / 1,000,000 = (75 + 75) / 1,000,000 = 0.000150
    cost_small = CostCalculator.calculate_cost(
        provider="gemini",
        model="gemini-2.5-flash",
        input_tokens=1000,
        output_tokens=250
    )
    assert cost_small == 0.000150

    # 3. None returned if tokens are unexposed (no fabrication)
    assert CostCalculator.calculate_cost("gemini", "gemini-2.5-flash", None, None) is None

    # 4. Unknown model returns None
    assert CostCalculator.calculate_cost("unknown", "super-model-9000", 1000, 500) is None

def test_error_handler_classification():
    """Verify HTTP error classification, 429 rate limit categorization, and sanitization."""
    import httpx

    # Mock 429 Rate Limit
    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models")
    resp_429 = httpx.Response(429, request=req, text="Resource exhausted: Rate limit exceeded")
    err_429 = httpx.HTTPStatusError("429 Too Many Requests", request=req, response=resp_429)

    err_type, is_retryable, user_msg = AIErrorHandler.classify_exception(err_429)
    assert err_type == AIErrorType.RATE_LIMIT
    assert is_retryable is True
    assert "temporarily busy" in user_msg or "quota" in user_msg.lower()

    # Mock 401 Auth Error (Non-retryable)
    resp_401 = httpx.Response(401, request=req, text="API_KEY_INVALID")
    err_401 = httpx.HTTPStatusError("401 Unauthorized", request=req, response=resp_401)
    err_type_401, is_retryable_401, user_msg_401 = AIErrorHandler.classify_exception(err_401)
    assert err_type_401 == AIErrorType.AUTHENTICATION_ERROR
    assert is_retryable_401 is False

    # Mock Timeout Error
    err_type_timeout, retry_timeout, _ = AIErrorHandler.classify_exception(httpx.ReadTimeout("Timeout"))
    assert err_type_timeout == AIErrorType.TIMEOUT
    assert retry_timeout is True

def test_error_sanitization_strips_api_keys():
    """Verify sensitive API keys and authorization tokens are redacted from error logs."""
    raw_error = "Failed connecting to https://generativelanguage.googleapis.com/v1beta?key=AIzaSyD_SECRET_KEY_12345"
    sanitized = AIErrorHandler.sanitize_error_detail(raw_error)
    assert "AIzaSyD_SECRET_KEY_12345" not in sanitized
    assert "key=[REDACTED]" in sanitized

def test_retry_backoff_schedule():
    """Verify bounded backoff delays adhere to schedule (2s, 5s, 10s)."""
    d0 = AIErrorHandler.get_retry_delay(0)
    d1 = AIErrorHandler.get_retry_delay(1)
    d2 = AIErrorHandler.get_retry_delay(2)

    assert 2.0 <= d0 <= 2.6
    assert 5.0 <= d1 <= 5.6
    assert 10.0 <= d2 <= 10.6

def test_citation_validation_detailed():
    """Verify CitationService accurately detects verified vs hallucinated citations."""
    response_with_citations = (
        "Principal Component Analysis identifies orthogonal axes of maximum variance "
        "[Source: ML_Foundations.pdf — Page 4]. In contrast, LDA maximizes class separability "
        "[Source: Fake_Document.pdf — Page 99]."
    )

    actual_retrieved = [
        {"document_title": "ML_Foundations.pdf", "page_number": 4, "snippet": "PCA maximizes variance."}
    ]

    report = citation_service.validate_citations_detailed(response_with_citations, actual_retrieved)
    assert report["total_extracted"] == 2
    assert report["verified_count"] == 1
    assert report["hallucinated_count"] == 1
    assert report["citation_valid"] is False
    assert report["citation_correctness_score"] == 0.50
