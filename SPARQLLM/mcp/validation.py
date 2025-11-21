"""Query validation module for SPARQLLM MCP Server

Implements three-layer validation:
1. SPARQL syntax validation
2. Function whitelist enforcement
3. Query type detection
"""

import re
import logging
from typing import Set
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from SPARQLLM.config import ConfigSingleton
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.validation")


def extract_ggf_functions(query_str: str) -> Set[str]:
    """
    Extract all ggf:FUNCTION references from SPARQL query.

    Args:
        query_str: SPARQL query string

    Returns:
        Set of function names (without ggf: prefix)
    """
    # Pattern matches ggf:FUNCTION-NAME format
    pattern = r'ggf:([A-Z0-9_-]+)'
    matches = re.findall(pattern, query_str, re.IGNORECASE)
    return set(matches)


def validate_sparql_syntax(query_str: str) -> None:
    """
    Validate SPARQL syntax by attempting to parse.

    Args:
        query_str: SPARQL query string

    Raises:
        SparqllmError: If syntax is invalid
    """
    try:
        # Try parsing as query (SELECT, CONSTRUCT, ASK, DESCRIBE)
        parseQuery(query_str)
        logger.debug("Query parsed successfully as SELECT/CONSTRUCT/ASK/DESCRIBE")
    except Exception as query_error:
        # Try parsing as update (INSERT, DELETE, UPDATE)
        try:
            parseUpdate(query_str)
            logger.debug("Query parsed successfully as UPDATE")
        except Exception as update_error:
            # Neither worked - invalid syntax
            raise SparqllmError(
                ErrorCode.SPARQL_SYNTAX_ERROR,
                f"Invalid SPARQL syntax: {str(query_error)}",
                {
                    "line": getattr(query_error, "lineno", None),
                    "column": getattr(query_error, "col", None),
                    "suggestion": "Check SPARQL syntax. Expected SELECT, CONSTRUCT, ASK, DESCRIBE, or UPDATE."
                }
            )


def validate_function_whitelist(
    query_str: str,
    config: ConfigSingleton
) -> None:
    """
    Ensure only registered UDFs are used in query.

    Args:
        query_str: SPARQL query string
        config: ConfigSingleton with loaded [Associations]

    Raises:
        SparqllmError: If unknown functions are used
    """
    # Get allowed functions from config
    if "Associations" not in config.config:
        logger.warning("No [Associations] section in config - allowing all functions")
        return

    allowed = set(config.config["Associations"].keys())
    used = extract_ggf_functions(query_str)

    # Check for unknown functions
    unknown = used - allowed

    if unknown:
        logger.warning(f"Query uses unknown functions: {unknown}")
        raise SparqllmError(
            ErrorCode.INVALID_FUNCTION,
            f"Unknown functions: {', '.join(unknown)}",
            {
                "unknown": list(unknown),
                "allowed": list(allowed),
                "suggestion": "Check config.ini [Associations] for registered functions"
            }
        )

    logger.debug(f"All used functions are registered: {used}")


def validate_query(query_str: str, config: ConfigSingleton) -> None:
    """
    Perform full query validation (syntax + whitelist).

    Args:
        query_str: SPARQL query string
        config: ConfigSingleton instance

    Raises:
        SparqllmError: If validation fails
    """
    logger.debug("Starting query validation")

    # Layer 1: Syntax
    validate_sparql_syntax(query_str)

    # Layer 2: Function whitelist
    validate_function_whitelist(query_str, config)

    logger.debug("Query validation successful")
