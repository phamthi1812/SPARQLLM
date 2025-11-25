# Implementation Summary: LLM Direct SPARQL Generation

**Date:** 2025-11-21
**Status:** Ready for Implementation
**Estimated Effort:** 6-9 hours (4 phases)

---

## Quick Overview

**Goal:** Enable LLM to generate SPARQL queries with GGFs directly, bypassing PhysicalCompiler

**Architecture Change:**
```
BEFORE: User Question → LLM → JSON Plan → PhysicalCompiler → SPARQL → Execution
AFTER:  User Question → LLM → SPARQL (validated) → Execution
```

**Why:** PhysicalCompiler has bugs; working SPARQL examples exist; user wants direct generation

---

## Plan Structure

### Main Plan
[`plan.md`](./plan.md) - High-level overview, architecture, phases, risks (80 lines)

### Phase Plans (Sequential Implementation)

1. **Phase 1: System Prompt Creation** ([`phase-01-system-prompt-creation.md`](./phase-01-system-prompt-creation.md))
   - Create SPARQL-focused prompt teaching GGF syntax
   - Include 6 annotated examples from working queries
   - File: `demo/serial_killers/prompts/direct_system_prompt.txt`
   - Effort: 2-3 hours

2. **Phase 2: Query Generator Modification** ([`phase-02-query-generator-modification.md`](./phase-02-query-generator-modification.md))
   - Add `mode='direct'` support to QueryGenerator
   - Implement `generate_sparql()` method
   - File: `demo/query_generator.py` (+80-100 lines)
   - Effort: 1-2 hours

3. **Phase 3: Validation Layer** ([`phase-03-validation-layer.md`](./phase-03-validation-layer.md))
   - Create SPARQLValidator for syntax/semantic checks
   - File: `SPARQLLM/compiler/sparql_validator.py` (~200 lines)
   - Effort: 1.5-2 hours

4. **Phase 4: Testing & Integration** ([`phase-04-testing-integration.md`](./phase-04-testing-integration.md))
   - Unit tests, integration tests, E2E tests
   - Ground truth validation
   - Files: `tests/unit/`, `tests/integration/`
   - Effort: 2-3 hours

---

## Key Components

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `demo/serial_killers/prompts/direct_system_prompt.txt` | 150-200 | SPARQL prompt with examples |
| `SPARQLLM/compiler/sparql_validator.py` | 200 | Validation layer |
| `tests/unit/test_query_generator_direct.py` | 150 | Unit tests |
| `tests/integration/test_direct_sparql_e2e.py` | 100 | E2E tests |
| `demo/serial_killers/validate_direct_mode.py` | 80 | Ground truth validation |

**Total: ~680 new lines**

### Modified Files

| File | Changes |
|------|---------|
| `demo/query_generator.py` | +80-100 lines (generate_sparql method) |

---

## Implementation Order

```
Day 1 (4-5 hours):
├── Phase 1: Create system prompt
│   ├── Study working examples (30 min)
│   ├── Write prompt sections (90 min)
│   ├── Manual testing with LLM (30 min)
│   └── Refinement (30 min)
└── Phase 2: Modify QueryGenerator
    ├── Add generate_sparql method (60 min)
    ├── Integration with prompt (30 min)
    └── Manual testing (30 min)

Day 2 (3-4 hours):
├── Phase 3: Create validator
│   ├── Implement validation logic (90 min)
│   ├── Write unit tests (60 min)
│   └── Integration testing (30 min)
└── Phase 4: Testing & Integration
    ├── E2E tests (60 min)
    ├── Ground truth validation (60 min)
    └── Documentation (30 min)
```

---

## Critical Dependencies

**External:**
- Ollama running (`ollama serve`)
- Model available: llama3.2:latest or equivalent
- slm-run CLI working
- Serial killers dataset exists

**Internal:**
- Research reports (already complete)
- Working query examples (already exist)
- Existing QueryGenerator infrastructure

---

## Success Metrics

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Valid SPARQL generation | 90%+ | Unit tests |
| Correct results | 80%+ | Ground truth comparison |
| Validation catches errors | 95%+ | Intentional error tests |
| E2E query time | <10s | Benchmark script |
| No plan mode regression | 100% | Existing tests still pass |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM generates invalid SPARQL | Validation layer + 5-8 examples in prompt |
| Token limit exceeded | Keep prompt <2000 tokens, use concise examples |
| Variable binding errors | Explicit rules in prompt + validator checks |
| Regression in plan mode | Isolate direct mode code, don't modify plan logic |

---

## Testing Strategy

**3-Tier Approach:**

1. **Unit Tests** - Individual components (prompt loading, validation, markdown cleaning)
2. **Integration Tests** - Component interactions (generator + validator)
3. **E2E Tests** - Full flow (question → SPARQL → execution → results)

**Ground Truth:** Validate against known correct results for serial killers questions

---

## Documentation Updates Needed

1. Update README.md with direct mode usage
2. Add examples to demo/serial_killers/README.md
3. Document prompt engineering decisions
4. Create troubleshooting guide

---

## Future Enhancements (Out of Scope)

- Multi-hop queries (LLM → CSV chaining)
- Auto-fix common errors
- Dynamic GGF catalog injection
- Support for other datasets
- Comparison mode (direct vs plan side-by-side)

---

## Quick Start Guide

**For Implementer:**

1. Read [`plan.md`](./plan.md) for architecture overview
2. Implement phases sequentially (1 → 2 → 3 → 4)
3. Each phase has detailed instructions in `phase-0X-*.md`
4. Test after each phase before proceeding
5. Follow success criteria in each phase plan

**For Reviewer:**

1. Check prompt quality (Phase 1): Does it teach GGF syntax clearly?
2. Check code quality (Phase 2): Is generate_sparql() robust?
3. Check validation coverage (Phase 3): Does it catch main error types?
4. Check test coverage (Phase 4): Do tests cover happy/error paths?

---

## References

**Research Reports:**
- [researcher-01-direct-sparql-generation.md](./research/researcher-01-direct-sparql-generation.md)
- [researcher-02-prompt-engineering.md](./research/researcher-02-prompt-engineering.md)

**Working Examples:**
- `demo/serial_killers/queries/q1_top_victims.sparql`
- `demo/serial_killers/queries/q5_geographical_patterns.sparql`
- `demo/serial_killers/queries/q6_decade_statistics.sparql`

**Existing Code:**
- `demo/query_generator.py` (has mode='direct' placeholder)
- `demo/serial_killers/prompts/system_prompt_serial_killers.txt` (plan mode reference)

---

## Contact & Questions

**Unresolved Questions:**
1. Should direct mode be default or opt-in? (Recommend: opt-in initially)
2. Token budget acceptable? (~2000 tokens for prompt, fits in 8K context)
3. Multi-hop query support? (Defer to future phase)
4. Auto-fix vs fail-fast? (Recommend: fail-fast for clarity)

**Implementation Notes:**
- Keep changes minimal (YAGNI principle)
- Follow existing code style in query_generator.py
- Prioritize correctness over optimization
- Document all assumptions

---

**Ready for Implementation:** ✅

Start with Phase 1 and proceed sequentially through Phase 4.
