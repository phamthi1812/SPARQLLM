# Phase 1: GGF Catalog Infrastructure

**Duration:** 2 weeks
**Dependencies:** None
**Owner:** Backend Developer

---

## Context

Currently GGFs registered dynamically via `alias.py` + `slm_mcp_tool.py`. LLM has no queryable registry to discover functions, signatures, costs, or capabilities. Need self-describing catalog for LLM query planning.

---

## Overview

Build RDF catalog exposing all GGFs (39 confirmed) with metadata:
- Signature (params, types, return shape)
- Cost estimates (latency, tokens, API limits)
- Capabilities (data sources accessed, determinism, cacheability)
- Examples (few-shot prompts)

**Output:** Turtle file (`ggf-catalog.ttl`) + Python generator script + query API

**Status:** COMPLETED ✓ (Nov 20, 2025)

---

## Key Insights (from Research)

1. **MCP `tools/list` pattern**: Tools self-describe via JSON Schema (researcher-02 L6-12). Apply same to GGFs.
2. **Content-addressed stability**: Use SHA256 for catalog versioning (researcher-02 L46-51).
3. **Cost metadata missing**: Current PROV-O only tracks actual duration (researcher-02 L129-133). Add static estimates.
4. **Schema.org extension**: Reuse existing vocabularies where possible (Action, SoftwareApplication).

---

## Requirements

### Functional
- [x] Catalog includes all 39 GGF modules (verified from config.ini aliases)
- [x] Queryable via SPARQL (`SELECT ?ggf WHERE { ?ggf ggf:accessesDataSource "filesystem" }`)
- [x] Auto-generated from code (docstrings + decorators)
- [x] Versioned with git (regenerate on code change)

### Non-Functional
- [x] Generation script runs in <5s (actual: ~1s)
- [x] Catalog file <100KB (actual: 21KB uncompressed)
- [x] Zero runtime overhead (static file, loaded once)

---

## Architecture

### 1. Schema Design (Turtle Ontology)

```turtle
@prefix ggf: <http://ggf.org/> .
@prefix schema: <https://schema.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Core class
ggf:GraphGeneratingFunction a rdfs:Class ;
    rdfs:label "Graph Generating Function" ;
    rdfs:comment "Function returning named RDF graph" .

# Properties
ggf:signature a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:string ;
    rdfs:comment "Function signature: name(param1:type, param2:type) -> Graph" .

ggf:costLatencyMs a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:decimal ;
    rdfs:comment "Estimated latency in milliseconds (P50)" .

ggf:costTokens a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:integer ;
    rdfs:comment "Estimated token consumption (LLM calls only)" .

ggf:rateLimitPerHour a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:integer ;
    rdfs:comment "API rate limit (calls/hour)" .

ggf:accessesDataSource a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:string ;
    rdfs:comment "Data source type: filesystem, llm, web, sql, vector" .

ggf:deterministic a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Returns same output for same input" .

ggf:cacheable a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:boolean .

ggf:requiresEnvVar a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:string ;
    rdfs:comment "Required environment variable (e.g., GROQ_API_KEY)" .

ggf:exampleUsage a rdf:Property ;
    rdfs:domain ggf:GraphGeneratingFunction ;
    rdfs:range xsd:string ;
    rdfs:comment "SPARQL snippet showing usage" .
```

### 2. Catalog Generator Script

**File:** `SPARQLLM/tools/generate_ggf_catalog.py`

```python
#!/usr/bin/env python3
"""
Generate GGF catalog from codebase.
Scans SPARQLLM/udf/ for GGF modules, extracts metadata from:
- Docstrings (description, examples)
- Type hints (signature)
- Decorators (@ggf_metadata)
- MCP provider registrations
"""

import ast, inspect, hashlib
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

GGF = Namespace("http://ggf.org/")
SCHEMA = Namespace("https://schema.org/")

def extract_ggf_metadata(module_path: Path) -> dict:
    """Parse Python module, extract GGF metadata from AST."""
    # Parse docstring for description, examples
    # Extract function signature from type hints
    # Look for @ggf_metadata decorator
    pass

def scan_udf_directory() -> list[dict]:
    """Scan SPARQLLM/udf for all GGF modules."""
    # Filesystem: readfile.py, readdir.py, csv_reader.py
    # LLM: llmgraph_groq.py, llmgraph_ollama.py
    # MCP: slm_mcp_tool.py (extract registered tools)
    # Web: search.py
    # Vector: faiss_search.py
    pass

def generate_catalog(ggf_list: list[dict]) -> Graph:
    """Build RDF catalog graph."""
    g = Graph()
    g.bind("ggf", GGF)
    g.bind("schema", SCHEMA)

    for ggf in ggf_list:
        uri = GGF[ggf['name']]
        g.add((uri, RDF.type, GGF.GraphGeneratingFunction))
        g.add((uri, RDFS.label, Literal(ggf['name'])))
        g.add((uri, RDFS.comment, Literal(ggf['description'])))
        g.add((uri, GGF.signature, Literal(ggf['signature'])))

        # Cost metadata
        if 'latency_ms' in ggf:
            g.add((uri, GGF.costLatencyMs, Literal(ggf['latency_ms'], datatype=XSD.decimal)))
        if 'tokens' in ggf:
            g.add((uri, GGF.costTokens, Literal(ggf['tokens'], datatype=XSD.integer)))
        if 'rate_limit' in ggf:
            g.add((uri, GGF.rateLimitPerHour, Literal(ggf['rate_limit'], datatype=XSD.integer)))

        # Capabilities
        for source in ggf.get('data_sources', []):
            g.add((uri, GGF.accessesDataSource, Literal(source)))

        g.add((uri, GGF.deterministic, Literal(ggf.get('deterministic', False), datatype=XSD.boolean)))
        g.add((uri, GGF.cacheable, Literal(ggf.get('cacheable', True), datatype=XSD.boolean)))

        if 'env_var' in ggf:
            g.add((uri, GGF.requiresEnvVar, Literal(ggf['env_var'])))

        if 'example' in ggf:
            g.add((uri, GGF.exampleUsage, Literal(ggf['example'])))

    return g

if __name__ == "__main__":
    ggf_modules = scan_udf_directory()
    catalog = generate_catalog(ggf_modules)

    # Write to file
    catalog_path = Path(__file__).parent.parent / "data" / "ggf-catalog.ttl"
    catalog.serialize(destination=str(catalog_path), format="turtle")

    # Compute content hash
    content = catalog.serialize(format="turtle")
    h = hashlib.sha256(content.encode()).hexdigest()[:16]
    print(f"Generated catalog: {catalog_path} (hash: {h})")
```

### 3. Manual Metadata Annotations

**File:** `SPARQLLM/udf/metadata.py`

```python
"""
Metadata registry for GGFs.
Use decorators when auto-extraction insufficient.
"""

def ggf_metadata(**kwargs):
    """Decorator to annotate GGFs with catalog metadata.

    Args:
        latency_ms: Estimated P50 latency (int)
        tokens: Estimated token consumption (int)
        rate_limit: API rate limit per hour (int)
        data_sources: List of accessed sources (list[str])
        deterministic: Deterministic output (bool)
        cacheable: Safe to cache (bool)
        env_var: Required env variable (str)
        example: SPARQL usage example (str)
    """
    def decorator(func):
        func._ggf_metadata = kwargs
        return func
    return decorator

# Example usage in llmgraph_groq.py:
@ggf_metadata(
    latency_ms=800,
    tokens=500,
    rate_limit=1000,
    data_sources=["llm"],
    deterministic=False,
    cacheable=False,
    env_var="GROQ_API_KEY",
    example='BIND(ggf:LLM("Extract event JSON-LD") AS ?g)'
)
def llm_graph_groq_model(prompt, model=None, temperature=0.0):
    ...
```

### 4. Query API for LLM

**File:** `SPARQLLM/catalog/query.py`

```python
"""
Query GGF catalog programmatically.
Used by LLM planner to discover functions.
"""

from rdflib import Graph
from pathlib import Path

_CATALOG = None

def load_catalog():
    global _CATALOG
    if _CATALOG is None:
        catalog_path = Path(__file__).parent.parent / "data" / "ggf-catalog.ttl"
        _CATALOG = Graph()
        _CATALOG.parse(catalog_path, format="turtle")
    return _CATALOG

def find_ggfs_by_source(source: str) -> list[dict]:
    """Find GGFs accessing specific data source.

    Args:
        source: "filesystem", "llm", "web", "sql", "vector"

    Returns:
        List of dicts with name, signature, cost
    """
    g = load_catalog()
    query = f"""
    PREFIX ggf: <http://ggf.org/>
    SELECT ?name ?signature ?latency WHERE {{
        ?ggf a ggf:GraphGeneratingFunction ;
             rdfs:label ?name ;
             ggf:signature ?signature ;
             ggf:accessesDataSource "{source}" .
        OPTIONAL {{ ?ggf ggf:costLatencyMs ?latency }}
    }}
    """
    results = []
    for row in g.query(query):
        results.append({
            'name': str(row.name),
            'signature': str(row.signature),
            'latency_ms': float(row.latency) if row.latency else None
        })
    return results

def get_ggf_details(name: str) -> dict:
    """Get full metadata for specific GGF."""
    # SPARQL query to extract all properties
    pass
```

---

## Implementation Steps

### Week 1: Schema + Generator

1. **Day 1-2:** Define catalog schema (turtle ontology)
   - Create `SPARQLLM/data/ggf-schema.ttl`
   - Document all properties with examples

2. **Day 3-4:** Build catalog generator script
   - Implement AST parser for docstrings/type hints
   - Scan filesystem GGFs (readfile, readdir, csv)
   - Extract MCP tool registrations from `slm_mcp_tool.py`

3. **Day 5:** Manual metadata annotations
   - Create `@ggf_metadata` decorator
   - Annotate 10 key GGFs (LLM, SEARCH, FAISS, etc.)
   - Document annotation guidelines

### Week 2: Query API + Validation

4. **Day 6-7:** Implement query API
   - Create `catalog/query.py` with helper functions
   - Test queries: by source, by cost, by env requirements

5. **Day 8:** Integration with existing code
   - Add catalog generation to CI/CD (pre-commit hook)
   - Update `config.ini` with catalog path
   - Load catalog in `SPARQLLM.py` startup

6. **Day 9-10:** Testing + Documentation
   - Unit tests for generator + query API
   - Validate catalog completeness (all 44 functions)
   - Write developer guide for adding new GGFs

---

## Todo List

- [x] Design catalog schema (properties, classes, examples)
- [x] Implement AST-based metadata extractor
- [x] Scan all 39 GGF modules (verified from config.ini)
- [x] Create `@ggf_metadata` decorator
- [x] Annotate GGFs with cost/capability metadata
- [x] Build query API (`find_ggfs_by_source`, `get_ggf_details`)
- [x] Add catalog generation to build pipeline
- [x] Write unit tests (generator + query API) - 26 tests, 100% pass rate
- [x] Validate catalog completeness (39/39 functions)
- [x] Document annotation guidelines for future GGFs

---

## Success Criteria

1. [x] Catalog includes all 39 GGFs (verified from config.ini aliases)
2. [x] SPARQL query returns correct GGFs by source (6 query functions: by alias, source, cost, network, env requirements, summary)
3. [x] Generation script runs in <5s (actual: ~1s)
4. [x] Zero false positives (no non-GGF functions in catalog)
5. [x] Documentation: Guidelines for adding GGF metadata in future phases
6. [x] Unit test coverage: 26 tests, 100% pass rate
7. [x] Catalog metrics: 567 RDF triples, 21KB file size

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| AST parsing fails for complex code | Medium | Fallback to manual annotations; prioritize top 20 GGFs |
| Cost estimates wildly inaccurate | High | Start with static "low/medium/high" buckets; refine in Phase 4 |
| Catalog bloat (>100KB) | Low | Compress with gzip; load on-demand not startup |
| Metadata drift (code changes, catalog stale) | High | CI fails if catalog out-of-sync; auto-regen on commit |

---

## Security Considerations

- **No secrets in catalog**: Env var names only (GROQ_API_KEY), never values
- **Read-only catalog**: No runtime writes; regenerate from code only
- **Validate inputs**: Query API sanitizes SPARQL injection attempts

---

## Unresolved Questions

1. Should catalog track runtime statistics (actual P50 latency) or only static estimates?
2. How to version catalog for breaking changes (GGF signature updates)?
3. Include negative examples (common errors) in catalog for LLM training?

---

## Completion Summary

**Status:** COMPLETED - Nov 20, 2025

### Deliverables
1. **GGF Schema** (`SPARQLLM/data/ggf-schema.ttl`)
   - 18 RDF properties defined
   - Covers signature, cost, capabilities, requirements

2. **Catalog Generator** (`SPARQLLM/tools/generate_ggf_catalog.py`)
   - Scans 39 GGFs from config.ini
   - Extracts metadata from docstrings + decorators
   - Execution time: ~1s
   - Output: 567 RDF triples, 21KB

3. **Metadata Decorator** (`SPARQLLM/udf/metadata.py`)
   - `@ggf_metadata` annotation system
   - Extensible metadata framework for future GGFs

4. **Query API** (`SPARQLLM/catalog/query.py`)
   - 6 query functions: `find_ggfs_by_alias`, `find_ggfs_by_source`, `find_ggfs_by_cost`, `find_ggfs_by_network`, `find_ggfs_by_env_requirements`, `get_catalog_summary`
   - SPARQL-based catalog querying
   - Fast in-memory lookups

5. **Unit Tests** (`tests/unit/test_catalog.py`)
   - 26 tests covering all catalog functions
   - 100% pass rate
   - Coverage: generator, metadata extraction, query API

### Key Achievements
- All 39 GGFs indexed (verified against config.ini aliases)
- Smart data source inference with priority ordering
- Network requirement detection (local vs remote GGFs)
- Cost categorization (low/medium/high)
- Zero false positives
- Extensible annotation system for future GGFs

### Files Created/Modified
- Created: `SPARQLLM/data/ggf-schema.ttl` (1.2KB)
- Created: `SPARQLLM/data/ggf-catalog.ttl` (21KB, 567 triples)
- Created: `SPARQLLM/udf/metadata.py` (0.8KB)
- Created: `SPARQLLM/tools/generate_ggf_catalog.py` (4.5KB)
- Created: `SPARQLLM/catalog/query.py` (3.2KB)
- Created: `SPARQLLM/catalog/__init__.py` (0.4KB)
- Created: `tests/unit/test_catalog.py` (6.8KB)

### Next Phase
**Phase 2 - Two-Stage Compiler:** Use GGF catalog to plan and compile SPARQL queries with automatic function selection and cost optimization.
