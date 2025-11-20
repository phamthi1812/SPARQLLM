# Quick Start Guide - SPARQLLM MCP Server Implementation

**For Developers:** Read this first, then dive into phase plans

## TL;DR

Transform SPARQLLM into MCP server: expose SPARQL + GGFs as tools. 5 phases, 3-4 weeks, research-backed.

## What We're Building

```
AI Agent → MCP Server → SPARQLLM Core
              ↓
    Tools: sparql.query, extract_structured_data, rag_search, web_to_knowledge
```

## Before You Start

### Read These First (30 min)
1. `SUMMARY.md` - Overview + timeline
2. `plan.md` - Architecture decisions
3. `phase-01-infrastructure.md` - Your starting point

### Verify Prerequisites
```bash
# Check Python version
python --version  # Should be >= 3.10

# Check existing CLI works
slm-run --config config.ini -q "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"

# Run existing tests
pytest tests/ -v
```

## Phase-by-Phase Checklist

### Phase 1: Infrastructure (Days 1-2)
**Goal:** MCP server starts, responds to basic requests

**Key files to create:**
- `SPARQLLM/mcp/server.py` - Core MCP server
- `SPARQLLM/cli/slm_mcp_server.py` - CLI entry point
- `SPARQLLM/cli/shared.py` - Extract logic from slm.py

**Critical steps:**
1. Install MCP SDK: `pip install mcp`
2. Extract `execute_query()` from `slm.py`
3. Implement echo tool for testing
4. Test with MCP inspector

**Success criteria:**
```bash
slm-mcp-server --config config.ini  # Starts without errors
# In another terminal:
mcp-inspector slm-mcp-server --config config.ini  # Shows "connected"
```

**Read:** `phase-01-infrastructure.md`

### Phase 2: Core Query Tool (Days 3-5)
**Goal:** Execute SPARQL queries via MCP

**Key files to create:**
- `SPARQLLM/mcp/validation.py` - Query validation
- `SPARQLLM/mcp/formatting.py` - Result formatting
- `SPARQLLM/mcp/tools/sparql_query.py` - Main tool

**Critical steps:**
1. Implement 3-layer validation (syntax, whitelist, timeout)
2. Support JSON-LD, CSV, Turtle output formats
3. Store isolation (reset_store() before/after)
4. Error handling with agent-focused messages

**Success criteria:**
```python
# Via MCP:
{
  "name": "sparql_query",
  "arguments": {
    "query": "SELECT ?city WHERE { ... ggf:SLM-CSV(...) ... }"
  }
}
# Returns: JSON-LD result
```

**Read:** `phase-02-sparql-query.md`

### Phase 3: Convenience Tools (Days 6-10)
**Goal:** High-level workflow wrappers

**Key files to create:**
- `SPARQLLM/mcp/templates.py` - SPARQL templates
- `SPARQLLM/mcp/tools/extract_structured_data.py`
- `SPARQLLM/mcp/tools/rag_search.py`
- `SPARQLLM/mcp/tools/web_to_knowledge.py`
- `SPARQLLM/mcp/tools/query_database.py`

**Pattern for each tool:**
1. Define SPARQL template
2. Build query from user arguments
3. Call `sparql_query_tool()` internally
4. Add tool-specific error suggestions

**Success criteria:**
```python
# Agent: "Extract cities from data.csv"
{
  "name": "extract_structured_data",
  "arguments": {
    "file_path": "./data.csv",
    "extraction_prompt": "Extract city names"
  }
}
# Returns: schema.org RDF graph
```

**Read:** `phase-03-convenience-tools.md`

### Phase 4: Resources (Days 11-12)
**Goal:** Graph inspection for debugging

**Key files to create:**
- `SPARQLLM/mcp/resources/store_resource.py`

**Critical steps:**
1. Track session_id in server
2. List named graphs as resources
3. Serialize graphs to JSON-LD on read
4. Clear graphs on connection close

**Success criteria:**
```python
# After query execution:
resources/list → [store://sess-123/graphs/urn%3Auuid%3A456, ...]
resources/read → JSON-LD content
```

**Read:** `phase-04-resources.md`

### Phase 5: Testing + Docs (Days 13-14)
**Goal:** Production readiness

**Key files to create:**
- `tests/test_*.py` - Unit + integration tests
- `docs/TOOL_REFERENCE.md`
- `docs/WORKFLOWS.md`
- `examples/notebooks/*.ipynb`

**Critical steps:**
1. >90% test coverage for core modules
2. Integration tests via MCP protocol
3. 5 agent workflow simulations
4. Complete documentation

**Success criteria:**
```bash
pytest tests/ -v --cov=SPARQLLM/mcp
# Coverage: >90%

# All docs readable, examples runnable
```

**Read:** `phase-05-testing-docs.md`

## Common Pitfalls

### 1. Store Contamination
**Problem:** Graphs persist across requests
**Solution:** Call `reset_store()` before AND after each tool execution

### 2. SPARQL Injection
**Problem:** User input in query string
**Solution:** Use templates with `.format()`, escape literals, validate functions

### 3. Timeout Not Enforced
**Problem:** Long queries hang
**Solution:** `asyncio.wait_for()` with configurable timeout

### 4. Breaking Existing CLI
**Problem:** Refactoring breaks `slm-run`
**Solution:** Extract shared logic, don't modify existing flow, run regression tests

### 5. Error Messages for Machines
**Problem:** Errors optimized for humans, not agents
**Solution:** Include error code, suggestion for next action, relevant context

## Development Workflow

```bash
# 1. Create feature branch
git checkout -b mcp-server-phase-1

# 2. Implement + test
# ... code ...
pytest tests/test_mcp_server_basic.py -v

# 3. Test integration
slm-mcp-server --config config.ini --debug

# 4. Test existing CLI still works
slm-run -f queries/filesystem/simple-csv.sparql

# 5. Commit + PR
git add .
git commit -m "Phase 1: MCP server infrastructure"
```

## Testing Strategy

### During Development
```bash
# Unit tests (fast)
pytest tests/test_validation.py -v

# Integration tests (moderate)
pytest tests/test_mcp_integration.py -v

# Specific test
pytest tests/test_sparql_query_tool.py::test_csv_file_query -v
```

### Before PR
```bash
# Full test suite
pytest tests/ -v --cov=SPARQLLM/mcp

# Regression tests
pytest tests/test_queries.py -v  # Existing CLI tests
```

## Debugging Tips

### MCP Server Not Starting
```bash
# Check logs
slm-mcp-server --config config.ini --debug

# Common issue: Config file not found
slm-mcp-server --config /absolute/path/to/config.ini
```

### Tool Call Fails
```bash
# Check tool is registered
# In server logs: "Registering {func_name} with URI..."

# Check function in config.ini
grep "SLM-CSV" config.ini
```

### Timeout Issues
```python
# Increase timeout for testing
{
  "query": "...",
  "timeout": 120  # 2 minutes instead of 30s
}
```

### Store Not Resetting
```python
# Add logging
from SPARQLLM.udf.SPARQLLM import store
logger.info(f"Store size before: {len(store)}")
reset_store()
logger.info(f"Store size after: {len(store)}")  # Should be 0
```

## Key Resources

### Research Reports
- `research/researcher-01-mcp-protocol.md` - MCP spec, best practices
- `research/researcher-02-sparql-apis.md` - Security, performance

### Codebase Analysis
- `scout/scout-01-mcp-and-udf.md` - MCP client, UDF system
- `scout/scout-02-cli-execution.md` - CLI flow, config management
- `scout/scout-03-query-patterns.md` - Query patterns, GGF usage

### External Docs
- MCP Spec: https://modelcontextprotocol.io/specification/
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- RDFlib: https://rdflib.readthedocs.io/

## Getting Help

1. **Architecture questions:** Review `plan.md` → Design Decisions
2. **Implementation questions:** Read relevant phase plan
3. **Codebase questions:** Check scout reports
4. **Protocol questions:** Read research reports
5. **Stuck?** Review success criteria in phase plan, ensure prerequisites met

## Quick Reference

### MCP Tool Schema
```python
Tool(
    name="tool_name",  # snake_case
    description="What it does and when to use it",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {
                "type": "string",
                "description": "What this param does"
            }
        },
        "required": ["param"]
    }
)
```

### Tool Implementation
```python
async def my_tool(arguments: dict) -> list[TextContent]:
    # 1. Extract arguments
    param = arguments.get("param")

    # 2. Validate
    if not param:
        raise SparqllmError(ErrorCode.INVALID_INPUT, "Missing param")

    # 3. Execute
    result = do_work(param)

    # 4. Return
    return [TextContent(type="text", text=json.dumps(result))]
```

### Error Handling
```python
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

raise SparqllmError(
    ErrorCode.SPARQL_TIMEOUT,
    "Query exceeded timeout",
    {"suggestion": "Increase timeout parameter"}
)
```

## Timeline Estimate

- **Phase 1:** 2 days
- **Phase 2:** 3 days
- **Phase 3:** 5 days
- **Phase 4:** 2 days
- **Phase 5:** 3 days
- **Buffer:** 5 days

**Total:** 20 days (4 weeks)

## Ready to Start?

1. Read `phase-01-infrastructure.md` in detail
2. Set up development environment
3. Create feature branch
4. Start with Step 1: Project Structure Setup
5. Test incrementally after each step

**Good luck!**
