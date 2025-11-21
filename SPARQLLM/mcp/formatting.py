"""Result formatting module for SPARQLLM MCP Server

Formats SPARQL query results in multiple formats:
- JSON-LD for CONSTRUCT results
- JSON/CSV for SELECT results
- Turtle for CONSTRUCT results
"""

import json
import io
import csv
import logging
from typing import Any
from rdflib.query import Result

logger = logging.getLogger("SPARQLLM.mcp.formatting")


def format_select_json(result: Result, max_results: int = 1000) -> str:
    """
    Format SELECT query results as JSON array.

    Args:
        result: rdflib Result object
        max_results: Maximum number of rows to return

    Returns:
        JSON string with SELECT results
    """
    rows = []
    for i, row in enumerate(result):
        if i >= max_results:
            logger.warning(f"Result truncated at {max_results} rows")
            break

        row_dict = {}
        for var in result.vars:
            value = row[var]
            # Convert RDF terms to strings
            row_dict[str(var)] = str(value) if value is not None else None

        rows.append(row_dict)

    output = {
        "type": "SELECT",
        "vars": [str(v) for v in result.vars],
        "results": rows,
        "count": len(rows),
        "truncated": len(rows) >= max_results
    }

    return json.dumps(output, indent=2)


def format_select_csv(result: Result, max_results: int = 1000) -> str:
    """
    Format SELECT query results as CSV.

    Args:
        result: rdflib Result object
        max_results: Maximum number of rows to return

    Returns:
        CSV string with header and data rows
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([str(v) for v in result.vars])

    # Write data rows
    row_count = 0
    for i, row in enumerate(result):
        if i >= max_results:
            logger.warning(f"CSV result truncated at {max_results} rows")
            break

        row_values = []
        for var in result.vars:
            value = row[var]
            row_values.append(str(value) if value is not None else "")

        writer.writerow(row_values)
        row_count += 1

    return output.getvalue()


def format_construct_jsonld(result: Any) -> str:
    """
    Format CONSTRUCT query results as JSON-LD.

    Args:
        result: rdflib Graph or Result object

    Returns:
        JSON-LD string
    """
    # CONSTRUCT results are Graph objects
    graph = result.graph if hasattr(result, "graph") else result

    # Serialize to JSON-LD with compact formatting
    try:
        jsonld_bytes = graph.serialize(format="json-ld", indent=2)
        # Handle both str and bytes return types
        if isinstance(jsonld_bytes, bytes):
            return jsonld_bytes.decode("utf-8")
        return jsonld_bytes
    except Exception as e:
        logger.error(f"Error serializing to JSON-LD: {e}")
        # Fallback to turtle if JSON-LD fails
        return format_construct_turtle(result)


def format_construct_turtle(result: Any) -> str:
    """
    Format CONSTRUCT query results as Turtle.

    Args:
        result: rdflib Graph or Result object

    Returns:
        Turtle string
    """
    graph = result.graph if hasattr(result, "graph") else result

    try:
        turtle_bytes = graph.serialize(format="turtle")
        # Handle both str and bytes return types
        if isinstance(turtle_bytes, bytes):
            return turtle_bytes.decode("utf-8")
        return turtle_bytes
    except Exception as e:
        logger.error(f"Error serializing to Turtle: {e}")
        raise


def format_result(
    result: Result,
    output_format: str = "json-ld",
    max_results: int = 1000
) -> str:
    """
    Format query result based on type and requested format.

    Args:
        result: rdflib Result object
        output_format: Desired format ("json-ld", "csv", "turtle", "json")
        max_results: Maximum rows for SELECT queries

    Returns:
        Formatted result string

    Raises:
        ValueError: If format is incompatible with result type
    """
    logger.debug(f"Formatting result as {output_format}")

    # Detect query type
    result_type = getattr(result, 'type', None)
    is_construct = result_type == "CONSTRUCT"

    if is_construct:
        logger.debug("Formatting CONSTRUCT result")
        if output_format == "json-ld":
            return format_construct_jsonld(result)
        elif output_format == "turtle":
            return format_construct_turtle(result)
        else:
            raise ValueError(
                f"Format '{output_format}' not supported for CONSTRUCT queries. "
                f"Use 'json-ld' or 'turtle'."
            )
    else:
        # SELECT, ASK, DESCRIBE
        logger.debug(f"Formatting {result_type} result")
        if output_format in ("json-ld", "json"):
            return format_select_json(result, max_results)
        elif output_format == "csv":
            return format_select_csv(result, max_results)
        else:
            raise ValueError(
                f"Format '{output_format}' not supported for {result_type} queries. "
                f"Use 'json' or 'csv'."
            )
