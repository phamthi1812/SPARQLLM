# Implementation Plan: Fix LLM GGF Execution Failures

**Date**: 2025-11-20
**Status**: Ready for execution
**Complexity**: Medium (2 independent bugs, simple fixes)
**Risk Level**: Low (minimal SPARQLLM core changes)

---

## Executive Summary

Two independent bugs prevent LLM-based GGF queries from executing:

1. **Primary Bug - Lazy Evaluation**: Custom evaluator doesn't force BIND evaluation → GGF functions never execute
2. **Secondary Bug - Function Signature**: `LLMGRAPH_OLLAMA` requires 2 args, queries provide 1

**Chosen Strategy**: Hybrid approach combining signature fix (simple/safe) with query workaround (immediate relief).

**Rationale**: Modifying SPARQLLM core evaluator (Strategy 1/2) is complex, risky, breaks YAGNI. Making `uri` parameter optional aligns with other LLM functions (Groq, OpenAI) and is backwards-compatible.

---

## Problem Analysis

### Bug 1: Lazy Evaluation (Root Cause)

**Location**: `SPARQLLM/udf/SPARQLLM.py:37-49`

**Issue**:
- Custom evaluator only intercepts "Join" patterns
- BIND (Extend) patterns evaluate lazily
- If downstream GRAPH clause finds empty graph, join short-circuits before BIND evaluation
- GGF function in BIND never called

**Evidence**:
```python
def customEval(ctx, part):
    if part.name == "Join":
        return my_evaljoin(ctx, part)
    raise NotImplementedError()
```

Only Join is handled; Extend (BIND) patterns not forced to evaluate.

**Query Pattern**:
```sparql
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)  # Never executes
GRAPH ?llmGraph { ... }                       # Empty graph, join aborts
```

### Bug 2: Function Signature Mismatch

**Location**: `SPARQLLM/udf/llmgraph_ollama.py:26`

**Issue**:
```python
def LLMGRAPH_OLLAMA(prompt, uri):  # Requires 2 args
```

**Queries provide 1 arg**:
```sparql
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)  # Only 1 arg
```

**Comparison with other providers**:
- Groq: `def llm_graph_groq(prompt, uri=None, temperature=0.0)` ✓ Optional
- Mistral: `def llm_graph_mistral(prompt, uri)` ✗ Required
- OpenAI: `def llm_graph_openai(prompt, uri)` ✗ Required

**Inconsistency**: Ollama should match Groq's optional `uri` pattern.

---

## Chosen Strategy: Hybrid Approach

### Part A: Fix Function Signature (Primary Fix)
**Type**: Code modification
**Risk**: Low
**Impact**: Fixes Q2, Q3, Q4 immediately

### Part B: Add Evaluation Workaround (Fallback Safety)
**Type**: Query pattern documentation
**Risk**: None
**Impact**: Ensures reliability until core evaluator fixed

### Why NOT Strategy 1/2 (Core Evaluator Changes)?
- Complex: Requires deep RDFlib SPARQL internals knowledge
- Risky: Could break existing queries (Q1, Q5, Q6)
- Violates YAGNI: Over-engineering for 3 failing queries
- Time-sensitive: User needs working demo NOW

---

## Implementation Steps

### Phase 1: Fix Ollama Function Signature

**File**: `SPARQLLM/udf/llmgraph_ollama.py`

**Change 1 - Make uri optional** (Line 26):
```python
# BEFORE
def LLMGRAPH_OLLAMA(prompt, uri):

# AFTER
def LLMGRAPH_OLLAMA(prompt, uri=None):
```

**Change 2 - Handle None uri** (Line 66-67):
```python
# BEFORE
graph_name = prompt + ":" + str(uri)

# AFTER
graph_name = prompt + ":" + str(uri if uri is not None else "default")
```

**Change 3 - Update uri validation** (Line 65):
```python
# BEFORE (implicit assertion via usage)
logger.debug(f"uri: {uri}, Prompt: {prompt[:100]} <...>, ...")

# AFTER
if uri is None:
    uri = URIRef("http://example.org/default-entity")
logger.debug(f"uri: {uri}, Prompt: {prompt[:100]} <...>, ...")
```

**Change 4 - Fix INSERT query** (Line 104-110):
```python
# BEFORE
insert_query_str = f"""
    INSERT  {{
    <{uri}> <http://example.org/has_schema_type> ?subject .}}
        WHERE {{
            ?subject a ?type .
        }}"""

# AFTER
if uri is not None:
    insert_query_str = f"""
        INSERT  {{
        <{uri}> <http://example.org/has_schema_type> ?subject .}}
            WHERE {{
                ?subject a ?type .
            }}"""
    named_graph.update(insert_query_str)
```

**Why these changes?**
- Matches Groq function signature (proven to work)
- Backwards compatible (2-arg calls still work)
- No changes needed to Q2, Q3, Q4 queries

---

### Phase 2: Test Basic Functionality

**Test 1 - Minimal LLM call**:
```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
source venv312_new/bin/activate

python -m SPARQLLM.cli.slm -c config.ini -q '
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <http://schema.org/>
SELECT ?desc WHERE {
  BIND(ggf:SLM-LLMGRAPH("Return JSON-LD: {\"@context\":\"https://schema.org/\",\"@type\":\"Person\",\"description\":\"test methods\"}") AS ?g)
  GRAPH ?g {
    ?p schema:description ?desc
  }
}' --debug
```

**Expected**: Returns `?desc = "test methods"`
**Pass Criteria**: Non-empty result, no TypeError

**Test 2 - Simple demo query**:
```bash
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/test_llm_simple.sparql \
  --debug
```

**Expected**: Returns Ted Bundy info
**Pass Criteria**: Non-empty DataFrame with name/description

---

### Phase 3: Validate Failing Queries

**Test Q2 - Methods by decade**:
```bash
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q2_methods_by_decade.sparql \
  --debug 2>&1 | head -100
```

**Success Criteria**:
- Sees "LLMGRAPH_OLLAMA" execution in debug logs
- Returns DataFrame with columns [decade, name, methods]
- At least 1 row of data (LIMIT 20)

**Test Q3 - Wikipedia summaries**:
```bash
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q3_wikipedia_summary.sparql
```

**Success Criteria**:
- Returns 5 rows (top killers with >150 victims)
- Each row has non-empty summary (500 chars)

**Test Q4 - Extract methods**:
```bash
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q4_extract_methods.sparql
```

**Success Criteria**:
- Returns structured methods (name, tool)
- At least 1 method per killer

---

### Phase 4: Regression Testing

**Test working queries remain functional**:

```bash
# Q1 - Pure CSV (must still work)
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q1_top_victims.sparql

# Q5 - Geographical patterns
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q5_geographical_patterns.sparql

# Q6 - Decade statistics
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q6_decade_statistics.sparql
```

**Pass Criteria**: All return non-empty results matching previous output

---

### Phase 5: Document Workaround (Optional Safety Net)

**If signature fix alone insufficient**, document query workaround:

**File**: `demo/serial_killers/queries/README.md` (create if missing)

**Content**:
```markdown
## Troubleshooting Empty Results

If LLM queries return empty results despite function fix:

### Workaround: Force BIND evaluation

Add FILTER after BIND to force evaluation:

```sparql
# ORIGINAL (may fail)
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)
GRAPH ?llmGraph { ... }

# WORKAROUND (forces evaluation)
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)
FILTER(BOUND(?llmGraph))  # Forces BIND to execute
GRAPH ?llmGraph { ... }
```

This forces SPARQL engine to evaluate BIND before GRAPH clause.
```

**Only create if Phase 3 tests fail after signature fix.**

---

## File Modifications Summary

### Modified Files

1. **`SPARQLLM/udf/llmgraph_ollama.py`**
   - Line 26: Add `=None` default to `uri` parameter
   - Line 65: Add None check, create default URIRef
   - Line 66: Handle None uri in graph name
   - Line 104-110: Conditionally execute INSERT query

### Created Files (Optional)

2. **`demo/serial_killers/queries/README.md`** (only if needed)
   - Document FILTER workaround
   - Explain lazy evaluation issue

### Not Modified

- `SPARQLLM/udf/SPARQLLM.py` - No core evaluator changes
- `config.ini` - No configuration changes
- `demo/serial_killers/queries/*.sparql` - No query modifications

---

## Risk Assessment

### Low Risk (Green)
- Function signature change: Backwards compatible
- Default `uri=None`: Matches Groq pattern
- No SPARQLLM core changes: Won't break other queries

### Medium Risk (Yellow)
- INSERT query conditional: May lose metadata linkage
  - **Mitigation**: Only affects optional `has_schema_type` triple, not core LLM output

### Zero Risk (Blue)
- Query workaround: Pure documentation, no code changes
- Regression tests: Validates no breakage

---

## Rollback Strategy

If implementation breaks something:

### Rollback Step 1: Revert function signature
```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
git diff SPARQLLM/udf/llmgraph_ollama.py
git checkout SPARQLLM/udf/llmgraph_ollama.py
```

### Rollback Step 2: Use query workaround instead
Modify Q2, Q3, Q4 to add `FILTER(BOUND(?llmGraph))` after BIND.

### Rollback Step 3: Test with 2-arg signature
Modify queries to provide 2nd argument:
```sparql
BIND(ggf:SLM-LLMGRAPH(?prompt, <http://example.org/entity>) AS ?llmGraph)
```

---

## Success Criteria

### Must Have (Blocking)
1. ✓ Q2 returns non-empty results (methods by decade)
2. ✓ Q3 returns Wikipedia summaries (5 rows)
3. ✓ Q4 returns structured methods (>= 1 row)
4. ✓ Q1, Q5, Q6 still work (regression test)

### Should Have (Non-blocking)
5. ✓ Debug logs show LLMGRAPH_OLLAMA execution
6. ✓ No TypeError exceptions
7. ✓ Graph URIs generated correctly

### Nice to Have (Future)
8. Core evaluator fix (force BIND evaluation)
9. Unified LLM function signatures across providers
10. Automated test suite for GGF evaluation order

---

## Timeline Estimate

- **Phase 1**: 10 minutes (code changes)
- **Phase 2**: 5 minutes (basic tests)
- **Phase 3**: 10 minutes (validate Q2/Q3/Q4)
- **Phase 4**: 5 minutes (regression Q1/Q5/Q6)
- **Phase 5**: 5 minutes (optional documentation)

**Total**: 30-35 minutes end-to-end

---

## Unresolved Questions

1. **Why does Groq 2-arg signature work?**
   - Need to verify: Does Groq query actually provide 2 args?
   - Check: `queries/` for Groq examples

2. **Should Mistral/OpenAI also get optional uri?**
   - Consistency across providers
   - May be future task

3. **Why doesn't customEval intercept Extend?**
   - RDFlib design decision?
   - Security/performance tradeoff?

4. **Is lazy evaluation intentional?**
   - May be optimization for large graphs
   - Need SPARQLLM author input

---

## Implementation Checklist

Phase 1: Code Changes
- [ ] Modify `llmgraph_ollama.py` line 26 (add `=None`)
- [ ] Add None check at line 65
- [ ] Update graph_name at line 66
- [ ] Conditionalize INSERT query at line 104-110

Phase 2: Basic Testing
- [ ] Run minimal LLM query
- [ ] Run test_llm_simple.sparql
- [ ] Verify no TypeError

Phase 3: Validate Fixes
- [ ] Test Q2 (methods by decade)
- [ ] Test Q3 (Wikipedia summaries)
- [ ] Test Q4 (extract methods)
- [ ] Check debug logs for function execution

Phase 4: Regression Testing
- [ ] Test Q1 (top victims)
- [ ] Test Q5 (geographical patterns)
- [ ] Test Q6 (decade statistics)

Phase 5: Documentation (if needed)
- [ ] Create queries/README.md
- [ ] Document FILTER workaround
- [ ] Update CLAUDE.md if needed

---

## Next Steps After Success

1. **Document findings** in Q2_INVESTIGATION_SUMMARY.md
2. **Consider unified function signature** PR (Mistral/OpenAI)
3. **File issue** for core evaluator lazy evaluation
4. **Create test suite** for GGF evaluation order
5. **Share workaround** in SPARQLLM community

---

## References

- Working Groq signature: `SPARQLLM/udf/llmgraph_groq.py:255`
- Failing queries: `demo/serial_killers/queries/q{2,3,4}_*.sparql`
- Custom evaluator: `SPARQLLM/udf/SPARQLLM.py:37-49`
- Investigation: `Q2_INVESTIGATION_SUMMARY.md`

---

**Plan ready for execution. Awaiting confirmation.**
