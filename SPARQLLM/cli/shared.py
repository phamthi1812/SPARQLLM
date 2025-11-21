"""Shared query execution logic between CLI and MCP server

Extracted from slm.py to follow DRY principle.
"""

import logging
from typing import Optional, Tuple, Any
from rdflib.plugins.sparql.parser import parseUpdate
from SPARQLLM.udf.SPARQLLM import store


logger = logging.getLogger("SPARQLLM.cli.shared")


def is_update_query(sparql_query: str) -> bool:
    """
    Check if a SPARQL query is an UPDATE query.

    Args:
        sparql_query: SPARQL query string

    Returns:
        True if UPDATE query, False otherwise
    """
    try:
        parseUpdate(sparql_query)
        return True
    except Exception:
        return False


def execute_query(
    query_str: str,
    config_file: Optional[str] = None,
    load_file: Optional[str] = None,
    load_format: str = "xml",
    timeout: Optional[int] = None
) -> Tuple[Any, str]:
    """
    Execute a SPARQL query and return results.

    Args:
        query_str: SPARQL query to execute
        config_file: Optional config file path (already initialized if None)
        load_file: Optional RDF file to preload into store
        load_format: Format of RDF file (turtle, xml, nquads, etc.)
        timeout: Query timeout in seconds

    Returns:
        Tuple of (query_result, result_type) where result_type is "UPDATE", "CONSTRUCT", or "SELECT"
    """
    # Load RDF data if specified
    if load_file is not None:
        store.parse(load_file, format=load_format)
        logger.debug(f"Loaded data from {load_file} (format={load_format}), store size: {len(store)} triples")

    # Execute query
    if is_update_query(query_str):
        logger.info("Executing UPDATE query")
        store.update(query_str)
        return None, "UPDATE"
    else:
        qres = store.query(query_str)
        result_type = qres.type if hasattr(qres, 'type') else "SELECT"
        return qres, result_type


def format_query_result(qres: Any, result_type: str, output_format: str = "table") -> str:
    """
    Format query results for output.

    Args:
        qres: Query result object from rdflib
        result_type: Type of query result ("CONSTRUCT", "SELECT", etc.)
        output_format: Output format ("table", "csv", "turtle", "json-ld")

    Returns:
        Formatted result string
    """
    if result_type == "UPDATE":
        return "UPDATE query executed successfully"

    if result_type == "CONSTRUCT":
        if output_format == "turtle":
            return qres.serialize(format="turtle")
        elif output_format == "json-ld":
            return qres.serialize(format="json-ld")
        else:
            return qres.serialize(format="turtle")  # default

    # SELECT results
    if output_format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(qres.vars)
        for row in qres:
            writer.writerow(row)
        return output.getvalue()
    else:
        # Table format - delegate to original CLI formatting
        from SPARQLLM.utils.utils import print_result_as_table
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        print_result_as_table(qres)
        result = sys.stdout.getvalue()
        sys.stdout = old_stdout
        return result
