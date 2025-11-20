# Phase 2: Core sparql.query Tool

**Duration:** 2-3 days
**Status:** Ready for implementation
**Dependencies:** Phase 1 complete

## Overview

Implement low-level `sparql.query` tool exposing full SPARQL execution via MCP. Focus: query validation, store isolation, result formatting, timeout enforcement. Outcome: Agents execute arbitrary SPARQL with registered UDFs.

## Context & Key Insights

**From research:**
- Parameterized queries "not foolproof" - need layered validation
- JSON-LD preferred for RDF results (LLM-friendly)
- 30s timeout standard for SPARQL endpoints
- Result cardinality limits prevent out-of-memory

**From codebase analysis:**
- `store.query()` executes SELECT/CONSTRUCT
- `store.update()` executes UPDATE/INSERT/DELETE
- `is_update_query()` detects query type
- Results formatted via `print_result_as_table()` (SELECT) or `serialize()` (CONSTRUCT)
- `reset_store()` clears graphs between queries

## Architecture Decisions

### 1. Query Validation Strategy
**Decision:** Three-layer validation
1. **Syntax validation**: Parse with `parseQuery()` before execution
2. **Function whitelist**: Scan for `ggf:*` functions, reject if not in config
3. **Timeout enforcement**: 30s default (configurable per request)

**Implementation:**
```python
def validate_query(query_str: str, config: ConfigSingleton) -> None:
    # Layer 1: Syntax
    try:
        parseQuery(query_str)
    except Exception as e:
        raise SparqllmError(ErrorCode.SPARQL_SYNTAX_ERROR, str(e))

    # Layer 2: Function whitelist
    allowed_functions = set(config.config["Associations"].keys())
    used_functions = extract_ggf_functions(query_str)  # regex: ggf:(\w+)
    unknown = used_functions - allowed_functions

    if unknown:
        raise SparqllmError(
            ErrorCode.INVALID_FUNCTION,
            f"Unknown functions: {unknown}",
            {"allowed": list(allowed_functions)}
        )
```

**Rationale:** Defense in depth, prevents injection + unknown UDF calls

### 2. Store Isolation
**Decision:** Reset store before and after each tool call

```python
async def sparql_query_tool(arguments: dict) -> list[TextContent]:
    reset_store()  # Clear previous state
    try:
        result = execute_query(...)
        return format_result(result)
    finally:
        reset_store()  # Cleanup even on error
```

**Rationale:** Prevents cross-request contamination, critical for multi-agent deployments

### 3. Result Format Negotiation
**Decision:** Support 3 formats via `output_format` parameter
- `json-ld` (default): CONSTRUCT results as JSON-LD, SELECT as JSON array
- `csv`: SELECT results only
- `turtle`: CONSTRUCT results only

**Schema:**
```json
{
  "query": "SELECT ?s WHERE { ?s ?p ?o }",
  "output_format": "json-ld",  // or "csv", "turtle"
  "timeout": 30,  // seconds
  "max_results": 1000  // row limit for SELECT
}
```

**Rationale:** Flexibility for different agent use cases, JSON-LD default per research

### 4. Timeout Mechanism
**Decision:** Use `asyncio.wait_for()` with configurable timeout

```python
async def sparql_query_tool(arguments: dict) -> list[TextContent]:
    timeout = arguments.get("timeout", 30)
    query_str = arguments["query"]

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(store.query, query_str),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise SparqllmError(
            ErrorCode.SPARQL_TIMEOUT,
            f"Query exceeded {timeout}s timeout",
            {"suggestion": "Simplify query or increase timeout"}
        )
```

**Rationale:** Prevents resource exhaustion, aligns with SPARQL endpoint standards

## Implementation Steps

### Step 1: Query Validation Module (3-4 hours)
**File:** `SPARQLLM/mcp/validation.py`

```python
import re
from typing import Set
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from SPARQLLM.config import ConfigSingleton
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

def extract_ggf_functions(query_str: str) -> Set[str]:
    """Extract all ggf:FUNCTION references from query."""
    pattern = r'ggf:([A-Z0-9_-]+)'
    matches = re.findall(pattern, query_str, re.IGNORECASE)
    return set(matches)

def validate_sparql_syntax(query_str: str) -> None:
    """Validate SPARQL syntax."""
    try:
        parseQuery(query_str)
    except Exception as parse_error:
        try:
            parseUpdate(query_str)
        except Exception:
            raise SparqllmError(
                ErrorCode.SPARQL_SYNTAX_ERROR,
                f"Invalid SPARQL: {str(parse_error)}",
                {
                    "line": getattr(parse_error, "lineno", None),
                    "column": getattr(parse_error, "col", None)
                }
            )

def validate_function_whitelist(
    query_str: str,
    config: ConfigSingleton
) -> None:
    """Ensure only registered functions are used."""
    allowed = set(config.config["Associations"].keys())
    used = extract_ggf_functions(query_str)
    unknown = used - allowed

    if unknown:
        raise SparqllmError(
            ErrorCode.INVALID_FUNCTION,
            f"Unknown functions: {', '.join(unknown)}",
            {
                "unknown": list(unknown),
                "allowed": list(allowed),
                "suggestion": "Check config.ini [Associations]"
            }
        )

def validate_query(query_str: str, config: ConfigSingleton) -> None:
    """Full query validation."""
    validate_sparql_syntax(query_str)
    validate_function_whitelist(query_str, config)
```

### Step 2: Result Formatting Module (4-5 hours)
**File:** `SPARQLLM/mcp/formatting.py`

```python
from typing import Any, List
from rdflib.query import Result
import json
import io

def format_select_json(result: Result, max_results: int = 1000) -> str:
    """Format SELECT results as JSON array."""
    rows = []
    for i, row in enumerate(result):
        if i >= max_results:
            break
        rows.append({
            str(var): str(row[var]) if row[var] else None
            for var in result.vars
        })

    return json.dumps({
        "type": "SELECT",
        "vars": [str(v) for v in result.vars],
        "results": rows,
        "truncated": len(rows) >= max_results
    }, indent=2)

def format_select_csv(result: Result, max_results: int = 1000) -> str:
    """Format SELECT results as CSV."""
    import csv
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([str(v) for v in result.vars])

    # Rows
    for i, row in enumerate(result):
        if i >= max_results:
            break
        writer.writerow([str(row[v]) if row[v] else "" for v in result.vars])

    return output.getvalue()

def format_construct_jsonld(result: Result) -> str:
    """Format CONSTRUCT results as JSON-LD."""
    # result is an rdflib.Graph for CONSTRUCT
    graph = result.graph if hasattr(result, "graph") else result

    # Serialize to JSON-LD with compact context
    jsonld_str = graph.serialize(format="json-ld", indent=2)

    return jsonld_str

def format_construct_turtle(result: Result) -> str:
    """Format CONSTRUCT results as Turtle."""
    graph = result.graph if hasattr(result, "graph") else result
    return graph.serialize(format="turtle")

def format_result(
    result: Result,
    output_format: str = "json-ld",
    max_results: int = 1000
) -> str:
    """Format query result based on type and requested format."""

    # Detect query type
    is_construct = result.type == "CONSTRUCT"

    if is_construct:
        if output_format == "json-ld":
            return format_construct_jsonld(result)
        elif output_format == "turtle":
            return format_construct_turtle(result)
        else:
            raise ValueError(f"Format {output_format} not supported for CONSTRUCT")
    else:  # SELECT, ASK, DESCRIBE
        if output_format == "json-ld" or output_format == "json":
            return format_select_json(result, max_results)
        elif output_format == "csv":
            return format_select_csv(result, max_results)
        else:
            raise ValueError(f"Format {output_format} not supported for SELECT")
```

### Step 3: Core sparql.query Tool (5-6 hours)
**File:** `SPARQLLM/mcp/tools/sparql_query.py`

```python
import asyncio
import logging
from typing import Dict, Any
from mcp.types import TextContent
from SPARQLLM.udf.SPARQLLM import store, reset_store
from SPARQLLM.mcp.validation import validate_query
from SPARQLLM.mcp.formatting import format_result
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode, handle_error
from SPARQLLM.config import ConfigSingleton

logger = logging.getLogger("SPARQLLM.mcp.tools")

async def sparql_query_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Execute SPARQL query with registered UDFs.

    Args:
        query: SPARQL query string (SELECT, CONSTRUCT, ASK, DESCRIBE)
        output_format: "json-ld" (default), "csv", "turtle"
        timeout: Timeout in seconds (default: 30)
        max_results: Max rows for SELECT queries (default: 1000)
        preload_data: Optional RDF data to load before query
        preload_format: Format of preload_data (default: "turtle")

    Returns:
        Query results in requested format
    """

    # Extract arguments
    query_str = arguments.get("query")
    output_format = arguments.get("output_format", "json-ld")
    timeout = arguments.get("timeout", 30)
    max_results = arguments.get("max_results", 1000)
    preload_data = arguments.get("preload_data")
    preload_format = arguments.get("preload_format", "turtle")

    if not query_str:
        raise SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            "Missing required parameter: query"
        )

    # Reset store for isolation
    reset_store()

    try:
        # Validate query
        config = ConfigSingleton()
        validate_query(query_str, config)

        # Optional: Preload data
        if preload_data:
            logger.debug(f"Preloading data (format: {preload_format})")
            store.parse(data=preload_data, format=preload_format)

        # Execute with timeout
        logger.info(f"Executing query (timeout: {timeout}s)")
        result = await asyncio.wait_for(
            asyncio.to_thread(store.query, query_str),
            timeout=timeout
        )

        # Format result
        formatted = format_result(result, output_format, max_results)

        logger.info(f"Query completed successfully")

        return [
            TextContent(
                type="text",
                text=formatted
            )
        ]

    except asyncio.TimeoutError:
        error = SparqllmError(
            ErrorCode.SPARQL_TIMEOUT,
            f"Query exceeded {timeout}s timeout",
            {"suggestion": "Simplify query or increase timeout parameter"}
        )
        return [TextContent(type="text", text=json.dumps(error.to_dict()))]

    except SparqllmError as e:
        logger.warning(f"Query validation failed: {e.message}")
        return [TextContent(type="text", text=json.dumps(e.to_dict()))]

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        error_dict = handle_error(e)
        return [TextContent(type="text", text=json.dumps(error_dict))]

    finally:
        # Cleanup
        reset_store()
```

### Step 4: Update Tool Schema (1-2 hours)
**File:** `SPARQLLM/mcp/schemas/tool_schemas.py`

```python
from mcp.types import Tool

TOOL_SCHEMAS = [
    # ... existing echo tool ...

    Tool(
        name="sparql_query",
        description=(
            "Execute SPARQL query with Graph Generating Functions (GGFs). "
            "Supports SELECT, CONSTRUCT, ASK, DESCRIBE. "
            "Use ggf:FUNCTION(?args) to call registered functions. "
            "Available functions depend on config.ini [Associations]."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SPARQL query string (SELECT, CONSTRUCT, etc.)"
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json-ld", "csv", "turtle"],
                    "default": "json-ld",
                    "description": "Result format (json-ld for CONSTRUCT, csv/json-ld for SELECT)"
                },
                "timeout": {
                    "type": "number",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 300,
                    "description": "Query timeout in seconds"
                },
                "max_results": {
                    "type": "number",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Maximum rows for SELECT queries"
                },
                "preload_data": {
                    "type": "string",
                    "description": "Optional RDF data to load before query (Turtle/JSON-LD)"
                },
                "preload_format": {
                    "type": "string",
                    "enum": ["turtle", "xml", "json-ld", "nquads"],
                    "default": "turtle",
                    "description": "Format of preload_data"
                }
            },
            "required": ["query"]
        }
    )
]
```

### Step 5: Register Tool in Server (30 minutes)
**File:** `SPARQLLM/mcp/server.py`

```python
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool

class SparqllmMCPServer:
    def __init__(self, config_file: str):
        # ... existing code ...
        self.server.call_tool("sparql_query")(sparql_query_tool)
```

### Step 6: Unit Tests (4-5 hours)
**File:** `tests/test_sparql_query_tool.py`

```python
import pytest
import asyncio
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.config import ConfigSingleton

@pytest.fixture
def setup_config():
    ConfigSingleton(config_file="config.ini")

@pytest.mark.asyncio
async def test_simple_select(setup_config):
    """Test basic SELECT query."""
    result = await sparql_query_tool({
        "query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
        "output_format": "json-ld"
    })

    assert len(result) == 1
    # Should return empty results (no preloaded data)
    import json
    data = json.loads(result[0].text)
    assert data["type"] == "SELECT"

@pytest.mark.asyncio
async def test_csv_file_query(setup_config):
    """Test CSV parsing UDF."""
    query = '''
    PREFIX ggf: <http://example.org/>
    PREFIX ex: <http://example.org/>
    SELECT ?city WHERE {
        BIND(ggf:SLM-FILE("./data/results.csv") as ?file)
        BIND(ggf:SLM-CSV(?file) AS ?g)
        GRAPH ?g { ?x ex:city ?city . }
    } LIMIT 10
    '''

    result = await sparql_query_tool({
        "query": query,
        "output_format": "json-ld"
    })

    import json
    data = json.loads(result[0].text)
    assert data["type"] == "SELECT"
    assert len(data["results"]) > 0

@pytest.mark.asyncio
async def test_timeout_enforcement(setup_config):
    """Test query timeout."""
    # Infinite loop query (if RECURSE with no limit)
    query = '''
    PREFIX ggf: <http://example.org/>
    SELECT ?s WHERE {
        BIND(ggf:SLM-GRAPH("ex:a ex:p ex:b .") AS ?g)
        BIND(ggf:SLM-RECURSE("CONSTRUCT {?s ?p ?o} WHERE {?s ?p ?o}", ?g, 999999) AS ?out)
        GRAPH ?out { ?s ?p ?o }
    }
    '''

    result = await sparql_query_tool({
        "query": query,
        "timeout": 2  # 2 second timeout
    })

    import json
    data = json.loads(result[0].text)
    assert "error" in data
    assert data["error"]["code"] == "SPARQL_TIMEOUT"

@pytest.mark.asyncio
async def test_invalid_function(setup_config):
    """Test unknown function rejection."""
    query = '''
    PREFIX ggf: <http://example.org/>
    SELECT ?s WHERE {
        BIND(ggf:UNKNOWN-FUNCTION("test") AS ?g)
        GRAPH ?g { ?s ?p ?o }
    }
    '''

    result = await sparql_query_tool({"query": query})

    import json
    data = json.loads(result[0].text)
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FUNCTION"

@pytest.mark.asyncio
async def test_syntax_error(setup_config):
    """Test syntax error handling."""
    result = await sparql_query_tool({
        "query": "INVALID SPARQL"
    })

    import json
    data = json.loads(result[0].text)
    assert "error" in data
    assert data["error"]["code"] == "SPARQL_SYNTAX_ERROR"
```

### Step 7: Integration Test (2-3 hours)
**File:** `tests/test_mcp_integration.py`

```python
import pytest
import subprocess
import json

@pytest.mark.integration
def test_mcp_sparql_query_via_stdio():
    """Test sparql_query tool via STDIO."""

    # Start server
    proc = subprocess.Popen(
        ["slm-mcp-server", "--config", "config.ini"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1
    }
    message = json.dumps(init_request) + "\n"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

    # Read response
    response_line = proc.stdout.readline()
    init_response = json.loads(response_line)
    assert "result" in init_response

    # Send tools/list request
    list_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    message = json.dumps(list_request) + "\n"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

    response_line = proc.stdout.readline()
    list_response = json.loads(response_line)
    tools = list_response["result"]["tools"]
    assert any(t["name"] == "sparql_query" for t in tools)

    # Send sparql_query request
    query_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "sparql_query",
            "arguments": {
                "query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"
            }
        },
        "id": 3
    }
    message = json.dumps(query_request) + "\n"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

    response_line = proc.stdout.readline()
    query_response = json.loads(response_line)
    assert "result" in query_response

    proc.terminate()
```

## Success Criteria

- [ ] `sparql_query` tool listed in `tools/list`
- [ ] Simple SELECT query executes and returns JSON
- [ ] CSV parsing query (filesystem UDF) works
- [ ] Timeout enforced for long queries
- [ ] Unknown functions rejected with error
- [ ] Syntax errors return helpful messages
- [ ] Store reset between calls (no contamination)
- [ ] JSON-LD output for CONSTRUCT queries
- [ ] CSV output for SELECT queries
- [ ] Tests pass: `pytest tests/test_sparql_query_tool.py -v`

## Security Considerations

- **Function whitelist**: Only registered UDFs allowed
- **Syntax validation**: Prevents injection via malformed queries
- **Timeout**: Prevents resource exhaustion
- **Max results**: Caps memory usage for large result sets
- **Store reset**: Isolates requests, prevents data leaks

## Performance Notes

- **Typical query latency**: 50-500ms (filesystem UDFs)
- **LLM query latency**: 2-10s (depends on model)
- **Memory per query**: 10-100MB (depends on result size)
- **Concurrent requests**: Limited by STDIO (1 per connection)

## Known Limitations

- **No query optimization hints**: Future enhancement
- **No streaming results**: Full result materialized before return
- **No partial results on timeout**: All-or-nothing
- **No query plan inspection**: Debug mode future enhancement

## Next Steps

After Phase 2 completion:
- Phase 3: Build convenience tools on top of `sparql.query`
- Gather feedback on error messages from early users
- Identify common query patterns for wrappers

## References

- SPARQL 1.1 Spec: https://www.w3.org/TR/sparql11-query/
- Apache Jena Parameterization: https://jena.apache.org/documentation/query/parameterized-sparql-strings.html
- JSON-LD Spec: https://www.w3.org/TR/json-ld11/
- Existing CLI: `SPARQLLM/cli/slm.py`
