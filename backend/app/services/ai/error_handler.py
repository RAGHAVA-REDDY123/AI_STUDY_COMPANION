import enum
import random
from typing import Optional
import httpx

class AIErrorType(str, enum.Enum):
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    TIMEOUT = "TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    STRUCTURED_OUTPUT_ERROR = "STRUCTURED_OUTPUT_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class AIException(Exception):
    def __init__(
        self,
        message: str,
        error_type: AIErrorType = AIErrorType.UNKNOWN_ERROR,
        status_code: Optional[int] = None,
        raw_error: Optional[str] = None,
        is_retryable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.raw_error = raw_error
        self.is_retryable = is_retryable

class AIErrorHandler:
    """
    Centralized AI Error Classifier & Sanitizer.
    Ensures safe, bounded error handling without leaking secrets or API internals.
    """

    @classmethod
    def classify_exception(cls, exc: Exception) -> tuple[AIErrorType, bool, str]:
        """
        Classifies an exception into standard AIErrorType, whether it's retryable,
        and a sanitized user-facing message.
        """
        if isinstance(exc, AIException):
            return exc.error_type, exc.is_retryable, exc.message

        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            text = exc.response.text.lower() if exc.response else ""

            if code == 429:
                if "quota" in text or "resource_exhausted" in text:
                    return AIErrorType.QUOTA_EXCEEDED, True, "AI request quota reached. Please try again shortly."
                return AIErrorType.RATE_LIMIT, True, "The AI service is temporarily busy. Please try again in a moment."

            if code in (401, 403):
                return AIErrorType.AUTHENTICATION_ERROR, False, "AI provider authentication failed. Please contact administrator."

            if code in (500, 502, 503, 504):
                return AIErrorType.PROVIDER_ERROR, True, "AI provider service is experiencing instability. Retrying..."

            return AIErrorType.PROVIDER_ERROR, False, f"AI provider returned unexpected status code {code}."

        if isinstance(exc, httpx.TimeoutException):
            return AIErrorType.TIMEOUT, True, "AI request timed out. Please try again."

        if isinstance(exc, httpx.NetworkError):
            return AIErrorType.NETWORK_ERROR, True, "AI network communication error. Retrying..."

        if isinstance(exc, (ValueError, KeyError)) and "json" in str(exc).lower():
            return AIErrorType.STRUCTURED_OUTPUT_ERROR, False, "Failed to parse structured AI output."

        return AIErrorType.UNKNOWN_ERROR, False, "An unexpected AI processing error occurred."

    @classmethod
    def get_retry_delay(cls, attempt: int, base_delays: Optional[list[float]] = None) -> float:
        """
        Bounded exponential backoff with jitter.
        Default schedule: 2.0s, 5.0s, 10.0s + jitter.
        """
        delays = base_delays or [2.0, 5.0, 10.0]
        idx = min(attempt, len(delays) - 1)
        base = delays[idx]
        jitter = random.uniform(0.1, 0.5)
        return base + jitter

    @classmethod
    def sanitize_error_detail(cls, error_msg: str) -> str:
        """Strips potential API keys and URL credentials from error strings."""
        if not error_msg:
            return ""
        import re
        # Strip ?key=... or key=...
        sanitized = re.sub(r"key=[A-Za-z0-9_\-]+", "key=[REDACTED]", str(error_msg))
        # Strip Bearer tokens
        sanitized = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", sanitized)
        return sanitized[:500]

error_handler = AIErrorHandler()
