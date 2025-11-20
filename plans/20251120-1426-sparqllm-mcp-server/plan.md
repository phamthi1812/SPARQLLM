# SPARQLLM MCP Server Implementation Plan

**Created:** 2025-11-20
**Status:** Ready for implementation

## Executive Summary

Transform SPARQLLM from MCP client to dual-mode system: continue consuming MCP tools while exposing neuro-symbolic RAG capabilities as MCP server. Core insight: SPARQLLM's strength lies in chaining operations (file→parse→LLM→RDF), not just executing queries. MCP tools should reflect this workflow-oriented design.

**Key Decision:** Hybrid approach - low-level `sparql.query` tool + high-level convenience wrappers (`extract_structured_data`, `rag_search`, etc.) balancing flexibility and usability.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  AI Agent (Claude, GPT-4, etc.)                     │
└─────────────────────────────────────────────────────┘
                      │ MCP Protocol (STDIO)
                      ↓
┌─────────────────────────────────────────────────────┐
│  MCP Server (slm-mcp-server CLI)                    │
│  ┌───────────────────────────────────────────────┐  │
│  │ Tools:                                        │  │
│  │  - sparql.query (core)                        │  │
│  │  - extract_structured_data (convenience)     │  │
│  │  - rag_search (convenience)                   │  │
│  │  - web_to_knowledge (convenience)             │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │ Resources:                                    │  │
│  │  - store://{session_id}/graphs (optional)    │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────┐
│  SPARQLLM Core                                      │
│  - UDF system (GGFs)                                │
│  - Global store (Dataset)                           │
│  - ConfigSingleton                                  │
│  - MCP client (nested calls)                        │
└─────────────────────────────────────────────────────┘
```

## Core Principles

1. **YAGNI**: Start with STDIO transport, defer HTTP/SSE
2. **KISS**: Reuse CLI logic (`slm_cmd`), don't rewrite query execution
3. **DRY**: Share config management, UDF registration between CLI and server
4. **Security First**: Query injection prevention, resource limits, session isolation
5. **Backward Compatibility**: Existing `slm-run` CLI unchanged

## Implementation Phases

### Phase 1: Core MCP Server Infrastructure (3-5 days)
- STDIO transport with JSON-RPC 2.0
- Tool schema design & registration
- Session lifecycle management
- Error handling framework
- **Deliverable:** `slm-mcp-server` CLI responding to basic tool calls

### Phase 2: Core sparql.query Tool (2-3 days)
- Query validation & sanitization
- Store isolation per request
- Result formatting (JSON-LD, CSV, Turtle)
- Timeout enforcement
- **Deliverable:** Functional low-level SPARQL execution via MCP

### Phase 3: High-Level Convenience Tools (4-6 days)
- `extract_structured_data`: File → Parser → LLM → RDF
- `rag_search`: Query → Vector search → LLM synthesis
- `web_to_knowledge`: URL → Scrape → LLM extraction → RDF
- `query_database`: SQL → Results → RDF mapping
- **Deliverable:** Production-ready workflow wrappers

### Phase 4: Resource Providers (2-3 days)
- `store://{session_id}/graphs` resource
- Named graph inspection
- Optional persistence (if needed)
- **Deliverable:** Agents can inspect intermediate graphs

### Phase 5: Testing, Documentation, Examples (3-4 days)
- Unit tests for tools
- Integration tests (agent simulations)
- Usage documentation
- Example queries for common patterns
- **Deliverable:** Production-ready MCP server

## Design Decisions & Rationale

### 1. Tool Naming Convention
**Decision:** `snake_case` with dot-notation for namespacing
- Core: `sparql.query`, `sparql.update`, `sparql.construct`
- Workflows: `extract_structured_data`, `rag_search`

**Rationale:** 90%+ MCP servers use snake_case; dot-notation groups related tools

### 2. State Management
**Decision:** Stateless per-request isolation
- Create fresh store context per tool call
- Call `reset_store()` after each MCP response
- Optional: persist via `store://` resource if agent needs multi-turn access

**Rationale:** Prevents cross-contamination; simplifies deployment

### 3. Input Validation
**Decision:** Layered defense
1. JSON Schema validation (MCP protocol level)
2. SPARQL syntax validation (parse before execute)
3. Function whitelist (only allow registered UDFs)
4. Timeout enforcement (30s default, configurable)

**Rationale:** "Parameterized queries not foolproof" per Apache Jena docs

### 4. Output Format
**Decision:** JSON-LD default, Turtle/CSV optional
- SELECT results: CSV or JSON array
- CONSTRUCT results: JSON-LD (compact context)
- Errors: JSON object with error details

**Rationale:** JSON-LD native JSON compatibility, LLM-friendly

### 5. Reuse CLI Logic
**Decision:** Extract shared function `execute_query(query_str, config_file, load_file, format, timeout)` from `slm_cmd()`
- CLI: Calls `execute_query()`, formats for terminal
- MCP server: Calls `execute_query()`, formats for JSON-RPC

**Rationale:** DRY principle, reduces bugs, maintains feature parity

## Security Considerations

### Query Injection Prevention
1. **No string concatenation**: All UDF args passed via SPARQL variables
2. **Function whitelist**: Reject queries calling unknown functions
3. **Syntax validation**: Parse query before execution
4. **Result size limits**: Cap rows returned (default 1000)

### Resource Limits
- **Timeout**: 30s default (configurable)
- **Memory**: Monitor store size, reject if > 100MB (configurable)
- **CPU**: OS-level process limits (future: cgroups)

### Multi-Tenancy
**Phase 1 approach:** Process-per-agent (STDIO isolation)
- Each agent spawns separate `slm-mcp-server` process
- OS provides memory/CPU isolation
- No cross-tenant graph contamination

**Future (HTTP):** Logical isolation with tenant ID predicates

## Performance Optimizations

1. **Lazy evaluation**: Preserve existing `evalLazyJoin` logic
2. **Efficient serialization**: JSON-LD framing for compact output
3. **Store cleanup**: Aggressively prune graphs after response
4. **Connection pooling**: For nested MCP client calls (DB, LLM APIs)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Query injection exploits | Medium | High | Layered validation, whitelist, timeout |
| Store memory leaks | Medium | High | Aggressive cleanup, size monitoring |
| Infinite recursion (SLM-RECURSE) | Low | High | Iteration limit, timeout |
| Breaking existing CLI | Low | Medium | Extract shared logic, unit tests |
| Complex tool schemas | Medium | Low | Start simple, iterate based on feedback |

## Success Criteria

### Phase 1
- [ ] `slm-mcp-server --config config.ini` starts and responds to `initialize` request
- [ ] `tools/list` returns valid JSON schema
- [ ] Echo tool returns "pong" on ping

### Phase 2
- [ ] Agent executes `sparql.query` with filesystem query (no LLM)
- [ ] Results returned as JSON-LD
- [ ] Timeout enforced for long queries
- [ ] Error handling for syntax errors

### Phase 3
- [ ] `extract_structured_data` chains file → parser → LLM → RDF
- [ ] `rag_search` queries FAISS index, synthesizes with LLM
- [ ] `web_to_knowledge` scrapes URL, extracts entities

### Phase 4
- [ ] Agent lists graphs via `store://{session_id}/graphs`
- [ ] Agent reads specific graph via `resources/read`

### Phase 5
- [ ] Test suite passes (>90% coverage)
- [ ] Documentation published
- [ ] Example agent workflow runs end-to-end

## File Structure

```
SPARQLLM/
├── cli/
│   ├── slm.py (existing)
│   ├── slm_mcp_server.py (new)
│   └── shared.py (new - extracted execute_query logic)
├── mcp/
│   ├── server.py (new - MCP protocol handler)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── sparql_query.py (new)
│   │   ├── extract_structured_data.py (new)
│   │   ├── rag_search.py (new)
│   │   └── web_to_knowledge.py (new)
│   ├── resources/
│   │   ├── __init__.py
│   │   └── store_resource.py (new)
│   └── schemas/
│       └── tool_schemas.json (new)
├── udf/ (existing)
└── tests/
    └── test_mcp_server.py (new)

setup.py (updated):
  entry_points:
    slm-mcp-server = SPARQLLM.cli.slm_mcp_server:main
```

## Dependencies

**New packages:**
- `mcp` - Official MCP SDK for Python (stdio server primitives)
- None! SPARQLLM already has all RDF/SPARQL deps

**Version constraints:**
- Python >= 3.10 (existing)
- rdflib >= 6.0 (existing)
- click >= 8.0 (existing)

## Development Strategy

1. **Parallel work streams**:
   - Stream A: Phase 1 infrastructure
   - Stream B: Extract shared CLI logic

2. **Incremental testing**: Each tool tested independently before integration

3. **Early feedback**: Deploy Phase 2 to staging, gather agent usage patterns

4. **Defer complexity**: HTTP transport, advanced auth → post-MVP

## Open Questions

1. **Session persistence**: Should `store://` resources persist across server restarts? Initial answer: NO (stateless), revisit if needed
2. **Nested MCP calls**: Should agents see SPARQLLM's own MCP client calls (GitHub, Postgres)? Initial answer: YES (transparent), hide via config if problematic
3. **Query optimization hints**: Should tools accept optimizer hints (join order, cardinality)? Initial answer: NO (YAGNI), add if performance issues arise

## References

- Phase 1 details: `plans/20251120-1426-sparqllm-mcp-server/phase-01-infrastructure.md`
- Phase 2 details: `plans/20251120-1426-sparqllm-mcp-server/phase-02-sparql-query.md`
- Phase 3 details: `plans/20251120-1426-sparqllm-mcp-server/phase-03-convenience-tools.md`
- Phase 4 details: `plans/20251120-1426-sparqllm-mcp-server/phase-04-resources.md`
- Phase 5 details: `plans/20251120-1426-sparqllm-mcp-server/phase-05-testing-docs.md`
- Research: `research/researcher-01-mcp-protocol.md`, `research/researcher-02-sparql-apis.md`
- Codebase: `scout/scout-01-mcp-and-udf.md`, `scout/scout-02-cli-execution.md`, `scout/scout-03-query-patterns.md`
