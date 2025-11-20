# Scout Report: CLI Query Execution Flow

**Scope:** SPARQL query execution via CLI
**Duration:** ~2 minutes

## Entry Point & CLI Command

### `/Users/e23e889b/Documents/2025/2025_11/SPARQLLM/setup.py`
- Maps `slm-run` command → `SPARQLLM.cli.slm:slm_cmd`

### `/SPARQLLM/cli/slm.py` (172 lines)
**Main function:** `slm_cmd()` - Click command handler

**CLI Arguments:**
- `-q, --query` - Inline SPARQL query string
- `-f, --file` - SPARQL query file path
- `-c, --config` - Config file (default: config.ini)
- `-l, --load` - Pre-load RDF data file
- `-fo, --format` - RDF format (turtle, xml, nquads, jsonld)
- `-d, --debug` - Debug logging
- `-k, --keep-store` - Save intermediate graphs (n-quads)
- `-o, --output-result` - Output file for results

**Execution Flow (lines 101-172):**
1. Read query from `-q` or `-f`
2. Initialize `ConfigSingleton` from config file
3. Pre-load RDF data via `store.parse()` if provided
4. Detect query type: `is_update_query()` → UPDATE vs SELECT/CONSTRUCT
5. Execute: `store.query()` or `store.update()`
6. Format results: CSV (SELECT) or Turtle (CONSTRUCT)
7. Persist store: `store.serialize(format="nquads")` if `--keep-store`

## Configuration Management

### `/SPARQLLM/config.py` (93 lines)
**ConfigSingleton class** - Singleton pattern for config

**__new__() method (lines 22-53):**
1. Read INI file via `configparser.ConfigParser()`
2. Iterate **[Associations]** section
3. Map aliases → Python function paths
4. Dynamically import modules: `importlib.import_module(module_name)`
5. Register with rdflib: `register_custom_function(URIRef(f"http://ggf.org/{ALIAS}"), func)`

**Example registration:**
```python
# config.ini
[Associations]
SLM-CSV = SPARQLLM.udf.mycsv.slm_csv

# Becomes
register_custom_function(URIRef("http://ggf.org/SLM-CSV"), slm_csv)
```

### `/config.ini`
**[Associations]** - Function registration:
```ini
SLM-FILE = SPARQLLM.udf.absPath.absPath
SLM-CSV = SPARQLLM.udf.mycsv.slm_csv
LLM = SPARQLLM.udf.mcp.alias._alias_llm
SLM-RECURSE = SPARQLLM.udf.recurse.recurse
```

**[Requests]** - Runtime parameters:
```ini
SLM-TIMEOUT = 120
SLM-OLLAMA-MODEL = llama3.1:latest
SLM-GROQ-MODEL = llama-3.3-70b-versatile
```

## Query Execution Engine

### `/SPARQLLM/udf/SPARQLLM.py`
**Global store (line 55):** `store = Dataset()`

**Custom evaluator (lines 37-51):**
- `customEval()` patches join evaluation
- `my_evaljoin()` intercepts "Join" operations
- Delegates to `evalLazyJoin()` - ensures named graphs materialize before GRAPH clauses

**reset_store() (lines 57-62):** Clears graphs between sessions

## UDF Pattern Example

### `/SPARQLLM/udf/mycsv.py`
**Signature:** `def slm_csv(file_url)`

**Pattern:**
1. Receive argument from SPARQL BIND()
2. Create named graph: `store.get_context(graph_uri)`
3. Build RDF triples, add to graph
4. Return `URIRef` (not string/literal)

**Import:** `from SPARQLLM.udf.SPARQLLM import store`

## Result Formatting

### `/SPARQLLM/utils/utils.py`
`print_result_as_table()` - Formats SELECT results as pandas DataFrame

### slm.py output handling (lines 150-168)
- **SELECT:** Write CSV or print table
- **CONSTRUCT:** Serialize to Turtle

## Execution Flow Summary

```
CLI: slm-run --config config.ini -f query.sparql
    ↓
slm_cmd() parses CLI args
    ↓
ConfigSingleton() loads config.ini
    ↓
For each [Associations]: register_custom_function(URIRef(http://ggf.org/{ALIAS}), func)
    ↓
Optional: store.parse(data_file)
    ↓
is_update_query() determines type
    ↓
store.query(query_str) or store.update(query_str)
    ↓
During execution: BIND(ggf:FUNCTION(?args) AS ?g) invokes UDF
    ↓
UDF returns graph URI
    ↓
Format results: CSV/Turtle
    ↓
Optional: store.serialize(keep_store, format="nquads")
```

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `slm_cmd()` | slm.py | Main CLI orchestrator |
| `is_update_query()` | slm.py | Detect UPDATE vs SELECT |
| `ConfigSingleton.__new__()` | config.py | Load config, register UDFs |
| `register_custom_function()` | rdflib | Register UDF with SPARQL engine |
| `store.query()` | rdflib Dataset | Execute SPARQL query |
| `my_evaljoin()` | SPARQLLM.py | Ensure graphs materialize before GRAPH clauses |

## Query Example

**File:** `queries/filesystem/simple-csv.sparql`
```sparql
PREFIX ggf: <http://ggf.org/>
SELECT ?x ?z WHERE {
    BIND(ggf:SLM-FILE("./data/results.csv") as ?value)
    BIND(ggf:SLM-CSV(?value) AS ?g)
    GRAPH ?g { ?x ex:city ?z . }
}
```

UDFs invoked via `BIND(ggf:ALIAS(args) AS ?g)`, return graph URIs consumed by `GRAPH ?g { ... }`.
