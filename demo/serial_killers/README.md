# Serial Killers Demo - SPARQLLM

A demonstration of SPARQLLM's Graph Generating Functions (GGFs) using a real-world dataset of serial killers.

**Two ways to query the data:**
1. **Pre-written SPARQL** - Run existing .sparql files directly (no LLM needed)
2. **Natural Language → SPARQL** - Use LLM to generate queries from questions (requires Ollama)

---

## Quick Start

### Setup

```bash
# Activate virtual environment
source venv312_new/bin/activate

# (Optional) For LLM query generation, start Ollama
ollama serve &
ollama pull qwen2.5:3b
```

### Option 1: Run Pre-written SPARQL (Fastest)

**No LLM needed** - Just execute the query:

```bash
# Q1: Top 10 serial killers
slm-run -c config.ini -f demo/serial_killers/queries/q1_top_victims.sparql

# Q6: Statistics by decade
slm-run -c config.ini -f demo/serial_killers/queries/q6_decade_statistics.sparql
```

### Option 2: Generate SPARQL from Natural Language (Demo LLM Pipeline)

**Requires Ollama** - Full NL → SPARQL pipeline:

```bash
# Interactive menu with 5 demo questions
python demo/serial_killers/demo_nl_to_sparql.py

# Ask your own question
python demo/serial_killers/demo_nl_to_sparql.py --interactive

# Specific question
python demo/serial_killers/demo_nl_to_sparql.py \
  --question "Who are the top 10 serial killers?"
```

**What this does:**
1. Sends your question to LLM (Ollama)
2. LLM generates JSON logical plan
3. Physical compiler translates to SPARQL
4. Executes query and shows results

**Output:**
```
                          name  proven_victims  possible_victims                     country
0          Murder Incorporated           400.0            1000.0               United States
1               Harold Shipman           218.0             250.0              United Kingdom
2                Luis Garavito           193.0             247.0  Colombia, Ecuador, Venezuela
...
```

## Dataset

**File:** `data/serial_killers_clean.csv`
**Rows:** 757 serial killers
**Columns:**
- `name` - Serial killer's name
- `country` - Country/countries of operation
- `start_year`, `end_year` - Active period
- `proven_victims`, `possible_victims` - Victim counts
- `victim_min`, `victim_max` - Normalized victim range
- `notes` - Detailed description (for LLM extraction)
- `decade` - Primary decade of activity

**Source:** Wikipedia List of Serial Killers (cleaned and structured)

---

## Query Examples by Data Source

### 📊 CSV Queries (Pure Data)

#### Q1: Top Killers by Victim Count
**Question:** "Who are the top 10 serial killers with the most victims?"

```bash
slm-run -c config.ini -f demo/serial_killers/queries/q1_top_victims.sparql
```

**How it works:**
```sparql
# Load CSV as RDF graph
BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

# Query the graph
GRAPH ?csvGraph {
    ?row ex:name ?name .
    ?row ex:victim_max ?victim_max .
}

# Sort and limit
ORDER BY DESC(?victim_max)
LIMIT 10
```

**Key Concepts:**
- `SLM-CSV` GGF converts CSV → RDF triples
- Each row becomes a blank node with properties
- Column names become predicates (ex:name, ex:victim_max)

---

#### Q6: Decade Statistics (Aggregation)
**Question:** "What are the statistics for serial killers in each decade?"

```bash
slm-run -c config.ini -f demo/serial_killers/queries/q6_decade_statistics.sparql
```

**Output:**
```
   decade  killers  total_victims  avg_victims
10  1970s      116         1516.0        13.07
11  1980s      155         1535.0         9.90  ← Most active decade
12  1990s      153         2030.0        13.27  ← Most victims
```

**How it works:**
```sparql
SELECT ?decade
       (COUNT(?name) AS ?killers)
       (SUM(?victim_min) AS ?total_victims)
       (AVG(?victim_min) AS ?avg_victims)
WHERE {
    BIND(ggf:SLM-CSV("./data/serial_killers_clean.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:decade ?decade .
        ?row ex:victim_min ?victim_min .
    }
}
GROUP BY ?decade
ORDER BY ?decade
```

**Key Concepts:**
- Standard SPARQL aggregation (COUNT, SUM, AVG)
- GROUP BY works on GGF-generated graphs
- No special syntax needed for CSV data

---

#### Q5: Multi-Country Patterns
**Question:** "Which serial killers operated across multiple countries?"

```bash
slm-run -c config.ini -f demo/serial_killers/queries/q5_geographical_patterns.sparql
```

**Output:**
```
                 name                      country  proven_victims
0       Luis Garavito  Colombia, Ecuador, Venezuela           193.0
1         Pedro López      Colombia, Peru, Ecuador           110.0
```

**How it works:**
```sparql
FILTER(CONTAINS(?country, ","))  # Countries with commas = multiple countries
```

---

### 🤖 CSV + LLM Queries (Semantic Analysis)

#### Simple LLM Test
**Question:** "Who was Ted Bundy?" (using LLM)

```bash
slm-run -c config.ini -f demo/serial_killers/test_llm_simple.sparql
```

**Output:**
```
        name                           desc
0  Ted Bundy  was a prolific and cunning serial killer...
```

**How it works:**
```sparql
# Build prompt
BIND(CONCAT(
    "Who was Ted Bundy? Answer in one sentence. ",
    "Return ONLY a JSON-LD object: ",
    '{"@context": "http://schema.org/", ',
    ' "@type": "Person", ',
    ' "name": "Ted Bundy", ',
    ' "description": "your answer here"}'
) AS ?prompt)

# Call LLM and get RDF graph back
BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)

# Query LLM response as RDF
GRAPH ?llmGraph {
    ?person a schema:Person ;
            schema:description ?desc .
}
```

**Key Concepts:**
- `SLM-LLMGRAPH_OLLAMA` calls local Ollama LLM
- LLM returns JSON-LD → automatically converted to RDF
- Query LLM output using standard SPARQL GRAPH pattern

---

#### Q2: Extract Killing Methods (Advanced LLM)
**Question:** "What killing methods were used by serial killers in the 1970s-1990s?"

```bash
slm-run -c config.ini -f demo/serial_killers/queries/q2_methods_by_decade.sparql
```

**Note:** This query requires either:
- Option A: Set `GROQ_API_KEY` environment variable
- Option B: Modify query to use `SLM-LLMGRAPH_OLLAMA` instead of `SLM-LLMGRAPH`

**How it works:**
```sparql
# Step 1: Subquery filters CSV BEFORE LLM calls (optimization)
{
    SELECT ?name ?notes ?decade WHERE {
        BIND(ggf:SLM-CSV("./data/serial_killers_clean.csv") AS ?csvGraph)
        GRAPH ?csvGraph {
            ?row ex:name ?name .
            ?row ex:decade ?decade .
        }
        OPTIONAL {
            GRAPH ?csvGraph { ?row ex:notes ?notes . }
        }
        FILTER(?decade IN ("1970s", "1980s", "1990s", "2000s"))
    }
    LIMIT 5  # ← CRITICAL: Only 5 LLM calls instead of 757
}

# Step 2: For each row, extract methods using LLM
BIND(CONCAT(
    "Extract the killing methods from this text. ",
    "Return JSON-LD with methods as comma-separated list.",
    "\n\nText: ", SUBSTR(?notes, 1, 500)
) AS ?prompt)

BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)

GRAPH ?llmGraph {
    ?person schema:description ?methods .
}
```

**Key Concepts:**
- Subquery + LIMIT reduces expensive LLM calls
- OPTIONAL handles NULL notes gracefully
- SUBSTR truncates long text to save tokens
- Each LLM call generates a new named graph

---

### 🌐 CSV + Web Search Queries

#### Q3: Wikipedia Summaries
**Question:** "Get Wikipedia summaries for the top 5 serial killers"

```bash
slm-run -c config.ini -f demo/serial_killers/queries/q3_wikipedia_summary.sparql
```

**How it works:**
```sparql
# Step 1: Get top 5 from CSV
{
    SELECT ?name WHERE {
        BIND(ggf:SLM-CSV("./data/serial_killers_clean.csv") AS ?csvGraph)
        GRAPH ?csvGraph {
            ?row ex:name ?name .
            ?row ex:victim_max ?victims .
        }
    }
    ORDER BY DESC(?victims)
    LIMIT 5
}

# Step 2: Fetch Wikipedia page for each killer
BIND(CONCAT("https://en.wikipedia.org/wiki/", ENCODE_FOR_URI(?name)) AS ?url)
BIND(ggf:SLM-GETTEXT(?url) AS ?webGraph)

# Step 3: Extract text from web page
GRAPH ?webGraph {
    ?doc schema:text ?summary .
}
```

**Key Concepts:**
- `SLM-GETTEXT` fetches web pages and converts to RDF
- Combines CSV data with live web content
- Can chain multiple GGFs in single query

---

## Query Structure Patterns

### Pattern 1: Simple CSV Query
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?value WHERE {
    # Load CSV
    BIND(ggf:SLM-CSV("./path/to/data.csv") AS ?g)

    # Query data
    GRAPH ?g {
        ?row ex:name ?name .
        ?row ex:value ?value .
    }

    # Filter, sort, limit
    FILTER(?value > 100)
    ORDER BY DESC(?value)
    LIMIT 10
}
```

### Pattern 2: CSV + LLM Analysis
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?name ?llm_result WHERE {
    # Step 1: Get CSV data (with LIMIT to reduce LLM calls)
    {
        SELECT ?name ?text WHERE {
            BIND(ggf:SLM-CSV("./data.csv") AS ?csvGraph)
            GRAPH ?csvGraph {
                ?row ex:name ?name .
                ?row ex:text ?text .
            }
        }
        LIMIT 5  # ← Optimize: only 5 LLM calls
    }

    # Step 2: Build LLM prompt
    BIND(CONCAT(
        "Analyze this text and extract key information. ",
        "Return JSON-LD format.",
        "\n\nText: ", ?text
    ) AS ?prompt)

    # Step 3: Call LLM
    BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)

    # Step 4: Query LLM results
    GRAPH ?llmGraph {
        ?entity schema:description ?llm_result .
    }
}
```

### Pattern 3: CSV + Web + LLM (Multi-Source)
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?name ?csv_data ?web_data ?llm_analysis WHERE {
    # Source 1: CSV
    BIND(ggf:SLM-CSV("./data.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:value ?csv_data .
    }

    # Source 2: Web
    BIND(CONCAT("https://example.com/", ?name) AS ?url)
    BIND(ggf:SLM-GETTEXT(?url) AS ?webGraph)
    GRAPH ?webGraph {
        ?doc schema:text ?web_data .
    }

    # Source 3: LLM analysis
    BIND(CONCAT("Compare CSV and web data: ", ?csv_data, " vs ", ?web_data) AS ?prompt)
    BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)
    GRAPH ?llmGraph {
        ?analysis schema:description ?llm_analysis .
    }
}
LIMIT 3
```

---

## LLM Provider Configuration

SPARQLLM supports multiple LLM providers. Choose based on your needs:

### Option 1: Local Ollama (Recommended for Demo)

**Pros:** Free, private, no API keys, fast
**Cons:** Requires local installation

**Setup:**
```bash
# Install Ollama (https://ollama.com)
ollama serve

# Pull model
ollama pull qwen2.5:3b  # Fast, 3B parameters
# OR
ollama pull llama3.1    # Slower, higher quality
```

**Usage in SPARQL:**
```sparql
BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?g)
```

---

### Option 2: Groq (Cloud, Fast)

**Pros:** Very fast inference, free tier
**Cons:** Requires API key, sends data to cloud

**Setup:**
```bash
# Get API key from https://console.groq.com
export GROQ_API_KEY="your-key-here"
```

**Usage in SPARQL:**
```sparql
# Default SLM-LLMGRAPH uses Groq via MCP
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?g)

# OR explicitly
BIND(ggf:SLM-LLMGRAPH_GROQ(?prompt) AS ?g)
```

---

### Option 3: OpenAI (Cloud, High Quality)

**Pros:** Best quality (GPT-4)
**Cons:** Costs money, requires API key

**Setup:**
```bash
export OPENAI_API_KEY="your-key-here"
```

**Usage in SPARQL:**
```sparql
BIND(ggf:SLM-LLMGRAPH_OPENAI(?prompt) AS ?g)
```

---

## Performance Tips

### 1. Limit LLM Calls

**Bad (slow, expensive):**
```sparql
# This calls LLM 757 times (one per row)
SELECT ?name ?analysis WHERE {
    BIND(ggf:SLM-CSV("./data.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:text ?text .
    }
    BIND(ggf:SLM-LLMGRAPH(?text) AS ?llmGraph)  # ← 757 LLM calls!
    GRAPH ?llmGraph { ?e schema:description ?analysis . }
}
```

**Good (fast):**
```sparql
# Use subquery with LIMIT to reduce calls
SELECT ?name ?analysis WHERE {
    {
        SELECT ?name ?text WHERE {
            BIND(ggf:SLM-CSV("./data.csv") AS ?csvGraph)
            GRAPH ?csvGraph {
                ?row ex:name ?name .
                ?row ex:text ?text .
            }
        }
        LIMIT 5  # ← Only 5 LLM calls
    }
    BIND(ggf:SLM-LLMGRAPH(?text) AS ?llmGraph)
    GRAPH ?llmGraph { ?e schema:description ?analysis . }
}
```

### 2. Use OPTIONAL for Nullable Columns

```sparql
# notes column may be NULL
GRAPH ?csvGraph {
    ?row ex:name ?name .  # Always present
}
OPTIONAL {
    GRAPH ?csvGraph {
        ?row ex:notes ?notes .  # May be NULL
    }
}
```

### 3. Filter Before GGF Calls

```sparql
# Good: Filter CSV first, then call expensive GGFs
GRAPH ?csvGraph {
    ?row ex:name ?name .
    ?row ex:decade ?decade .
}
FILTER(?decade = "1990s")  # ← Filter reduces rows before LLM

BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)
```

---

## Common Issues & Solutions

### Issue 1: "GROQ_API_KEY is not set"

**Symptom:** Query returns empty results, stderr shows Groq API key error

**Cause:** Query uses `SLM-LLMGRAPH` without suffix, which defaults to Groq MCP

**Solution A - Use Ollama explicitly:**
```sparql
# Change this:
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?g)

# To this:
BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?g)
```

**Solution B - Set Groq API key:**
```bash
export GROQ_API_KEY="your-key-here"
slm-run -c config.ini -f query.sparql
```

---

### Issue 2: "Query returns empty DataFrame"

**Possible Causes:**

1. **LLM response doesn't match expected schema**
   ```sparql
   # Make sure LLM prompt specifies exact JSON-LD structure
   BIND(CONCAT(
       "Return ONLY a JSON-LD object with this structure: ",
       '{"@context": "http://schema.org/", "@type": "Person", "name": "...", "description": "..."}'
   ) AS ?prompt)
   ```

2. **Column name mismatch**
   ```bash
   # Check actual CSV columns
   head -1 demo/serial_killers/data/serial_killers_clean.csv

   # Use exact column names in SPARQL
   GRAPH ?csvGraph {
       ?row ex:name ?name .  # Column is "name", not "killer_name"
   }
   ```

3. **NULL values not handled**
   ```sparql
   # Use OPTIONAL for columns that may be NULL
   OPTIONAL {
       GRAPH ?csvGraph {
           ?row ex:notes ?notes .
       }
   }
   ```

---

### Issue 3: "Ollama connection refused"

**Symptom:** LLM queries fail with connection error

**Solution:**
```bash
# Start Ollama server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags

# Check config.ini has correct URL
grep SLM-OLLAMA-URL config.ini
# Should be: http://localhost:11434/api/generate
```

---

## Ground Truth Queries (For Testing)

The `ground_truth/` directory contains validated baseline queries:

```bash
# Run all ground truth queries with validation
python demo/serial_killers/run_ground_truth.py

# Run individual ground truth query
slm-run -c config.ini -f demo/serial_killers/ground_truth/gt_01_top_victims.sparql
```

**Available Ground Truth Queries:**
- `gt_01_top_victims.sparql` - Top 10 killers by victim count
- `gt_02_decade_count.sparql` - Count killers per decade
- `gt_03_country_count.sparql` - Countries with most killers
- `gt_04_us_1970s.sparql` - US killers in 1970s
- `gt_05_high_victims.sparql` - Killers with 50+ victims

**Results saved to:** `ground_truth/results/`

---

## Running Interactive Demos

### Demo Script (Recommended Order)

**1. Start with Simple CSV (30 seconds)**
```bash
echo "Q1: Top 10 serial killers with most victims"
slm-run -c config.ini -f demo/serial_killers/queries/q1_top_victims.sparql
```

**2. Show Aggregation (30 seconds)**
```bash
echo "Q6: Statistics by decade (GROUP BY, COUNT, AVG)"
slm-run -c config.ini -f demo/serial_killers/queries/q6_decade_statistics.sparql
```

**3. Demonstrate LLM Integration (45 seconds)**
```bash
echo "LLM Test: Who was Ted Bundy?"
slm-run -c config.ini -f demo/serial_killers/test_llm_simple.sparql
```

**4. Show Multi-Country Patterns (30 seconds)**
```bash
echo "Q5: Serial killers who operated across multiple countries"
slm-run -c config.ini -f demo/serial_killers/queries/q5_geographical_patterns.sparql
```

**Total Demo Time:** ~2.5 minutes

---

## Creating Your Own Queries

### Step 1: Understand Your Data

```bash
# View CSV structure
head -5 demo/serial_killers/data/serial_killers_clean.csv

# Count rows
wc -l demo/serial_killers/data/serial_killers_clean.csv
```

### Step 2: Write SPARQL Query

Create `my_query.sparql`:

```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?country ?victims WHERE {
    # Load CSV
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

    # Query data
    GRAPH ?csvGraph {
        ?row ex:name ?name .
        ?row ex:country ?country .
        ?row ex:victim_min ?victims .
    }

    # Your filters here
    FILTER(?victims > 50)
}
ORDER BY DESC(?victims)
LIMIT 10
```

### Step 3: Run Query

```bash
slm-run -c config.ini -f my_query.sparql
```

### Step 4: Add LLM Analysis (Optional)

```sparql
# After CSV query, add LLM extraction
BIND(CONCAT(
    "Analyze this serial killer: ", ?name,
    " with ", STR(?victims), " victims. ",
    "What patterns do you notice? ",
    "Return JSON-LD: {...}"
) AS ?prompt)

BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)

GRAPH ?llmGraph {
    ?analysis schema:description ?insight .
}
```

---

## Additional Resources

**Documentation:**
- SPARQLLM Overview: `/CLAUDE.md`
- Demo Questions: `/demo/serial_killers/DEMO_QUESTIONS.md`
- Run Report: `/demo/serial_killers/DEMO_RUN_REPORT.md`
- Validation Report: `/demo/serial_killers/validation_report.json`

**Query Examples:**
- Pure CSV: `queries/q1_top_victims.sparql`, `queries/q5_geographical_patterns.sparql`, `queries/q6_decade_statistics.sparql`
- CSV + LLM: `queries/q2_methods_by_decade.sparql`, `test_llm_simple.sparql`
- CSV + Web: `queries/q3_wikipedia_summary.sparql`

**Scripts:**
- Validation: `validate_demo.py`
- Ground Truth Runner: `run_ground_truth.py`
- Data Cleaning: `setup/clean_data.py`

---

## Troubleshooting

### Enable Debug Logging

```bash
slm-run -c config.ini -f query.sparql --debug
```

### Check Configuration

```bash
# View GGF registrations
grep "^\[Associations\]" -A 20 config.ini

# View LLM settings
grep "SLM-OLLAMA" config.ini
```

### Validate Dataset

```bash
python demo/serial_killers/validate_demo.py
```

---

## Contributing

To add new queries:

1. Create query file in `queries/` directory
2. Add description to `DEMO_QUESTIONS.md`
3. Test query: `slm-run -c config.ini -f queries/your_query.sparql`
4. Document in this README

---

## License

Dataset source: Wikipedia (CC BY-SA 3.0)
Code: See main SPARQLLM license

**Last Updated:** 2025-11-21
