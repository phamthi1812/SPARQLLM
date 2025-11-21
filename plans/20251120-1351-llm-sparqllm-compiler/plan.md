# LLM as SPARQLLM Compiler - Implementation Plan

**Date:** 2025-11-20
**Status:** Planning Complete
**Effort:** 5 phases, ~8-12 weeks

---

## Vision

Transform SPARQLLM into compilation target for LLM reasoning. Instead of imperative tool chains, LLM generates declarative SPARQLLM query → optimizer executes efficiently.

**Analogy:** LLM = SQL query planner | SPARQLLM = executable SQL | MCP = physical operators

---

## Core Architecture

```
User Question
    ↓
[Stage 1: Logical Planner]  ← LLM generates JSON plan (steps, dependencies, joins)
    ↓
[Stage 2: SPARQLLM Compiler] ← Template expander: plan → SPARQL + GGF calls
    ↓
[User Confirmation] ← Explain plan in natural language, show cost estimate
    ↓
[Execution Engine] ← Existing evaluator with lazy joins, provenance tracking
    ↓
Results + Provenance
```

---

## Key Components

### 1. GGF Catalog (Self-Describing)
- RDF registry: all GGFs with signatures, cost, capabilities
- Queryable by LLM ("what GGFs access SQL?")
- Auto-generated from code + docstrings

### 2. Two-Stage Compilation
- **Logical Plan**: JSON schema (steps, deps, filters, joins) - LLM output
- **Physical Plan**: SPARQL query with BIND/GRAPH patterns - template expansion
- User sees both: natural language explanation + generated SPARQL

### 3. Enhanced Query Generator
- Extend `demo/query_generator.py` with two-stage flow
- Add cost estimation (latency + token budget)
- Interactive confirmation before execution

### 4. MCP-to-GGF Alignment
- 1:1 wrapper for common MCP tools (GitHub, Postgres, DuckDuckGo, Browser)
- Ensure all MCPs callable as GGFs
- Document mapping strategy

### 5. Evaluation Framework
- 20 integration questions (filesystem + LLM + web + SQL)
- Compare: direct agent vs compiler vs manual
- Metrics: correctness, efficiency, cost

---

## Implementation Phases

| Phase | Focus | Duration | Dependencies |
|-------|-------|----------|--------------|
| **Phase 1** | GGF Catalog Infrastructure | 2 weeks | None |
| **Phase 2** | Two-Stage Compiler | 3 weeks | Phase 1 |
| **Phase 3** | Enhanced Query Generator | 2 weeks | Phase 2 |
| **Phase 4** | Testing & Validation | 2 weeks | Phase 3 |
| **Phase 5** | Documentation & Examples | 1 week | Phase 4 |

---

## Success Criteria

1. LLM generates valid logical plans (90%+ success rate)
2. Compiler produces executable SPARQL from plans (95%+ correctness)
3. Cost estimation within 20% of actual execution
4. 20/20 integration tests pass
5. Performance: compiler path ≤ 1.5x manual query latency

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucinates invalid GGFs | High | Catalog validation layer; retry with error feedback |
| Cost model inaccurate | Medium | Empirical profiling; user-adjustable weights |
| Template expansion brittle | High | Schema validation; extensive unit tests |
| Backward compatibility breaks | Medium | Feature flag; parallel implementations |

---

## Technical Decisions (from Research)

1. **Logical plan format**: JSON (not SPARQL algebra) - easier for LLM to generate
2. **Cost model**: Latency-aware (ms/s regime), not cardinality-based
3. **Catalog storage**: RDF (turtle) - queryable via SPARQL, versioned with code
4. **Error recovery**: Iterative refinement loop (max 3 retries with feedback)
5. **Caching**: Content-addressed graphs (existing SHA256 URIs) - no change needed

---

## File Structure

```
plans/20251120-1351-llm-sparqllm-compiler/
├── plan.md                          # This file
├── phase-01-ggf-catalog.md          # GGF registry + schema
├── phase-02-compiler.md             # Logical → Physical compiler
├── phase-03-query-generator.md      # Enhanced demo + UI
├── phase-04-testing.md              # Integration test suite
├── phase-05-documentation.md        # User guides + examples
└── research/                        # Existing research reports
    ├── researcher-01-llm-compilation.md
    └── researcher-02-mcp-ggf-design.md
```

---

## Unresolved Questions

1. Should catalog include runtime statistics (avg latency per GGF) or static estimates?
2. How to handle dynamic GGF registration (user-defined functions)?
3. Cost threshold for parallel vs serial execution - empirical or user-configurable?
4. Error recovery: LLM self-corrects or return to user?
