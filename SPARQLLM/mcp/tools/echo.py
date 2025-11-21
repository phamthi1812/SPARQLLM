"""Echo tool implementation for testing MCP connectivity"""

from mcp.types import TextContent
import logging

logger = logging.getLogger("SPARQLLM.mcp.tools.echo")


async def echo_tool(arguments: dict) -> list[TextContent]:
    """
    Echo test tool - returns the input message.

    Args:
        arguments: Dict containing "message" key

    Returns:
        List of TextContent with echoed message
    """
    message = arguments.get("message", "")
    logger.info(f"Echo tool called with message: {message}")

    return [
        TextContent(
            type="text",
            text=f"Echo: {message}"
        )
    ]
