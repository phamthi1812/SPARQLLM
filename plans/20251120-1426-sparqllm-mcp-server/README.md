# SPARQLLM MCP Server - Implementation Plan

**Created:** 2025-11-20
**Status:** Ready for implementation
**Total Documentation:** ~4,500 lines across 13 files

## Navigation Guide

### Start Here

1. **[QUICK_START.md](QUICK_START.md)** - Developer quick start (15 min read)
2. **[SUMMARY.md](SUMMARY.md)** - Executive summary + timeline
3. **[plan.md](plan.md)** - Main architectural plan

### Phase Implementation Plans

Detailed step-by-step guides for each phase:

| Phase | File | Duration | Description |
|-------|------|----------|-------------|
| **Phase 1** | [phase-01-infrastructure.md](phase-01-infrastructure.md) | 3-5 days | STDIO server, tool registration, error handling |
| **Phase 2** | [phase-02-sparql-query.md](phase-02-sparql-query.md) | 2-3 days | Core `sparql_query` tool with validation |
| **Phase 3** | [phase-03-convenience-tools.md](phase-03-convenience-tools.md) | 4-6 days | Workflow wrappers (extract, RAG, web, DB) |
| **Phase 4** | [phase-04-resources.md](phase-04-resources.md) | 2-3 days | Graph inspection resources |
| **Phase 5** | [phase-05-testing-docs.md](phase-05-testing-docs.md) | 3-4 days | Testing, docs, examples |

### Research Foundation

Background research that informed the plan:

- **[research/researcher-01-mcp-protocol.md](research/researcher-01-mcp-protocol.md)** - MCP spec, STDIO transport, tool schemas, best practices
- **[research/researcher-02-sparql-apis.md](research/researcher-02-sparql-apis.md)** - SPARQL security, JSON-LD serialization, performance

### Codebase Analysis

Detailed analysis of existing SPARQLLM code:

- **[scout/scout-01-mcp-and-udf.md](scout/scout-01-mcp-and-udf.md)** - MCP client implementation, UDF system, global store
- **[scout/scout-02-cli-execution.md](scout/scout-02-cli-execution.md)** - CLI execution flow, config management
- **[scout/scout-03-query-patterns.md](scout/scout-03-query-patterns.md)** - Query patterns, GGF chaining, MCP usage examples

## Project Overview

### What We're Building

Transform SPARQLLM into an MCP server that exposes its neuro-symbolic RAG capabilities as tools for AI agents.

**Before:**
```
SPARQLLM (MCP Client) → External MCP Tools (GitHub, Postgres, LLM)
```

**After:**
```
SPARQLLM (Dual Mode)
  ├─ MCP Client → External tools (existing)
  └─ MCP Server → Expose own capabilities
         ↓
    AI Agents can use SPARQLLM tools
```

### Core Capabilities Exposed

1. **sparql_query** - Execute SPARQL with Graph Generating Functions
2. **extract_structured_data** - File → Parse → LLM → RDF
3. **rag_search** - Query → Vector search → LLM synthesis
4. **web_to_knowledge** - URL → Scrape → Entity extraction → RDF
5. **query_database** - SQL → RDF mapping

### Architecture

```
┌─────────────────────────────────────┐
│  AI Agent (Claude, GPT-4, etc.)    │
└─────────────────────────────────────┘
              │ MCP Protocol (STDIO)
              ↓
┌─────────────────────────────────────┐
│  MCP Server (slm-mcp-server)        │
│  ┌───────────────────────────────┐  │
│  │ Tools + Resources + Errors    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│  SPARQLLM Core                      │
│  - UDF system (GGFs)                │
│  - Global store (Dataset)           │
│  - ConfigSingleton                  │
└─────────────────────────────────────┘
```

## Timeline

**Total Duration:** 14-21 days

```
Week 1: Infrastructure + Core Tool
├─ Days 1-2: Phase 1 (MCP server infrastructure)
├─ Days 3-5: Phase 2 (sparql_query tool)

Week 2: Convenience Tools + Resources
├─ Days 6-10: Phase 3 (4 workflow wrappers)
├─ Days 11-12: Phase 4 (resource providers)

Week 3: Testing + Documentation
├─ Days 13-14: Phase 5 (tests, docs, examples)
└─ Buffer: 7 days for polish, debugging, feedback
```

## Key Design Principles

1. **YAGNI** - Start with STDIO, defer HTTP/SSE
2. **KISS** - Reuse CLI logic, don't rewrite
3. **DRY** - Share config management between CLI and server
4. **Security First** - Layered validation, resource limits
5. **Backward Compatibility** - Existing CLI must still work

## File Structure

```
SPARQLLM/
├── mcp/ (new - ~2,000 lines)
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
├── cli/
│   ├── slm.py (existing - updated)
│   ├── slm_mcp_server.py (new)
│   └── shared.py (new)
└── tests/ (updated - ~1,000 new lines)
    ├── test_validation.py
    ├── test_formatting.py
    ├── test_sparql_query_tool.py
    ├── test_convenience_tools.py
    ├── test_resources.py
    ├── test_mcp_integration.py
    └── test_agent_workflows.py
```

## Success Metrics

- [ ] All 5 tools registered and functional
- [ ] >90% test coverage for core modules
- [ ] 5 agent workflow simulations pass
- [ ] Documentation complete and accurate
- [ ] Existing CLI tests still pass
- [ ] Zero breaking changes to existing code

## Dependencies

**New:**
- `mcp` - Official Python MCP SDK

**Existing (no changes):**
- rdflib >= 6.0
- click >= 8.0
- Python >= 3.10

## Getting Started

### For Developers
1. Read [QUICK_START.md](QUICK_START.md)
2. Review [phase-01-infrastructure.md](phase-01-infrastructure.md)
3. Set up development environment
4. Start implementing Phase 1

### For Reviewers
1. Read [SUMMARY.md](SUMMARY.md)
2. Review [plan.md](plan.md) for architecture decisions
3. Check research reports for validation
4. Review phase plans for implementation details

### For Stakeholders
1. Read this README
2. Review [SUMMARY.md](SUMMARY.md)
3. Check timeline and success metrics
4. Approve plan or request changes

## Plan Quality Metrics

- **Research-backed:** 297 lines of protocol/security research
- **Codebase-validated:** 460 lines of codebase analysis
- **Detailed implementation:** 2,940 lines of phase-specific guidance
- **Comprehensive testing:** 659 lines of test strategy
- **Production-ready:** Error handling, security, performance considerations

## References

### External Documentation
- [MCP Specification](https://modelcontextprotocol.io/specification/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [SPARQL 1.1 Spec](https://www.w3.org/TR/sparql11-query/)
- [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/)

### Internal Documentation
- SPARQLLM README: `/CLAUDE.md`
- Existing queries: `/queries/*`
- Current tests: `/tests/*`

## Contributing

1. Create feature branch from `main`
2. Implement one phase at a time
3. Write tests first (TDD)
4. Ensure existing CLI tests pass
5. Update documentation
6. Submit PR with phase reference

## Questions?

- **Architecture:** Review [plan.md](plan.md) → Design Decisions
- **Implementation:** Check relevant phase plan
- **Research:** Read research reports
- **Codebase:** Check scout reports
- **Timeline:** See [SUMMARY.md](SUMMARY.md)

---

**Plan Version:** 1.0
**Last Updated:** 2025-11-20
**Status:** Ready for implementation approval
