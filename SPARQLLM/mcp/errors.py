"""Error handling framework for SPARQLLM MCP Server"""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(Enum):
    """Error codes for SPARQLLM MCP operations"""
    SPARQL_SYNTAX_ERROR = "SPARQL_SYNTAX_ERROR"
    SPARQL_TIMEOUT = "SPARQL_TIMEOUT"
    INVALID_FUNCTION = "INVALID_FUNCTION"
    STORE_OVERFLOW = "STORE_OVERFLOW"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class SparqllmError(Exception):
    """Base exception for SPARQLLM errors with agent-focused messages"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert error to MCP-friendly JSON response"""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }


def handle_error(e: Exception) -> dict:
    """
    Convert exception to MCP-friendly error response.

    Provides agent-focused error messages with actionable suggestions.
    """
    if isinstance(e, SparqllmError):
        return e.to_dict()

    # Map known SPARQL exceptions
    error_type = str(type(e).__name__)
    error_msg = str(e)

    if "ParseException" in error_type or "ParseError" in error_type:
        return SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            f"Invalid SPARQL syntax: {error_msg}",
            {
                "suggestion": "Check query syntax. Expected SELECT/CONSTRUCT/ASK/DESCRIBE/UPDATE",
                "error_type": error_type
            }
        ).to_dict()

    if "TimeoutError" in error_type or "timeout" in error_msg.lower():
        return SparqllmError(
            ErrorCode.SPARQL_TIMEOUT,
            f"Query execution timeout: {error_msg}",
            {
                "suggestion": "Simplify query or increase timeout limit",
                "error_type": error_type
            }
        ).to_dict()

    # Unknown error - provide generic response
    return SparqllmError(
        ErrorCode.INTERNAL_ERROR,
        f"Unexpected error: {error_msg}",
        {"error_type": error_type}
    ).to_dict()
