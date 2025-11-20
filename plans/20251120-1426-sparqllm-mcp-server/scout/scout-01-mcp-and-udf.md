# Scout Report: MCP Client Implementation & UDF System

**Status:** Complete
**Scope:** SPARQLLM/udf/mcp/ + core UDF architecture
**Duration:** ~2 minutes

## Core Architecture Files

### 1. `/SPARQLLM/udf/SPARQLLM.py` (62 lines)
- Global `store = Dataset()` - single RDFlib Dataset for entire session
- Custom SPARQL evaluator: `customEval()` + `my_evaljoin()` ensures lazy Join evaluation
- `reset_store()` to clear graphs between independent query sessions
- **Critical:** One store per session to avoid cross-contamination

### 2. `/SPARQLLM/udf/mcp/client.py` (90 lines)
- `MCPClient` class: unified interface for HTTP, STDIO, and static handle transport
- `MCPHandle` dataclass: stores connection metadata (kind, target, token, proc, registry)
- `tools_call(handle, tool_name, arguments)` - dispatches to correct transport:
  - **Static**: Direct Python function call from registry
  - **STDIO**: JSON-RPC over subprocess pipes with threading
  - **HTTP**: JSON-RPC POST with Authorization header

### 3. `/SPARQLLM/udf/mcp/slm_mcp_tool.py` (409 lines)
**Main UDF function:** `slm_mcp_tool(handle, tool_name, args_json, graph_name_hint)`

**Returns:** `URIRef` of named graph (or `None` on error)

**Workflow:**
1. Call MCP tool via client
2. Detect output format: native JSON-LD vs JSON vs error
3. Convert to JSON-LD (heuristic or mapper-based)
4. Parse JSON-LD → RDF triples
5. Create named graph in global `store`
6. Attach PROV-O provenance (start/end times, duration, agent, tool, args)
7. Return graph URI

**Pre-registered static tools:**
- GitHub: `github.pullRequests.list`, `github.issues.list`
- PostgreSQL: `postgres.tables.list`, `postgres.table.preview`, `postgres.sql.query`
- DuckDuckGo: `duckduckgo.search`
- Browser: `browser.snapshot`
- FAISS: `faiss.index_file`, `faiss.search_index`
- Groq LLM: `groq.generate_jsonld`
- Echo (STDIO test): `echo.ping`

### 4. `/SPARQLLM/udf/mcp/alias.py` (143 lines)
High-level SPARQL function aliases wrapping `slm_mcp_tool`:
- `_alias_llm(prompt, model, temperature)` → `ggf:LLM(?prompt [, ?model [, ?temp]])`
- `_alias_snapshot(url, text_max)` → `ggf:SNAP(?url [, ?text_max])`
- `_alias_ddg_search(query, limit, region, safesearch)` → `ggf:SEARCH(?query [, ?limit])`

### 5. `/SPARQLLM/servers/echo_mcp_server.py` (34 lines)
**Toy MCP server example** (STDIO transport)
- Single tool: `echo.ping`
- Demonstrates server-side MCP protocol for testing

## MCP Provider Files

### 6-11. Provider Implementations
- `/SPARQLLM/udf/mcp/providers/github_provider.py` - REST API wrapper for GitHub
- `/SPARQLLM/udf/mcp/providers/postgres_provider.py` - PostgreSQL connection wrapper
- `/SPARQLLM/udf/mcp/providers/duckduckgo_provider.py` - Web search
- `/SPARQLLM/udf/mcp/providers/browser_provider.py` - Browser automation
- `/SPARQLLM/udf/mcp/providers/faiss_provider.py` - Vector similarity search

## Reference UDF Implementations

### 12. `/SPARQLLM/udf/mycsv.py`
Pattern: CSV file → RDF named graph
- Reads CSV, creates RDF triples per row, adds to global `store`
- Returns `URIRef` (named graph IRI)

### 13. `/SPARQLLM/udf/readfile.py`
Pattern: HTML/text file → RDF named graph
- `readhtmlfile(path_uri, max_size)` parses HTML → markdown/text
- Returns `URIRef`

## Configuration Files

### 14. `/config.ini`
**[Associations]:** UDF registration mapping
```ini
LLM = SPARQLLM.udf.mcp.alias._alias_llm
SEARCH = SPARQLLM.udf.mcp.alias._alias_ddg_search
SLM-MCP-TOOL = SPARQLLM.udf.mcp.slm_mcp_tool.slm_mcp_tool
SLM-CSV = SPARQLLM.udf.mycsv.slm_csv
```

**[Requests]:** Runtime parameters
```ini
SLM-GROQ-MODEL = llama-3.3-70b-versatile
SLM-MCP-TRANSPORT = http
SLM-MCP-TARGET = https://mcp.github.com
```

## Data Flow

```
SPARQL Query
    ↓
BIND(ggf:LLM(?prompt) AS ?g)
    ↓
alias._alias_llm() executes
    ↓
slm_mcp_tool("groq", "groq.generate_jsonld", {"prompt": ...})
    ↓
_MCP.tools_call() dispatches to transport
    ↓
Tool returns JSON-LD
    ↓
Parse JSON-LD → named graph in store
    ↓
Attach PROV-O metadata
    ↓
Return graph_uri (URIRef)
    ↓
GRAPH ?g { ?s ?p ?o } queries the named graph
```

## Critical Insights

1. **Single Global Store**: Shared across entire query session - must call `reset_store()` between queries
2. **Three Transport Modes**: Static (embedded), STDIO (subprocess), HTTP (remote)
3. **All UDFs Return Named Graph URIs**: Not strings or JSON—always `URIRef` added to store
4. **Provenance Tracking**: Every MCP tool call annotated with timing, agent, tool, args
5. **Lazy Evaluation**: Custom `evalLazyJoin` ensures graphs materialize before GRAPH clauses
