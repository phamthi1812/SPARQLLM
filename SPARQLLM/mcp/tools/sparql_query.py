"""SPARQL query tool for SPARQLLM MCP Server

Executes SPARQL queries with Graph Generating Functions (GGFs).
Supports SELECT, CONSTRUCT, ASK, DESCRIBE queries with validation,
timeout enforcement, and multiple output formats.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from mcp.types import TextContent

from SPARQLLM.udf.SPARQLLM import store, reset_store
from SPARQLLM.mcp.validation import validate_query
from SPARQLLM.mcp.formatting import format_result
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode, handle_error
from SPARQLLM.config import ConfigSingleton

logger = logging.getLogger("SPARQLLM.mcp.tools.sparql_query")


async def sparql_query_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Execute SPARQL query with registered UDFs.

    Provides low-level access to SPARQL execution with:
    - Query validation (syntax + function whitelist)
    - Store isolation (reset before/after)
    - Timeout enforcement
    - Multiple output formats
    - Error handling with agent-focused messages

    Args:
        query: SPARQL query string (required)
        output_format: "json-ld" (default), "csv", "turtle"
        timeout: Timeout in seconds (default: 30, max: 300)
        max_results: Max rows for SELECT (default: 1000, max: 10000)
        preload_data: Optional RDF data to load before query
        preload_format: Format of preload_data (default: "turtle")

    Returns:
        List with single TextContent containing formatted results or error
    """
    # Extract and validate arguments
    query_str = arguments.get("query")
    output_format = arguments.get("output_format", "json-ld")
    timeout = arguments.get("timeout", 30)
    max_results = arguments.get("max_results", 1000)
    preload_data = arguments.get("preload_data")
    preload_format = arguments.get("preload_format", "turtle")

    # Validate required parameters
    if not query_str:
        error = SparqllmError(
            ErrorCode.INVALID_INPUT,
            "Missing required parameter: query",
            {"suggestion": "Provide a SPARQL query string"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]

    # Validate timeout bounds
    if timeout < 1 or timeout > 300:
        error = SparqllmError(
            ErrorCode.INVALID_INPUT,
            f"Timeout must be between 1 and 300 seconds (got {timeout})",
            {"suggestion": "Use timeout between 1-300 seconds"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]

    # Reset store for isolation
    logger.info("Resetting store for query isolation")
    reset_store()

    try:
        # Get config singleton
        config = ConfigSingleton()

        # Validate query (syntax + function whitelist)
        logger.debug("Validating query")
        validate_query(query_str, config)

        # Optional: Preload RDF data
        if preload_data:
            logger.info(f"Preloading data (format: {preload_format})")
            try:
                store.parse(data=preload_data, format=preload_format)
                logger.debug(f"Preloaded data, store size: {len(store)} triples")
            except Exception as e:
                logger.error(f"Failed to preload data: {e}")
                raise SparqllmError(
                    ErrorCode.INVALID_INPUT,
                    f"Failed to parse preload_data: {str(e)}",
                    {"suggestion": f"Check preload_data format (expected {preload_format})"}
                )

        # Execute query with timeout
        logger.info(f"Executing query (timeout: {timeout}s, max_results: {max_results})")

        try:
            # Run query in thread pool to avoid blocking event loop
            result = await asyncio.wait_for(
                asyncio.to_thread(store.query, query_str),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Query exceeded {timeout}s timeout")
            error = SparqllmError(
                ErrorCode.SPARQL_TIMEOUT,
                f"Query execution exceeded {timeout}s timeout",
                {
                    "suggestion": "Simplify query or increase timeout parameter",
                    "timeout": timeout
                }
            )
            return [TextContent(type="text", text=json.dumps(error.to_dict()))]

        # Format result based on requested format
        logger.debug(f"Formatting result as {output_format}")
        formatted = format_result(result, output_format, max_results)

        logger.info(f"Query completed successfully")

        return [
            TextContent(
                type="text",
                text=formatted
            )
        ]

    except SparqllmError as e:
        # Known errors with structured responses
        logger.warning(f"Query failed: {e.message}")
        return [TextContent(type="text", text=json.dumps(e.to_dict()))]

    except ValueError as e:
        # Format errors
        logger.error(f"Formatting error: {e}")
        error = SparqllmError(
            ErrorCode.INVALID_INPUT,
            str(e),
            {"suggestion": "Check output_format parameter"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
        error_dict = handle_error(e)
        return [TextContent(type="text", text=json.dumps(error_dict))]

    finally:
        # Always cleanup store to prevent contamination
        logger.debug("Cleaning up store")
        reset_store()
