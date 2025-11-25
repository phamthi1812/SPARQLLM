# PhysicalCompiler Bug Investigation Report

**Date:** 2025-11-21
**Investigator:** Debug Agent
**Status:** Root Cause Identified
**Priority:** Critical (Blocks NL-to-SPARQL Pipeline)

---

## Executive Summary

**Problem:** PhysicalCompiler generates incorrect SPARQL from valid JSON plans, causing query execution failures.

**Impact:** LLM successfully generates correct JSON plans, but compiler breaks them with wrong predicates, double-wrapped filters, and incorrect subject patterns.

**Root Cause:** Hardcoded pattern generation logic in `_generate_graph()` method doesn't match actual CSV GGF output structure.

**Recommendation:** Fix binding translation to use `?row ex:{column_name} ?var` pattern and unwrap pre-formatted filters.

---

## Bug Analysis

### Test Case Context

**Input JSON Plan:**
```json
{
  "steps": [{
    "id": "step1",
    "operation": "read_filesystem",
    "ggf": {"name": "SLM-CSV", "args": {"file": "..."}},
    "bindings": {
      "name": "?name",
      "victim_min": "?victim_min"
    },
    "filters": ["FILTER(?victim_min > 50)"]
  }]
}
```

**Expected SPARQL:**
```sparql
GRAPH ?csvGraph {
    ?row ex:name ?name .
    ?row ex:victim_min ?victim_min .
}
FILTER(?victim_min > 50)
```

**Actual (Broken) SPARQL:**
```sparql
GRAPH ?step1Graph {
    ?item schema:value ?name .
    ?item schema:value ?victim_min .
    FILTER(FILTER(?victim_min > 50))
}
```

---

## Root Cause #1: Wrong Predicates

### Location
**File:** `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/SPARQLLM/compiler/physical_compiler.py`
**Method:** `_generate_graph()`, Lines 211-223

### Code Snippet
```python
if operation == "read_filesystem":
    # Filesystem operations typically return file/directory metadata
    if bindings:
        for semantic_name, sparql_var in bindings.items():
            if 'file' in semantic_name.lower() or 'path' in semantic_name.lower():
                patterns.append(f"?item schema:contentUrl {sparql_var} .")
            elif 'content' in semantic_name.lower():
                patterns.append(f"?item schema:text {sparql_var} .")
            else:
                patterns.append(f"?item schema:value {sparql_var} .")  # ← BUG HERE
    else:
        patterns.append("?item ?p ?o .")
```

### Problem
- Line 220 generates: `?item schema:value ?name`
- Should generate: `?row ex:name ?name`
- All bindings fall through to generic `schema:value` predicate
- Column names like `name`, `victim_min` don't match hardcoded keywords (`file`, `path`, `content`)

### Evidence from Working Queries
**Ground Truth Query (gt_05_high_victims.sparql):**
```sparql
GRAPH ?csvGraph {
    ?row ex:name ?name .
    ?row ex:victim_min ?victim_min .
    ?row ex:country ?country .
}
```

**Company Demo (example_join.sparql):**
```sparql
GRAPH ?empGraph {
    ?emp ex:name ?employee_name .
    ?emp ex:salary ?salary .
    ?emp ex:department_id ?dept_id .
}
```

**Pattern:** CSV rows use `?row` (or `?emp`, `?dept`) as subject and `ex:{column_name}` as predicate.

### Why This Fails
1. **Wrong Subject:** Uses `?item` instead of `?row`
2. **Wrong Predicate:** Uses generic `schema:value` instead of specific `ex:{column_name}`
3. **Name Collision:** All columns map to same predicate (`schema:value`), making them indistinguishable
4. **RDF Mismatch:** SLM-CSV GGF generates `ex:` predicates, not `schema:` predicates

---

## Root Cause #2: Double FILTER Wrapping

### Location
**File:** `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/SPARQLLM/compiler/physical_compiler.py`
**Method:** `_generate_graph()`, Line 272

### Code Snippet
```python
# Add filters
filter_clauses = [f"FILTER({f})" for f in filters]  # ← BUG HERE
```

### Problem
- Input: `filters = ["FILTER(?victim_min > 50)"]` (already has FILTER keyword)
- Line 272 wraps it: `f"FILTER({f})"` → `"FILTER(FILTER(?victim_min > 50))"`
- Result: Invalid SPARQL with double FILTER

### Evidence
**Input (from JSON plan):**
```json
"filters": ["FILTER(?victim_min > 50)"]
```

**Generated:**
```sparql
FILTER(FILTER(?victim_min > 50))  # Invalid!
```

**Expected:**
```sparql
FILTER(?victim_min > 50)  # Valid
```

### Why This Happens
- LLM generates filters with `FILTER()` keyword (correct SPARQL syntax)
- Compiler assumes filters are bare expressions and wraps them again
- No check for existing `FILTER()` keyword

---

## Root Cause #3: Wrong Subject Pattern

### Location
**File:** `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/SPARQLLM/compiler/physical_compiler.py`
**Method:** `_generate_graph()`, Line 220

### Code Snippet
```python
patterns.append(f"?item schema:value {sparql_var} .")  # ← BUG: ?item
```

### Problem
- Generates: `?item schema:value ?name`
- Should generate: `?row ex:name ?name`
- Subject variable name matters for CSV row semantics

### Evidence
All working CSV queries use `?row` (or semantically named variables like `?emp`, `?dept`):

**Pattern 1 (Serial Killers):**
```sparql
?row ex:name ?name .
?row ex:victim_min ?victim_min .
```

**Pattern 2 (Employees):**
```sparql
?emp ex:name ?employee_name .
?emp ex:salary ?salary .
```

**Pattern 3 (Departments):**
```sparql
?dept ex:department_id ?dept_id .
?dept ex:department_name ?department_name .
```

### Why ?row Not ?item
- CSV rows are entities (people, companies, departments)
- `?row` represents one row in the CSV table
- `?item` is generic file system object (misleading semantics)
- RDF structure: each row becomes a subject with column predicates

---

## Additional Context: How SLM-CSV GGF Works

### RDF Structure Generated by SLM-CSV
```turtle
# For each CSV row, SLM-CSV generates:
<http://example.org/row/1> ex:name "Ted Bundy" .
<http://example.org/row/1> ex:country "USA" .
<http://example.org/row/1> ex:victim_min "30" .

<http://example.org/row/2> ex:name "Harold Shipman" .
<http://example.org/row/2> ex:country "UK" .
<http://example.org/row/2> ex:victim_min "218" .
```

### Correct SPARQL Pattern
```sparql
GRAPH ?csvGraph {
    ?row ex:name ?name .          # Match specific column
    ?row ex:victim_min ?victim_min .
}
```

### Current Broken Pattern
```sparql
GRAPH ?step1Graph {
    ?item schema:value ?name .    # Wrong predicate (no column distinction)
    ?item schema:value ?victim_min .  # Same predicate for all columns!
}
```

**Why This Breaks:**
- Both `?name` and `?victim_min` match the same triple pattern
- Query returns garbage or empty results
- RDF database can't distinguish between columns

---

## Proposed Fix (DO NOT IMPLEMENT)

### Fix #1: Correct Binding Translation
**Location:** `_generate_graph()`, Lines 211-223

**Current (Wrong):**
```python
if operation == "read_filesystem":
    if bindings:
        for semantic_name, sparql_var in bindings.items():
            if 'file' in semantic_name.lower() or 'path' in semantic_name.lower():
                patterns.append(f"?item schema:contentUrl {sparql_var} .")
            elif 'content' in semantic_name.lower():
                patterns.append(f"?item schema:text {sparql_var} .")
            else:
                patterns.append(f"?item schema:value {sparql_var} .")
```

**Proposed (Correct):**
```python
if operation == "read_filesystem":
    if bindings:
        subject_var = "?row"  # Use ?row for CSV rows
        for semantic_name, sparql_var in bindings.items():
            # Map bindings to column-specific predicates
            predicate = f"ex:{semantic_name}"
            patterns.append(f"{subject_var} {predicate} {sparql_var} .")
```

**Result:**
```sparql
?row ex:name ?name .
?row ex:victim_min ?victim_min .
?row ex:country ?country .
```

---

### Fix #2: Unwrap Pre-Formatted Filters
**Location:** `_generate_graph()`, Line 272

**Current (Wrong):**
```python
filter_clauses = [f"FILTER({f})" for f in filters]
```

**Proposed (Correct):**
```python
# Filters may already have FILTER() keyword from LLM
filter_clauses = []
for f in filters:
    if f.strip().startswith("FILTER"):
        filter_clauses.append(f)  # Already formatted
    else:
        filter_clauses.append(f"FILTER({f})")  # Wrap bare expression
```

**Result:**
```sparql
FILTER(?victim_min > 50)  # Correct
```

---

### Fix #3: Use Semantic Subject Variables
**Location:** `_generate_graph()`, throughout method

**Enhancement:** Infer subject variable name from operation type:
```python
if operation == "read_filesystem":
    subject_var = "?row"  # CSV rows
elif operation == "web_search":
    subject_var = "?result"  # Search results
elif operation == "llm_extract":
    subject_var = "?entity"  # Extracted entities
else:
    subject_var = "?item"  # Fallback
```

---

## Testing Recommendations

### Test Case 1: Simple Bindings
**Input JSON:**
```json
{
  "steps": [{
    "operation": "read_filesystem",
    "bindings": {"name": "?name", "country": "?country"}
  }]
}
```

**Expected SPARQL:**
```sparql
?row ex:name ?name .
?row ex:country ?country .
```

---

### Test Case 2: Pre-Formatted Filters
**Input JSON:**
```json
{
  "filters": ["FILTER(?victim_min > 50)"]
}
```

**Expected SPARQL:**
```sparql
FILTER(?victim_min > 50)
```

**NOT:**
```sparql
FILTER(FILTER(?victim_min > 50))
```

---

### Test Case 3: Bare Filters (Legacy Support)
**Input JSON:**
```json
{
  "filters": ["?victim_min > 50"]
}
```

**Expected SPARQL:**
```sparql
FILTER(?victim_min > 50)
```

---

## Impact Assessment

### Severity: CRITICAL
- **Pipeline Blocked:** LLM generates correct plans but compiler breaks them
- **Success Rate:** 0% (all generated queries fail)
- **User Impact:** NL-to-SPARQL feature unusable

### Scope
**Affected Operations:**
- `read_filesystem` (CSV files) - HIGH PRIORITY
- `web_search` (may have similar issues)
- `llm_extract` (may have similar issues)

**Working Operations:**
- Manual SPARQL queries (bypass compiler)
- Ground truth queries (handwritten)

### Dependencies
**Downstream:**
- Demo pipeline (`demo_nl_to_sparql.py`)
- Query generator (`query_generator.py`)
- Integration tests

**Upstream:**
- LLM prompt system (working correctly)
- JSON plan generation (working correctly)

---

## Files to Modify

1. **Primary Fix:**
   - `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/SPARQLLM/compiler/physical_compiler.py`
     - Method: `_generate_graph()` (lines 211-280)
     - Changes: Binding translation, filter handling, subject variables

2. **Test Coverage:**
   - Create: `tests/unit/test_physical_compiler_bindings.py`
   - Create: `tests/unit/test_physical_compiler_filters.py`
   - Update: `tests/integration/test_nl_to_sparql_pipeline.py`

3. **Documentation:**
   - Update: `docs/compiler-design.md` (binding rules)
   - Update: `docs/logical-plan-schema.md` (filter format)

---

## Comparison: Expected vs Actual

| Aspect | Expected (Correct) | Actual (Broken) | Status |
|--------|-------------------|-----------------|--------|
| Subject Variable | `?row` | `?item` | ❌ Wrong |
| Predicate Pattern | `ex:name` | `schema:value` | ❌ Wrong |
| Filter Wrapping | `FILTER(expr)` | `FILTER(FILTER(expr))` | ❌ Double |
| Column Distinction | Each column unique | All columns same | ❌ Collision |
| RDF Compatibility | Matches GGF output | Mismatches GGF | ❌ Incompatible |

---

## Unresolved Questions

1. **Other Operations:** Do `web_search`, `llm_extract`, `vector_search` have same binding bugs?
2. **Backward Compatibility:** Will fixing this break existing manual queries?
3. **GGF Contract:** Is there documented spec for RDF structure each GGF returns?
4. **Filter Format:** Should LLM generate bare expressions or full FILTER() statements?
5. **Subject Naming:** Should compiler infer semantic names (`?emp`, `?dept`) or always use `?row`?

---

## Next Steps

1. **Implement Fix #1** (Binding Translation) - Highest priority
2. **Implement Fix #2** (Filter Handling) - High priority
3. **Add Unit Tests** - Cover all binding scenarios
4. **Test End-to-End** - Run full NL-to-SPARQL pipeline
5. **Document GGF Contract** - Specify RDF structure expectations

---

## Conclusion

**Root Cause Confirmed:** PhysicalCompiler's `_generate_graph()` method uses hardcoded pattern matching that doesn't align with actual CSV GGF output.

**Fix Complexity:** LOW (single method, ~30 lines)

**Testing Required:** HIGH (affects all generated queries)

**Recommendation:** Apply fixes incrementally with test coverage at each step.

---

**Investigation Complete.**
**Status:** Ready for Implementation
**Blocking:** NL-to-SPARQL Demo, LLM Pipeline
**Priority:** Critical - Fix Required for Feature to Work
