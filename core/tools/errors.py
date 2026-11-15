from core.tools.results import ToolErrorResult

VALIDATION = "validation"  # bad or impossible input - Claude fixes the input
TRANSIENT = "transient"  # temporary failure, result unknown - code may retry
BUSINESS = "business"  # valid request, blocked by policy - do not retry
PERMISSION = "permission"  # caller not allowed yet (e.g. not verified)
INTERNAL = "internal"  # bug / unexpected crash


class ToolError(Exception):
    category: str = INTERNAL
    retryable: bool = False

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_result(self) -> ToolErrorResult:
        return {
            "is_error": True,
            "error_category": self.category,
            "is_retryable": self.retryable,
            "content": {**self.details, "message": self.message},
        }


class ToolValidationError(ToolError):
    category = VALIDATION


class ToolTransientError(ToolError):
    category = TRANSIENT
    retryable = True


class ToolPermissionError(ToolError):
    category = PERMISSION


class ToolBusinessError(ToolError):
    category = BUSINESS
