# Implementation Plan: LLM Direct SPARQL Generation

**Date:** 2025-11-21
**Status:** Ready for Implementation
**Complexity:** Medium (4 phases)

---

## Context

**Current Architecture:** LLM → JSON plan → PhysicalCompiler → SPARQL (has bugs)
**Target Architecture:** LLM → SPARQL directly (bypass compiler)

**Motivation:** PhysicalCompiler has bugs with variable bindings/filters. Working SPARQL queries exist in `demo/serial_killers/queries/*.sparql`. User wants LLM to generate SPARQL directly like those working examples.

**Research Reports:**
- [Direct SPARQL Generation Analysis](./research/researcher-01-direct-sparql-generation.md)
- [Prompt Engineering Strategy](./research/researcher-02-prompt-engineering.md)

---

## Key Insights

1. **Infrastructure Ready:** `mode='direct'` placeholder exists in query_generator.py L408
2. **Working Examples Available:** 6 validated queries in demo/serial_killers/queries/
3. **Pattern Identified:** `BIND(ggf:FUNCTION(...) AS ?g)` + `GRAPH ?g { patterns }`
4. **Validation Needed:** SPARQL syntax validation before execution (rdflib parser)
5. **Prompt Strategy:** 5-8 examples + explicit GGF syntax rules + error prevention

---

## Requirements

### Functional
- Generate valid SPARQL with GGFs from natural language questions
- Support CSV (SLM-CSV), LLM (SLM-LLM), web (SLM-SPARQL) data sources
- Handle filters (FILTER), ordering (ORDER BY), aggregations (GROUP BY)
- Validate SPARQL syntax before execution
- Maintain backward compatibility with plan mode

### Non-Functional
- <200ms prompt construction overhead
- 90%+ valid SPARQL generation rate (after prompt optimization)
- Minimal changes to existing codebase
- Clear error messages for syntax/semantic issues

---

## Architecture

### New Components
```
demo/serial_killers/prompts/
├── direct_system_prompt.txt          [NEW] SPARQL-focused prompt (150-200 lines)

SPARQLLM/compiler/
├── sparql_validator.py               [NEW] Syntax/semantic validation (80-100 lines)

demo/
├── query_generator.py                [MODIFY] Add generate_sparql() method
```

### Data Flow
```
User Question
    ↓
QueryGenerator(mode='direct')
    ↓
Load direct_system_prompt.txt + inject examples
    ↓
LLM generates SPARQL string
    ↓
Strip markdown fences (```sparql)
    ↓
SPARQLValidator.validate()
    ↓
Return validated SPARQL or error
```

---

## Implementation Phases

### Phase 1: System Prompt Creation
**File:** `demo/serial_killers/prompts/direct_system_prompt.txt`
**Lines:** ~150-200

**Structure:**
1. Role definition (query generator for serial killers dataset)
2. GGF catalog (CSV, LLM, web sources with syntax)
3. SPARQL syntax rules (PREFIX, BIND, GRAPH, FILTER)
4. 6 annotated examples from demo/serial_killers/queries/
5. Column mapping (CSV headers → ex:property URIs)
6. Error prevention (common mistakes + fixes)
7. Output format (SPARQL only, no markdown)

**Key Sections:**
```
# GGF Syntax
BIND(ggf:SLM-CSV("path") AS ?g)
GRAPH ?g { ?row ex:column_name ?var . }

# Examples (from queries/)
[q1_top_victims.sparql - basic aggregation]
[q5_geographical_patterns.sparql - FILTER with CONTAINS]
[q6_decade_statistics.sparql - GROUP BY with aggregations]
[+ 3 more]

# Rules
- Use ex: prefix for CSV columns
- All variables in FILTER must be bound
- ORDER BY/LIMIT for ranking questions
```

---

### Phase 2: Query Generator Modification
**File:** `demo/query_generator.py`

**Changes:**
1. Implement mode='direct' branch in `__init__` (L408-420)
2. Add `generate_sparql(question, context)` method
3. Load direct_system_prompt.txt
4. Call LLM with SPARQL-focused prompt
5. Strip markdown code fences
6. Return raw SPARQL string

**Code Snippet:**
```python
def generate_sparql(self, question: str, context: dict = None) -> str:
    """Generate SPARQL directly (mode='direct')."""
    # Load prompt
    prompt_path = "demo/serial_killers/prompts/direct_system_prompt.txt"
    with open(prompt_path) as f:
        system_prompt = f.read()

    # Build user message
    user_msg = f"Question: {question}"
    if context:
        user_msg += f"\nContext: {json.dumps(context)}"

    # Call LLM
    response = self.llm.generate(system_prompt, user_msg)

    # Strip markdown
    sparql = response.strip()
    if sparql.startswith("```sparql"):
        sparql = sparql.split("```sparql")[1].split("```")[0]
    elif sparql.startswith("```"):
        sparql = sparql.split("```")[1].split("```")[0]

    return sparql.strip()
```

---

### Phase 3: Validation Layer
**File:** `SPARQLLM/compiler/sparql_validator.py` [NEW]

**Responsibilities:**
1. Syntax validation (rdflib parser)
2. Semantic validation (GGF names in catalog)
3. Variable binding checks (unbound variables in FILTER)
4. Provide actionable error messages

**Code Structure:**
```python
from rdflib.plugins.sparql import prepareQuery

class SPARQLValidator:
    def __init__(self, catalog):
        self.catalog = catalog  # GGF metadata

    def validate(self, sparql: str) -> tuple[bool, str]:
        """Returns (is_valid, error_message)."""
        # 1. Syntax check
        try:
            prepareQuery(sparql)
        except Exception as e:
            return False, f"Syntax error: {e}"

        # 2. GGF existence check
        ggf_pattern = r'ggf:([A-Z-]+)\('
        for match in re.findall(ggf_pattern, sparql):
            if match not in self.catalog:
                return False, f"Unknown GGF: {match}"

        # 3. Variable binding check (basic heuristic)
        # Extract FILTER variables, check they're in GRAPH patterns
        # [Implementation omitted for brevity]

        return True, ""
```

---

### Phase 4: Testing & Integration
**File:** `demo/serial_killers/demo_nl_to_sparql.py` [MODIFY]

**Test Cases:**
1. **Basic CSV query:** "Top 10 serial killers by victim count"
2. **Filtered query:** "Serial killers with more than 50 victims"
3. **Pattern matching:** "Killers who operated in multiple countries"
4. **Aggregation:** "How many killers per decade?"
5. **Complex filter:** "American killers active in the 1980s"

**Integration Steps:**
1. Add `--mode=direct` CLI flag to demo script
2. Call `generator.generate_sparql(question)` instead of `generate_query()`
3. Pass SPARQL to `SPARQLValidator.validate()`
4. Execute via `slm-run` if valid
5. Compare results with ground truth (demo/serial_killers/ground_truth/)

**Success Metrics:**
- 5/5 test cases generate valid SPARQL
- 4/5 test cases produce correct results
- Validation catches at least 1 intentional error

---

## Code Files Summary

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| direct_system_prompt.txt | NEW | 150-200 | SPARQL-focused prompt with examples |
| sparql_validator.py | NEW | 80-100 | Syntax/semantic validation |
| query_generator.py | MODIFY | +50-80 | Add generate_sparql() method |
| demo_nl_to_sparql.py | MODIFY | +20-30 | Add direct mode CLI flag |

**Total LOC:** ~250-350 new lines

---

## Success Criteria

1. ✅ LLM generates syntactically valid SPARQL (rdflib parses without errors)
2. ✅ Generated queries use correct GGF syntax (BIND + GRAPH patterns)
3. ✅ Queries execute successfully via slm-run
4. ✅ Results match ground truth for 4/5 test cases
5. ✅ Validation layer catches at least 3 error types (syntax, unknown GGF, unbound var)
6. ✅ Backward compatibility: plan mode still works

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM generates invalid SPARQL | Medium | High | Validation layer + 5-8 examples in prompt |
| Variable binding errors | Medium | Medium | Explicit rules in prompt + validator checks |
| Prompt too long (token limit) | Low | Medium | Keep examples concise, inline comments |
| Regression in plan mode | Low | High | Don't modify plan mode logic, only add direct |
| GGF catalog changes break prompt | Low | Medium | Use minimal GGF list, document update process |

---

## Unresolved Questions

1. Should direct mode be default or opt-in? (Recommend opt-in initially)
2. How to handle multi-hop queries (LLM → CSV chaining)? (Defer to Phase 5)
3. Should validator auto-fix common errors (e.g., missing PREFIX)? (No, fail fast)
4. Token budget for prompt with 6 examples? (~2000 tokens, acceptable for 8K context models)

---

## Next Steps

1. Create detailed phase plans (phase-01-*.md, phase-02-*.md, ...)
2. Implement Phase 1 (system prompt) first
3. Test prompt in isolation (manual LLM calls)
4. Proceed to Phase 2-4 sequentially
5. Document findings in implementation report

---

**References:**
- Research: [researcher-01](./research/researcher-01-direct-sparql-generation.md), [researcher-02](./research/researcher-02-prompt-engineering.md)
- Working examples: demo/serial_killers/queries/*.sparql
- Existing prompt: demo/serial_killers/prompts/system_prompt_serial_killers.txt
