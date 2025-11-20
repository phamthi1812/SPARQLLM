# SPARQLLM MCP Server Implementation - Summary

**Created:** 2025-11-20
**Total Duration:** 14-21 days
**Status:** Ready for implementation

## Executive Summary

Transform SPARQLLM from MCP client to dual-mode system - consuming MCP tools while exposing neuro-symbolic RAG capabilities as MCP server. Core value: Enable AI agents to leverage SPARQL + Graph Generating Functions for workflow-oriented data processing.

## Strategic Insight

SPARQLLM's strength is **workflow composition** (File→Parse→LLM→RDF), not just query execution. MCP tools should reflect this:
- Low-level `sparql.query` for power users
- High-level wrappers (`extract_structured_data`, `rag_search`) for common patterns
- Resource providers for multi-turn debugging

## Plan Structure

### Main Plan
**File:** `plan.md` (11KB)
- Architecture overview
- Design decisions & rationale
- File structure
- Dependencies
- Risk assessment
- Open questions

### Phase Plans (86KB total)

#### Phase 1: Core MCP Server Infrastructure (3-5 days)
**File:** `phase-01-infrastructure.md` (11KB)
- STDIO transport with JSON-RPC 2.0
- Tool registration framework
- Error handling
- Session management
- **Deliverable:** `slm-mcp-server` CLI responding to basic requests

#### Phase 2: Core sparql.query Tool (2-3 days)
**File:** `phase-02-sparql-query.md` (20KB)
- Query validation (syntax, whitelist, timeout)
- Store isolation per request
- Result formatting (JSON-LD, CSV, Turtle)
- **Deliverable:** Functional low-level SPARQL execution

#### Phase 3: High-Level Convenience Tools (4-6 days)
**File:** `phase-03-convenience-tools.md` (24KB)
- `extract_structured_data`: File → Parser → LLM → RDF
- `rag_search`: Query → FAISS → LLM synthesis
- `web_to_knowledge`: URL → Scrape → Entities
- `query_database`: SQL → RDF mapping
- **Deliverable:** Production-ready workflow wrappers

#### Phase 4: Resource Providers (2-3 days)
**File:** `phase-04-resources.md` (13KB)
- `store://{session_id}/graphs` resource
- Named graph inspection
- JSON-LD serialization
- **Deliverable:** Agents can inspect intermediate graphs

#### Phase 5: Testing, Documentation, Examples (3-4 days)
**File:** `phase-05-testing-docs.md` (18KB)
- Unit tests (>90% coverage)
- Integration tests (MCP protocol)
- Agent simulation (5 workflows)
- Docs: README, TOOL_REFERENCE, WORKFLOWS, TROUBLESHOOTING
- **Deliverable:** Production-ready server

## Key Design Decisions

### 1. Hybrid Tool Architecture
**Rationale:** Balance flexibility (low-level SPARQL) with usability (high-level wrappers)

### 2. Stateless Per-Request Isolation
**Implementation:** Call `reset_store()` before/after each tool execution
**Rationale:** Prevents cross-contamination, simplifies deployment

### 3. JSON-LD Default Format
**Rationale:** Native JSON compatibility, LLM-friendly, schema.org interoperability

### 4. Layered Security Validation
1. JSON Schema (MCP protocol)
2. SPARQL syntax validation
3. Function whitelist (registered UDFs only)
4. Timeout enforcement (30s default)

**Rationale:** "Parameterized queries not foolproof" per Apache Jena docs

### 5. Reuse CLI Logic
**Strategy:** Extract `execute_query()` from `slm_cmd()`, share between CLI and MCP server
**Rationale:** DRY principle, feature parity, reduced bugs

## Critical Success Factors

### Phase 1
- MCP server starts and responds to `initialize`
- Echo tool works (basic connectivity test)
- Existing CLI unchanged

### Phase 2
- `sparql_query` executes filesystem query (no LLM)
- Timeout enforced
- Unknown functions rejected

### Phase 3
- `extract_structured_data` chains File→Parse→LLM→RDF
- `rag_search` works with/without FAISS index
- Error messages include tool-specific suggestions

### Phase 4
- `resources/list` returns generated graphs
- `resources/read` serializes to JSON-LD
- Session isolation verified

### Phase 5
- >90% test coverage for core modules
- 5 agent workflows pass
- Documentation complete and accurate

## Implementation Timeline

```
Week 1: Phase 1 + Phase 2
  Days 1-2: Infrastructure (STDIO, tool registration)
  Days 3-5: sparql.query tool (validation, formatting)

Week 2: Phase 3 + Phase 4
  Days 6-8: Convenience tools (extract, rag, web, db)
  Days 9-10: Resources (listing, reading)

Week 3: Phase 5
  Days 11-13: Testing (unit, integration, simulation)
  Days 14: Documentation + examples
```

**Buffer:** 3-7 days for debugging, polish, feedback

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Query injection | Layered validation, whitelist, timeout |
| Store memory leaks | Aggressive cleanup, size monitoring |
| Breaking existing CLI | Extract shared logic, regression tests |
| Complex tool schemas | Start simple, iterate on feedback |

## Dependencies

**New packages:**
- `mcp` - Official Python SDK for STDIO server

**Existing (no changes):**
- rdflib >= 6.0
- click >= 8.0
- Python >= 3.10

## File Structure Created

```
SPARQLLM/
├── cli/
│   ├── slm.py (existing - updated)
│   ├── slm_mcp_server.py (new)
│   └── shared.py (new - extracted logic)
├── mcp/ (new)
│   ├── server.py
│   ├── validation.py
│   ├── formatting.py
│   ├── errors.py
│   ├── templates.py
│   ├── tools/
│   │   ├── echo.py
│   │   ├── sparql_query.py
│   │   ├── extract_structured_data.py
│   │   ├── rag_search.py
│   │   ├── web_to_knowledge.py
│   │   └── query_database.py
│   ├── resources/
│   │   └── store_resource.py
│   └── schemas/
│       └── tool_schemas.py
├── tests/ (updated)
│   ├── test_validation.py
│   ├── test_formatting.py
│   ├── test_errors.py
│   ├── test_sparql_query_tool.py
│   ├── test_convenience_tools.py
│   ├── test_resources.py
│   ├── test_mcp_integration.py
│   ├── test_agent_workflows.py
│   └── test_performance.py
├── docs/ (new)
│   ├── TOOL_REFERENCE.md
│   ├── WORKFLOWS.md
│   └── TROUBLESHOOTING.md
└── examples/notebooks/ (new)
    ├── 01-csv-extraction.ipynb
    ├── 02-rag-search.ipynb
    ├── 03-web-research.ipynb
    ├── 04-database-query.ipynb
    └── 05-recursive-graphs.ipynb
```

## Post-MVP Enhancements

**Defer to v2.0:**
- HTTP transport (SSE)
- Streaming LLM responses
- Query result caching
- Multi-tenant authentication
- Resource persistence (across restarts)
- Query plan inspection/optimization hints
- Metrics/instrumentation

## Research Foundation

Plans informed by:
- **MCP Protocol:** STDIO transport, tool schemas, resource templates, error handling
- **SPARQL Security:** Query injection prevention, parameterization limitations, resource limits
- **Codebase Analysis:** CLI execution flow, UDF registration, global store pattern, MCP client implementation
- **Query Patterns:** 60+ example queries showing GGF chaining, workflow composition

## Next Actions

1. Review plan with stakeholders
2. Set up development branch
3. Begin Phase 1 implementation
4. Establish PR review cadence
5. Set up CI/CD pipeline early

## Plan Files

- `plan.md` - Main architectural plan
- `phase-01-infrastructure.md` - STDIO server, tool registration
- `phase-02-sparql-query.md` - Core query execution tool
- `phase-03-convenience-tools.md` - Workflow wrappers
- `phase-04-resources.md` - Graph inspection resources
- `phase-05-testing-docs.md` - Testing, docs, examples
- `SUMMARY.md` - This file

**Total Documentation:** 97KB of detailed implementation guidance

## Contact & Questions

For questions about this plan:
1. Review specific phase document for technical details
2. Check research reports for foundational decisions
3. Consult scout reports for codebase context
4. Escalate architectural questions to plan author

---

**Plan Status:** Ready for implementation
**Estimated Completion:** 3-4 weeks
**Confidence Level:** High (research-backed, codebase-validated)
