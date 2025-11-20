# Phase 5: Documentation & Examples

**Duration:** 1 week
**Dependencies:** Phase 1-4 (all components implemented & tested)
**Owner:** Technical Writer + Developer

---

## Context

Production-ready system needs comprehensive docs: user guides, API references, examples, troubleshooting. Target audiences: end users (researchers/analysts), developers (extending GGFs), contributors.

---

## Overview

Create documentation suite:
1. **User Guide:** How to use two-stage compiler (non-technical audience)
2. **Developer Guide:** Extending catalog, adding GGFs, compiler internals
3. **API Reference:** Auto-generated from docstrings (Sphinx)
4. **Examples Gallery:** 10 annotated use cases with explanations
5. **Troubleshooting:** Common errors + solutions
6. **Research Paper Draft:** Technical writeup for academic dissemination

**Output:** Documentation site (GitHub Pages) + inline code docs + tutorial videos (optional)

---

## Key Insights (from Research)

1. **Self-describing catalogs aid adoption** (researcher-02 L83-99): Document how to query catalog for discovery.
2. **Cost transparency builds trust**: Explain cost model assumptions, how to calibrate.
3. **Multi-hop examples critical** (researcher-01 L62-70): Show complex workflows, not just toy examples.

---

## Requirements

### Functional
- [ ] User guide: getting started in <10 minutes (installation → first query)
- [ ] Developer guide: add new GGF in <30 minutes (template + checklist)
- [ ] API reference: all public functions documented (100% coverage)
- [ ] 10 annotated examples (code + explanation + use case)
- [ ] Troubleshooting: 20 common errors with solutions

### Non-Functional
- [ ] Docs site loads in <2s
- [ ] Mobile-responsive (80% of pages readable on phone)
- [ ] Searchable (full-text search via Algolia/Docsify)
- [ ] Versioned (link to docs for v1.0, v1.1, etc.)

---

## Architecture

### 1. Documentation Structure

```
docs/
├── index.md                        # Landing page
├── user-guide/
│   ├── quickstart.md               # Install + first query (10 min)
│   ├── two-stage-workflow.md       # Plan → compile → execute flow
│   ├── cost-estimation.md          # Understanding cost model
│   ├── comparison-mode.md          # Direct vs compiled benchmarking
│   └── faq.md                      # Frequently asked questions
├── developer-guide/
│   ├── architecture.md             # System overview (diagrams)
│   ├── catalog.md                  # GGF catalog design
│   ├── compiler.md                 # Logical → physical compilation
│   ├── adding-ggfs.md              # Step-by-step GGF addition
│   ├── extending-compiler.md       # Custom operation types
│   └── contributing.md             # PR guidelines, code standards
├── api-reference/
│   ├── catalog.md                  # Auto-generated from catalog/query.py
│   ├── compiler.md                 # Auto-generated from compiler/*.py
│   ├── query-generator.md          # Auto-generated from demo/query_generator.py
│   └── ggf-registry.md             # List all 44 GGFs (from catalog)
├── examples/
│   ├── 01-simple-filesystem.md
│   ├── 02-llm-extraction.md
│   ├── 03-web-search.md
│   ├── 04-hybrid-files-llm.md
│   ├── 05-hybrid-web-llm.md
│   ├── 06-multi-source-join.md
│   ├── 07-sql-integration.md
│   ├── 08-vector-search.md
│   ├── 09-iterative-refinement.md
│   └── 10-cost-optimization.md
├── troubleshooting.md
├── changelog.md
└── research/
    └── llm-sparqllm-compiler-paper.md
```

### 2. User Guide (Quickstart)

**File:** `docs/user-guide/quickstart.md`

```markdown
# Quickstart: Two-Stage SPARQLLM Compiler

Get started with SPARQLLM's LLM-powered query compiler in 10 minutes.

## Installation

Requires Python 3.10+, Groq API key (free tier: 1000 req/hour).

```bash
git clone https://github.com/your-org/SPARQLLM.git
cd SPARQLLM
python -m venv venv
source venv/bin/activate
pip install -e .
```

Set API key:
```bash
export GROQ_API_KEY="your_key_here"
```

## First Query

Ask a natural language question, get SPARQLLM query automatically:

```bash
cd demo
python query_generator.py
```

**Example interaction:**
```
Mode: 1 (Two-stage)
Question: List all CSV files in ./data

[Logical Plan Generated]
Query Explanation: This query will: (1) list files in ./data. Returns: path. Estimated cost: 0 tokens ($0.0000), 0.1 seconds.

Execution Steps:
└─ step1: Read Filesystem (SLM-READDIR)

[y] Approve and execute
Your choice: y

Results:
./data/results.csv
./data/events.csv
```

## How It Works

1. **LLM generates logical plan** (JSON with steps, dependencies)
2. **Compiler translates to SPARQL** (optimized query with GGF calls)
3. **Cost estimator predicts** latency/tokens before execution
4. **You confirm**, then query executes
5. **Results returned** with provenance (which GGFs ran, how long)

## Next Steps

- [Understand the two-stage workflow](two-stage-workflow.md)
- [Explore 10 annotated examples](../examples/)
- [Learn cost model details](cost-estimation.md)
```

### 3. Developer Guide (Adding GGFs)

**File:** `docs/developer-guide/adding-ggfs.md`

```markdown
# Adding New Graph Generating Functions

Step-by-step guide to extend SPARQLLM with custom GGFs.

## Prerequisites

- Understand RDFLib basics (Graph, URIRef, Literal)
- Know which data source you're integrating (API, DB, service)
- Have Python function ready (input → output)

## Steps

### 1. Create GGF Module

**File:** `SPARQLLM/udf/my_custom_ggf.py`

```python
from rdflib import Graph, URIRef, Literal, Namespace
from SPARQLLM.udf.SPARQLLM import store

SCHEMA = Namespace("https://schema.org/")

def my_custom_function(arg1: str, arg2: int) -> URIRef:
    """
    Your GGF function docstring (appears in catalog).

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        URIRef: Named graph URI containing results
    """
    # 1. Call external service/API
    data = fetch_from_api(arg1, arg2)

    # 2. Create named graph
    graph_uri = URIRef(f"urn:custom:{hashlib.sha256(arg1.encode()).hexdigest()[:16]}")
    g = store.graph(graph_uri)

    # 3. Convert data to RDF triples
    for item in data:
        subject = URIRef(f"urn:custom:item:{item['id']}")
        g.add((subject, SCHEMA.name, Literal(item['name'])))
        g.add((subject, SCHEMA.value, Literal(item['value'])))

    # 4. Add provenance (optional but recommended)
    # See slm_mcp_tool.py:_attach_prov() for pattern

    # 5. Return graph URI
    return graph_uri
```

### 2. Register with Catalog

Add metadata decorator:

```python
from SPARQLLM.udf.metadata import ggf_metadata

@ggf_metadata(
    latency_ms=200,
    tokens=0,
    rate_limit=100,
    data_sources=["api"],
    deterministic=True,
    cacheable=True,
    env_var="MY_API_KEY",
    example='BIND(ggf:MY-CUSTOM("arg1", 42) AS ?g)'
)
def my_custom_function(arg1: str, arg2: int) -> URIRef:
    ...
```

### 3. Create Alias (Optional)

**File:** `SPARQLLM/udf/mcp/alias.py`

Add alias registration:

```python
def register_custom_alias():
    from rdflib.plugins.sparql.evalutils import register_custom_function
    register_custom_function(
        URIRef("http://ggf.org/MY-CUSTOM"),
        lambda arg1, arg2: my_custom_function(str(arg1), int(arg2))
    )
```

### 4. Regenerate Catalog

```bash
python SPARQLLM/tools/generate_ggf_catalog.py
```

Verify your GGF appears:

```bash
grep "MY-CUSTOM" SPARQLLM/data/ggf-catalog.ttl
```

### 5. Test

**File:** `tests/unit/test_my_custom_ggf.py`

```python
def test_my_custom_function():
    result_uri = my_custom_function("test", 42)
    g = store.graph(result_uri)

    assert len(g) > 0, "Graph should contain triples"
    # Add specific assertions
```

Run tests:
```bash
pytest tests/unit/test_my_custom_ggf.py
```

## Checklist

- [ ] GGF function implemented (input → RDF graph)
- [ ] Metadata decorator added
- [ ] Alias registered (if needed)
- [ ] Catalog regenerated
- [ ] Unit tests written
- [ ] Example query created
- [ ] Documentation added to `api-reference/ggf-registry.md`

## Common Pitfalls

1. **Forgetting to return graph URI**: Function must return `URIRef`, not `Graph` object
2. **Not adding provenance**: Makes debugging hard - use `_attach_prov()` pattern
3. **Missing error handling**: External APIs fail - wrap in try/except, return error graph
4. **Ignoring rate limits**: Add sleep/backoff if API has strict limits

## Resources

- [GGF design patterns](../research/researcher-02-mcp-ggf-design.md)
- [MCP provider examples](../../SPARQLLM/udf/mcp/providers/)
- [RDFLib documentation](https://rdflib.readthedocs.io/)
```

### 4. Examples Gallery

**File:** `docs/examples/04-hybrid-files-llm.md`

```markdown
# Example 4: Hybrid Files + LLM Extraction

**Use Case:** Extract structured event data from local text files using LLM.

**Data Source:** Filesystem (text files) + LLM (Groq)

**Complexity:** Medium (3 steps, 2 dependencies)

---

## Scenario

You have 10 text files in `./data/events/` containing event announcements (unstructured text). Extract event names, dates, and locations as structured JSON-LD.

**Sample file (`./data/events/concert.txt`):**
```
The Summer Jazz Festival will take place on July 15, 2025, in Central Park, New York.
Featuring world-renowned artists, this event promises an unforgettable experience.
```

---

## Natural Language Query

"Extract event information from text files in data/events using an LLM"

---

## Generated Logical Plan

```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-READDIR",
        "args": { "path": "./data/events", "filter": "*.txt" }
      },
      "bindings": { "fileUri": "?fileUri" }
    },
    {
      "id": "step2",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-READFILE",
        "args": { "file": "?fileUri", "maxChars": -1 }
      },
      "depends_on": ["step1"],
      "bindings": { "content": "?content" }
    },
    {
      "id": "step3",
      "operation": "llm_extract",
      "ggf": {
        "name": "LLM",
        "args": {
          "prompt": "Extract JSON-LD Event: { '@context': 'https://schema.org/', '@type': 'Event', 'name': '...', 'startDate': 'YYYY-MM-DD', 'location': { '@type': 'Place', 'name': '...' } } from: {?content}"
        }
      },
      "depends_on": ["step2"],
      "bindings": {
        "event": "?event",
        "eventName": "?eventName",
        "eventDate": "?eventDate",
        "location": "?location"
      }
    }
  ],
  "output": {
    "variables": ["eventName", "eventDate", "location"],
    "distinct": true,
    "order_by": [{"variable": "eventDate", "order": "ASC"}]
  }
}
```

---

## Cost Estimate

- **Latency:** ~3.2 seconds
- **Token Usage:** 500 tokens × 10 files = 5000 tokens
- **Cost:** ~$0.0005 (Groq pricing)
- **API Calls:** 10 (one LLM call per file)

---

## Compiled SPARQL Query

```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <https://schema.org/>

SELECT DISTINCT ?eventName ?eventDate ?location WHERE {
    # Step 1: List text files
    BIND(URI(ggf:SLM-FILE("./data/events")) AS ?dir)
    BIND(ggf:SLM-READDIR(?dir, ?dir) AS ?dirGraph)
    GRAPH ?dirGraph {
        ?dir ex:has_path ?fileUri .
        ?fileUri ex:has_type ?type .
        FILTER(STR(?type) = "file")
        FILTER(STRENDS(STR(?fileUri), ".txt"))
    }

    # Step 2: Read file content
    BIND(ggf:SLM-READFILE(?fileUri, -1) AS ?content)

    # Step 3: LLM extraction
    BIND(CONCAT(
        "Extract JSON-LD Event: { '@context': 'https://schema.org/', '@type': 'Event', 'name': '...', 'startDate': 'YYYY-MM-DD', 'location': { '@type': 'Place', 'name': '...' } } from: ",
        ?content
    ) AS ?prompt)
    BIND(ggf:LLM(?prompt) AS ?llmGraph)
    GRAPH ?llmGraph {
        ?event a schema:Event ;
               schema:name ?eventName ;
               schema:startDate ?eventDate .
        OPTIONAL {
            ?event schema:location ?place .
            ?place schema:name ?location .
        }
    }
}
ORDER BY ASC(?eventDate)
```

---

## Sample Results

| eventName | eventDate | location |
|-----------|-----------|----------|
| Summer Jazz Festival | 2025-07-15 | Central Park, New York |
| Tech Conference 2025 | 2025-08-20 | San Francisco Convention Center |
| ... | ... | ... |

---

## Key Learnings

1. **Multi-stage pipeline**: Filesystem → Read → LLM extraction chained via dependencies
2. **LLM prompt engineering**: Explicit JSON-LD schema in prompt ensures structured output
3. **Cost awareness**: 10 files × 500 tokens = 5000 tokens total (trackable via cost model)
4. **OPTIONAL handling**: Some events may not have location (gracefully handled)

---

## Try It Yourself

1. Create sample files:
   ```bash
   mkdir -p data/events
   echo "The Summer Jazz Festival will take place on July 15, 2025, in Central Park, New York." > data/events/concert.txt
   ```

2. Run demo:
   ```bash
   cd demo
   python query_generator.py
   ```

3. Enter question: "Extract event information from text files in data/events using an LLM"

4. Approve plan, see results!

---

## Related Examples

- [Example 3: LLM Extraction (single file)](03-llm-extraction.md)
- [Example 5: Hybrid Web + LLM](05-hybrid-web-llm.md)
- [Example 9: Iterative Refinement](09-iterative-refinement.md)
```

### 5. Troubleshooting Guide

**File:** `docs/troubleshooting.md`

```markdown
# Troubleshooting

Common issues and solutions for SPARQLLM compiler.

---

## Installation Issues

### `slm-run` command not found

**Cause:** Package not installed or virtual environment not activated.

**Solution:**
```bash
source venv/bin/activate
pip install -e .
which slm-run  # Should show path
```

---

## Plan Generation Errors

### LLM returns invalid JSON

**Symptom:**
```
Error: Plan generation failed: Expecting property name enclosed in double quotes
```

**Cause:** LLM output contains markdown code blocks or extra text.

**Solution:** Automatic cleanup in `query_generator.py` (regex strips ```json blocks). If persists:
- Check prompt: ensure "Return ONLY valid JSON" instruction present
- Try different model: `export GROQ_MODEL=llama-3.3-70b-versatile`

---

### Unknown GGF in plan

**Symptom:**
```
ValueError: Unknown GGF: INVALID_FUNCTION
```

**Cause:** LLM hallucinated function name not in catalog.

**Solution:**
1. Check catalog: `grep INVALID_FUNCTION SPARQLLM/data/ggf-catalog.ttl`
2. If missing, regenerate catalog: `python SPARQLLM/tools/generate_ggf_catalog.py`
3. If LLM consistently hallucinates, update prompt with explicit function list

---

## Compilation Errors

### Circular dependency detected

**Symptom:**
```
ValueError: Circular dependency detected in plan
```

**Cause:** Step A depends on Step B, Step B depends on Step A.

**Solution:** Edit plan (press `e` at confirmation prompt), remove circular `depends_on`.

---

### Unbound variable

**Symptom:**
```
ValueError: Unbound variable ?undefinedVar used in step3
```

**Cause:** Step references variable not produced by prior steps.

**Solution:** Check `bindings` in earlier steps - ensure variable defined before use.

---

## Execution Errors

### GROQ_API_KEY not set

**Symptom:**
```
ValueError: GROQ_API_KEY not found in environment variables
```

**Solution:**
```bash
export GROQ_API_KEY="your_key_here"
# Or add to .env file in project root
```

---

### Query timeout (60s)

**Symptom:**
```
Query execution timed out (60s)
```

**Cause:** LLM call too slow or web search hanging.

**Solution:**
- Increase timeout: Edit `demo/query_generator.py` L274 (`timeout=120`)
- Reduce data size: Filter files before LLM (use FILTER in step1)
- Check network: `ping api.groq.com`

---

### Empty results

**Symptom:** Query succeeds but returns no rows.

**Cause:** FILTER too restrictive, or data source empty.

**Debug:**
1. Run with `--debug`: `slm-run --config config.ini -q "..." --debug`
2. Check intermediate graphs: Add `BIND(ggf:PRINT(?var) AS ?debug)`
3. Remove FILTERs one by one to isolate issue

---

## Cost Estimation Issues

### Estimated cost wildly inaccurate

**Symptom:** Estimated 2s, actual 10s execution.

**Cause:** Cost model uses static averages, actual latency varies (network, LLM load).

**Solution:**
- Use estimates as order-of-magnitude guide, not exact predictions
- Calibrate: Run benchmark suite, update catalog metadata with empirical values

---

## Performance Issues

### Compiler very slow (>5s)

**Symptom:** Plan → SPARQL compilation takes >5 seconds.

**Cause:** Large plan (>20 steps), or complex dependency graph.

**Solution:**
- Simplify plan: Break into smaller queries
- Profile: `python -m cProfile demo/query_generator.py`

---

## Getting Help

1. **Check logs:** Run with `--debug` flag for detailed output
2. **Search issues:** [GitHub Issues](https://github.com/your-org/SPARQLLM/issues)
3. **Ask community:** [Discussions](https://github.com/your-org/SPARQLLM/discussions)
4. **Report bug:** Include: OS, Python version, full error trace, minimal reproduction case
```

---

## Implementation Steps

### Week 1: Core Documentation

1. **Day 1-2:** User guide
   - Write quickstart (installation → first query)
   - Document two-stage workflow
   - Explain cost estimation
   - Create FAQ (10 common questions)

2. **Day 3-4:** Developer guide
   - Architecture overview with diagrams
   - Adding GGFs tutorial
   - Extending compiler guide
   - Contributing guidelines

3. **Day 5:** Examples gallery
   - Annotate 10 test cases from Phase 4
   - Add use case descriptions
   - Include cost breakdowns

4. **Day 6-7:** API reference + troubleshooting
   - Generate API docs with Sphinx
   - Write troubleshooting guide (20 common errors)
   - Create changelog

---

## Todo List

- [ ] Write user guide (quickstart, workflow, cost model, FAQ)
- [ ] Write developer guide (architecture, adding GGFs, extending compiler)
- [ ] Generate API reference (Sphinx auto-docs)
- [ ] Create 10 annotated examples with explanations
- [ ] Write troubleshooting guide (20 common errors)
- [ ] Set up documentation site (GitHub Pages or Docsify)
- [ ] Add search functionality (Algolia or lunr.js)
- [ ] Create changelog (v1.0 release notes)
- [ ] Draft research paper (academic dissemination)
- [ ] Record tutorial video (optional, 10 min screencast)

---

## Success Criteria

1. User can complete quickstart in <10 minutes (user testing: 5 participants)
2. Developer can add new GGF in <30 minutes (following guide)
3. API reference: 100% public functions documented
4. Examples gallery: 10 annotated use cases covering all GGF types
5. Troubleshooting: covers 90% of support questions (measured via GitHub Issues)
6. Docs site loads in <2s, mobile-responsive

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Docs become stale (code changes) | High | Auto-generate API docs; add docs build to CI |
| Examples too complex (intimidating) | Medium | Include "simple" tag; progressive complexity |
| Troubleshooting incomplete | Medium | Collect real user issues for 2 weeks before finalizing |
| Research paper rejected | Low | Share as arXiv preprint regardless |

---

## Security Considerations

- **No API keys in examples**: Use placeholders (`your_key_here`)
- **Sanitized data**: Example files contain synthetic data only

---

## Unresolved Questions

1. Host docs on GitHub Pages, ReadTheDocs, or custom domain?
2. Include video tutorials or text-only (accessibility vs engagement)?
3. Research paper target venue: ISWC, ESWC, or domain-specific (e.g., NeurIPS workshop)?
