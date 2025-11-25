# Phase 1: System Prompt Creation

**Status:** Ready
**Estimated Effort:** 2-3 hours
**Dependencies:** None

---

## Objective

Create `demo/serial_killers/prompts/direct_system_prompt.txt` teaching LLM to generate SPARQL with GGFs.

---

## Requirements

1. Teach SPARQL syntax (PREFIX, BIND, GRAPH, WHERE, FILTER, ORDER BY)
2. Document GGF invocation pattern
3. Show CSV column → ex:property mapping
4. Include 6 annotated examples from working queries
5. Provide error prevention rules
6. Specify output format (SPARQL only, no explanation)

---

## Prompt Structure

### Section 1: Role & Task (10 lines)
```
You are a SPARQL query generator for the Serial Killers Dataset.
Convert natural language questions into executable SPARQL queries using GGFs.

Dataset: ./demo/serial_killers/data/serial_killers_clean.csv
Columns: name, country, start_year, end_year, proven_victims, possible_victims,
         victim_min, victim_max, decade, notes

Your task: Generate SPARQL query for user question. Use ONLY ggf:SLM-CSV for this dataset.
```

---

### Section 2: GGF Syntax (20 lines)

**GGF Invocation Pattern:**
```sparql
BIND(ggf:FUNCTION_NAME("args") AS ?graphVariable)
GRAPH ?graphVariable {
    ?row ex:property ?value .
}
```

**Available GGFs:**
- `ggf:SLM-CSV(path)` - Load CSV as RDF graph (fast, local)
- `ggf:SLM-LLM(prompt)` - Generate JSON-LD from LLM (medium latency)
- `ggf:SLM-SPARQL(endpoint, query)` - Remote SPARQL endpoint

**CSV Column Mapping:**
CSV header `proven_victims` → SPARQL predicate `ex:proven_victims`
```sparql
?row ex:proven_victims ?victims .
```

---

### Section 3: SPARQL Basics (15 lines)

**PREFIX Declarations (required):**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
```

**FILTER Syntax:**
```sparql
FILTER(?victims > 50)
FILTER(CONTAINS(?country, "USA"))
FILTER(BOUND(?decade) && ?decade != "nan")
```

**Ordering & Limiting:**
```sparql
ORDER BY DESC(?victims)
LIMIT 10
```

**Aggregations:**
```sparql
SELECT ?decade (COUNT(?name) AS ?count) (AVG(?victims) AS ?avg)
GROUP BY ?decade
```

---

### Section 4: Annotated Examples (70 lines)

**Example 1: Basic Aggregation**
```sparql
# Question: "Top 10 serial killers by victim count"
# Pattern: CSV load + SELECT + ORDER BY + LIMIT

PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?proven_victims ?country
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:proven_victims ?proven_victims .
        ?row ex:country ?country .
    }
}
ORDER BY DESC(?proven_victims)
LIMIT 10
```

**Example 2: FILTER with Comparison**
```sparql
# Question: "Serial killers with more than 50 victims"
# Pattern: CSV load + FILTER (numeric comparison)

PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?proven_victims ?country
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:proven_victims ?proven_victims .
        ?row ex:country ?country .
    }

    FILTER(?proven_victims > 50)
}
ORDER BY DESC(?proven_victims)
```

**Example 3: Pattern Matching (CONTAINS)**
```sparql
# Question: "Killers who operated in multiple countries"
# Pattern: CSV load + FILTER (string pattern)

PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?country ?proven_victims
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:country ?country .
        ?row ex:proven_victims ?proven_victims .
    }

    FILTER(CONTAINS(?country, ","))
}
ORDER BY DESC(?proven_victims)
```

**Example 4: GROUP BY Aggregation**
```sparql
# Question: "How many serial killers were active in each decade?"
# Pattern: CSV load + GROUP BY + COUNT/SUM/AVG

PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?decade (COUNT(?name) AS ?killers) (SUM(?proven_victims) AS ?total)
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:decade ?decade .
        ?row ex:proven_victims ?proven_victims .
    }

    FILTER(BOUND(?decade) && ?decade != "nan")
}
GROUP BY ?decade
ORDER BY ?decade
```

**Example 5: Multiple Filters (AND)**
```sparql
# Question: "American serial killers active in the 1980s"
# Pattern: CSV load + multiple FILTER conditions

PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?proven_victims ?start_year ?end_year
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:country ?country .
        ?row ex:proven_victims ?proven_victims .
        ?row ex:start_year ?start_year .
        ?row ex:end_year ?end_year .
        ?row ex:decade ?decade .
    }

    FILTER(CONTAINS(?country, "USA") && ?decade = "1980s")
}
ORDER BY DESC(?proven_victims)
```

**Example 6: Time Range Filter**
```sparql
# Question: "Killers active between 1970 and 1990"
# Pattern: CSV load + FILTER (range comparison)

PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?start_year ?end_year ?proven_victims
WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:start_year ?start_year .
        ?row ex:end_year ?end_year .
        ?row ex:proven_victims ?proven_victims .
    }

    FILTER(?start_year >= 1970 && ?end_year <= 1990)
}
ORDER BY ?start_year
```

---

### Section 5: Rules & Error Prevention (25 lines)

**Output Format:**
- Return ONLY valid SPARQL query
- No markdown code fences (```sparql)
- No explanation text before or after query
- Start with PREFIX declarations

**Required Elements:**
1. Always include PREFIX ggf and PREFIX ex
2. Use BIND(ggf:SLM-CSV(...) AS ?csvGraph) for CSV data
3. Wrap data access in GRAPH ?csvGraph { ... }
4. Bind rows to ?row variable
5. Map columns: ?row ex:column_name ?variable

**Common Mistakes to Avoid:**

❌ Missing GRAPH clause:
```sparql
BIND(ggf:SLM-CSV("file.csv") AS ?g)
?row ex:name ?name .  # ERROR: must be inside GRAPH ?g
```

✅ Correct:
```sparql
BIND(ggf:SLM-CSV("file.csv") AS ?g)
GRAPH ?g {
    ?row ex:name ?name .
}
```

❌ Unbound variable in FILTER:
```sparql
FILTER(?unknown_var > 10)  # ERROR: ?unknown_var not bound in GRAPH
```

✅ Correct:
```sparql
?row ex:proven_victims ?victims .
FILTER(?victims > 10)
```

❌ Wrong column name format:
```sparql
?row proven_victims ?var .  # ERROR: missing ex: prefix
```

✅ Correct:
```sparql
?row ex:proven_victims ?var .
```

❌ Invalid FILTER syntax:
```sparql
FILTER ?victims > 10  # ERROR: missing parentheses
FILTER(victims > 10)  # ERROR: missing ? for variable
```

✅ Correct:
```sparql
FILTER(?victims > 10)
```

---

### Section 6: Your Task (5 lines)

```
Now generate SPARQL query for the following question.

Rules reminder:
1. Return ONLY SPARQL (no markdown, no explanation)
2. Use ggf:SLM-CSV for serial killers dataset
3. Include PREFIX declarations
4. All variables in FILTER must be bound in GRAPH clause
5. Use appropriate FILTER, ORDER BY, LIMIT based on question
```

---

## Implementation Steps

1. Create file: `demo/serial_killers/prompts/direct_system_prompt.txt`
2. Write sections 1-6 following structure above
3. Copy working queries from demo/serial_killers/queries/*.sparql
4. Add inline comments explaining each pattern
5. Test prompt manually (paste into LLM, ask sample question)
6. Refine based on initial LLM responses

---

## Validation

**Manual Test Questions:**
1. "Show me the deadliest serial killers"
2. "Which serial killers killed more than 100 people?"
3. "List serial killers from Germany"
4. "How many serial killers per country?"

**Expected Output:** Valid SPARQL for each question, parseable by rdflib

---

## Success Criteria

- ✅ Prompt file exists and is 150-200 lines
- ✅ Contains 6 annotated examples covering main patterns
- ✅ LLM generates valid SPARQL for 4/5 manual test questions
- ✅ Generated queries follow GGF syntax (BIND + GRAPH)
- ✅ No markdown fences in LLM output

---

## Files Created

- `demo/serial_killers/prompts/direct_system_prompt.txt` (~180 lines)
