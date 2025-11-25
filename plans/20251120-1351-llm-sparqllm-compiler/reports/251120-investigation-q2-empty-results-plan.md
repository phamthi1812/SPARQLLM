# Q2 Empty Results Investigation Plan

**Date**: 2025-11-20
**Investigator**: Claude Code Debugging Agent
**Issue**: Q2 query returns empty DataFrame despite successful execution
**Query**: `demo/serial_killers/queries/q2_methods_by_decade.sparql`

---

## Executive Summary

Q2 executes without errors but returns 0 results. The query:
1. Loads CSV via `ggf:SLM-CSV` (proven working in Q1)
2. Filters for specific decades (1970s-2000s)
3. Calls `ggf:SLM-LLMGRAPH` with JSON-LD prompt
4. Expects LLM to return graph with `schema:Person` + `schema:description`

**Hypothesis**: Either:
- LLM not being called (lazy evaluation issue)
- LLM returns invalid/unexpected JSON-LD format
- SPARQL pattern mismatch between LLM output and query expectations
- Graph materialization timing issue

---

## Investigation Approach

### Phase 1: Environment Verification
**Goal**: Confirm all prerequisites are met

1. **Python Environment**
   - Check venv activation (venv312_new or venv312)
   - Verify html2text dependency (current blocker)
   - Confirm SPARQLLM installed in editable mode

2. **Ollama Server**
   - Verify server running at `http://localhost:11434`
   - Check qwen2.5:3b model availability
   - Test basic generation request

3. **Data Availability**
   - Confirm `serial_killers_clean.csv` exists
   - Verify rows exist for target decades (1970s-2000s)
   - Check notes field contains text for LLM extraction

**Tools**: `investigate_q2.sh`, manual curl tests

---

### Phase 2: LLM Response Analysis
**Goal**: Inspect actual LLM output for JSON-LD validity

1. **Direct LLM Test**
   - Send exact Q2 prompt structure to Ollama
   - Capture raw JSON response
   - Validate JSON-LD parsing
   - Count resulting RDF triples

2. **Schema Validation**
   - Check if `@context` is `https://schema.org/`
   - Verify `@type` is `Person`
   - Confirm `description` property exists
   - Compare with expected SPARQL pattern:
     ```sparql
     ?person a schema:Person ;
             schema:description ?methods .
     ```

3. **Common LLM Issues**
   - Extra text before/after JSON
   - Wrong property names (e.g., `method` vs `description`)
   - Missing `@context` or incorrect namespace
   - Empty description value

**Tools**: `demo/serial_killers/investigate_q2.py` (test_ollama_generate)

---

### Phase 3: SPARQL Execution Tracing
**Goal**: Identify where query pipeline breaks

1. **CSV Loading**
   - Verify CSV graph URI returned
   - Count rows matching decade filter
   - Confirm notes field accessible

2. **Prompt Construction**
   - Log actual CONCAT result
   - Verify no SPARQL syntax errors in prompt string
   - Check SUBSTR doesn't truncate critically

3. **LLM Graph Generation**
   - Confirm `ggf:SLM-LLMGRAPH` is called (check DEBUG logs)
   - Verify graph URI returned
   - Inspect graph contents using SPARQL CONSTRUCT

4. **Graph Pattern Matching**
   - Check if triples exist in LLM graph
   - Test alternative SPARQL patterns:
     ```sparql
     # Option A: Current pattern
     ?person a schema:Person ; schema:description ?methods .

     # Option B: Relaxed type check
     ?person schema:description ?methods .

     # Option C: Any property
     ?person ?p ?methods .
     ```

**Tools**: `demo/serial_killers/investigate_q2.py` (test_sparql_query), DEBUG logging

---

### Phase 4: Graph Materialization
**Goal**: Check lazy evaluation and named graph timing

1. **Store Inspection**
   - Use `--keep-store` to persist graphs:
     ```bash
     python -m SPARQLLM.cli.slm -c config.ini \
       -f demo/serial_killers/queries/q2_methods_by_decade.sparql \
       --keep-store q2_debug.nq
     ```
   - Inspect `q2_debug.nq` for:
     - CSV graph triples
     - LLM-generated graph URIs
     - Actual triples in LLM graphs

2. **Lazy Join Evaluation**
   - Review `SPARQLLM/udf/SPARQLLM.py` evalLazyJoin patch
   - Check if LLM graphs materialize before GRAPH clause executes
   - Add debug logging to LLMGRAPH_OLLAMA function

3. **Caching Behavior**
   - Check if graph_uri caching (line 68-70 in llmgraph_ollama.py) works
   - Verify `named_graph_exists` doesn't skip generation incorrectly

**Tools**: N-Quads inspection, store query analysis

---

### Phase 5: Comparative Analysis
**Goal**: Compare working vs non-working queries

1. **Working Queries**
   - Q1: Pure CSV (no LLM) → works
   - Q5, Q6: CSV only → work
   - Q3, Q4: LLM-based → check status

2. **Key Differences**
   - Prompt structure
   - Expected output schema
   - SPARQL pattern complexity

3. **Reference Implementation**
   - Check if any other query successfully uses `SLM-LLMGRAPH`
   - Compare prompt templates
   - Identify working patterns

**Tools**: Query file comparison, execution logs

---

## Investigation Tools Created

### 1. `investigate_q2.sh`
**Location**: `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/investigate_q2.sh`

Quick diagnostic bash script:
- Activates correct venv
- Checks Ollama server
- Runs Q2 with debug output (first 200 lines)

**Usage**:
```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
chmod +x investigate_q2.sh
./investigate_q2.sh
```

### 2. `demo/serial_killers/investigate_q2.py`
**Location**: `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/demo/serial_killers/investigate_q2.py`

Comprehensive Python diagnostic:
- **test_ollama_connection**: Verify server + models
- **test_ollama_generate**: Send Q2-style prompt, inspect JSON-LD
- **test_csv_data**: Confirm CSV has target decade data
- **test_sparql_query**: Run simplified Q2 (1970s only, LIMIT 1)

**Usage**:
```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
source venv312_new/bin/activate  # or venv312
python demo/serial_killers/investigate_q2.py
```

**Output**: Pass/fail for each test + actionable next steps

---

## Expected Findings

### Scenario A: LLM Returns Invalid JSON-LD
**Symptom**: test_ollama_generate fails to parse JSON-LD

**Evidence**:
- Raw LLM response contains extra text
- Missing `@context` or wrong namespace
- Property names don't match schema.org

**Fix**: Update prompt to be more explicit, add validation

---

### Scenario B: SPARQL Pattern Mismatch
**Symptom**: Graph has triples but query finds none

**Evidence**:
- N-Quads show LLM graph with data
- Different property names (e.g., `methods` vs `description`)
- Wrong RDF type (not `schema:Person`)

**Fix**: Adjust SPARQL WHERE clause or prompt

---

### Scenario C: Lazy Evaluation Issue
**Symptom**: LLM function not called

**Evidence**:
- DEBUG logs don't show LLMGRAPH_OLLAMA execution
- No HTTP requests to Ollama
- Empty LLM graphs in N-Quads

**Fix**: Review evalLazyJoin, force evaluation

---

### Scenario D: Graph Caching Bug
**Symptom**: Same graph URI reused incorrectly

**Evidence**:
- Hash collision or improper URI generation
- `named_graph_exists` returns true when shouldn't

**Fix**: Adjust hashing in llmgraph_ollama.py line 66-67

---

## Prerequisites Before Execution

1. **Install html2text** (current blocker):
   ```bash
   source venv312_new/bin/activate
   pip install html2text
   ```

2. **Start Ollama** (if not running):
   ```bash
   ollama serve &
   ollama pull qwen2.5:3b
   ```

3. **Verify CSV exists**:
   ```bash
   ls -lh demo/serial_killers/data/serial_killers_clean.csv
   ```

---

## Success Criteria

Investigation complete when we can definitively answer:

1. **Is LLM being called?** (yes/no + evidence)
2. **What does LLM return?** (valid JSON-LD? show example)
3. **Do returned triples match query pattern?** (yes/no + diff)
4. **Root cause identified?** (which scenario A-D, or other)

---

## Next Steps After Investigation

Based on findings, action will be one of:

1. **Prompt Fix**: Update Q2 prompt template for better JSON-LD
2. **Query Fix**: Adjust SPARQL pattern to match LLM output
3. **Code Fix**: Patch llmgraph_ollama.py or evalLazyJoin
4. **Documentation**: If working as designed, explain limitations

---

## Unresolved Questions

1. Do Q3/Q4 (other LLM queries) work? Need to test.
2. Is qwen2.5:3b good at following JSON-LD instructions? May need model swap.
3. Should prompt use stricter format specification? (e.g., show example)
4. Is temperature=0.0 too restrictive for creative extraction?

---

## Files Modified

- Created: `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/investigate_q2.sh`
- Created: `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/demo/serial_killers/investigate_q2.py`
- Created: This plan document

**No code changes yet** - investigation only
