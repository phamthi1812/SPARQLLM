# Phase 3: High-Level Convenience Tools

**Duration:** 4-6 days
**Status:** Ready for implementation
**Dependencies:** Phase 2 complete

## Overview

Build workflow-oriented tools wrapping common SPARQL query patterns. These tools simplify agent interactions by abstracting GGF chaining. Focus: extract_structured_data, rag_search, web_to_knowledge, query_database. Outcome: Production-ready tools for common RAG patterns.

## Context & Key Insights

**From query analysis:**
- Most workflows chain 2-4 GGFs: File → Parse → LLM → Extract
- Search workflows: Query → FAISS → LLM synthesis
- Web workflows: URL → Scrape → LLM extraction → RDF
- Agents prefer high-level abstractions over raw SPARQL

**From research:**
- Tool descriptions critical for LLM discoverability
- Flat input schemas preferred (avoid nested objects)
- Return schema.org types for interoperability
- Convenience tools can wrap `sparql_query` internally

## Architecture Decisions

### 1. Tool Design Philosophy
**Decision:** Convenience tools are wrappers around pre-built SPARQL templates
- Each tool constructs SPARQL query from simple parameters
- Calls `sparql_query_tool()` internally
- Post-processes results for agent consumption

**Example:**
```python
async def extract_structured_data(arguments: dict) -> list[TextContent]:
    file_path = arguments["file_path"]
    extraction_prompt = arguments["extraction_prompt"]

    # Build SPARQL from template
    query = EXTRACT_TEMPLATE.format(
        file_path=file_path,
        prompt=extraction_prompt
    )

    # Delegate to core tool
    return await sparql_query_tool({"query": query, "output_format": "json-ld"})
```

**Rationale:** DRY principle, single source of truth for query execution

### 2. Template Management
**Decision:** SPARQL templates as Python string constants
- Templates in `SPARQLLM/mcp/templates.py`
- Use `.format()` for simple substitution
- Escape user input for literal injection prevention

**Alternative rejected:** External .sparql files (adds I/O overhead)

### 3. Return Schema Standardization
**Decision:** All tools return schema.org types
- `extract_structured_data` → `schema:Thing` with extracted properties
- `rag_search` → `schema:SearchResultsPage` with `schema:itemListElement`
- `web_to_knowledge` → `schema:WebPage` with entities
- `query_database` → `schema:Dataset` with observations

**Rationale:** Consistency, interoperability with other MCP tools

### 4. Error Handling
**Decision:** Propagate `sparql_query` errors with context-specific suggestions

```python
except SparqllmError as e:
    # Add tool-specific suggestion
    if e.code == ErrorCode.SPARQL_TIMEOUT:
        e.details["suggestion"] = "Try smaller file or simpler extraction prompt"
    raise
```

**Rationale:** Agent-focused messages per research guidelines

## Implementation Steps

### Step 1: SPARQL Template Library (3-4 hours)
**File:** `SPARQLLM/mcp/templates.py`

```python
# Template: Extract structured data from file
EXTRACT_STRUCTURED_DATA_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?entity ?property ?value WHERE {{
    # Step 1: Resolve file path
    BIND(ggf:SLM-FILE("{file_path}") AS ?filePath)

    # Step 2: Parse file based on extension
    BIND(ggf:SLM-READFILE(?filePath) AS ?contentGraph)

    # Step 3: Extract text
    GRAPH ?contentGraph {{
        ?doc schema:text ?text .
    }}

    # Step 4: LLM extraction
    BIND(ggf:LLM(CONCAT("{extraction_prompt}", "\\n\\nText: ", ?text), "{model}", {temperature}) AS ?llmGraph)

    # Step 5: Extract structured output
    GRAPH ?llmGraph {{
        ?entity ?property ?value .
    }}
}}
"""

# Template: RAG search with vector similarity
RAG_SEARCH_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?result ?score WHERE {{
    # Step 1: Vector search
    BIND(ggf:MCP-TOOL("faiss", "faiss.search_index",
        ggf:OBJ("query", "{query}", "k", {top_k})) AS ?searchGraph)

    # Step 2: Extract results
    GRAPH ?searchGraph {{
        ?dataset schema:hasPart ?obs .
        ?obs schema:name ?docText ;
             schema:value ?score .
    }}

    # Step 3: LLM synthesis
    BIND(ggf:LLM(CONCAT("{synthesis_prompt}", "\\n\\nDocuments: ", ?docText), "{model}", 0.0) AS ?llmGraph)

    # Step 4: Extract answer
    GRAPH ?llmGraph {{
        ?answer schema:text ?result .
    }}
}}
ORDER BY DESC(?score)
LIMIT {limit}
"""

# Template: Web scraping to knowledge graph
WEB_TO_KNOWLEDGE_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

CONSTRUCT {{
    ?entity ?property ?value .
    ?entity a schema:Thing ;
            schema:url <{url}> .
}}
WHERE {{
    # Step 1: Scrape webpage
    BIND(ggf:SNAP("{url}", {text_max_chars}) AS ?snapGraph)

    # Step 2: Extract text
    GRAPH ?snapGraph {{
        ?page schema:text ?text .
    }}

    # Step 3: LLM entity extraction
    BIND(ggf:LLM(CONCAT("{extraction_prompt}", "\\n\\nText: ", ?text), "{model}", 0.0) AS ?llmGraph)

    # Step 4: Extract entities
    GRAPH ?llmGraph {{
        ?entity ?property ?value .
    }}
}}
"""

# Template: Database query to RDF
QUERY_DATABASE_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?column ?value WHERE {{
    # Step 1: Execute SQL
    BIND(ggf:MCP-TOOL("postgres", "postgres.sql.query",
        ggf:OBJ("sql", "{sql_query}")) AS ?dbGraph)

    # Step 2: Extract results
    GRAPH ?dbGraph {{
        ?dataset schema:hasPart ?obs .
        ?obs schema:name ?column ;
             schema:value ?value .
    }}
}}
LIMIT {limit}
"""
```

### Step 2: extract_structured_data Tool (4-5 hours)
**File:** `SPARQLLM/mcp/tools/extract_structured_data.py`

```python
import logging
from typing import Dict, Any
from mcp.types import TextContent
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.templates import EXTRACT_STRUCTURED_DATA_TEMPLATE
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.tools")

async def extract_structured_data_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Extract structured data from files using LLM.

    Workflow: File → Parser → LLM → Structured RDF

    Args:
        file_path: Path to file (local or URL)
        extraction_prompt: Instructions for LLM extraction
        model: LLM model name (default: llama-3.3-70b-versatile)
        temperature: LLM temperature (default: 0.0)
        timeout: Timeout in seconds (default: 60)

    Returns:
        Extracted entities as JSON-LD graph
    """

    # Extract arguments
    file_path = arguments.get("file_path")
    extraction_prompt = arguments.get("extraction_prompt")
    model = arguments.get("model", "llama-3.3-70b-versatile")
    temperature = arguments.get("temperature", 0.0)
    timeout = arguments.get("timeout", 60)

    if not file_path:
        raise SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            "Missing required parameter: file_path"
        )

    if not extraction_prompt:
        raise SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            "Missing required parameter: extraction_prompt"
        )

    logger.info(f"Extracting structured data from: {file_path}")

    # Escape prompt for SPARQL string literal
    escaped_prompt = extraction_prompt.replace('"', '\\"').replace('\n', '\\n')

    # Build query from template
    query = EXTRACT_STRUCTURED_DATA_TEMPLATE.format(
        file_path=file_path,
        extraction_prompt=escaped_prompt,
        model=model,
        temperature=temperature
    )

    # Execute via core tool
    try:
        result = await sparql_query_tool({
            "query": query,
            "output_format": "json-ld",
            "timeout": timeout
        })

        logger.info("Extraction completed successfully")
        return result

    except SparqllmError as e:
        # Add tool-specific suggestions
        if e.code == ErrorCode.SPARQL_TIMEOUT:
            e.details["suggestion"] = "File too large or LLM slow - try smaller file or increase timeout"
        elif e.code == ErrorCode.INVALID_FUNCTION:
            e.details["suggestion"] = "Ensure SLM-FILE, SLM-READFILE, LLM functions are registered"
        raise
```

### Step 3: rag_search Tool (4-5 hours)
**File:** `SPARQLLM/mcp/tools/rag_search.py`

```python
import logging
from typing import Dict, Any
from mcp.types import TextContent
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.templates import RAG_SEARCH_TEMPLATE
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.tools")

async def rag_search_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Semantic search with LLM synthesis (RAG pattern).

    Workflow: Query → Vector Search (FAISS) → LLM Synthesis

    Args:
        query: Search query
        synthesis_prompt: Instructions for LLM synthesis (default: "Synthesize answer from documents")
        top_k: Number of documents to retrieve (default: 3)
        model: LLM model name (default: llama-3.3-70b-versatile)
        limit: Max results to return (default: 10)
        timeout: Timeout in seconds (default: 90)

    Returns:
        Search results with LLM-synthesized answer
    """

    # Extract arguments
    query = arguments.get("query")
    synthesis_prompt = arguments.get("synthesis_prompt", "Synthesize a comprehensive answer from these documents")
    top_k = arguments.get("top_k", 3)
    model = arguments.get("model", "llama-3.3-70b-versatile")
    limit = arguments.get("limit", 10)
    timeout = arguments.get("timeout", 90)

    if not query:
        raise SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            "Missing required parameter: query"
        )

    logger.info(f"RAG search: {query} (top_k={top_k})")

    # Escape prompts
    escaped_query = query.replace('"', '\\"')
    escaped_synthesis = synthesis_prompt.replace('"', '\\"').replace('\n', '\\n')

    # Build query from template
    sparql_query = RAG_SEARCH_TEMPLATE.format(
        query=escaped_query,
        synthesis_prompt=escaped_synthesis,
        top_k=top_k,
        model=model,
        limit=limit
    )

    # Execute
    try:
        result = await sparql_query_tool({
            "query": sparql_query,
            "output_format": "json-ld",
            "timeout": timeout
        })

        logger.info("RAG search completed")
        return result

    except SparqllmError as e:
        if e.code == ErrorCode.SPARQL_TIMEOUT:
            e.details["suggestion"] = "Reduce top_k or increase timeout"
        elif e.code == ErrorCode.INVALID_FUNCTION:
            e.details["suggestion"] = "Ensure FAISS index built (slm-index-faiss) and MCP-TOOL registered"
        raise
```

### Step 4: web_to_knowledge Tool (4-5 hours)
**File:** `SPARQLLM/mcp/tools/web_to_knowledge.py`

```python
import logging
from typing import Dict, Any
from mcp.types import TextContent
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.templates import WEB_TO_KNOWLEDGE_TEMPLATE
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.tools")

async def web_to_knowledge_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Convert webpage to knowledge graph via LLM extraction.

    Workflow: URL → Scrape → LLM Extraction → RDF Graph

    Args:
        url: Webpage URL
        extraction_prompt: Instructions for entity extraction
        model: LLM model name (default: llama-3.3-70b-versatile)
        text_max_chars: Max characters to extract from page (default: 10000)
        timeout: Timeout in seconds (default: 60)

    Returns:
        Knowledge graph as JSON-LD (CONSTRUCT result)
    """

    # Extract arguments
    url = arguments.get("url")
    extraction_prompt = arguments.get(
        "extraction_prompt",
        "Extract all entities (people, places, organizations, events) with their properties as RDF triples"
    )
    model = arguments.get("model", "llama-3.3-70b-versatile")
    text_max_chars = arguments.get("text_max_chars", 10000)
    timeout = arguments.get("timeout", 60)

    if not url:
        raise SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            "Missing required parameter: url"
        )

    logger.info(f"Converting webpage to knowledge: {url}")

    # Escape prompt
    escaped_prompt = extraction_prompt.replace('"', '\\"').replace('\n', '\\n')

    # Build query
    sparql_query = WEB_TO_KNOWLEDGE_TEMPLATE.format(
        url=url,
        extraction_prompt=escaped_prompt,
        model=model,
        text_max_chars=text_max_chars
    )

    # Execute
    try:
        result = await sparql_query_tool({
            "query": sparql_query,
            "output_format": "json-ld",
            "timeout": timeout
        })

        logger.info("Knowledge extraction completed")
        return result

    except SparqllmError as e:
        if e.code == ErrorCode.SPARQL_TIMEOUT:
            e.details["suggestion"] = "Reduce text_max_chars or increase timeout"
        elif e.code == ErrorCode.INVALID_FUNCTION:
            e.details["suggestion"] = "Ensure SNAP, LLM functions are registered"
        raise
```

### Step 5: query_database Tool (3-4 hours)
**File:** `SPARQLLM/mcp/tools/query_database.py`

```python
import logging
from typing import Dict, Any
from mcp.types import TextContent
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.templates import QUERY_DATABASE_TEMPLATE
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

logger = logging.getLogger("SPARQLLM.mcp.tools")

async def query_database_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Execute SQL query and return results as RDF.

    Workflow: SQL → PostgreSQL → RDF Mapping

    Args:
        sql_query: SQL query string
        limit: Max rows to return (default: 100)
        timeout: Timeout in seconds (default: 30)

    Returns:
        Query results as JSON-LD with schema:Dataset structure
    """

    # Extract arguments
    sql_query = arguments.get("sql_query")
    limit = arguments.get("limit", 100)
    timeout = arguments.get("timeout", 30)

    if not sql_query:
        raise SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            "Missing required parameter: sql_query"
        )

    logger.info(f"Executing database query (limit={limit})")

    # Escape SQL for SPARQL string
    escaped_sql = sql_query.replace('"', '\\"').replace('\n', '\\n')

    # Build query
    sparql_query = QUERY_DATABASE_TEMPLATE.format(
        sql_query=escaped_sql,
        limit=limit
    )

    # Execute
    try:
        result = await sparql_query_tool({
            "query": sparql_query,
            "output_format": "json-ld",
            "timeout": timeout
        })

        logger.info("Database query completed")
        return result

    except SparqllmError as e:
        if e.code == ErrorCode.SPARQL_TIMEOUT:
            e.details["suggestion"] = "Query too slow - add indexes or reduce limit"
        elif e.code == ErrorCode.INVALID_FUNCTION:
            e.details["suggestion"] = "Ensure postgres MCP provider configured"
        raise
```

### Step 6: Update Tool Schemas (2-3 hours)
**File:** `SPARQLLM/mcp/schemas/tool_schemas.py`

Add schemas for all new tools:
```python
TOOL_SCHEMAS = [
    # ... existing sparql_query, echo ...

    Tool(
        name="extract_structured_data",
        description=(
            "Extract structured data from files (HTML, CSV, TXT, PDF) using LLM. "
            "Automatically parses file and extracts entities/properties. "
            "Returns schema.org RDF graph."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file (local path or URL)"
                },
                "extraction_prompt": {
                    "type": "string",
                    "description": "Instructions for LLM extraction (e.g., 'Extract all people and their roles')"
                },
                "model": {
                    "type": "string",
                    "default": "llama-3.3-70b-versatile",
                    "description": "LLM model name"
                },
                "temperature": {
                    "type": "number",
                    "default": 0.0,
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "description": "LLM temperature"
                },
                "timeout": {
                    "type": "number",
                    "default": 60,
                    "description": "Timeout in seconds"
                }
            },
            "required": ["file_path", "extraction_prompt"]
        }
    ),

    Tool(
        name="rag_search",
        description=(
            "Semantic search with LLM synthesis (RAG pattern). "
            "Queries FAISS vector index, retrieves top documents, synthesizes answer with LLM. "
            "Requires FAISS index built via slm-index-faiss."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "synthesis_prompt": {
                    "type": "string",
                    "default": "Synthesize a comprehensive answer from these documents",
                    "description": "Instructions for LLM synthesis"
                },
                "top_k": {
                    "type": "number",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Number of documents to retrieve"
                },
                "model": {
                    "type": "string",
                    "default": "llama-3.3-70b-versatile",
                    "description": "LLM model name"
                },
                "limit": {
                    "type": "number",
                    "default": 10,
                    "description": "Max results to return"
                },
                "timeout": {
                    "type": "number",
                    "default": 90,
                    "description": "Timeout in seconds"
                }
            },
            "required": ["query"]
        }
    ),

    Tool(
        name="web_to_knowledge",
        description=(
            "Convert webpage to knowledge graph via LLM extraction. "
            "Scrapes page, extracts entities (people, places, orgs, events), returns RDF graph."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Webpage URL to extract from"
                },
                "extraction_prompt": {
                    "type": "string",
                    "default": "Extract all entities with their properties as RDF triples",
                    "description": "Instructions for entity extraction"
                },
                "model": {
                    "type": "string",
                    "default": "llama-3.3-70b-versatile",
                    "description": "LLM model name"
                },
                "text_max_chars": {
                    "type": "number",
                    "default": 10000,
                    "description": "Max characters to extract from page"
                },
                "timeout": {
                    "type": "number",
                    "default": 60,
                    "description": "Timeout in seconds"
                }
            },
            "required": ["url"]
        }
    ),

    Tool(
        name="query_database",
        description=(
            "Execute SQL query against PostgreSQL and return results as RDF. "
            "Results mapped to schema:Dataset with schema:Observation rows."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": "SQL query to execute"
                },
                "limit": {
                    "type": "number",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Max rows to return"
                },
                "timeout": {
                    "type": "number",
                    "default": 30,
                    "description": "Timeout in seconds"
                }
            },
            "required": ["sql_query"]
        }
    )
]
```

### Step 7: Register Tools in Server (1 hour)
**File:** `SPARQLLM/mcp/server.py`

```python
from SPARQLLM.mcp.tools.extract_structured_data import extract_structured_data_tool
from SPARQLLM.mcp.tools.rag_search import rag_search_tool
from SPARQLLM.mcp.tools.web_to_knowledge import web_to_knowledge_tool
from SPARQLLM.mcp.tools.query_database import query_database_tool

class SparqllmMCPServer:
    def __init__(self, config_file: str):
        # ... existing code ...
        self.server.call_tool("extract_structured_data")(extract_structured_data_tool)
        self.server.call_tool("rag_search")(rag_search_tool)
        self.server.call_tool("web_to_knowledge")(web_to_knowledge_tool)
        self.server.call_tool("query_database")(query_database_tool)
```

### Step 8: Unit Tests (4-5 hours)
**File:** `tests/test_convenience_tools.py`

```python
import pytest
from SPARQLLM.mcp.tools.extract_structured_data import extract_structured_data_tool
from SPARQLLM.mcp.tools.rag_search import rag_search_tool
from SPARQLLM.config import ConfigSingleton

@pytest.fixture
def setup_config():
    ConfigSingleton(config_file="config.ini")

@pytest.mark.asyncio
async def test_extract_structured_data_csv(setup_config):
    """Test extraction from CSV file."""
    result = await extract_structured_data_tool({
        "file_path": "./data/results.csv",
        "extraction_prompt": "Extract city names"
    })

    import json
    data = json.loads(result[0].text)
    # Should contain extracted entities
    assert "results" in data or "@graph" in data

@pytest.mark.asyncio
@pytest.mark.slow
async def test_rag_search_requires_index(setup_config):
    """Test RAG search (requires FAISS index)."""
    # This test may fail if FAISS index not built
    # Mark as slow/integration test
    result = await rag_search_tool({
        "query": "What is Paris?",
        "top_k": 2
    })

    import json
    data = json.loads(result[0].text)
    # Check for results or error
    assert "results" in data or "error" in data

# Add tests for web_to_knowledge, query_database
```

### Step 9: Example Usage Documentation (2-3 hours)
**File:** `docs/mcp-tools-examples.md`

Create examples for each tool showing typical agent workflows.

## Success Criteria

- [ ] All 4 convenience tools registered in `tools/list`
- [ ] `extract_structured_data` extracts from CSV file
- [ ] `rag_search` executes (with/without FAISS index)
- [ ] `web_to_knowledge` scrapes URL and extracts entities
- [ ] `query_database` executes SQL (requires PostgreSQL MCP provider)
- [ ] Error messages include tool-specific suggestions
- [ ] Templates properly escape user input
- [ ] Tests pass: `pytest tests/test_convenience_tools.py -v`

## Security Considerations

- **Input escaping**: All user prompts/queries escaped for SPARQL literals
- **Template injection**: Use `.format()` with known keys only, no `eval()`
- **SQL injection**: Delegated to PostgreSQL MCP provider (assume sanitized)
- **URL validation**: Consider whitelist for `web_to_knowledge` (optional)

## Performance Notes

- **extract_structured_data**: 5-15s (file I/O + LLM latency)
- **rag_search**: 3-10s (FAISS fast, LLM synthesis slow)
- **web_to_knowledge**: 10-30s (scraping + LLM extraction)
- **query_database**: 0.5-5s (depends on SQL complexity)

## Known Limitations

- **No streaming**: LLM responses fully materialized
- **Fixed templates**: No runtime template customization
- **Single LLM provider**: Hardcoded to Groq/Ollama (configurable via model param)
- **No caching**: Each request regenerates results

## Next Steps

After Phase 3 completion:
- Phase 4: Add resource providers for graph inspection
- Gather usage metrics to identify missing tools
- Consider streaming support for long LLM responses

## References

- Query patterns: `scout/scout-03-query-patterns.md`
- Schema.org vocabulary: https://schema.org/
- Existing queries: `queries/LLM/*.sparql`, `queries/faiss/*.sparql`
