class FridayError(Exception):
    """Base exception for FRIDAY."""


class ConfigurationError(FridayError):
    """Configuration-related errors."""


class AIProviderError(FridayError):
    """AI provider errors."""


class ToolError(FridayError):
    """Tool execution errors."""
