# MCP Ecosystem & Graph Generating Functions Design Research

## 1. MCP Protocol Standards (Anthropic)

**Tool Specification Format:**
- Tools declared via `tools/list` JSON-RPC method. Returns name, description, and JSON Schema for input args.
- Example from SPARQLLM client:
  ```python
  # slm_mcp_tool.py L45-56: Tools registered as static handlers
  _MCP.register_static_tool("github", "github.pullRequests.list", lambda a: _tool_dispatch(a, ...))
  _MCP.register_static_tool("postgres", "postgres.sql.query", lambda a: _pg_provider.call(...))
  ```

**Server Discovery Mechanisms:**
- **Static Registration** (current SPARQLLM approach): Tools hardcoded into client via `connect_static()` + provider lambdas.
- **HTTP-based**: `tools/list` polling from MCP server endpoint.
- **STDIO Protocol**: JSON-RPC over subprocess pipes (supported in client.py L15-19).
- **MCP Registry** (new 2025): Official published catalog for discoverable servers.

**Authentication Patterns:**
- Bearer token support (slm_mcp_tool.py L33: `_MCP.connect_http(..., f"Bearer {gh_token}")`).
- OAuth 2 for third-party integrations (GraphQL MCP, Azure AI Agent Service).
- Environment-based secrets (GITHUB_TOKEN, OPENAI_API_KEY).

**Error Handling:**
- JSON-RPC protocol errors (unknown tools, invalid args) vs tool execution errors (API failures).
- SPARQLLM wraps errors in RDF graphs (slm_mcp_tool.py L383-408): error status + message as triples.

**Adoption Status:**
- Anthropic standard (Nov 2024), now adopted by OpenAI (Mar 2025), Google DeepMind (Apr 2025).
- SDKs: Python, TypeScript, C#, Java available. Becoming *de facto* interop standard for AI-tool integration.

## 2. GGF Design Patterns from SPARQLLM

**Core Pattern - Graph-Returning Functions:**
```python
# slm_mcp_tool.py L254-409: Signature pattern
def slm_mcp_tool(handle: str, tool_name: str, args_json: str, graph_name_hint: str = None) -> Union[URIRef, None]:
    # 1) Call MCP tool
    # 2) Convert result to JSON-LD
    # 3) Parse JSON-LD into named graph
    # 4) Attach PROV-O metadata (start_dt, end_dt, duration_s)
    # 5) Return graph IRI
```

**Content-Addressed Graphs (Stable URIs):**
```python
# slm_mcp_tool.py L179-181: SHA256 hash of JSON-LD → stable graph IRI
h = hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
graph_uri = URIRef(graph_name_hint or f"urn:mcp:graph:{h}")
```

**Provenance Annotation (PROV-O):**
- slm_mcp_tool.py L207-252: `_attach_prov()` adds Activity, Agent, Entity triples.
- Metrics: start_dt, end_dt, duration_s automatically recorded.
- Source hint (e.g., `https://api.github.com`) tracked as `prov:wasDerivedFrom`.

**Recursive Patterns (RECURSE):**
```python
# recurse.py L24-70: Recursive fixpoint computation on graphs
def recurse(query_str, ginit, max_depth_lit):
    def func_recurse_on(gin_rec, depth=0):
        result = store.graph(gin_rec).query(query_str)  # CONSTRUCT query
        if len(result) == len(previous):  # Fixpoint check
            return graph_uri
        if depth <= max_depth:
            return func_recurse_on(gout.identifier, depth+1)
```

**MCP Tool → GGF Wrapper Pattern:**
1. User calls `ggf:LLM(prompt)` in SPARQL.
2. Alias resolver (alias.py L25-56) unpacks into `slm_mcp_tool("groq", "groq.generate_jsonld", {...})`.
3. MCP tool returns JSON-LD, which is materialized as named graph.
4. SPARQL can query result graph in subsequent GRAPH clauses.

## 3. Self-Describing Function Catalogs

**Current Approach (Implicit):**
- SPARQLLM exposes GGF names via URI namespace `http://ggf.org/` in queries.
- Examples: `ggf:LLM`, `ggf:SEARCH`, `ggf:SNAP`, `ggf:FAISS`.
- Aliases auto-expand via rdflib custom function registration (alias.py L59, L99, L142).

**Discovery Opportunity:**
- MCP `tools/list` can be queried to self-populate available functions.
- Example: LLM could ask "what tools access SQL?" via semantic search over tool descriptions.
- **GraphQL MCP** (2025 innovation): Introspection schema → dynamic tool generation. SPARQLLM could do similar for SQL (postgres provider).

**Example - Queryable Catalog:**
```sparql
PREFIX ggf: <http://ggf.org/>
SELECT ?tool ?desc ?inputSchema WHERE {
  ?tool a ggf:MCPTool ;
        rdfs:label ?tool_name ;
        ggf:handles "postgres" ;
        schema:description ?desc ;
        ggf:inputSchema ?inputSchema .
  FILTER CONTAINS(?desc, "SQL")
}
```

## 4. GGF Composability

**Output → Input Chaining:**
```sparql
# Example: SEARCH → LLM → FAISS
BIND(ggf:SEARCH("physics") AS ?g1)
GRAPH ?g1 { ?result schema:url ?url }
BIND(ggf:SNAP(?url) AS ?g2)
GRAPH ?g2 { ?text schema:text ?webpage_text }
BIND(ggf:LLM(CONCAT("Summarize: ", ?webpage_text)) AS ?g3)
GRAPH ?g3 { ?summary schema:text ?summary_text }
```

**Dependency Resolution:**
- SPARQL optimiser already orders joins; GRAPH clauses execute when variables bound.
- GGFs compose naturally via lazy evaluation (store uses `Dataset` L55 in SPARQLLM.py).

**Circular Dependency Prevention:**
- RECURSE enforces fixpoint detection (recurse.py L50-52): stops if output == input graph size.
- No explicit cycle detection needed; CONSTRUCT query results drive termination.

**Recursive GGF Patterns:**
- `RECURSE(query_str, ginit, max_depth)` applies CONSTRUCT recursively until fixpoint or max_depth.
- Useful for: transitive closure, iterative enrichment, depth-limited BFS.

## 5. Cost & Capability Metadata

**Current Metadata (Implicit in PROV):**
```python
# slm_mcp_tool.py L232-233: Duration automatically recorded
named_graph.add((act, SCHEMA.duration, Literal(round(duration_s, 6), datatype=XSD.decimal)))
named_graph.add((graph_uri, SCHEMA.duration, Literal(round(duration_s, 6), datatype=XSD.decimal)))
```

**Missing: Cost/Capability Signals**
- No explicit rate-limit annotation (GitHub API limit: 60 req/hr free tier).
- No LLM cost metadata (Groq token pricing not tracked).
- No cache-ability flags (FAISS is deterministic, Groq varies by temperature).

**Recommended Annotations:**
```turtle
ggf:groq.generate_jsonld
  a ggf:Tool ;
  schema:name "Groq LLM Generation" ;
  ggf:costPerCall 0.001 ;
  ggf:latencyMs 500 ;
  ggf:rateLimitPerHour 1000 ;
  ggf:requiresPrecondition [
    a ggf:Precondition ;
    ggf:envVar "GROQ_API_KEY" ;
    ggf:resourceType "API Key"
  ] ;
  ggf:cacheable false ;  # temperature variation
  ggf:deterministic false ;
  ggf:accessesResource [ a ggf:ExternalAPI ; schema:url "https://api.groq.com" ]
```

## Key Findings & Recommendations

1. **MCP is becoming standard**: Anthropic → OpenAI → Google DeepMind adoption (2024-2025).
2. **GGF ↔ MCP alignment natural**: Both return structured data (JSON-LD → RDF graphs). Use MCP static registration for now, migrate to dynamic discovery.
3. **Composability via lazy evaluation**: SPARQL optimiser handles ordering. RECURSE pattern for fixpoints.
4. **Self-describing catalogs underexplored**: Could expose GGF registry as RDF queries (TBD for next phase).
5. **Cost tracking missing**: Add optional `ggf:costMetadata` triple pattern for LLM budget awareness.

## Unresolved Questions

- How to detect circular tool dependencies at compile-time (before execution)?
- Should GGF catalog be queried by LLM dynamically, or statically indexed?
- How to balance MCP spec conformance vs SPARQLLM-specific optimisations (content-addressed graphs)?
- Cost/latency metadata: standard ontology (schema.org extension vs custom)?
