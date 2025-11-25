# Research: LLM Direct SPARQL Generation for SPARQLLM

**Date:** 2025-11-21
**Status:** Complete
**Scope:** How to make LLM generate SPARQL with GGFs directly, bypassing PhysicalCompiler

---

## Executive Summary

LLM can generate SPARQL with GGFs directly by using a **SPARQL-focused system prompt** that teaches the model SPARQL syntax, GGF binding patterns, and working examples. Current codebase has infrastructure for this (mode='direct' exists in query_generator.py) but is unimplemented. Implementation requires:

1. **SPARQL-specific system prompt** (teaching SPARQL, GGFs, BIND/GRAPH patterns)
2. **Direct mode in QueryGenerator** (LLM → SPARQL, skip JSON plan)
3. **Example catalog** (working .sparql files from demo/serial_killers/queries/)
4. **GGF syntax documentation** (CSV, LLM, web sources with BIND/GRAPH patterns)

---

## Key Findings

### 1. System Prompt Architecture

**Current Plan-Mode Prompt:** `demo/serial_killers/prompts/system_prompt_serial_killers.txt`
- Teaches **JSON logical plan format** (operation, steps, output)
- Maps domain (serial killers CSV) to JSON structure
- Injects catalog summary (GGF metadata) dynamically

**Direct-Mode Prompt Needs:**
- Teach **SPARQL PREFIX declarations** (ggf, ex, schema namespaces)
- Teach **GGF binding pattern**: `BIND(ggf:FUNCTION(...) AS ?graph)`
- Teach **GRAPH clause**: `GRAPH ?graph { ?row ?p ?o }`
- Teach **WHERE clause structure** (FILTER, ORDER BY, LIMIT)
- Provide **annotated examples** showing GGF ↔ SPARQL mapping

### 2. GGF Syntax Patterns (From Working Examples)

**q1_top_victims.sparql** - CSV aggregation:
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?proven_victims ?possible_victims ?country WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:proven_victims ?proven_victims .
        ...
    }
}
ORDER BY DESC(?proven_victims)
LIMIT 10
```

**Pattern Elements:**
- `BIND(ggf:FUNCTION(args) AS ?varName)` - GGF invocation
- `GRAPH ?varName { triple_patterns }` - Graph materialization
- Row variables: `?row` (CSV rows) or `?result` (LLM JSON-LD)
- Property format: `ex:column_name` (matches CSV headers or JSON-LD @context)

### 3. GGF Catalog Structure

**Location:** `SPARQLLM/catalog/` with RDF TurtleGraph metadata
**Available Functions by Source:**
- **filesystem**: SLM-CSV, SLM-READFILE, SLM-LISTDIR
- **llm**: SLM-LLM, LLMGRAPH_OLLAMA (local), LLMGRAPH_OPENAI (remote)
- **web**: SLM-SPARQL (Wikidata endpoint), SLM-SEARCH
- **vector**: SLM-FAISS, SLM-WHOOSH (text search)
- **graph**: SLM-GRAPH (RDF triplestore access)

**Cost Metadata:**
- Latency (latency_ms): <100ms (CSV) → 1000+ms (LLM)
- Tokens: cached vs. non-deterministic
- Network requirements: boolean flag

### 4. Query Type Handling

**CSV (Fastest, Local):**
```sparql
BIND(ggf:SLM-CSV("path/to/file.csv") AS ?g)
GRAPH ?g { ?row ex:column_name ?var . }
```

**LLM Generation (Medium Latency, JSON-LD):**
```sparql
BIND("""<prompt text>""" AS ?prompt)
BIND(ggf:SLM-LLM(?prompt) AS ?g)
GRAPH ?g { ?root a schema:Event . OPTIONAL { ?root schema:message ?var . } }
```

**Web Search (Remote SPARQL):**
```sparql
BIND(ggf:SLM-SPARQL("wikidata", "<sparql_query>") AS ?g)
GRAPH ?g { ?s ?p ?o . }
```

### 5. Implementation Path

**Step 1: Direct Mode Prompt**
- Create `demo/serial_killers/prompts/direct_system_prompt.txt`
- Structure: explain SPARQL + GGFs → show annotated examples → rules

**Step 2: QueryGenerator Enhancement**
- Implement `mode='direct'` branch in `__init__`
- Add `generate_sparql()` method (LLM → SPARQL string)
- Strip markdown, return raw query
- Validation: parse with rdflib to catch syntax errors

**Step 3: Example Gallery**
- Existing 6 queries in `demo/serial_killers/queries/*.sparql` are gold standard
- Each has comment header: question, category, cost, expected output
- Use as few-shot examples in prompt

**Step 4: Testing Flow**
- User question → LLM (direct prompt) → SPARQL → slm-run validation
- No PhysicalCompiler validation needed
- Execution test via `--keep-store` determinism check

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Use SPARQL directly** | Avoids compiler bugs; model can "see" query patterns |
| **Prompt + Few-shot** | SPARQL is learnable; 3-5 examples enough for serial killers domain |
| **Minimal prompt injection** | Don't embed massive catalog; trust model knows common GGFs |
| **Markdown stripping** | LLMs add code fences; parser handles it |
| **Validation via rdflib** | Syntax errors caught before execution |

---

## Files Involved

**To Create:**
- `demo/serial_killers/prompts/direct_system_prompt.txt` (150-200 lines)
- `SPARQLLM/compiler/direct_mode.py` (100-150 lines, optional utility class)

**To Modify:**
- `demo/query_generator.py` (add mode='direct' initialization + generate_sparql method)
- `SPARQLLM/catalog/query.py` (already supports GGF discovery; no change needed)

**Reference Files (Read-Only):**
- `demo/serial_killers/queries/q*.sparql` (examples)
- `demo/serial_killers/prompts/system_prompt_serial_killers.txt` (plan mode reference)
- `SPARQLLM/data/ggf-catalog.ttl` (GGF metadata)

---

## Example Direct Prompt Structure

```
You are a SPARQL query generator for the Serial Killers dataset.

# GGF (Graph Generating Functions)

GGFs are SPARQL functions that return RDF graphs during query execution:
- ggf:SLM-CSV(path) → CSV as RDF graph
- ggf:SLM-LLM(prompt) → LLM JSON-LD as RDF graph
- ggf:SLM-SPARQL(endpoint, query) → remote SPARQL results

## Syntax

BIND(ggf:FunctionName(args) AS ?graphVariable)
GRAPH ?graphVariable { ?s ?p ?o . }  # Pattern matching in result graph

## Column → Property Mapping

CSV columns become ex:column_name URIs:
- column: "name" → predicate: ex:name
- column: "proven_victims" → predicate: ex:proven_victims

## Examples

[6 annotated queries from demo/serial_killers/queries/]

## Your Task

Generate SPARQL query for: {USER_QUESTION}

Rules:
1. Return ONLY SPARQL, no markdown, no explanation
2. Use PREFIX ggf and PREFIX ex
3. All CSV queries: ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv")
4. Bind CSV results to ?csvGraph, bind rows to ?row variable
5. Use ?row ex:column_name for column access
6. Use FILTER(...), ORDER BY, LIMIT as needed
```

---

## Unresolved Questions

1. **Backward compatibility:** Should plan mode remain default, with direct as opt-in?
2. **Error recovery:** What does LLM do if ggf:function() fails at runtime? (Handled by slm-run, not prompt)
3. **Multi-hop queries:** Can direct prompt handle LLM→CSV chaining? (Testable after impl)
4. **Catalog injection:** Should we embed full GGF list in prompt or keep it minimal?

---

## References

- README.md: GGF concept, SPARQL examples, slm-run CLI
- demo/serial_killers/queries/: 6 working queries (q1-q6)
- demo/serial_killers/prompts/system_prompt_serial_killers.txt: Plan mode structure
- SPARQLLM/catalog/query.py: Catalog API (ready to use)
- query_generator.py L408: mode='direct' placeholder
