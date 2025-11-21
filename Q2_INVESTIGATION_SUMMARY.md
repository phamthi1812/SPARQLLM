# Q2 Empty Results Investigation

**Status**: Investigation tools created, ready to execute
**Issue**: Q2 query (`demo/serial_killers/queries/q2_methods_by_decade.sparql`) returns empty DataFrame
**Date**: 2025-11-20

---

## Problem Statement

Query executes successfully but returns 0 results:
- **Expected**: Decade, killer name, killing methods from LLM analysis
- **Actual**: Empty DataFrame with correct column names [decade, name, methods]
- **Context**: Q1 (pure CSV) works, proving CSV loading is functional

---

## Root Cause Hypotheses

1. **LLM Response Format** - Ollama returns invalid JSON-LD or wrong schema
2. **SPARQL Pattern Mismatch** - LLM output doesn't match query expectations
3. **Lazy Evaluation** - LLM function not called due to query optimization
4. **Graph Materialization** - Timing issue with named graph availability

---

## Investigation Tools Created

### Quick Diagnostic: `investigate_q2.sh`
```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
chmod +x investigate_q2.sh
./investigate_q2.sh
```

**What it does**:
- Activates correct Python venv
- Checks Ollama server status
- Runs Q2 with debug logging (first 200 lines)

---

### Comprehensive Test: `demo/serial_killers/investigate_q2.py`
```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
source venv312_new/bin/activate  # or venv312
pip install html2text  # if missing
python demo/serial_killers/investigate_q2.py
```

**What it tests**:
1. ✓ Ollama connection + model availability
2. ✓ LLM JSON-LD generation with Q2-style prompt
3. ✓ CSV data for target decades (1970s-2000s)
4. ✓ Actual SPARQL query execution (simplified: 1970s only, LIMIT 1)

**Output**: Pass/fail per test + actionable next steps

---

## Prerequisites

Before running investigation:

```bash
# 1. Activate Python environment
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
source venv312_new/bin/activate

# 2. Install missing dependency
pip install html2text

# 3. Ensure Ollama is running
ollama serve &
ollama pull qwen2.5:3b

# 4. Verify CSV exists
ls -lh demo/serial_killers/data/serial_killers_clean.csv
```

---

## Expected Investigation Outcomes

### Scenario A: LLM Returns Invalid JSON-LD
**Evidence**: Raw response has extra text, wrong properties, or missing `@context`
**Fix**: Update prompt template in Q2 query

### Scenario B: SPARQL Pattern Mismatch
**Evidence**: Graph has data but property names don't match
- LLM uses `methods` instead of `description`
- Wrong RDF type (not `schema:Person`)

**Fix**: Adjust SPARQL WHERE clause or prompt

### Scenario C: LLM Not Called
**Evidence**: No DEBUG logs showing LLMGRAPH_OLLAMA execution
**Fix**: Review lazy evaluation in `SPARQLLM/udf/SPARQLLM.py`

### Scenario D: Graph Caching Issue
**Evidence**: Same graph URI reused incorrectly
**Fix**: Adjust hash generation in `llmgraph_ollama.py`

---

## Key Files to Review

### Query Definition
- `demo/serial_killers/queries/q2_methods_by_decade.sparql` - The failing query

### LLM Implementation
- `SPARQLLM/udf/llmgraph_ollama.py` - Ollama integration (lines 66-120)
  - Line 66-67: Graph URI hashing
  - Line 88-91: HTTP response handling
  - Line 97-101: JSON-LD parsing
  - Line 100: `clean_invalid_uris` - potential issue?

### Configuration
- `config.ini` - Ollama settings:
  ```ini
  SLM-OLLAMA-MODEL=qwen2.5:3b
  SLM-OLLAMA-URL=http://localhost:11434/api/generate
  SLM-LLM-TEMPERATURE=0.6
  ```

---

## What Query Expects

**Prompt structure** (Q2 lines 25-35):
```sparql
CONCAT(
  "Extract the killing methods...",
  "Return ONLY a JSON-LD object with this exact structure (no extra text): ",
  "{",
  "  \"@context\": \"https://schema.org/\",",
  "  \"@type\": \"Person\",",
  "  \"name\": \"", STR(?name), "\",",
  "  \"description\": \"brief comma-separated list of methods\"",
  "}",
  "\n\nText: ", SUBSTR(?notes, 1, 500)
)
```

**Expected LLM output**:
```json
{
  "@context": "https://schema.org/",
  "@type": "Person",
  "name": "Ted Bundy",
  "description": "bludgeoning, strangling"
}
```

**SPARQL pattern** (Q2 lines 39-42):
```sparql
GRAPH ?llmGraph {
    ?person a schema:Person ;
            schema:description ?methods .
}
```

---

## Debugging Commands

### Test Ollama Directly
```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:3b",
    "prompt": "Return this JSON: {\"@context\":\"https://schema.org/\",\"@type\":\"Person\",\"name\":\"Test\",\"description\":\"methods\"}",
    "format": "json",
    "stream": false,
    "options": {"temperature": 0.0}
  }'
```

### Inspect Store with --keep-store
```bash
python -m SPARQLLM.cli.slm -c config.ini \
  -f demo/serial_killers/queries/q2_methods_by_decade.sparql \
  --keep-store q2_debug.nq

# Then inspect
grep -A5 "schema.org" q2_debug.nq
```

### Run Simplified Query
```bash
python -m SPARQLLM.cli.slm -c config.ini -q '
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>
SELECT ?g WHERE {
  BIND(ggf:SLM-LLMGRAPH("Return JSON-LD: {\"@context\":\"https://schema.org/\",\"@type\":\"Person\",\"description\":\"test\"}") AS ?g)
}' -d
```

---

## Next Steps

1. **Run investigation script** to identify failure point
2. **Capture evidence** (logs, LLM responses, N-Quads)
3. **Implement fix** based on scenario (A/B/C/D)
4. **Validate fix** with Q2 re-execution
5. **Document findings** in final report

---

## Investigation Plan

Full investigation plan available at:
`/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/plans/20251120-1351-llm-sparqllm-compiler/reports/251120-investigation-q2-empty-results-plan.md`

Contains:
- Detailed 5-phase investigation approach
- Tool descriptions and usage
- Expected findings per scenario
- Success criteria
- Unresolved questions list
