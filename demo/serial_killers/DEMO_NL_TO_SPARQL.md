# Demo: Natural Language to SPARQL Query Generation

This demo shows the complete pipeline from natural language question to executed SPARQL query with results.

## Pipeline Overview

```
User Question (Natural Language)
         ↓
    LLM (Ollama)
         ↓
   JSON Logical Plan
         ↓
  Physical Compiler
         ↓
  SPARQL with GGFs
         ↓
    Query Execution
         ↓
      Results
```

---

## Quick Start

### Option 1: Python Script (Recommended)

```bash
# Activate virtual environment
source venv312_new/bin/activate

# Make sure Ollama is running
ollama serve &
ollama pull qwen2.5:3b

# Run demo with menu of questions
python demo/serial_killers/demo_nl_to_sparql.py
```

**Interactive mode:**
```bash
python demo/serial_killers/demo_nl_to_sparql.py --interactive
```

**Specific question:**
```bash
python demo/serial_killers/demo_nl_to_sparql.py --question "Who are the top 10 serial killers?"
```

**Generate query without executing:**
```bash
python demo/serial_killers/demo_nl_to_sparql.py --question "..." --no-execute
```

---

### Option 2: Bash Script

```bash
# Run demo
./demo/serial_killers/demo_query_generator.sh

# Or with question number (1-3)
./demo/serial_killers/demo_query_generator.sh 1

# Interactive mode
./demo/serial_killers/demo_query_generator.sh --interactive
```

---

## Example Demo Run

### Input
```
Question: Who are the top 10 serial killers with the most victims?
```

### Step 1: LLM Generates JSON Plan

**LLM:** Ollama (qwen2.5:3b)

**Generated JSON Logical Plan:**
```json
{
  "data_sources": [
    {
      "type": "csv",
      "path": "./demo/serial_killers/data/serial_killers_clean.csv",
      "alias": "killers"
    }
  ],
  "filters": [],
  "projections": [
    {
      "column": "name",
      "alias": "name"
    },
    {
      "column": "victim_max",
      "alias": "victims"
    },
    {
      "column": "country",
      "alias": "country"
    }
  ],
  "order_by": [
    {
      "column": "victim_max",
      "direction": "DESC"
    }
  ],
  "limit": 10
}
```

### Step 2: Physical Compiler Generates SPARQL

**Generated SPARQL Query:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?victims ?country
WHERE {
    # Load CSV data using GGF
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    # Query the generated RDF graph
    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:victim_max ?victims .
    }

    # Optional columns
    OPTIONAL {
        GRAPH ?csvGraph {
            ?row ex:country ?country .
        }
    }
}
ORDER BY DESC(?victims)
LIMIT 10
```

### Step 3: Query Execution

**Results:**
```
                          name  victims                     country
0          Murder Incorporated   1000.0               United States
1               Harold Shipman    250.0              United Kingdom
2                Luis Garavito    247.0  Colombia, Ecuador, Venezuela
3                    Pedro López    300.0       Colombia, Peru, Ecuador
4                    Javed Iqbal    100.0                      Pakistan
5                  Steven Massof    100.0               United States
6             Abboud and Khajawa    100.0                          Iraq
7  Delfina and María de Jesús...     91.0                        Mexico
8                    Niels Högel    300.0                       Germany
9                 Mikhail Popkov     86.0                        Russia
```

**Execution Time:** ~4 seconds

---

## Available Demo Questions

The demo includes 5 predefined questions:

1. **Top 10 killers** - "Who are the top 10 serial killers with the most victims?"
   - Tests: ORDER BY DESC, LIMIT, multiple columns

2. **Decade aggregation** - "How many serial killers were active in each decade?"
   - Tests: GROUP BY, COUNT, date handling

3. **Country aggregation** - "Which countries have the most serial killers?"
   - Tests: GROUP BY, COUNT, text aggregation

4. **Filtered query** - "Show me serial killers from the United States in the 1970s"
   - Tests: Multiple filters (country AND decade), FILTER clause

5. **Numeric filter** - "Which serial killers had more than 50 victims?"
   - Tests: Numeric filtering, comparison operators

---

## Understanding the Output

### JSON Logical Plan

The LLM generates a logical plan that is **database-agnostic**:

```json
{
  "data_sources": [/* Where to get data */],
  "filters": [/* What conditions to apply */],
  "projections": [/* Which columns to return */],
  "aggregations": [/* GROUP BY, COUNT, etc */],
  "order_by": [/* How to sort */],
  "limit": /* How many rows */
}
```

**Key Features:**
- No SPARQL syntax (LLM doesn't need to know SPARQL)
- No GGF function names (abstract data sources)
- Database-independent structure
- Easy to validate and debug

### Physical SPARQL Query

The compiler translates the logical plan to **executable SPARQL**:

```sparql
# Loads CSV using Graph Generating Function
BIND(ggf:SLM-CSV("./path/to/data.csv") AS ?csvGraph)

# Queries the dynamically generated RDF graph
GRAPH ?csvGraph {
    ?row ex:column_name ?value .
}
```

**Key Features:**
- Uses GGF functions (SLM-CSV, SLM-LLMGRAPH, etc.)
- Generates named graphs at runtime
- Standard SPARQL syntax
- Optimized for execution

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Question                            │
│         "Who are the top 10 serial killers?"                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Query Generator                             │
│  • Uses LLM (Ollama/OpenAI/Groq)                            │
│  • Understands dataset schema                               │
│  • Generates JSON logical plan                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 JSON Logical Plan                            │
│  {                                                           │
│    "data_sources": [...],                                   │
│    "projections": [...],                                    │
│    "filters": [...],                                        │
│    "order_by": [...],                                       │
│    "limit": 10                                              │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│               Physical Compiler                              │
│  • Translates JSON → SPARQL                                 │
│  • Maps data sources → GGF functions                        │
│  • Handles filters, aggregations, sorting                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  SPARQL with GGFs                            │
│  PREFIX ggf: <http://ggf.org/>                              │
│  SELECT ?name ?victims WHERE {                              │
│    BIND(ggf:SLM-CSV("data.csv") AS ?g)                      │
│    GRAPH ?g { ?row ex:name ?name }                          │
│  }                                                           │
│  ORDER BY DESC(?victims) LIMIT 10                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 SPARQLLM Engine                              │
│  • Executes GGF functions                                   │
│  • Generates RDF graphs dynamically                         │
│  • Returns query results                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Results                                 │
│  Murder Incorporated    1000 victims    United States       │
│  Harold Shipman          250 victims    United Kingdom      │
│  ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Query Generator (`demo/query_generator.py`)

**Purpose:** Translate natural language to structured JSON plan

**LLM Providers Supported:**
- Ollama (local, free) - `--provider ollama`
- OpenAI (cloud, paid) - `--provider openai`
- Groq (cloud, fast, free tier) - `--provider groq`

**Input Example:**
```
"Who are the top 10 serial killers with the most victims?"
```

**Output Example:**
```json
{
  "data_sources": [{"type": "csv", "path": "...", "alias": "killers"}],
  "projections": [{"column": "name"}, {"column": "victim_max"}],
  "order_by": [{"column": "victim_max", "direction": "DESC"}],
  "limit": 10
}
```

#### 2. Physical Compiler (`SPARQLLM/compiler/physical_compiler.py`)

**Purpose:** Translate JSON plan to executable SPARQL

**Mapping Rules:**
- `data_sources.type = "csv"` → `BIND(ggf:SLM-CSV(...) AS ?g)`
- `projections` → `SELECT ?var1 ?var2`
- `filters` → `FILTER(?var > value)`
- `aggregations` → `GROUP BY ?var, COUNT(?var)`
- `order_by` → `ORDER BY ASC/DESC(?var)`
- `limit` → `LIMIT N`

**Optimizations:**
- Handles NULL columns with OPTIONAL
- Generates efficient graph patterns
- Minimizes GGF function calls

#### 3. SPARQLLM Engine (`SPARQLLM/udf/SPARQLLM.py`)

**Purpose:** Execute SPARQL with GGF functions

**Execution Flow:**
1. Parse SPARQL query
2. Detect GGF function calls (BIND with ggf: prefix)
3. Execute GGF → generate RDF graph → store in named graph
4. Evaluate GRAPH clauses using generated graphs
5. Return query results as DataFrame

---

## Testing the Demo

### Test 1: Simple Query
```bash
python demo/serial_killers/demo_nl_to_sparql.py \
  --question "Who are the top 5 serial killers?"
```

**Expected:** Query with ORDER BY DESC, LIMIT 5

### Test 2: Aggregation
```bash
python demo/serial_killers/demo_nl_to_sparql.py \
  --question "How many serial killers per country?"
```

**Expected:** Query with GROUP BY, COUNT

### Test 3: Filtering
```bash
python demo/serial_killers/demo_nl_to_sparql.py \
  --question "Serial killers from Germany with more than 20 victims"
```

**Expected:** Query with multiple FILTER clauses

### Test 4: Complex Question
```bash
python demo/serial_killers/demo_nl_to_sparql.py \
  --question "What is the average number of victims per decade?"
```

**Expected:** Query with GROUP BY decade, AVG aggregation

---

## Debugging

### Enable Verbose Output

```python
# In demo_nl_to_sparql.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Generated Plan

```bash
# Generate query without executing
python demo/serial_killers/demo_nl_to_sparql.py \
  --question "..." \
  --no-execute
```

### Test Physical Compiler

```python
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler
import json

# Load JSON plan
with open('plan.json') as f:
    plan = json.load(f)

# Compile
compiler = PhysicalCompiler()
sparql = compiler.compile(plan)
print(sparql)
```

---

## Troubleshooting

### Issue 1: "Ollama is not running"

**Solution:**
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags

# Pull model if needed
ollama pull qwen2.5:3b
```

### Issue 2: "Query returns empty results"

**Possible Causes:**
1. LLM generated incorrect column names
2. Dataset path is wrong
3. Filters are too restrictive

**Debug:**
```bash
# Check generated SPARQL
python demo/serial_killers/demo_nl_to_sparql.py --question "..." --no-execute

# Check dataset columns
head -1 demo/serial_killers/data/serial_killers_clean.csv
```

### Issue 3: "JSON plan is invalid"

**Solution:** The LLM may need better prompting. Check `demo/query_generator.py`:

```python
# Update system prompt to be more specific
SYSTEM_PROMPT = """
You are a query generator for a serial killers dataset.
Dataset columns: name, country, decade, victim_min, victim_max
Generate JSON with exact column names.
"""
```

---

## Extending the Demo

### Add New LLM Provider

Edit `demo/query_generator.py`:

```python
def _init_custom_llm(self, model, api_key):
    """Initialize custom LLM provider."""
    from your_llm_client import Client
    self.client = Client(api_key=api_key)
    self.model = model
    self.llm_available = True

# Update __init__
elif provider == 'custom':
    self._init_custom_llm(model, api_key)
```

### Add New Question Templates

Edit `demo/serial_killers/demo_nl_to_sparql.py`:

```python
demo_questions = [
    # ... existing questions
    "Show me serial killers who operated internationally",
    "What were the most active decades for serial killers?",
    "List female serial killers",
]
```

### Support Additional Data Sources

Update `SPARQLLM/compiler/physical_compiler.py`:

```python
def _compile_data_source(self, source):
    if source['type'] == 'csv':
        return f"ggf:SLM-CSV('{source['path']}')"
    elif source['type'] == 'json':
        return f"ggf:SLM-JSON('{source['path']}')"
    elif source['type'] == 'api':
        return f"ggf:SLM-API('{source['url']}')"
```

---

## Performance

### Typical Timings

| Step | Time | Notes |
|------|------|-------|
| LLM Generation | ~2-5s | Depends on model size |
| SPARQL Compilation | <100ms | Fast, deterministic |
| Query Execution | ~4s | CSV parsing + RDF generation |
| **Total** | **~6-9s** | End-to-end pipeline |

### Optimization Tips

1. **Use smaller LLM models** (qwen2.5:3b vs llama3.1:8b)
2. **Cache JSON plans** for repeated questions
3. **Pre-load CSV data** in production (avoid re-parsing)
4. **Limit result sets** (use LIMIT in questions)

---

## Next Steps

1. **Try more questions** - Use `--interactive` mode
2. **Add web search** - Extend with `SLM-GETTEXT` for Wikipedia
3. **Add LLM analysis** - Use `SLM-LLMGRAPH` for semantic extraction
4. **Build UI** - Create web interface for query generation
5. **Add caching** - Cache generated queries for common questions

---

## References

- Query Generator: `demo/query_generator.py`
- Physical Compiler: `SPARQLLM/compiler/physical_compiler.py`
- SPARQLLM Engine: `SPARQLLM/udf/SPARQLLM.py`
- Dataset: `demo/serial_killers/data/serial_killers_clean.csv`
- Demo Questions: `demo/serial_killers/DEMO_QUESTIONS.md`

---

**Last Updated:** 2025-11-21
