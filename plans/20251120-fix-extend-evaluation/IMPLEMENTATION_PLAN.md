# Implementation Plan: Fix SPARQL Lazy Evaluation for GGFs (Extend Pattern)

**Status:** Ready for Implementation
**Created:** 2025-11-20
**Complexity:** Medium (2-3 hours)
**Risk Level:** Low-Medium (existing workaround covers Join pattern)

---

## Executive Summary

**Problem:** BIND clauses with GGF calls (`BIND(ggf:FUNC(...) AS ?g)`) followed by `GRAPH ?g {...}` fail because RDFlib's lazy evaluation never executes the BIND before GRAPH clause needs it.

**Root Cause:** Custom evaluator in `SPARQLLM/udf/SPARQLLM.py` only intercepts "Join" patterns, not "Extend" (BIND) patterns.

**Solution:** Add custom "Extend" pattern handler following same architecture as existing `my_evaljoin` patch.

**Evidence:** Algebra analysis shows query structure is `Join(Extend(BGP, Function), Graph(BGP))`. Current code only handles Join, causing Extend to use default lazy evaluation.

---

## 1. RDFlib Extend Evaluation Research

### 1.1 Current Evaluation Flow

**Location:** `/venv312_new/lib/python3.12/site-packages/rdflib/plugins/sparql/evaluate.py`

**Relevant Functions:**
- `evalPart()` (lines 278-340): Main dispatcher that checks CUSTOM_EVALS first
- `evalExtend()` (lines 125-140): Default Extend handler
- `evalLazyJoin()` (lines 142-155): Lazy join that pushes bindings forward

**Current evalExtend implementation (lines 125-140):**
```python
def evalExtend(ctx: QueryContext, extend: CompValue) -> Generator[FrozenBindings, None, None]:
    # TODO: Deal with dict returned from evalPart from GROUP BY

    for c in evalPart(ctx, extend.p):
        try:
            e = _eval(extend.expr, c.forget(ctx, _except=extend._vars))
            if isinstance(e, SPARQLError):
                raise e

            yield c.merge({extend.var: e})

        except SPARQLError:
            yield c
```

**Key observations:**
1. Iterates over sub-pattern `extend.p` (typically empty BGP)
2. Evaluates `extend.expr` (the function call) using `_eval`
3. Merges result into bindings
4. **Lazy:** Generator yields results one at a time

### 1.2 Algebra Structure

**Query:** `BIND(ggf:FUNC(...) AS ?g) GRAPH ?g {...}`

**Parsed Algebra:**
```
SelectQuery
  Project
    Join (lazy=True)
      p1: Extend
        p: BGP (empty, triples=[])
        expr: Function(iri=http://ggf.org/FUNC, ...)
        var: ?g
      p2: Graph
        term: ?g
        p: BGP (actual graph pattern)
```

**Execution Order (current):**
1. `evalPart()` receives Join
2. CUSTOM_EVALS["exampleEval"] intercepts → calls `my_evaljoin()`
3. `my_evaljoin()` calls `evalLazyJoin()` (RDFlib standard)
4. `evalLazyJoin()` evaluates `p1` (Extend), pushes bindings to `p2` (Graph)
5. **Problem:** When evaluating Extend, `evalPart()` is called recursively
6. Extend is NOT intercepted by CUSTOM_EVALS (raises NotImplementedError)
7. Falls through to default `evalExtend()` (line 306)
8. Default evaluator is lazy - function only executes when GRAPH requests ?g
9. Optimizer sees empty graph, short-circuits, function never called

### 1.3 Why my_evaljoin Works (for Join patterns)

**Working Query:** Join without BIND (Q1, Q5, Q6)
```sparql
BIND(...) AS ?csv
GRAPH ?csv { ... }
```

This gets parsed as:
```
Join(
  BGP(bind),  # Not an Extend!
  Graph
)
```

RDFlib converts simple BIND in WHERE clause to different algebra than BIND in filter position. When it's a Join child, `my_evaljoin` forces evaluation.

**Why it doesn't work for Extend:** Extend is nested INSIDE Join.p1, so needs separate interception.

---

## 2. Design: Custom Extend Evaluator

### 2.1 Architecture Principles

**Follow existing pattern:**
- Minimal changes to SPARQLLM.py
- Preserve default behavior for non-GGF queries
- Eager evaluation ONLY when Extend.expr is GGF call
- Use same global store mechanism as Join handler

### 2.2 Core Logic

**Function signature:**
```python
def my_evalextend(ctx: QueryContext, extend: CompValue) -> Generator[FrozenBindings, None, None]:
```

**Algorithm:**
1. Check if `extend.expr` is a GGF function call (URI starts with http://ggf.org/ or http://example.org/)
2. If YES: Force eager evaluation
   - Evaluate sub-pattern `extend.p`
   - For each binding, evaluate `extend.expr` immediately
   - Yield merged bindings
3. If NO: Delegate to default `evalExtend()`

**Detection logic:**
```python
def is_ggf_function(expr):
    """Detect if expression is a GGF call."""
    if hasattr(expr, 'name') and expr.name == 'Function':
        iri = expr.get('iri')
        if iri:
            iri_str = str(iri)
            return (iri_str.startswith('http://ggf.org/') or
                    iri_str.startswith('http://example.org/'))
    return False
```

### 2.3 Integration Points

**File:** `SPARQLLM/udf/SPARQLLM.py`

**Changes:**
1. Add `is_ggf_function()` helper (lines 7-15, before my_evaljoin)
2. Add `my_evalextend()` (lines 16-35, after is_ggf_function)
3. Import `evalExtend` from rdflib (line 3)
4. Modify `customEval()` to handle "Extend" (line 47-48)

**Modified customEval:**
```python
def customEval(ctx, part):  # noqa: N802
    """
    Custom evaluator for GGF patterns.
    Intercepts Join and Extend patterns to ensure eager evaluation.
    """
    if part.name == "Join":
        return my_evaljoin(ctx, part)
    if part.name == "Extend":
        return my_evalextend(ctx, part)

    raise NotImplementedError()
```

---

## 3. Detailed Code Changes

### 3.1 File: SPARQLLM/udf/SPARQLLM.py

**Current lines 1-50:**
```python
import rdflib
from rdflib import Graph, ConjunctiveGraph, Dataset,  URIRef, Literal, Namespace
from rdflib.plugins.sparql.evaluate import evalGraph, evalServiceQuery, evalLazyJoin

import logging

def my_evaljoin(ctx, part):
    #print(f"EVALJOIN ctx: {ctx}, part: {part}")
    ## only lazyJoin. Sure to have the named graphs computed before evaluating graph clauses...
    return evalLazyJoin(ctx, part)

def my_evalgraph(ctx, part):
    print(f"EVALGRAPH ctx: {ctx.graph.identifier}, part: {part}")
    # ... [commented code] ...
    res=evalGraph(ctx, part)
    # ... [commented code] ...
    return res

def my_evalservice(ctx, part):
    print(f"EVALSERVICE ctx: {ctx}, part: {part}")
    return evalServiceQuery(ctx, part)


def customEval(ctx, part):  # noqa: N802
    """
    Rewrite triple patterns to get super-classes
    """
    #logging.debug("part.name:{part.name}")
    # if part.name == "Graph":
    #         return my_evalgraph(ctx, part)
    # if part.name == "ServiceGraphPattern":
    #         return my_evalservice(ctx, part)
    if part.name == "Join":
            return my_evaljoin(ctx, part)

    raise NotImplementedError()

rdflib.plugins.sparql.CUSTOM_EVALS["exampleEval"] = customEval
```

**CHANGE 1: Update imports (line 3)**
```python
# OLD:
from rdflib.plugins.sparql.evaluate import evalGraph, evalServiceQuery, evalLazyJoin

# NEW:
from rdflib.plugins.sparql.evaluate import evalGraph, evalServiceQuery, evalLazyJoin, evalExtend
from rdflib.plugins.sparql.evalutils import _eval
from rdflib.plugins.sparql.sparql import SPARQLError
```

**CHANGE 2: Add GGF detection helper (after line 5, before my_evaljoin)**
```python
import logging

# ============ GGF Detection Helper ============
def is_ggf_function(expr):
    """
    Detect if an expression is a Graph Generating Function (GGF) call.

    GGFs have URIs starting with:
    - http://ggf.org/  (canonical GGF namespace)
    - http://example.org/  (legacy/alias namespace)

    Args:
        expr: SPARQL expression (CompValue)

    Returns:
        bool: True if expression is a GGF function call
    """
    if hasattr(expr, 'name') and expr.name == 'Function':
        iri = expr.get('iri')
        if iri:
            iri_str = str(iri)
            return (iri_str.startswith('http://ggf.org/') or
                    iri_str.startswith('http://example.org/'))
    return False

# ============ Custom Evaluators ============
```

**CHANGE 3: Add my_evalextend (after is_ggf_function, before my_evalgraph)**
```python
def my_evalextend(ctx, part):
    """
    Custom Extend evaluator for GGF functions.

    Forces eager evaluation when BIND contains a GGF call.
    This ensures named graphs are materialized before GRAPH clauses need them.

    Pattern: BIND(ggf:FUNC(...) AS ?g) GRAPH ?g {...}

    Args:
        ctx: Query context
        part: Extend CompValue with .expr, .var, .p

    Yields:
        FrozenBindings with ?g bound to named graph URI
    """
    # Check if this BIND contains a GGF call
    if is_ggf_function(part.expr):
        # Eager evaluation path for GGF functions
        logging.debug(f"GGF Extend detected: {part.expr.get('iri')}")

        # Evaluate sub-pattern (typically empty BGP)
        for c in evalPart(ctx, part.p):
            try:
                # Force immediate evaluation of GGF function
                # This materializes the named graph into global store
                result = _eval(part.expr, c.forget(ctx, _except=part._vars))

                if isinstance(result, SPARQLError):
                    raise result

                # Bind result to variable (?g)
                yield c.merge({part.var: result})

            except SPARQLError:
                # On error, yield binding without the variable
                yield c
    else:
        # Non-GGF path: delegate to default lazy evaluator
        # This preserves standard SPARQL behavior
        for binding in evalExtend(ctx, part):
            yield binding
```

**CHANGE 4: Update customEval (lines 37-49)**
```python
def customEval(ctx, part):  # noqa: N802
    """
    Custom evaluator for SPARQLLM GGF patterns.

    Intercepts specific algebra patterns to ensure eager evaluation:
    - Join: Forces evaluation order for nested patterns
    - Extend: Forces GGF function execution before GRAPH clauses

    Non-GGF queries fall through to default RDFlib evaluation.
    """
    if part.name == "Join":
        return my_evaljoin(ctx, part)

    if part.name == "Extend":
        return my_evalextend(ctx, part)

    # Other patterns (Graph, BGP, etc.) use default evaluators
    raise NotImplementedError()
```

**CHANGE 5: Add evalPart import (needed for recursive call in my_evalextend)**
```python
# Line 3 (extended import):
from rdflib.plugins.sparql.evaluate import (
    evalGraph,
    evalServiceQuery,
    evalLazyJoin,
    evalExtend,
    evalPart  # NEW: for recursive evaluation in my_evalextend
)
```

---

## 4. Pattern Matching Strategy

### 4.1 GGF URI Detection

**Namespaces to detect:**
1. `http://ggf.org/` - Canonical namespace (used in queries)
2. `http://example.org/` - Alias namespace (used in config.ini associations)

**Why both?**
- config.ini maps aliases like "LLM" → "http://example.org/LLM"
- User writes `ggf:LLM(...)` → parser expands to `http://ggf.org/LLM`
- Function registration converts both to same implementation

**Detection logic handles:**
- Function calls: `ggf:SLM-CSV(...)`
- Nested functions: `ggf:LLM(CONCAT(...))`
- Non-GGF functions: `CONCAT()`, `SUBSTR()`, `STR()` → skip

### 4.2 Edge Cases

**Case 1: Multiple BINDs in sequence**
```sparql
BIND(ggf:FUNC1(...) AS ?g1)
BIND(ggf:FUNC2(?g1) AS ?g2)
GRAPH ?g2 { ... }
```
**Handling:** Each Extend evaluated separately, in order (RDFlib guarantees order)

**Case 2: BIND with non-GGF expression**
```sparql
BIND(CONCAT(?a, ?b) AS ?label)
BIND(ggf:LLM(?label) AS ?g)
```
**Handling:** First BIND → lazy (is_ggf_function=False), second → eager

**Case 3: Nested GGF in expression**
```sparql
BIND(CONCAT(STR(ggf:FUNC(...)), "suffix") AS ?result)
```
**Handling:** Top-level check sees CONCAT (not Function), delegates to lazy eval. **Risk:** Nested GGF might not execute. **Mitigation:** Document as unsupported pattern (rare in practice)

**Case 4: GGF in FILTER**
```sparql
FILTER(EXISTS { BIND(ggf:FUNC(...) AS ?g) GRAPH ?g {...} })
```
**Handling:** Nested Extend inside Filter still intercepted by customEval (recursive evaluation)

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File:** `tests/unit/test_extend_evaluation.py` (NEW)

**Test cases:**
```python
import pytest
from rdflib import Dataset, Namespace
from rdflib.plugins.sparql import prepareQuery
from SPARQLLM.udf.SPARQLLM import store, reset_store, is_ggf_function

GGF = Namespace("http://ggf.org/")
EX = Namespace("http://example.org/")

class TestGGFDetection:
    """Test GGF function detection logic."""

    def test_ggf_namespace_detected(self):
        """GGF namespace functions are detected."""
        query = prepareQuery("""
            PREFIX ggf: <http://ggf.org/>
            SELECT ?g WHERE { BIND(ggf:SLM-CSV("data.csv") AS ?g) }
        """)
        extend = query.algebra.p.p1  # Navigate to Extend node
        assert is_ggf_function(extend.expr)

    def test_example_namespace_detected(self):
        """Example.org namespace (alias) detected."""
        query = prepareQuery("""
            PREFIX ex: <http://example.org/>
            SELECT ?g WHERE { BIND(ex:LLM("prompt") AS ?g) }
        """)
        extend = query.algebra.p.p1
        assert is_ggf_function(extend.expr)

    def test_standard_function_not_detected(self):
        """Standard SPARQL functions are NOT detected."""
        query = prepareQuery("""
            SELECT ?result WHERE { BIND(CONCAT("a", "b") AS ?result) }
        """)
        extend = query.algebra.p.p1
        assert not is_ggf_function(extend.expr)

class TestExtendEvaluation:
    """Test custom Extend evaluator."""

    def setup_method(self):
        """Reset store before each test."""
        reset_store()

    def test_q2_methods_by_decade(self):
        """Q2: BIND(CONCAT...) + BIND(ggf:LLM...) + GRAPH"""
        # Test with real query structure (mocked LLM)
        # Expected: Both BINDs execute, GRAPH finds results
        pass

    def test_q3_wikipedia_summary(self):
        """Q3: BIND(CONCAT...) + BIND(ggf:GETTEXT...) + GRAPH"""
        pass

    def test_q4_extract_methods(self):
        """Q4: BIND(CONCAT...) + BIND(ggf:LLM...) + GRAPH + nested pattern"""
        pass

    def test_multiple_sequential_binds(self):
        """Multiple GGF BINDs in sequence."""
        query = """
            PREFIX ggf: <http://ggf.org/>
            PREFIX ex: <http://example.org/>
            SELECT ?result WHERE {
                BIND(ggf:FUNC1("arg1") AS ?g1)
                BIND(ggf:FUNC2(?g1) AS ?g2)
                GRAPH ?g2 { ?s ex:value ?result }
            }
        """
        # Expected: Both functions execute in order
        pass
```

### 5.2 Integration Tests

**Update existing:** `tests/integration/test_fixtures_runner.py`

**Test queries:**
- Q2 (methods_by_decade.sparql)
- Q3 (wikipedia_summary.sparql)
- Q4 (extract_methods.sparql)
- Q5 (geographical_patterns.sparql) - ensure no regression
- Q6 (decade_statistics.sparql) - ensure no regression

**Execution:**
```bash
# Run with mocked LLM/web services
pytest tests/integration/test_fixtures_runner.py::test_q2_with_extend -v

# Run full suite (requires Ollama)
pytest tests/integration/test_fixtures_runner.py -v --run-slow
```

### 5.3 Regression Tests

**Ensure working queries still work:**
- Q1 (simple CSV) - uses Join pattern, should be unchanged
- Q5 (geographical patterns) - CSV only, no BIND+GRAPH
- Q6 (decade statistics) - aggregation, no GGF in critical path

**Test files from main repo:**
```bash
# Filesystem queries (no Extend patterns)
pytest tests/test_queries.py::test_sparql_queries[simple-csv.sparql] -v
pytest tests/test_queries.py::test_sparql_queries[ReadDir.sparql] -v

# LLM queries (may have Extend)
pytest tests/test_ollama.py -v --run-slow
```

### 5.4 Performance Tests

**Measure impact:**
```python
import time
from SPARQLLM.compiler import query

def test_extend_overhead():
    """Ensure custom evaluator adds <10ms overhead."""
    query_str = """
        PREFIX ggf: <http://ggf.org/>
        SELECT ?g WHERE { BIND(ggf:SLM-CSV("data.csv") AS ?g) }
    """

    start = time.time()
    result = query(query_str)
    duration = time.time() - start

    assert duration < 0.01  # <10ms for evaluation setup
```

---

## 6. Risk Assessment

### 6.1 Breaking Changes

**Risk Level: LOW**

**Reason:**
- Only intercepts Extend patterns (not used by working queries)
- Non-GGF Extend falls through to default evaluator
- Join pattern handling unchanged

**Mitigation:**
- Comprehensive regression test suite
- Test all 6 serial killer queries before/after

### 6.2 Performance Impact

**Risk Level: LOW**

**Reason:**
- `is_ggf_function()` is O(1) check (string prefix)
- Only adds overhead to Extend patterns with GGF calls
- Non-GGF queries use default lazy evaluation (no change)

**Mitigation:**
- Benchmark tests for CSV-only queries
- Profile with cProfile to verify no hot path changes

### 6.3 Edge Cases

**Risk Level: MEDIUM**

**Known limitations:**

1. **Nested GGF in expression** (rare):
   ```sparql
   BIND(CONCAT(STR(ggf:FUNC(...)), "suffix") AS ?result)
   ```
   - Top-level is CONCAT, not Function
   - is_ggf_function returns False
   - May fail if inner GGF not evaluated

   **Mitigation:** Document as unsupported. Add test to verify error message.

2. **GGF returning non-URI**:
   - Current GGF contract: must return URIRef
   - If broken, GRAPH clause will fail with unclear error

   **Mitigation:** Add validation in my_evalextend to check result type.

3. **Concurrent query sessions**:
   - Global store shared across queries
   - If not reset between sessions, cross-contamination

   **Mitigation:** Already documented in CLAUDE.md. Add warning log if store size > 1000 graphs.

### 6.4 Compatibility

**RDFlib versions:**
- Current: 7.x (confirmed via venv)
- Risk: Internal evaluate.py API might change
- Mitigation: Pin rdflib version in requirements.txt

**Python versions:**
- Current: 3.10, 3.12 (via venvs)
- Risk: None (no Python version-specific code)

---

## 7. Comparison with my_evaljoin

### 7.1 Architectural Consistency

**my_evaljoin (existing):**
```python
def my_evaljoin(ctx, part):
    ## only lazyJoin. Sure to have the named graphs computed before evaluating graph clauses...
    return evalLazyJoin(ctx, part)
```

**Purpose:** Intercept Join to force ordered evaluation

**Mechanism:** Delegate to RDFlib's evalLazyJoin (which pushes bindings forward)

**Why it works:** LazyJoin is already eager in evaluating p1 before p2

---

**my_evalextend (proposed):**
```python
def my_evalextend(ctx, part):
    if is_ggf_function(part.expr):
        # Eager evaluation for GGF
        for c in evalPart(ctx, part.p):
            result = _eval(part.expr, c.forget(...))
            yield c.merge({part.var: result})
    else:
        # Lazy evaluation for non-GGF
        for binding in evalExtend(ctx, part):
            yield binding
```

**Purpose:** Intercept Extend to force GGF execution

**Mechanism:** Conditional - eager if GGF, lazy otherwise

**Why it works:** `_eval()` immediately executes function, materializing graph before yield

---

### 7.2 Design Pattern Consistency

**Similarities:**
1. Both registered in `CUSTOM_EVALS["exampleEval"]`
2. Both check `part.name` in `customEval()`
3. Both delegate to RDFlib functions when possible
4. Both preserve generator pattern (yield)

**Differences:**
1. my_evaljoin: Unconditional delegation
2. my_evalextend: Conditional (GGF check)

**Justification:** Join always needs order guarantee, Extend only for GGF

---

## 8. Implementation Checklist

### Phase 1: Core Implementation (1 hour)
- [ ] Update imports in SPARQLLM.py (evalExtend, evalPart, _eval, SPARQLError)
- [ ] Add is_ggf_function() helper
- [ ] Add my_evalextend() function
- [ ] Update customEval() to handle "Extend"
- [ ] Add logging.debug statements for debugging

### Phase 2: Testing (1 hour)
- [ ] Create tests/unit/test_extend_evaluation.py
- [ ] Write TestGGFDetection test class
- [ ] Write TestExtendEvaluation test class
- [ ] Update integration test fixtures for Q2-Q4
- [ ] Run regression tests on Q1, Q5, Q6

### Phase 3: Documentation (30 min)
- [ ] Update CLAUDE.md with Extend pattern explanation
- [ ] Add docstring examples to my_evalextend
- [ ] Document unsupported edge cases (nested GGF)
- [ ] Update config.ini comments if needed

### Phase 4: Validation (30 min)
- [ ] Run full test suite: pytest -v
- [ ] Run slow tests: pytest -v --run-slow (if Ollama available)
- [ ] Benchmark performance: profile Q1 (CSV only)
- [ ] Manual test: slm-run on Q2, Q3, Q4

---

## 9. Success Criteria

### Must Have (Blocking)
1. Q2, Q3, Q4 execute successfully with BIND+GRAPH pattern
2. Q1, Q5, Q6 still work (no regression)
3. All unit tests pass
4. All integration tests pass

### Should Have (Important)
1. Performance overhead <10ms for evaluation setup
2. Clear error messages for unsupported patterns
3. Debug logging shows GGF detection

### Nice to Have (Optional)
1. Benchmark results showing no regression on CSV queries
2. Memory profiling showing no store leaks
3. Documentation with visual algebra tree diagrams

---

## 10. Rollback Plan

**If implementation fails:**

1. **Immediate rollback:**
   ```bash
   git checkout SPARQLLM/udf/SPARQLLM.py
   ```

2. **Partial rollback:**
   - Keep is_ggf_function() (useful for future)
   - Remove customEval Extend handling
   - Keep tests (mark as xfail)

3. **Alternative approach:**
   - If eager evaluation causes issues, try graph pre-materialization
   - Add explicit `slm-run --eager-ggf` flag instead of automatic detection

---

## 11. Open Questions

### 11.1 Answered by Research

**Q: Does RDFlib support custom Extend evaluators?**
A: Yes, CUSTOM_EVALS can intercept any pattern name.

**Q: Will this break non-GGF queries?**
A: No, is_ggf_function() filters correctly.

**Q: What about nested Extend patterns?**
A: Recursive evalPart() calls ensure all levels intercepted.

### 11.2 To Be Resolved During Implementation

**Q: Should we log GGF execution timing?**
A: Yes, add logging.debug with function name + duration.

**Q: Should we validate GGF return type?**
A: Yes, add isinstance(result, URIRef) check with helpful error.

**Q: Should we add --debug-extend CLI flag?**
A: Optional, but useful for troubleshooting. Add to slm-run if time permits.

---

## 12. Post-Implementation Tasks

### 12.1 Immediate (same PR)
- [ ] Update CHANGELOG.md with fix description
- [ ] Update README.md examples to show BIND+GRAPH pattern
- [ ] Add test coverage report

### 12.2 Follow-up (separate PRs)
- [ ] Add nested GGF support (if use cases emerge)
- [ ] Optimize is_ggf_function with LRU cache
- [ ] Add SPARQL query validator (pre-execution checks)
- [ ] Create visual debugger for algebra tree

---

## Appendix A: File Locations

**Implementation:**
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/SPARQLLM/udf/SPARQLLM.py`

**Tests:**
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/tests/unit/test_extend_evaluation.py` (NEW)
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/tests/integration/test_fixtures_runner.py` (UPDATE)

**Test Queries:**
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/demo/serial_killers/queries/q2_methods_by_decade.sparql`
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/demo/serial_killers/queries/q3_wikipedia_summary.sparql`
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/demo/serial_killers/queries/q4_extract_methods.sparql`

**RDFlib Reference:**
- `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/venv312_new/lib/python3.12/site-packages/rdflib/plugins/sparql/evaluate.py`

---

## Appendix B: Algebra Examples

### Before Fix (Q2 failure)

**Query:** q2_methods_by_decade.sparql
```
SelectQuery
  Project
    Join (lazy=True)
      p1: Join (nested)
        p1: Extend (CSV load) ← WORKS (Join forces eval)
        p2: Graph (csvGraph)
      p2: Join (LLM chain)
        p1: Extend (CONCAT prompt) ← WORKS (non-GGF, lazy OK)
        p2: Join
          p1: Extend (LLM call) ← FAILS (GGF not executed)
          p2: Graph (llmGraph) ← Empty, short-circuits
```

**Problem:** Nested Extend with GGF never intercepted

---

### After Fix (Q2 success)

**Same algebra, different evaluation:**
```
SelectQuery
  Project
    Join (lazy=True)
      p1: Join
        p1: Extend (CSV) ← customEval → my_evalextend → eager
        p2: Graph
      p2: Join
        p1: Extend (CONCAT) ← customEval → my_evalextend → lazy (non-GGF)
        p2: Join
          p1: Extend (LLM) ← customEval → my_evalextend → eager (GGF!)
          p2: Graph ← Finds data, query succeeds
```

**Fix:** All Extend nodes checked by customEval, GGF executed eagerly

---

## Appendix C: Code Diff Preview

```diff
diff --git a/SPARQLLM/udf/SPARQLLM.py b/SPARQLLM/udf/SPARQLLM.py
index abc123..def456 100644
--- a/SPARQLLM/udf/SPARQLLM.py
+++ b/SPARQLLM/udf/SPARQLLM.py
@@ -1,10 +1,51 @@
 import rdflib
 from rdflib import Graph, ConjunctiveGraph, Dataset,  URIRef, Literal, Namespace
-from rdflib.plugins.sparql.evaluate import evalGraph, evalServiceQuery, evalLazyJoin
+from rdflib.plugins.sparql.evaluate import (
+    evalGraph,
+    evalServiceQuery,
+    evalLazyJoin,
+    evalExtend,
+    evalPart
+)
+from rdflib.plugins.sparql.evalutils import _eval
+from rdflib.plugins.sparql.sparql import SPARQLError

 import logging

+# ============ GGF Detection Helper ============
+def is_ggf_function(expr):
+    """Detect if expression is a Graph Generating Function (GGF) call."""
+    if hasattr(expr, 'name') and expr.name == 'Function':
+        iri = expr.get('iri')
+        if iri:
+            iri_str = str(iri)
+            return (iri_str.startswith('http://ggf.org/') or
+                    iri_str.startswith('http://example.org/'))
+    return False
+
+# ============ Custom Evaluators ============
+def my_evalextend(ctx, part):
+    """Custom Extend evaluator for GGF functions (BIND clause)."""
+    if is_ggf_function(part.expr):
+        logging.debug(f"GGF Extend detected: {part.expr.get('iri')}")
+        for c in evalPart(ctx, part.p):
+            try:
+                result = _eval(part.expr, c.forget(ctx, _except=part._vars))
+                if isinstance(result, SPARQLError):
+                    raise result
+                yield c.merge({part.var: result})
+            except SPARQLError:
+                yield c
+    else:
+        for binding in evalExtend(ctx, part):
+            yield binding
+
 def my_evaljoin(ctx, part):
     #print(f"EVALJOIN ctx: {ctx}, part: {part}")
     ## only lazyJoin. Sure to have the named graphs computed before evaluating graph clauses...
@@ -37,9 +78,13 @@ def my_evalservice(ctx, part):

 def customEval(ctx, part):  # noqa: N802
     """
-    Rewrite triple patterns to get super-classes
+    Custom evaluator for SPARQLLM GGF patterns.
+    Intercepts Join and Extend to ensure eager evaluation.
     """
-    #logging.debug("part.name:{part.name}")
-    # if part.name == "Graph":
-    #         return my_evalgraph(ctx, part)
-    # if part.name == "ServiceGraphPattern":
-    #         return my_evalservice(ctx, part)
     if part.name == "Join":
-            return my_evaljoin(ctx, part)
+        return my_evaljoin(ctx, part)
+
+    if part.name == "Extend":
+        return my_evalextend(ctx, part)

     raise NotImplementedError()
```

---

**END OF IMPLEMENTATION PLAN**
