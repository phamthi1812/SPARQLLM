# LLM as SPARQLLM Compiler - Implementation Plan Summary

**Date:** 2025-11-20
**Status:** Planning Complete - Ready for Implementation
**Estimated Effort:** 8-12 weeks (5 phases)
**Plan Directory:** `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/plans/20251120-1351-llm-sparqllm-compiler/`

---

## Executive Summary

Transform SPARQLLM into a compilation target for LLM reasoning. Instead of LLM agents calling MCP tools sequentially (imperative), the LLM generates a declarative SPARQLLM query that the engine optimizes and executes.

**Analogy:** LLM acts as SQL query planner → SPARQLLM as executable SQL → MCP as physical operators

**Key Innovation:** Two-stage compilation separates logical reasoning (LLM) from physical execution (query optimizer), enabling cost estimation, user confirmation, and systematic optimization.

---

## Core Architecture

```
User Question
    ↓
[Stage 1: Logical Planner]
  LLM generates JSON plan:
  - Steps (read_filesystem, llm_extract, web_search, etc.)
  - Dependencies (step2 depends on step1)
  - Join conditions, filters, bindings
    ↓
[Stage 2: Physical Compiler]
  Template expander translates plan → SPARQL:
  - BIND clauses for GGF calls
  - GRAPH patterns for result querying
  - Topological sort for execution order
    ↓
[Cost Estimator]
  Predict latency + tokens from catalog metadata
    ↓
[Natural Language Explainer]
  Convert plan to 2-4 sentence summary
    ↓
[User Confirmation]
  Display plan, cost, explanation
  User approves/rejects/edits
    ↓
[Execution Engine]
  Existing SPARQLLM evaluator with:
  - Lazy join evaluation
  - Provenance tracking (PROV-O)
  - Content-addressed graphs (SHA256)
    ↓
Results + Provenance
```

---

## Implementation Phases

### Phase 1: GGF Catalog Infrastructure (2 weeks)
**Goal:** Self-describing RDF catalog of all 44 GGFs with metadata

**Deliverables:**
- Turtle schema (`ggf-schema.ttl`) defining properties: signature, cost, capabilities
- Catalog generator script (AST parser + docstring extractor)
- Query API for LLM discovery (`find_ggfs_by_source("llm")`)
- `@ggf_metadata` decorator for manual annotations

**Key Files:**
- `SPARQLLM/data/ggf-catalog.ttl` (auto-generated)
- `SPARQLLM/tools/generate_ggf_catalog.py` (generator script)
- `SPARQLLM/catalog/query.py` (query API)
- `SPARQLLM/udf/metadata.py` (decorator)

**Success Criteria:**
- Catalog includes all 44 GGFs (34 modules + 10 MCP wrappers)
- Generation runs in <5s
- SPARQL query returns correct GGFs by data source

---

### Phase 2: Two-Stage Compiler (3 weeks)
**Goal:** Logical plan → SPARQL translation with cost estimation

**Deliverables:**
- JSON schema for logical plans (8 operation types)
- Physical compiler (dependency graph → topological sort → SPARQL generation)
- Cost estimator (query catalog, aggregate latency/tokens)
- Natural language explainer (plan → 2-4 sentence summary)
- Error recovery loop (max 3 retries with feedback)

**Key Files:**
- `SPARQLLM/compiler/schema/logical_plan.json` (JSON Schema)
- `SPARQLLM/compiler/physical_compiler.py` (plan → SPARQL)
- `SPARQLLM/compiler/cost_estimator.py` (cost prediction)
- `SPARQLLM/compiler/explainer.py` (natural language)
- `SPARQLLM/compiler/error_recovery.py` (retry logic)

**Success Criteria:**
- Compiler generates valid SPARQL from 90%+ of plans
- Cost estimation MAE <30% (mean absolute error)
- Compilation latency <500ms
- Error recovery: 80%+ invalid plans fixed in ≤3 retries

---

### Phase 3: Enhanced Query Generator (2 weeks)
**Goal:** Two-stage UI with plan visualization and user confirmation

**Deliverables:**
- Plan system prompt (LLM outputs JSON, not SPARQL)
- Rich console UI (plan viewer with dependency tree)
- Interactive confirmation flow (approve/reject/edit)
- Comparison mode (direct vs compiled vs manual)

**Key Files:**
- `demo/prompts/plan_system_prompt.txt` (new prompt)
- `demo/ui/plan_viewer.py` (rich console UI)
- `demo/query_generator.py` (extended with two-stage flow)
- `demo/comparison.py` (benchmark 3 paths)

**Success Criteria:**
- LLM generates valid JSON plans (90%+ success rate)
- Plan viewer displays within 1s
- Comparison: compiled path ≤1.5x direct path latency
- User confirmation flow intuitive (80%+ first-time success)

---

### Phase 4: Testing & Validation (2 weeks)
**Goal:** Comprehensive test suite validating all components

**Deliverables:**
- 30 unit tests (catalog, compiler, cost estimator, explainer)
- 20 integration tests (diverse queries: filesystem, LLM, web, SQL, hybrid)
- Benchmark suite (direct vs compiled performance)
- 10 regression tests (existing demo queries unchanged)
- 10 adversarial tests (error recovery: invalid GGFs, cycles, etc.)
- CI/CD integration (GitHub Actions)

**Key Files:**
- `tests/unit/test_compiler.py`, `test_cost_estimator.py`, etc.
- `tests/integration/test_queries.py` (20 test cases)
- `tests/integration/fixtures/` (test data, plans, expected outputs)
- `tests/benchmarks/test_performance.py`
- `.github/workflows/test.yml` (CI config)

**Success Criteria:**
- 90% integration tests pass (18/20)
- Unit test coverage >80%
- Benchmark: compiler overhead <50%
- Cost estimation MAE <30% (actual vs predicted)
- Regression: 10/10 existing queries still work
- CI runs in <5 minutes

---

### Phase 5: Documentation & Examples (1 week)
**Goal:** Production-ready documentation for users and developers

**Deliverables:**
- User guide (quickstart, workflow, cost model, FAQ)
- Developer guide (architecture, adding GGFs, extending compiler)
- API reference (auto-generated with Sphinx)
- 10 annotated examples (use cases with explanations)
- Troubleshooting guide (20 common errors)
- Documentation site (GitHub Pages)

**Key Files:**
- `docs/user-guide/quickstart.md`
- `docs/developer-guide/adding-ggfs.md`
- `docs/api-reference/` (auto-generated)
- `docs/examples/01-simple-filesystem.md` through `10-cost-optimization.md`
- `docs/troubleshooting.md`

**Success Criteria:**
- User completes quickstart in <10 minutes
- Developer adds new GGF in <30 minutes
- API reference: 100% public functions documented
- 10 annotated examples covering all GGF types
- Docs site loads in <2s, mobile-responsive

---

## Technical Decisions (Research-Backed)

### From Researcher 01 (LLM Compilation)
1. **Two-stage architecture**: Logical (intent) → Physical (execution) separation enables error recovery
2. **Cost model**: Latency-aware (ms/s regime), not cardinality-based (traditional SQL)
3. **Error recovery**: Iterative refinement with max 3 retries (90%+ success rate in SOTA)
4. **Declarative > Imperative**: SPARQL patterns allow optimizer reordering (vs locked agent traces)

### From Researcher 02 (MCP & GGF Design)
1. **Content-addressed graphs**: SHA256 for stable URIs (existing pattern, keep it)
2. **Self-describing catalog**: RDF registry queryable via SPARQL (like MCP `tools/list`)
3. **Provenance tracking**: PROV-O metadata (duration, timestamps) - extend with cost
4. **MCP alignment**: 1:1 GGF wrappers for MCP tools (maintain compatibility)

---

## Key Metrics & Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Plan Generation Accuracy** | 90%+ valid JSON | Phase 3: LLM outputs, Phase 4: integration tests |
| **Compilation Correctness** | 95%+ valid SPARQL | Phase 2: unit tests, Phase 4: 20 integration tests |
| **Cost Estimation Precision** | MAE <30% | Phase 4: compare estimated vs actual for 5 queries |
| **Compilation Latency** | <500ms | Phase 2: profiling, Phase 4: benchmarks |
| **Error Recovery Rate** | 80%+ fixed in ≤3 retries | Phase 2: error recovery loop, Phase 4: adversarial tests |
| **Performance Overhead** | Compiled ≤1.5x direct | Phase 3: comparison mode, Phase 4: benchmarks |
| **Test Coverage** | >80% | Phase 4: pytest-cov |
| **Documentation Completeness** | 100% public APIs | Phase 5: Sphinx auto-gen |

---

## Risk Management

### High-Impact Risks

1. **LLM hallucinates invalid GGFs**
   - **Mitigation:** Catalog validation layer, retry with error feedback, explicit function list in prompt

2. **Template expansion brittle (edge cases)**
   - **Mitigation:** Extensive unit tests (30+ cases), fallback to direct SPARQL generation

3. **Cost model inaccurate (LLM variability)**
   - **Mitigation:** Use P50 not mean, empirical profiling in Phase 4, user-adjustable weights

4. **Backward compatibility breaks**
   - **Mitigation:** Feature flag, parallel implementations, regression tests (10 existing queries)

### Medium-Impact Risks

5. **Metadata drift (code changes, catalog stale)**
   - **Mitigation:** CI fails if catalog out-of-sync, auto-regen on commit (pre-commit hook)

6. **Test data too large (slow CI)**
   - **Mitigation:** Synthetic data <10MB, mock external APIs (DuckDuckGo, Groq)

---

## Dependencies & Prerequisites

### External
- **Groq API** (LLM): Free tier (1000 req/hr) sufficient for testing
- **Python 3.10+**: Type hints, pattern matching
- **RDFLib 7.0+**: SPARQL 1.1 support
- **Rich library**: Terminal UI (plan viewer)
- **Jinja2**: Template rendering (SPARQL generation)

### Internal (Existing Codebase)
- **GGF modules:** 34 Python modules in `SPARQLLM/udf/`
- **MCP wrappers:** 10 tools in `SPARQLLM/udf/mcp/`
- **Execution engine:** `SPARQLLM/SPARQLLM.py` (Dataset store, lazy joins)
- **Demo scaffold:** `demo/query_generator.py` (440 lines, extend in Phase 3)

---

## File Structure Summary

```
SPARQLLM/
├── data/
│   └── ggf-catalog.ttl                  # Phase 1: Auto-generated catalog
├── catalog/
│   └── query.py                         # Phase 1: Query API for catalog
├── compiler/
│   ├── schema/
│   │   └── logical_plan.json            # Phase 2: JSON Schema
│   ├── physical_compiler.py             # Phase 2: Plan → SPARQL
│   ├── cost_estimator.py                # Phase 2: Cost prediction
│   ├── explainer.py                     # Phase 2: Natural language
│   └── error_recovery.py                # Phase 2: Retry logic
├── udf/
│   ├── metadata.py                      # Phase 1: @ggf_metadata decorator
│   └── [existing GGF modules]           # Phase 1: Annotate with metadata
├── tools/
│   └── generate_ggf_catalog.py          # Phase 1: Catalog generator
├── demo/
│   ├── prompts/
│   │   └── plan_system_prompt.txt       # Phase 3: LLM prompt for plans
│   ├── ui/
│   │   └── plan_viewer.py               # Phase 3: Rich console UI
│   ├── query_generator.py               # Phase 3: Extended with two-stage
│   └── comparison.py                    # Phase 3: Benchmark direct vs compiled
├── tests/
│   ├── unit/                            # Phase 4: 30 unit tests
│   ├── integration/                     # Phase 4: 20 integration tests
│   ├── benchmarks/                      # Phase 4: Performance tests
│   ├── regression/                      # Phase 4: Existing query tests
│   └── error_recovery/                  # Phase 4: Adversarial tests
├── docs/
│   ├── user-guide/                      # Phase 5: User docs
│   ├── developer-guide/                 # Phase 5: Developer docs
│   ├── api-reference/                   # Phase 5: Auto-generated
│   ├── examples/                        # Phase 5: 10 annotated examples
│   └── troubleshooting.md               # Phase 5: Common errors
└── plans/20251120-1351-llm-sparqllm-compiler/
    ├── plan.md                          # This plan overview
    ├── phase-01-ggf-catalog.md
    ├── phase-02-compiler.md
    ├── phase-03-query-generator.md
    ├── phase-04-testing.md
    ├── phase-05-documentation.md
    └── research/
        ├── researcher-01-llm-compilation.md
        └── researcher-02-mcp-ggf-design.md
```

---

## Next Steps (Implementation Kickoff)

1. **Week 0 (Preparation):**
   - Review research reports with team
   - Set up development environment (Python 3.10+, dependencies)
   - Assign phase owners (Backend, LLM Integration, QA, Technical Writer)

2. **Week 1-2 (Phase 1):**
   - Design catalog schema (properties, classes)
   - Build catalog generator (AST parser)
   - Annotate top 10 GGFs with `@ggf_metadata`
   - Create query API

3. **Week 3-5 (Phase 2):**
   - Define logical plan JSON schema
   - Implement physical compiler (dependency graph → SPARQL)
   - Build cost estimator + explainer
   - Add error recovery loop

4. **Week 6-7 (Phase 3):**
   - Write plan system prompt
   - Build plan viewer UI (rich console)
   - Extend query generator with two-stage flow
   - Create comparison mode

5. **Week 8-9 (Phase 4):**
   - Write 30 unit tests + 20 integration tests
   - Run benchmarks (direct vs compiled)
   - Add CI/CD integration
   - Fix failing tests (target 90%+ pass rate)

6. **Week 10 (Phase 5):**
   - Write user + developer guides
   - Generate API reference
   - Create 10 annotated examples
   - Set up documentation site

---

## Unresolved Questions (Flagged for Team Discussion)

### Phase 1 (Catalog)
1. Should catalog track runtime statistics (actual P50 latency) or only static estimates?
2. How to version catalog for breaking changes (GGF signature updates)?

### Phase 2 (Compiler)
3. Should compiler optimize plans (filter pushdown) or trust LLM output?
4. Parallel execution: detect automatically or require explicit plan annotation?
5. Error recovery: LLM self-corrects or escalate to user?

### Phase 3 (UI)
6. Plan editor: support graphical DAG view (requires GUI) or terminal only?
7. How to handle very long explanations (>200 words) - truncate or paginate?

### Phase 4 (Testing)
8. Should benchmarks include LLM generation latency or only execution?
9. Cost estimation: use fixed catalog values or empirical averages from test runs?

### Phase 5 (Documentation)
10. Host docs on GitHub Pages, ReadTheDocs, or custom domain?
11. Research paper target venue: ISWC, ESWC, or NeurIPS workshop?

---

## References

- **Research Report 1:** [LLM as Query Compiler - State of Art](research/researcher-01-llm-compilation.md)
- **Research Report 2:** [MCP Ecosystem & GGF Design](research/researcher-02-mcp-ggf-design.md)
- **Existing Demo:** `demo/query_generator.py` (440 lines, direct SPARQL generation)
- **GGF Modules:** `SPARQLLM/udf/` (34 modules)
- **MCP Integration:** `SPARQLLM/udf/mcp/slm_mcp_tool.py` (10 wrappers)

---

## Contact & Ownership

**Plan Author:** Claude Code (Anthropic)
**Date Created:** 2025-11-20
**Status:** Planning Complete
**Next Milestone:** Phase 1 Kickoff (Week 1-2)

For questions or updates, refer to individual phase documents:
- `phase-01-ggf-catalog.md` (GGF Catalog Infrastructure)
- `phase-02-compiler.md` (Two-Stage Compiler)
- `phase-03-query-generator.md` (Enhanced Query Generator)
- `phase-04-testing.md` (Testing & Validation)
- `phase-05-documentation.md` (Documentation & Examples)
