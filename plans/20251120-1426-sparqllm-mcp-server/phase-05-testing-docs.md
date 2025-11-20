# Phase 5: Testing, Documentation, Examples

**Duration:** 3-4 days
**Status:** Ready for implementation
**Dependencies:** Phases 1-4 complete

## Overview

Comprehensive testing, documentation, and example workflows for production readiness. Focus: unit tests, integration tests, agent simulation, usage docs, troubleshooting guide. Outcome: Production-ready MCP server with >90% test coverage.

## Context & Key Insights

**From research:**
- MCP servers require robust error handling for LLM reliability
- Documentation critical for agent discoverability
- Examples should show end-to-end workflows, not just individual tools
- Testing must cover error paths, not just happy paths

**From codebase analysis:**
- Existing tests in `tests/` cover core UDFs
- No MCP-specific tests yet
- CLI has manual testing via example queries
- Need agent simulation for realistic testing

## Architecture Decisions

### 1. Test Strategy
**Decision:** Three test levels
1. **Unit tests**: Individual tools, validation, formatting (fast, no external deps)
2. **Integration tests**: STDIO protocol, full MCP lifecycle (moderate speed)
3. **Agent simulation**: Real-world workflows via scripted agent (slow, optional CI)

**Coverage target:** >90% for core tools, >70% for convenience tools

**Rationale:** Layered testing catches bugs at appropriate levels

### 2. Documentation Structure
**Decision:** Four documentation types
1. **README.md**: Quick start, installation, basic usage
2. **TOOL_REFERENCE.md**: All tools with schemas, examples
3. **WORKFLOWS.md**: End-to-end agent patterns
4. **TROUBLESHOOTING.md**: Common errors, solutions

**Rationale:** Supports different user personas (quick start vs deep dive)

### 3. Example Workflows
**Decision:** 5 representative workflows
1. CSV data extraction
2. RAG search (with FAISS)
3. Web research pipeline
4. Database query analysis
5. Recursive graph exploration

**Format:** Jupyter notebooks + Python scripts

**Rationale:** Covers 80% of use cases, runnable examples

### 4. CI/CD Integration
**Decision:** GitHub Actions workflow
- Run unit tests on every push
- Run integration tests on PR
- Skip agent simulation (requires API keys)
- Publish docs to GitHub Pages

**Rationale:** Automated testing, living documentation

## Implementation Steps

### Step 1: Unit Test Suite Completion (6-8 hours)
**Files:** `tests/test_*.py`

Ensure coverage for:
- `test_validation.py`: Query validation, function whitelist
- `test_formatting.py`: All output formats (JSON-LD, CSV, Turtle)
- `test_errors.py`: All error codes, error messages
- `test_sparql_query_tool.py`: Core tool execution paths
- `test_convenience_tools.py`: All 4 convenience tools
- `test_resources.py`: Resource listing, reading

**Example test structure:**
```python
# tests/test_validation.py
import pytest
from SPARQLLM.mcp.validation import (
    validate_sparql_syntax,
    validate_function_whitelist,
    extract_ggf_functions
)
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode
from SPARQLLM.config import ConfigSingleton

@pytest.fixture
def setup_config():
    ConfigSingleton(config_file="config.ini")

def test_extract_ggf_functions():
    """Test GGF function extraction from query."""
    query = """
    PREFIX ggf: <http://example.org/>
    SELECT ?s WHERE {
        BIND(ggf:SLM-CSV(?file) AS ?g)
        BIND(ggf:SLM-LLM(?prompt) AS ?g2)
    }
    """
    functions = extract_ggf_functions(query)
    assert functions == {"SLM-CSV", "SLM-LLM"}

def test_validate_syntax_valid():
    """Test valid SPARQL passes."""
    query = "SELECT ?s WHERE { ?s ?p ?o }"
    validate_sparql_syntax(query)  # Should not raise

def test_validate_syntax_invalid():
    """Test invalid SPARQL raises error."""
    query = "INVALID SPARQL"
    with pytest.raises(SparqllmError) as exc_info:
        validate_sparql_syntax(query)
    assert exc_info.value.code == ErrorCode.SPARQL_SYNTAX_ERROR

def test_validate_function_whitelist_allowed(setup_config):
    """Test registered functions pass."""
    query = "SELECT ?s WHERE { BIND(ggf:SLM-CSV(?f) AS ?g) }"
    validate_function_whitelist(query, ConfigSingleton())

def test_validate_function_whitelist_unknown(setup_config):
    """Test unknown functions rejected."""
    query = "SELECT ?s WHERE { BIND(ggf:UNKNOWN-FUNC(?x) AS ?g) }"
    with pytest.raises(SparqllmError) as exc_info:
        validate_function_whitelist(query, ConfigSingleton())
    assert exc_info.value.code == ErrorCode.INVALID_FUNCTION
    assert "UNKNOWN-FUNC" in exc_info.value.details["unknown"]
```

**Run tests:**
```bash
pytest tests/ -v --cov=SPARQLLM/mcp --cov-report=html
```

### Step 2: Integration Test Suite (4-6 hours)
**File:** `tests/test_mcp_integration.py`

Test full MCP protocol lifecycle:
```python
import pytest
import subprocess
import json
import time

class MCPClient:
    """Simple MCP client for testing."""

    def __init__(self, server_cmd: list[str]):
        self.proc = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.request_id = 0

    def send_request(self, method: str, params: dict) -> dict:
        """Send JSON-RPC request, return response."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }

        # Send with newline
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()

        # Read response
        response_line = self.proc.stdout.readline()
        return json.loads(response_line)

    def close(self):
        """Terminate server."""
        self.proc.terminate()
        self.proc.wait(timeout=5)

@pytest.fixture
def mcp_client():
    """Start MCP server for testing."""
    client = MCPClient(["slm-mcp-server", "--config", "config.ini"])
    yield client
    client.close()

@pytest.mark.integration
def test_mcp_initialization(mcp_client):
    """Test server initialization."""
    response = mcp_client.send_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    })

    assert "result" in response
    assert "capabilities" in response["result"]
    assert "serverInfo" in response["result"]
    assert response["result"]["serverInfo"]["name"] == "sparqllm"

@pytest.mark.integration
def test_mcp_tools_list(mcp_client):
    """Test tools/list returns all registered tools."""
    # Initialize first
    mcp_client.send_request("initialize", {})

    # List tools
    response = mcp_client.send_request("tools/list", {})

    assert "result" in response
    tools = response["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    # Check all tools present
    assert "sparql_query" in tool_names
    assert "extract_structured_data" in tool_names
    assert "rag_search" in tool_names
    assert "web_to_knowledge" in tool_names
    assert "query_database" in tool_names

@pytest.mark.integration
def test_mcp_sparql_query_execution(mcp_client):
    """Test sparql_query tool execution."""
    mcp_client.send_request("initialize", {})

    # Execute simple query
    response = mcp_client.send_request("tools/call", {
        "name": "sparql_query",
        "arguments": {
            "query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1",
            "output_format": "json-ld"
        }
    })

    assert "result" in response
    result = response["result"]
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"

    # Parse JSON result
    content = json.loads(result["content"][0]["text"])
    assert content["type"] == "SELECT"

@pytest.mark.integration
def test_mcp_extract_structured_data(mcp_client):
    """Test extract_structured_data tool."""
    mcp_client.send_request("initialize", {})

    response = mcp_client.send_request("tools/call", {
        "name": "extract_structured_data",
        "arguments": {
            "file_path": "./data/results.csv",
            "extraction_prompt": "Extract city names",
            "timeout": 30
        }
    })

    assert "result" in response
    # Should contain extracted data or error (acceptable)
    content = response["result"]["content"][0]["text"]
    data = json.loads(content)
    assert "results" in data or "error" in data

@pytest.mark.integration
def test_mcp_resources_list(mcp_client):
    """Test resource listing after query execution."""
    mcp_client.send_request("initialize", {})

    # Execute query that generates graphs
    mcp_client.send_request("tools/call", {
        "name": "sparql_query",
        "arguments": {
            "query": """
            PREFIX ggf: <http://example.org/>
            SELECT ?s WHERE {
                BIND(ggf:SLM-GRAPH("ex:a ex:p ex:b .") AS ?g)
                GRAPH ?g { ?s ?p ?o }
            }
            """,
            "preserve_graphs": True
        }
    })

    # List resources
    response = mcp_client.send_request("resources/list", {})

    assert "result" in response
    resources = response["result"]["resources"]
    assert len(resources) > 0
    assert all(r["mimeType"] == "application/ld+json" for r in resources)
```

### Step 3: Agent Simulation Tests (4-5 hours)
**File:** `tests/test_agent_workflows.py`

Simulate realistic agent interactions:
```python
import pytest
from tests.test_mcp_integration import MCPClient

@pytest.mark.slow
@pytest.mark.integration
def test_csv_extraction_workflow():
    """Simulate agent extracting data from CSV."""
    client = MCPClient(["slm-mcp-server", "--config", "config.ini"])

    # Initialize
    client.send_request("initialize", {})

    # Agent: "Extract cities from results.csv"
    response = client.send_request("tools/call", {
        "name": "extract_structured_data",
        "arguments": {
            "file_path": "./data/results.csv",
            "extraction_prompt": "Extract all city names and return as list"
        }
    })

    # Verify structured response
    content = json.loads(response["result"]["content"][0]["text"])
    assert "results" in content or "@graph" in content

    client.close()

@pytest.mark.slow
@pytest.mark.integration
def test_web_research_workflow():
    """Simulate agent researching topic from web."""
    client = MCPClient(["slm-mcp-server", "--config", "config.ini"])
    client.send_request("initialize", {})

    # Agent: "Research Python MCP from documentation"
    # Step 1: Web scraping
    response = client.send_request("tools/call", {
        "name": "web_to_knowledge",
        "arguments": {
            "url": "https://modelcontextprotocol.io/",
            "extraction_prompt": "Extract key concepts about Model Context Protocol",
            "timeout": 30
        }
    })

    # Should return knowledge graph or timeout error
    content = json.loads(response["result"]["content"][0]["text"])
    # Accept either success or timeout
    assert "@graph" in content or "error" in content

    client.close()

# Add more workflows: RAG search, database query, recursive expansion
```

### Step 4: Documentation - README (2-3 hours)
**File:** `README.md` (update)

Add MCP server section:
```markdown
# SPARQLLM MCP Server

## Quick Start

### Installation
```bash
pip install -e .
```

### Start Server
```bash
slm-mcp-server --config config.ini
```

### Configure in Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "sparqllm": {
      "command": "slm-mcp-server",
      "args": ["--config", "/path/to/config.ini"]
    }
  }
}
```

### Available Tools
- `sparql_query`: Execute SPARQL with GGFs
- `extract_structured_data`: File → Parser → LLM → RDF
- `rag_search`: Semantic search + LLM synthesis
- `web_to_knowledge`: URL → Scrape → Knowledge graph
- `query_database`: SQL → RDF mapping

See [TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md) for details.

## Examples

### Extract Data from CSV
```python
# Agent request: "Extract cities from results.csv"
# MCP tool call:
{
  "name": "extract_structured_data",
  "arguments": {
    "file_path": "./data/results.csv",
    "extraction_prompt": "Extract city names"
  }
}
```

### RAG Search
```python
# Agent request: "Search for information about Paris"
# MCP tool call:
{
  "name": "rag_search",
  "arguments": {
    "query": "What is Paris?",
    "top_k": 3
  }
}
```

See [WORKFLOWS.md](docs/WORKFLOWS.md) for complete examples.
```

### Step 5: Documentation - Tool Reference (3-4 hours)
**File:** `docs/TOOL_REFERENCE.md`

Document all tools with:
- Description
- Input schema
- Output format
- Example usage
- Common errors

### Step 6: Documentation - Workflows (3-4 hours)
**File:** `docs/WORKFLOWS.md`

Document 5 workflows:
1. **CSV Data Extraction**: File → Parse → LLM → Structured data
2. **RAG Search**: Query → FAISS → LLM synthesis
3. **Web Research**: URLs → Scrape → Entity extraction
4. **Database Analysis**: SQL → Results → RDF → LLM insights
5. **Recursive Exploration**: Seed → Pattern → Iterate → Graph

Each workflow includes:
- Use case description
- Step-by-step MCP tool calls
- Expected output
- Error handling

### Step 7: Documentation - Troubleshooting (2-3 hours)
**File:** `docs/TROUBLESHOOTING.md`

Common issues:
- "Function not registered" → Check config.ini
- "Timeout exceeded" → Increase timeout parameter
- "FAISS index not found" → Run `slm-index-faiss`
- "PostgreSQL connection failed" → Configure MCP provider
- "Store overflow" → Reduce query complexity

### Step 8: Example Notebooks (4-5 hours)
**Directory:** `examples/notebooks/`

Create Jupyter notebooks:
1. `01-csv-extraction.ipynb`
2. `02-rag-search.ipynb`
3. `03-web-research.ipynb`
4. `04-database-query.ipynb`
5. `05-recursive-graphs.ipynb`

Each notebook:
- Runnable code cells
- Explanatory markdown
- Expected outputs
- Troubleshooting tips

### Step 9: CI/CD Pipeline (3-4 hours)
**File:** `.github/workflows/mcp-tests.yml`

```yaml
name: MCP Server Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: |
          pytest tests/test_validation.py -v
          pytest tests/test_formatting.py -v
          pytest tests/test_errors.py -v

      - name: Run integration tests
        run: |
          pytest tests/test_mcp_integration.py -v -m "not slow"

      - name: Generate coverage report
        run: |
          pytest tests/ --cov=SPARQLLM/mcp --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build docs
        run: |
          # Future: Sphinx/MkDocs build

      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main'
        # Future: deploy step
```

### Step 10: Performance Benchmarking (2-3 hours)
**File:** `tests/test_performance.py`

```python
import pytest
import time
from tests.test_mcp_integration import MCPClient

@pytest.mark.performance
def test_sparql_query_latency():
    """Measure baseline query latency."""
    client = MCPClient(["slm-mcp-server", "--config", "config.ini"])
    client.send_request("initialize", {})

    start = time.time()
    response = client.send_request("tools/call", {
        "name": "sparql_query",
        "arguments": {
            "query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
        }
    })
    elapsed = time.time() - start

    assert "result" in response
    assert elapsed < 1.0  # Should complete in <1s

    client.close()

@pytest.mark.performance
def test_csv_extraction_latency():
    """Measure CSV extraction latency."""
    client = MCPClient(["slm-mcp-server", "--config", "config.ini"])
    client.send_request("initialize", {})

    start = time.time()
    response = client.send_request("tools/call", {
        "name": "extract_structured_data",
        "arguments": {
            "file_path": "./data/results.csv",
            "extraction_prompt": "Extract cities",
            "timeout": 30
        }
    })
    elapsed = time.time() - start

    # CSV parsing + LLM should be <30s
    assert elapsed < 30.0

    client.close()
```

## Success Criteria

- [ ] Unit tests: >90% coverage for core modules
- [ ] Integration tests: All tools tested via MCP protocol
- [ ] Agent simulation: 5 workflows pass
- [ ] Documentation: README, TOOL_REFERENCE, WORKFLOWS, TROUBLESHOOTING complete
- [ ] Examples: 5 runnable notebooks
- [ ] CI/CD: GitHub Actions running tests on push
- [ ] Performance: Baseline benchmarks recorded
- [ ] All tests pass: `pytest tests/ -v`

## Testing Strategy

### Unit Tests (Fast)
- Run on every commit
- No external dependencies
- Mock MCP client if needed

### Integration Tests (Moderate)
- Run on PR
- Start real MCP server
- Test STDIO protocol

### Agent Simulation (Slow)
- Run nightly or manually
- May require API keys
- Optional in CI

### Performance Tests (Optional)
- Run on release branches
- Establish baseline metrics
- Detect regressions

## Documentation Quality Checklist

- [ ] All tools documented with examples
- [ ] Error codes documented with solutions
- [ ] Installation instructions tested on clean machine
- [ ] Screenshots/diagrams for complex workflows
- [ ] API reference auto-generated (future: Sphinx)
- [ ] Changelog maintained

## Known Gaps (Post-MVP)

1. **Streaming support**: LLM responses not streamed
2. **Caching**: No query result caching
3. **Metrics**: No instrumentation for monitoring
4. **Load testing**: No concurrent request testing
5. **Security audit**: Penetration testing not performed

## Next Steps

After Phase 5 completion:
- Release v1.0.0
- Publish to PyPI
- Submit to MCP server directory
- Gather user feedback
- Plan Phase 6 (enhancements based on usage)

## References

- Pytest docs: https://docs.pytest.org/
- MCP testing examples: https://github.com/modelcontextprotocol/servers
- Coverage.py: https://coverage.readthedocs.io/
- GitHub Actions: https://docs.github.com/en/actions
