"""Extract structured data from files

High-level tool wrapping File → Parse → Extract workflow.
"""

import logging
import json
from typing import Dict, Any, List
from mcp.types import TextContent

from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.templates import CSV_EXTRACT_TEMPLATE, SIMPLE_EXTRACT_TEMPLATE
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.tools.extract_structured_data")


async def extract_structured_data_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Extract structured data from files.

    Supports CSV, HTML, TXT, and other formats via registered UDFs.
    Automatically selects appropriate parser based on file extension.

    Args:
        file_path: Path to file (local path or URL)
        format_hint: Optional format hint ("csv", "html", "txt")
        limit: Max results to return (default: 100)
        timeout: Timeout in seconds (default: 60)

    Returns:
        Extracted data as JSON-LD
    """
    # Extract arguments
    file_path = arguments.get("file_path")
    format_hint = arguments.get("format_hint", "").lower()
    limit = arguments.get("limit", 100)
    timeout = arguments.get("timeout", 60)

    if not file_path:
        error = SparqllmError(
            ErrorCode.INVALID_INPUT,
            "Missing required parameter: file_path",
            {"suggestion": "Provide a file path or URL"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]

    logger.info(f"Extracting structured data from: {file_path}")

    # Determine template based on file extension or hint
    if format_hint == "csv" or file_path.lower().endswith(".csv"):
        logger.debug("Using CSV extraction template")
        template = CSV_EXTRACT_TEMPLATE
    else:
        logger.debug("Using generic extraction template")
        template = SIMPLE_EXTRACT_TEMPLATE

    # Build query from template
    query = template.format(
        file_path=file_path,
        limit=limit
    )

    # Execute via core SPARQL tool
    try:
        result = await sparql_query_tool({
            "query": query,
            "output_format": "json",
            "timeout": timeout,
            "max_results": limit
        })

        logger.info("Extraction completed successfully")
        return result

    except SparqllmError as e:
        # Add tool-specific suggestions
        if e.code == ErrorCode.SPARQL_TIMEOUT:
            e.details["suggestion"] = "File too large - try reducing limit or increasing timeout"
        elif e.code == ErrorCode.INVALID_FUNCTION:
            e.details["suggestion"] = "Ensure SLM-FILE and file parser functions are registered in config.ini"

        logger.error(f"Extraction failed: {e.message}")
        return [TextContent(type="text", text=json.dumps(e.to_dict()))]

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        error = SparqllmError(
            ErrorCode.INTERNAL_ERROR,
            f"Extraction failed: {str(e)}",
            {"suggestion": "Check file path and format"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]
