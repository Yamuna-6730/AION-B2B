class LLMError(Exception):
    """Base exception for LLM runtime failures."""


class ProviderError(LLMError):
    """Raised when an LLM provider cannot complete a request."""


class ParsingError(LLMError):
    """Raised when a model response cannot be parsed or validated."""


class RateLimitError(ProviderError):
    """Raised when the provider rate-limits the request."""


class AuthenticationError(ProviderError):
    """Raised when provider credentials are missing or invalid."""
