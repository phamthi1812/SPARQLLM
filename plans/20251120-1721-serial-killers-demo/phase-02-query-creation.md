# Phase 2: Query Creation (6 SPARQL Queries)

**Duration:** 3 days
**Dependencies:** Phase 1 (dataset prepared)
**Status:** Not Started

---

## Objectives

1. Create 6 SPARQL queries demonstrating different GGF combinations
2. Design JSON logical plans for each query
3. Validate queries execute successfully
4. Document expected outputs and query patterns

---

## Query Design Principles

1. **Progressive Complexity:** Q1 (simple) → Q6 (multi-step)
2. **GGF Diversity:** Use different GGFs across queries
3. **Real Insights:** Queries answer meaningful questions
4. **Local-First:** Q1-Q4 use only filesystem + LLM (zero cost)
5. **Optional Web:** Q5-Q6 use web search (user opt-in)
6. **Two-Stage Ready:** All queries testable via QueryGenerator

---

## Query 1: Top 10 Serial Killers by Victim Count

**Category:** Basic Aggregation
**GGFs:** SLM-CSV
**Complexity:** Low
**Cost:** <100ms, zero API calls

### Natural Language Question
"Show me the top 10 serial killers by number of victims"

### Logical Plan (JSON)
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-CSV",
        "args": {
          "file": "./demo/serial_killers/data/serial_killers_clean.csv"
        }
      },
      "bindings": {
        "name": "?name",
        "victimMin": "?victimMin",
        "victimMax": "?victimMax"
      }
    }
  ],
  "output": {
    "variables": ["name", "victimMin", "victimMax"],
    "order_by": [{"variable": "victimMin", "order": "DESC"}],
    "limit": 10
  }
}
```

### Compiled SPARQL
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?name ?victimMin ?victimMax
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row schema:name ?name .
        ?row schema:victimMin ?victimMin .
        ?row schema:victimMax ?victimMax .
    }
}
ORDER BY DESC(?victimMin)
LIMIT 10
```

### Expected Output
```
name                    victimMin  victimMax
Harold Shipman          218        218
Luis Garavito           193        193
Pedro López             110        300
Javed Iqbal             100        100
Mikhail Popkov          83         83
...
```

### File Location
- Logical plan: `demo/serial_killers/queries/plans/q1_top_victims.json`
- SPARQL: `demo/serial_killers/queries/q1_top_victims.sparql`

---

## Query 2: How Did Methods Change by Decade?

**Category:** Temporal Analysis + LLM Categorization
**GGFs:** SLM-CSV, LLM
**Complexity:** Medium
**Cost:** ~30s (LLM categorization), ~50-100 LLM calls

### Natural Language Question
"How did killing methods evolve over decades? Categorize methods by era."

### Logical Plan (JSON)
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-CSV",
        "args": {
          "file": "./demo/serial_killers/data/serial_killers_clean.csv"
        }
      },
      "bindings": {
        "name": "?name",
        "decade": "?decade",
        "methods": "?methods"
      },
      "filters": ["BOUND(?methods)", "BOUND(?decade)"]
    },
    {
      "id": "step2",
      "operation": "llm_extract",
      "ggf": {
        "name": "LLM",
        "args": {
          "prompt": "Categorize this killing method into ONE category: 'poison', 'firearm', 'stabbing', 'strangulation', 'blunt force', 'other'. Methods: ?methods. Return ONLY the category name."
        }
      },
      "depends_on": ["step1"],
      "bindings": {
        "category": "?category"
      }
    }
  ],
  "output": {
    "variables": ["decade", "category"],
    "distinct": false
  }
}
```

### Compiled SPARQL
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?decade ?category
WHERE {
    # Step 1: Load CSV
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?step1Graph)

    GRAPH ?step1Graph {
        ?row schema:name ?name .
        ?row schema:decade ?decade .
        ?row schema:methods ?methods .
        FILTER(BOUND(?methods))
        FILTER(BOUND(?decade))
    }

    # Step 2: LLM categorization
    BIND(CONCAT("Categorize this killing method into ONE category: 'poison', 'firearm', 'stabbing', 'strangulation', 'blunt force', 'other'. Methods: ", ?methods, ". Return ONLY the category name.") AS ?prompt)
    BIND(ggf:LLM(?prompt) AS ?step2Graph)

    GRAPH ?step2Graph {
        ?result schema:text ?category .
    }
}
```

### Expected Output
```
decade   category
1960s    firearm
1960s    strangulation
1970s    poison
1970s    stabbing
1980s    strangulation
...
```

### Post-Processing
Python script aggregates results:
```python
df = pd.read_csv('results.csv')
pivot = df.groupby(['decade', 'category']).size().unstack(fill_value=0)
print(pivot)
```

### File Location
- Logical plan: `demo/serial_killers/queries/plans/q2_methods_by_decade.json`
- SPARQL: `demo/serial_killers/queries/q2_methods_by_decade.sparql`
- Post-processing: `demo/serial_killers/queries/q2_aggregate.py`

---

## Query 3: Get Wikipedia Summary for Specific Serial Killer

**Category:** CSV → Web Scraping
**GGFs:** SLM-CSV, SLM-GETTEXT
**Complexity:** Medium
**Cost:** ~5s (web fetch), 1 HTTP request

### Natural Language Question
"Get the Wikipedia summary for Ted Bundy"

### Logical Plan (JSON)
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-CSV",
        "args": {
          "file": "./demo/serial_killers/data/serial_killers_clean.csv"
        }
      },
      "bindings": {
        "name": "?name",
        "wikipediaUrl": "?wikipediaUrl"
      },
      "filters": ["?name = 'Ted Bundy'"]
    },
    {
      "id": "step2",
      "operation": "web_scrape",
      "ggf": {
        "name": "SLM-GETTEXT",
        "args": {
          "url": "?wikipediaUrl"
        }
      },
      "depends_on": ["step1"],
      "bindings": {
        "summary": "?summary"
      }
    }
  ],
  "output": {
    "variables": ["name", "summary"],
    "limit": 1
  }
}
```

### Compiled SPARQL
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?name ?summary
WHERE {
    # Step 1: Get Wikipedia URL from CSV
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?step1Graph)

    GRAPH ?step1Graph {
        ?row schema:name ?name .
        ?row schema:wikipediaUrl ?wikipediaUrl .
        FILTER(?name = "Ted Bundy")
    }

    # Step 2: Scrape Wikipedia page
    BIND(ggf:SLM-GETTEXT(?wikipediaUrl) AS ?step2Graph)

    GRAPH ?step2Graph {
        ?page schema:text ?summary .
    }
}
LIMIT 1
```

### Expected Output
```
name        summary
Ted Bundy   Theodore Robert Bundy (born Theodore Robert Cowell; November 24, 1946 – January 24, 1989) was an American serial killer...
```

### File Location
- Logical plan: `demo/serial_killers/queries/plans/q3_wikipedia_summary.json`
- SPARQL: `demo/serial_killers/queries/q3_wikipedia_summary.sparql`

---

## Query 4: Extract Structured Methods from Notes

**Category:** LLM Extraction from CSV
**GGFs:** SLM-CSV, LLM
**Complexity:** Medium
**Cost:** ~20s, ~20 LLM calls

### Natural Language Question
"Extract specific methods used by serial killers from their notes field"

### Logical Plan (JSON)
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-CSV",
        "args": {
          "file": "./demo/serial_killers/data/serial_killers_clean.csv"
        }
      },
      "bindings": {
        "name": "?name",
        "notes": "?notes"
      },
      "filters": ["BOUND(?notes)", "STRLEN(?notes) > 50"]
    },
    {
      "id": "step2",
      "operation": "llm_extract",
      "ggf": {
        "name": "LLM",
        "args": {
          "prompt": "Extract the specific killing method(s) from this text. Return ONLY comma-separated methods (e.g., 'shooting, stabbing'). Text: ?notes"
        }
      },
      "depends_on": ["step1"],
      "bindings": {
        "extractedMethods": "?extractedMethods"
      }
    }
  ],
  "output": {
    "variables": ["name", "extractedMethods"],
    "limit": 20
  }
}
```

### Compiled SPARQL
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?name ?extractedMethods
WHERE {
    # Step 1: Read CSV with notes
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?step1Graph)

    GRAPH ?step1Graph {
        ?row schema:name ?name .
        ?row schema:notes ?notes .
        FILTER(BOUND(?notes))
        FILTER(STRLEN(?notes) > 50)
    }

    # Step 2: Extract methods with LLM
    BIND(CONCAT("Extract the specific killing method(s) from this text. Return ONLY comma-separated methods (e.g., 'shooting, stabbing'). Text: ", ?notes) AS ?prompt)
    BIND(ggf:LLM(?prompt) AS ?step2Graph)

    GRAPH ?step2Graph {
        ?result schema:text ?extractedMethods .
    }
}
LIMIT 20
```

### Expected Output
```
name                extractedMethods
John Wayne Gacy     strangulation, asphyxiation
Jeffrey Dahmer      strangulation, dismemberment
Aileen Wuornos      shooting
...
```

### File Location
- Logical plan: `demo/serial_killers/queries/plans/q4_extract_methods.json`
- SPARQL: `demo/serial_killers/queries/q4_extract_methods.sparql`

---

## Query 5: Find Unsolved Cases with Similar Patterns

**Category:** Multi-Step Reasoning (CSV → Web Search → LLM Analysis)
**GGFs:** SLM-CSV, SEARCH, LLM
**Complexity:** High
**Cost:** ~45s, multiple web searches + LLM calls
**Note:** Requires web search enabled (MCP server or API key)

### Natural Language Question
"Find unsolved serial killer cases with patterns similar to known killers in the dataset"

### Logical Plan (JSON)
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-CSV",
        "args": {
          "file": "./demo/serial_killers/data/serial_killers_clean.csv"
        }
      },
      "bindings": {
        "methods": "?methods"
      },
      "filters": ["BOUND(?methods)"]
    },
    {
      "id": "step2",
      "operation": "web_search",
      "ggf": {
        "name": "SEARCH",
        "args": {
          "query": "CONCAT('unsolved serial killer ', ?methods)"
        }
      },
      "depends_on": ["step1"],
      "bindings": {
        "searchUrl": "?searchUrl",
        "searchTitle": "?searchTitle"
      }
    },
    {
      "id": "step3",
      "operation": "llm_extract",
      "ggf": {
        "name": "LLM",
        "args": {
          "prompt": "Does this search result describe an UNSOLVED serial killer case? Answer ONLY 'yes' or 'no'. Title: ?searchTitle"
        }
      },
      "depends_on": ["step2"],
      "bindings": {
        "isUnsolved": "?isUnsolved"
      },
      "filters": ["?isUnsolved = 'yes'"]
    }
  ],
  "output": {
    "variables": ["methods", "searchTitle", "searchUrl"],
    "distinct": true,
    "limit": 10
  }
}
```

### Compiled SPARQL
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT DISTINCT ?methods ?searchTitle ?searchUrl
WHERE {
    # Step 1: Get methods from dataset
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?step1Graph)

    GRAPH ?step1Graph {
        ?row schema:methods ?methods .
        FILTER(BOUND(?methods))
    }

    # Step 2: Web search for unsolved cases
    BIND(CONCAT("unsolved serial killer ", ?methods) AS ?searchQuery)
    BIND(ggf:SEARCH(?searchQuery) AS ?step2Graph)

    GRAPH ?step2Graph {
        ?result schema:url ?searchUrl .
        ?result schema:name ?searchTitle .
    }

    # Step 3: LLM verification
    BIND(CONCAT("Does this search result describe an UNSOLVED serial killer case? Answer ONLY 'yes' or 'no'. Title: ", ?searchTitle) AS ?verifyPrompt)
    BIND(ggf:LLM(?verifyPrompt) AS ?step3Graph)

    GRAPH ?step3Graph {
        ?verification schema:text ?isUnsolved .
        FILTER(?isUnsolved = "yes")
    }
}
LIMIT 10
```

### Expected Output
```
methods          searchTitle                           searchUrl
strangulation    Zodiac Killer remains unsolved        https://...
shooting         Long Island Serial Killer case        https://...
...
```

### File Location
- Logical plan: `demo/serial_killers/queries/plans/q5_unsolved_patterns.json`
- SPARQL: `demo/serial_killers/queries/q5_unsolved_patterns.sparql`

---

## Query 6: Verify Victim Counts from Wikipedia

**Category:** Cross-Reference Validation (CSV vs Web)
**GGFs:** SLM-CSV, SLM-GETTEXT, LLM
**Complexity:** High
**Cost:** ~60s, multiple HTTP + LLM calls

### Natural Language Question
"Cross-check victim counts in the dataset against Wikipedia data"

### Logical Plan (JSON)
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-CSV",
        "args": {
          "file": "./demo/serial_killers/data/serial_killers_clean.csv"
        }
      },
      "bindings": {
        "name": "?name",
        "csvVictims": "?csvVictims",
        "wikipediaUrl": "?wikipediaUrl"
      },
      "filters": ["BOUND(?wikipediaUrl)", "?csvVictims > 10"]
    },
    {
      "id": "step2",
      "operation": "web_scrape",
      "ggf": {
        "name": "SLM-GETTEXT",
        "args": {
          "url": "?wikipediaUrl"
        }
      },
      "depends_on": ["step1"],
      "bindings": {
        "wikiText": "?wikiText"
      }
    },
    {
      "id": "step3",
      "operation": "llm_extract",
      "ggf": {
        "name": "LLM",
        "args": {
          "prompt": "Extract the victim count from this Wikipedia text. Return ONLY the number. Text: ?wikiText"
        }
      },
      "depends_on": ["step2"],
      "bindings": {
        "wikiVictims": "?wikiVictims"
      }
    }
  ],
  "output": {
    "variables": ["name", "csvVictims", "wikiVictims"],
    "limit": 10
  }
}
```

### Compiled SPARQL
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?name ?csvVictims ?wikiVictims
WHERE {
    # Step 1: Get high-victim cases from CSV
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?step1Graph)

    GRAPH ?step1Graph {
        ?row schema:name ?name .
        ?row schema:victimMin ?csvVictims .
        ?row schema:wikipediaUrl ?wikipediaUrl .
        FILTER(BOUND(?wikipediaUrl))
        FILTER(?csvVictims > 10)
    }

    # Step 2: Fetch Wikipedia page
    BIND(ggf:SLM-GETTEXT(?wikipediaUrl) AS ?step2Graph)

    GRAPH ?step2Graph {
        ?page schema:text ?wikiText .
    }

    # Step 3: Extract victim count from Wikipedia
    BIND(CONCAT("Extract the victim count from this Wikipedia text. Return ONLY the number. Text: ", SUBSTR(?wikiText, 1, 1000)) AS ?extractPrompt)
    BIND(ggf:LLM(?extractPrompt) AS ?step3Graph)

    GRAPH ?step3Graph {
        ?extraction schema:text ?wikiVictims .
    }
}
LIMIT 10
```

### Expected Output
```
name                csvVictims  wikiVictims
Harold Shipman      218         218
Luis Garavito       193         193
Pedro López         110         300
...
```

### Post-Processing
```python
# Compare and report discrepancies
df = pd.read_csv('results.csv')
df['csv'] = pd.to_numeric(df['csvVictims'], errors='coerce')
df['wiki'] = pd.to_numeric(df['wikiVictims'], errors='coerce')
df['diff'] = abs(df['csv'] - df['wiki'])
df['match'] = df['diff'] < 5  # Allow small variance

print(f"Matching: {df['match'].sum()}/{len(df)}")
print("\nDiscrepancies:")
print(df[~df['match']][['name', 'csv', 'wiki', 'diff']])
```

### File Location
- Logical plan: `demo/serial_killers/queries/plans/q6_verify_counts.json`
- SPARQL: `demo/serial_killers/queries/q6_verify_counts.sparql`
- Post-processing: `demo/serial_killers/queries/q6_compare.py`

---

## Implementation Tasks

### Task 2.1: Create Query Files

For each query (Q1-Q6):
1. Create JSON logical plan: `demo/serial_killers/queries/plans/qN_*.json`
2. Create SPARQL file: `demo/serial_killers/queries/qN_*.sparql`
3. Validate JSON against schema: `SPARQLLM/compiler/schema/logical_plan.json`
4. Test compilation: `PhysicalCompiler.compile(plan)`

### Task 2.2: Test Execution

Execute each query manually:
```bash
# Test Q1 (simple CSV)
slm-run --config config.ini -f demo/serial_killers/queries/q1_top_victims.sparql --debug

# Test Q2 (CSV + LLM) - requires Ollama
slm-run --config config.ini -f demo/serial_killers/queries/q2_methods_by_decade.sparql --debug

# Save intermediate results
slm-run -f demo/serial_killers/queries/q3_wikipedia_summary.sparql -o results/q3_output.csv
```

### Task 2.3: Create Post-Processing Scripts

Where needed:
- `q2_aggregate.py` - Pivot decade vs method category
- `q6_compare.py` - Compare CSV vs Wikipedia victim counts

### Task 2.4: Document Query Patterns

Create `demo/serial_killers/queries/README.md`:
```markdown
# Serial Killers Query Library

## Query Index
- Q1: Basic CSV aggregation (top victims)
- Q2: Temporal analysis with LLM categorization
- Q3: CSV → web scraping (Wikipedia summaries)
- Q4: LLM extraction from unstructured CSV field
- Q5: Multi-step reasoning (CSV → search → LLM verification)
- Q6: Cross-reference validation (CSV vs web)

## Execution Guide
[Instructions for running each query]

## Expected Outputs
[Sample outputs for each query]
```

---

## Deliverables

### Query Files
- [ ] `demo/serial_killers/queries/plans/q1_top_victims.json`
- [ ] `demo/serial_killers/queries/q1_top_victims.sparql`
- [ ] `demo/serial_killers/queries/plans/q2_methods_by_decade.json`
- [ ] `demo/serial_killers/queries/q2_methods_by_decade.sparql`
- [ ] `demo/serial_killers/queries/plans/q3_wikipedia_summary.json`
- [ ] `demo/serial_killers/queries/q3_wikipedia_summary.sparql`
- [ ] `demo/serial_killers/queries/plans/q4_extract_methods.json`
- [ ] `demo/serial_killers/queries/q4_extract_methods.sparql`
- [ ] `demo/serial_killers/queries/plans/q5_unsolved_patterns.json`
- [ ] `demo/serial_killers/queries/q5_unsolved_patterns.sparql`
- [ ] `demo/serial_killers/queries/plans/q6_verify_counts.json`
- [ ] `demo/serial_killers/queries/q6_verify_counts.sparql`

### Post-Processing Scripts
- [ ] `demo/serial_killers/queries/q2_aggregate.py`
- [ ] `demo/serial_killers/queries/q6_compare.py`

### Documentation
- [ ] `demo/serial_killers/queries/README.md` - Query library guide

### Validation
- [ ] All JSON plans validate against schema
- [ ] All SPARQL queries compile successfully
- [ ] Q1-Q4 execute without errors (local only)
- [ ] Q5-Q6 documented with web search requirements

---

## Verification Commands

```bash
# Validate all JSON plans
for plan in demo/serial_killers/queries/plans/*.json; do
    python -c "
import json
from jsonschema import validate
plan = json.load(open('$plan'))
schema = json.load(open('SPARQLLM/compiler/schema/logical_plan.json'))
validate(plan, schema)
print('✓ $plan')
"
done

# Test compilation
python -c "
from SPARQLLM.compiler import PhysicalCompiler
import json
compiler = PhysicalCompiler()
for i in range(1, 7):
    plan_path = f'demo/serial_killers/queries/plans/q{i}_*.json'
    plan = json.load(open(plan_path))
    sparql = compiler.compile(plan)
    print(f'✓ Q{i} compiled successfully')
"

# Execute local queries (Q1-Q4)
slm-run -f demo/serial_killers/queries/q1_top_victims.sparql
slm-run -f demo/serial_killers/queries/q2_methods_by_decade.sparql
slm-run -f demo/serial_killers/queries/q3_wikipedia_summary.sparql
slm-run -f demo/serial_killers/queries/q4_extract_methods.sparql
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM prompt engineering failures | High | Test prompts interactively, refine based on output quality |
| Wikipedia scraping rate limits | Medium | Add delays, use `--keep-store` to cache results |
| CSV bindings mismatch schema | High | Validate against actual cleaned CSV column names |
| Query timeout on large datasets | Medium | Add LIMIT clauses, document expected execution time |
| Web search unavailable | Low | Q5-Q6 optional, document requirements clearly |

---

## Next Steps

After Phase 2 completion:
1. Use queries Q1-Q6 as examples in Phase 3 CLI demo
2. Embed logical plans in demo prompt (examples for LLM)
3. Use execution times for cost estimation calibration
4. Create test fixtures based on these queries for Phase 5
