"""Convert webpages to knowledge graphs

High-level tool wrapping URL → Scrape → Extract workflow.
"""

import logging
import json
from typing import Dict, Any, List
from mcp.types import TextContent

from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.templates import SIMPLE_WEB_TEMPLATE
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.tools.web_to_knowledge")


async def web_to_knowledge_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Convert webpage to knowledge graph.

    Fetches webpage content and optionally extracts structured data.

    Args:
        url: Webpage URL to scrape
        text_max_chars: Max characters to extract (default: 10000)
        timeout: Timeout in seconds (default: 60)

    Returns:
        Web content as JSON (text extraction)
    """
    # Extract arguments
    url = arguments.get("url")
    text_max_chars = arguments.get("text_max_chars", 10000)
    timeout = arguments.get("timeout", 60)

    if not url:
        error = SparqllmError(
            ErrorCode.INVALID_INPUT,
            "Missing required parameter: url",
            {"suggestion": "Provide a valid URL"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]

    logger.info(f"Fetching knowledge from: {url}")

    # Build query from template
    query = SIMPLE_WEB_TEMPLATE.format(url=url)

    # Execute via core SPARQL tool
    try:
        result = await sparql_query_tool({
            "query": query,
            "output_format": "json",
            "timeout": timeout
        })

        logger.info("Web extraction completed successfully")
        return result

    except SparqllmError as e:
        # Add tool-specific suggestions
        if e.code == ErrorCode.SPARQL_TIMEOUT:
            e.details["suggestion"] = "URL taking too long - increase timeout or try different URL"
        elif e.code == ErrorCode.INVALID_FUNCTION:
            e.details["suggestion"] = "Ensure SLM-GETTEXT function is registered in config.ini"

        logger.error(f"Web extraction failed: {e.message}")
        return [TextContent(type="text", text=json.dumps(e.to_dict()))]

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        error = SparqllmError(
            ErrorCode.INTERNAL_ERROR,
            f"Web extraction failed: {str(e)}",
            {"suggestion": "Check URL is accessible and valid"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]
