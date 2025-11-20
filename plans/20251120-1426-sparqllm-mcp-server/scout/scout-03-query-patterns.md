# Scout Report: SPARQL Query Patterns & GGF Usage

**Analyzed:** 60+ SPARQL query files across 8 categories
**Duration:** ~2 minutes

## 1. Filesystem Operations

**Pattern:** Path resolution → Data parsing → RDF graph

```sparql
BIND(ggf:SLM-FILE("./data/results.csv") as ?value)
BIND(ggf:SLM-CSV(?value) AS ?g)
GRAPH ?g { ?x ex:city ?z . }
```

**Features:**
- Chain operations: file path → parser → RDF
- Directory listing returns path/type/size metadata
- Supports CSV, HTML, TXT, RDF formats

## 2. LLM Integration

**Basic pattern:**
```sparql
BIND(ggf:LLM(?prompt) AS ?g)
GRAPH ?g { ?root a schema:Event; schema:name ?name . }
```

**Complex 3-step pipeline** (Search → Snapshot → LLM):
```sparql
# Step 1: Web search
BIND(ggf:SEARCH(?keywords, 3) AS ?gSearch)
GRAPH ?gSearch {
    ?feed a schema:DataFeed; schema:dataFeedElement ?item .
    ?item schema:url ?url .
}

# Step 2: Browser snapshot
BIND(ggf:SNAP(?url) AS ?gSnap)
GRAPH ?gSnap { ?page schema:text ?text . }

# Step 3: LLM extraction
BIND(ggf:LLM(CONCAT("Extract...", ?text), "llama-3.3-70b-versatile", 0.0) AS ?gLLM)
GRAPH ?gLLM { ?entity a schema:Thing; schema:name ?name . }
```

**Features:**
- Model selection support
- Temperature control
- Returns schema.org RDF graphs

## 3. Raw MCP-TOOL (Current Low-Level API)

**GitHub example:**
```sparql
BIND(ggf:MCP-TOOL("github", "github.pullRequests.list",
      ggf:OBJ("owner", "twitter", "repo", "the-algorithm")) AS ?g)
GRAPH ?g {
    ?repo a schema:Repository; schema:hasPart ?pr .
    ?pr schema:name ?title .
}
```

**PostgreSQL example:**
```sparql
BIND(ggf:MCP-TOOL("postgres", "postgres.sql.query",
      ggf:OBJ("sql", "SELECT * FROM users LIMIT 10")) AS ?g)
GRAPH ?g {
    ?dataset a schema:Dataset; schema:hasPart ?obs .
    ?obs schema:PropertyValue ?prop .
}
```

**FAISS search:**
```sparql
BIND(ggf:MCP-TOOL("faiss", "faiss.search_index",
      ggf:OBJ("query", ?ragQuery, "k", 3)) AS ?g)
```

## 4. Recursion Patterns

**Recursive graph expansion:**
```sparql
BIND(ggf:SLM-GRAPH("PREFIX ex: <...> ex:a ex:linkedTo ex:b .") AS ?ginit)
BIND(ggf:SLM-RECURSE(?queryStr, ?ginit, 10) AS ?out)
GRAPH ?out { ?s ?p ?o . }
```

**Features:**
- Applies SPARQL CONSTRUCT iteratively
- Fixpoint detection or iteration limit
- Used for transitive closures, graph expansion

## 5. Web Scraping

**High-level aliases:**
```sparql
BIND(ggf:SEARCH(?keywords, ?limit) AS ?g)  # DuckDuckGo
BIND(ggf:SNAP(?url) AS ?g)                 # Browser snapshot
GRAPH ?g {
    ?feed a schema:DataFeed; schema:dataFeedElement ?item .
    ?item schema:headline ?title; schema:url ?url .
}
```

## Key I/O Characteristics

### Inputs
- **Strings**: prompts, queries, URLs, SQL
- **URIs**: graph references
- **Numbers**: limits, iterations, temperature
- **Lists**: model names via VALUES clause

### Outputs
- **Always**: Named graph URIs (BNode or URIRef)
- **Content**: schema.org types + custom properties
- **Metadata**: Optional `prov:generatedAtTime`, `schema:duration`

## Chaining Strategy

**Sequential binding pattern:**
```sparql
# Step 1: Generate G1
BIND(ggf:FUNCTION1(?input) AS ?g1)

# Step 2: Extract from G1, generate G2
GRAPH ?g1 { ?x ?p ?value . }
BIND(ggf:FUNCTION2(?value) AS ?g2)

# Step 3: Extract from G2, generate G3
GRAPH ?g2 { ?y ?q ?result . }
BIND(ggf:FUNCTION3(?result) AS ?g3)

# Step 4: Final extraction
GRAPH ?g3 { ?s ?r ?finalResult . }
```

**No accumulation** - each step consumes previous output as input.

## MCP Mapping Opportunities

### Current (Verbose)
```sparql
BIND(ggf:MCP-TOOL("server", "tool.method", ggf:OBJ(...)) AS ?g)
```

### Could Become (High-Level Aliases)
```sparql
BIND(ggf:LLM(?prompt, ?model, ?temp) AS ?g)
BIND(ggf:SEARCH(?query, ?limit) AS ?g)
BIND(ggf:SQL(?sql) AS ?g)
BIND(ggf:FAISS(?query, ?k) AS ?g)
BIND(ggf:GITHUB(?endpoint, ?params) AS ?g)
```

## Schema Standardization Observed

| Domain | Schema.org Type | Properties |
|--------|-----------------|------------|
| Web results | DataFeed → DataFeedItem → WebPage | headline, url, text |
| DB results | Dataset → Observation → PropertyValue | name, value |
| LLM results | Event, Person, Thing | name, startDate, description |
| Scores | Custom | example.org/score |

## Common Query Files Analyzed

- `queries/mcp/mcp_github.sparql` - GitHub API integration
- `queries/mcp/mcp_duckduckgo_search.sparql` - Web search
- `queries/mcp/mcp_postgres_sql.sparql` - SQL queries
- `queries/LLM/simple-groq.sparql` - LLM text extraction
- `queries/filesystem/simple-csv.sparql` - CSV parsing
- `queries/faiss/faiss_search.sparql` - Vector similarity search

## Patterns for MCP Server Design

1. **Extract structured data from files**: File → Parser → LLM → Schema
2. **RAG search**: Query → Vector search → LLM synthesis
3. **Web to knowledge**: URL → Scrape → LLM extraction → RDF
4. **Database query**: SQL → Results → RDF mapping
5. **Recursive expansion**: Seed → Pattern → Iterate → Graph
