# Phase 4: Documentation & User Guide

**Duration:** 1 day
**Dependencies:** Phase 3 (CLI demo complete)
**Status:** Not Started

---

## Objectives

1. Create comprehensive README with quick start guide
2. Document all 6 queries with examples
3. Provide troubleshooting guide
4. Generate demo session transcript
5. Create architecture diagram

---

## Documentation Structure

```
demo/serial_killers/
├── README.md                    # Main documentation
├── docs/
│   ├── QUICKSTART.md            # 5-minute getting started
│   ├── QUERIES.md               # Query library walkthrough
│   ├── ARCHITECTURE.md          # System design diagram
│   ├── TROUBLESHOOTING.md       # Common issues + fixes
│   └── DEMO_SESSION.md          # Example CLI session
└── examples/
    ├── sample_outputs/          # Expected query results
    │   ├── q1_top_victims.txt
    │   ├── q2_methods_by_decade.txt
    │   └── ...
    └── screenshots/             # Optional: terminal screenshots
```

---

## Document 4.1: Main README

**File:** `demo/serial_killers/README.md`

**Structure:**
```markdown
# Serial Killers Dataset - Interactive CLI Demo

Demonstrates SPARQLLM's two-stage compilation (Natural Language → JSON Logical Plan → SPARQL) using the Kaggle Wikipedia Serial Killers dataset.

## Features
- 6 preset queries covering different GGF combinations
- Custom natural language query generation
- Local LLM (qwen2.5:3b) - zero external costs
- Interactive CLI with cost estimation and explanations
- Real-world hybrid reasoning: CSV + web scraping + LLM analysis

## Quick Start (5 minutes)

### Prerequisites
- Python 3.10+
- Ollama (local LLM server)
- SPARQLLM installed

### Setup
```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5:3b

# 2. Download dataset (requires Kaggle account)
# Visit: https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list
# Download and extract to: demo/serial_killers/data/serial_killers.csv

# 3. Prepare data
cd demo/serial_killers
python setup/clean_data.py
python setup/validate_data.py data/serial_killers_clean.csv

# 4. Run demo
python serial_killers_demo.py
```

### First Query (30 seconds)
```bash
python serial_killers_demo.py
# Select option: 1
# Execute this query? [y/N]: y
```

Expected output: Top 10 serial killers by victim count

## Preset Queries

| Query | Description | GGFs | Execution Time |
|-------|-------------|------|----------------|
| Q1 | Top victims (basic aggregation) | SLM-CSV | <1s |
| Q2 | Methods by decade (temporal + LLM) | SLM-CSV, LLM | ~30s |
| Q3 | Wikipedia summary (web scraping) | SLM-CSV, SLM-GETTEXT | ~5s |
| Q4 | Extract methods (LLM extraction) | SLM-CSV, LLM | ~20s |
| Q5 | Unsolved patterns (multi-step) | SLM-CSV, SEARCH, LLM | ~45s (requires web) |
| Q6 | Verify counts (cross-reference) | SLM-CSV, SLM-GETTEXT, LLM | ~60s |

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design details.

```
User Question (NL)
    ↓
[QueryGenerator + qwen2.5:3b] → JSON Logical Plan
    ↓
[PhysicalCompiler] → SPARQL Query
    ↓
[User Confirmation] → Review plan, cost estimate
    ↓
[slm-run Execution] → Query results
```

## Documentation

- **[QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute getting started guide
- **[QUERIES.md](docs/QUERIES.md)** - Detailed query explanations
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design diagram
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues + fixes
- **[DEMO_SESSION.md](docs/DEMO_SESSION.md)** - Example CLI interaction

## Dataset

**Source:** [Kaggle Wikipedia Serial Killers List](https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list)

**Schema (after cleaning):**
- `name` (string): Serial killer name
- `years_active` (string): Active period (e.g., "1972-1978")
- `decade` (string): Decade (e.g., "1970s")
- `year_start` (int): Start year
- `year_end` (int): End year
- `victims` (string): Victim count or range
- `victim_min` (int): Minimum victim count
- `victim_max` (int): Maximum victim count
- `methods` (string): Killing methods
- `notes` (text): Additional information
- `wikipedia_url` (string): Wikipedia page URL

**Statistics:**
- Rows: ~500 serial killers
- Time range: 1870-2020
- Total victims: ~3000+
- Most active decade: 1980s

## Troubleshooting

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

**Common Issues:**

| Issue | Solution |
|-------|----------|
| Dataset not found | Download from Kaggle, run setup/download_data.py |
| Ollama not running | `ollama serve &` |
| Model not found | `ollama pull qwen2.5:3b` |
| Query timeout | Add LIMIT clause, reduce result size |
| Web search not working | Q5-Q6 require MCP server or API key |

## Development

### Running Tests
```bash
pytest demo/serial_killers/tests/ -v
```

### Adding New Queries
1. Create logical plan JSON in `queries/plans/`
2. Test compilation: `PhysicalCompiler().compile(plan)`
3. Add to preset questions in `serial_killers_demo.py`
4. Document in `docs/QUERIES.md`

## License

See project root LICENSE file.

## Citation

If using this dataset or demo, please cite:
- **Dataset:** Dante890b. (2023). Wikipedia Serial Killers List. Kaggle.
- **SPARQLLM:** [Your citation here]

## Contact

[Your contact information]
```

---

## Document 4.2: Quick Start Guide

**File:** `demo/serial_killers/docs/QUICKSTART.md`

**Structure:**
```markdown
# Quick Start Guide (5 minutes)

## Goal
Get the Serial Killers demo running and execute your first query.

## Prerequisites Check
```bash
# Check Python version (need 3.10+)
python --version

# Check SPARQLLM installed
slm-run --help

# Check Ollama installed
ollama --version
```

## Step 1: Install Ollama (2 minutes)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve &

# Download model (qwen2.5:3b, ~2GB)
ollama pull qwen2.5:3b

# Verify model
ollama list
# Should show: qwen2.5:3b
```

## Step 2: Get Dataset (2 minutes)
```bash
# Option A: Manual download
# 1. Sign up at https://www.kaggle.com
# 2. Go to: https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list
# 3. Click "Download"
# 4. Extract CSV to: demo/serial_killers/data/serial_killers.csv

# Option B: Kaggle CLI (if configured)
kaggle datasets download -d dante890b/wikipedia-serial-killers-list
unzip wikipedia-serial-killers-list.zip -d demo/serial_killers/data/
```

## Step 3: Prepare Data (1 minute)
```bash
cd demo/serial_killers

# Clean and validate data
python setup/clean_data.py
python setup/validate_data.py data/serial_killers_clean.csv

# Expected output: "VALIDATION PASSED: 485 rows, 11 columns"
```

## Step 4: Run Demo (30 seconds)
```bash
python serial_killers_demo.py
```

You'll see:
```
================================================================================
Serial Killers Dataset - Interactive CLI Demo
================================================================================

Dataset: Wikipedia Serial Killers List (Kaggle)
Rows: 485
Time range: 1870-2020
Total victims: 3241

LLM: qwen2.5:3b (local, zero cost)
Mode: Two-stage compilation (Natural Language → JSON Plan → SPARQL)
================================================================================

Options:
  [1-6] - Run preset question
  [Q]   - Ask custom question (natural language)
  [L]   - List all preset questions
  [S]   - Show dataset statistics
  [H]   - Help
  [X]   - Exit

Select option: _
```

## Step 5: Run First Query (30 seconds)
```
Select option: 1

================================================================================
Question: Show me the top 10 serial killers by victim count
================================================================================

Logical Plan:
{
  "version": "1.0",
  "steps": [...]
}

Estimated cost: 85ms, 0 API calls

Compiled SPARQL:
PREFIX ggf: <http://ggf.org/>
...

Execute this query? [y/N]: y

Executing query...

================================================================================
Results:
================================================================================
name                    victimMin  victimMax
Harold Shipman          218        218
Luis Garavito           193        193
Pedro López             110        300
...
```

## Next Steps

1. **Try other preset questions:** Select options 2-6
2. **Ask custom questions:** Select Q and type natural language
3. **Read query documentation:** See [QUERIES.md](QUERIES.md)
4. **Explore architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)

## Troubleshooting

If something goes wrong, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

**Quick fixes:**
- Dataset not found: Re-run Step 2
- Ollama error: `ollama serve &`
- Model not found: `ollama pull qwen2.5:3b`
```

---

## Document 4.3: Query Library Walkthrough

**File:** `demo/serial_killers/docs/QUERIES.md`

**Structure:**
```markdown
# Query Library Walkthrough

Detailed explanation of all 6 preset queries with examples, patterns, and expected outputs.

## Query 1: Top 10 Serial Killers by Victim Count

**Category:** Basic Aggregation
**Complexity:** Low
**Execution Time:** <1s

### Question
"Show me the top 10 serial killers by victim count"

### What It Does
Reads the cleaned CSV, sorts by victim count (descending), returns top 10.

### GGF Pattern
```
SLM-CSV (read CSV)
  ↓
Filter/Order/Limit in SPARQL
```

### Logical Plan
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {"name": "SLM-CSV", "args": {"file": "./demo/serial_killers/data/serial_killers_clean.csv"}},
      "bindings": {"name": "?name", "victimMin": "?victimMin", "victimMax": "?victimMax"}
    }
  ],
  "output": {
    "variables": ["name", "victimMin", "victimMax"],
    "order_by": [{"variable": "victimMin", "order": "DESC"}],
    "limit": 10
  }
}
```

### SPARQL Query
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
Daniel Camargo Barbosa  72         72
Andrei Chikatilo        53         53
Alexander Pichushkin    49         49
Gary Ridgway            49         71
Ahmad Suradji           42         42
```

### Key Takeaways
- Simple CSV read + SPARQL aggregation
- No LLM or web calls → very fast
- Uses derived columns (victim_min) from cleaning phase
- Demonstrates basic GGF pattern: BIND → GRAPH

---

## Query 2: Methods Evolution by Decade

**Category:** Temporal Analysis + LLM Categorization
**Complexity:** Medium
**Execution Time:** ~30s (50-100 LLM calls)

### Question
"How did killing methods change over decades?"

### What It Does
1. Reads CSV with methods and decade columns
2. For each row, asks LLM to categorize method into standard categories
3. Returns decade + category pairs for analysis

### GGF Pattern
```
SLM-CSV (read methods + decades)
  ↓
LLM (categorize each method)
  ↓
Aggregate results (external Python script)
```

### Logical Plan
[Full JSON here - see phase-02-query-creation.md]

### Expected Output (raw)
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
```python
# demo/serial_killers/queries/q2_aggregate.py
import pandas as pd

df = pd.read_csv('q2_results.csv')
pivot = df.groupby(['decade', 'category']).size().unstack(fill_value=0)
print(pivot)
```

Output:
```
category     firearm  poison  stabbing  strangulation  other
decade
1960s        12       3       8         15             5
1970s        28       7       12        31             10
1980s        45       4       18        52             15
...
```

### Key Takeaways
- Multi-step pipeline: CSV → LLM
- LLM categorizes unstructured text into structured categories
- Demonstrates chaining with `depends_on`
- Post-processing aggregates results

[Continue for Q3-Q6 with same structure...]

## Query Pattern Summary

| Pattern | Queries | Complexity | Use Case |
|---------|---------|------------|----------|
| Simple CSV | Q1 | Low | Aggregation, filtering |
| CSV → LLM | Q2, Q4 | Medium | Extraction, categorization |
| CSV → Web | Q3 | Medium | Enrichment from external sources |
| Multi-step (CSV → Web → LLM) | Q5, Q6 | High | Complex reasoning chains |

## Extending the Library

To add a new query:
1. Design logical plan following schema
2. Test compilation: `PhysicalCompiler().compile(plan)`
3. Save to `queries/plans/qN_*.json`
4. Generate SPARQL: save to `queries/qN_*.sparql`
5. Test execution: `slm-run -f queries/qN_*.sparql`
6. Document here with examples
7. Add to preset questions in `serial_killers_demo.py`
```

---

## Document 4.4: Architecture Diagram

**File:** `demo/serial_killers/docs/ARCHITECTURE.md`

**Content:**
```markdown
# Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       User Interaction                          │
│  - CLI Menu (preset questions or custom natural language)      │
│  - Display plan, cost estimate, explanation                     │
│  - Confirm execution                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 1: Plan Generation                        │
│  QueryGenerator + qwen2.5:3b (local LLM)                        │
│  - Input: Natural language question + dataset context          │
│  - Output: JSON logical plan                                    │
│  - Retries: Max 3 attempts with error feedback                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 2: Compilation                           │
│  PhysicalCompiler                                               │
│  - Input: JSON logical plan                                     │
│  - Validation: Schema check, GGF existence                      │
│  - Dependency resolution: Topological sort                      │
│  - Output: Executable SPARQL query                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Execution Engine                           │
│  slm-run (via subprocess)                                       │
│  - Custom evaluator with lazy join materialization             │
│  - GGF calls: SLM-CSV, LLM, SLM-GETTEXT, etc.                  │
│  - Provenance tracking: SHA256 graph URIs                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Results                                 │
│  - Display: Table/CSV/JSON format                              │
│  - Optional: Save to file                                       │
│  - Debug output: GGF timings, graph URIs                        │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Serial Killers Demo CLI (`serial_killers_demo.py`)
- Main entry point
- Menu-driven interface
- Dataset context management
- Environment validation

### 2. Query Generator (`demo/query_generator.py`)
- Two-stage compilation orchestration
- LLM integration (OpenAI API compatible)
- Logical plan generation
- User confirmation flow

### 3. Physical Compiler (`SPARQLLM/compiler/physical_compiler.py`)
- JSON → SPARQL translation
- Schema validation
- Dependency graph resolution
- SPARQL query assembly

### 4. Cost Estimator (`SPARQLLM/compiler/cost_estimator.py`)
- Latency estimation (ms)
- API call counting
- Token budget estimation
- Parallelism detection

### 5. Execution Engine (`slm-run` + custom evaluator)
- SPARQL query execution
- GGF function dispatch
- Named graph management (global store)
- Lazy join evaluation

## Data Flow: Example Query (Q1)

**User Input:**
```
"Show me the top 10 serial killers by victim count"
```

**Stage 1: Plan Generation (via LLM)**
```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {"name": "SLM-CSV", "args": {"file": "./data/serial_killers_clean.csv"}},
      "bindings": {"name": "?name", "victimMin": "?victimMin"}
    }
  ],
  "output": {"variables": ["name", "victimMin"], "order_by": [{"variable": "victimMin", "order": "DESC"}], "limit": 10}
}
```

**Stage 2: Compilation (PhysicalCompiler)**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?name ?victimMin
WHERE {
    BIND(ggf:SLM-CSV("./data/serial_killers_clean.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row schema:name ?name .
        ?row schema:victimMin ?victimMin .
    }
}
ORDER BY DESC(?victimMin)
LIMIT 10
```

**Execution (slm-run)**
1. Parse SPARQL
2. Evaluate BIND: Call `SLM-CSV` GGF
   - Read CSV file
   - Parse to RDF triples
   - Store in named graph `urn:uuid:...`
   - Return graph URI
3. Evaluate GRAPH clause: Query named graph
4. Apply ORDER BY + LIMIT
5. Return results

**Output:**
```
name                    victimMin
Harold Shipman          218
Luis Garavito           193
...
```

## GGF Catalog Integration

**Catalog File:** `SPARQLLM/catalog/ggfs.json`

**Structure:**
```json
[
  {
    "name": "SLM-CSV",
    "module_path": "SPARQLLM.udf.mycsv.slm_csv",
    "description": "Parse CSV file to RDF triples",
    "data_sources": ["filesystem"],
    "latency_ms": 50,
    "deterministic": true,
    "requires_network": false
  },
  ...
]
```

**Usage in QueryGenerator:**
- Catalog summary injected into LLM system prompt
- LLM selects appropriate GGFs based on question
- Compiler validates GGF existence before execution

## Configuration

**Config File:** `config.ini`

**Key Settings:**
```ini
[Associations]
SLM-CSV = SPARQLLM.udf.mycsv.slm_csv
LLM = SPARQLLM.udf.mcp.alias._alias_llm
SLM-GETTEXT = SPARQLLM.udf.uri2text.GETTEXT

[Requests]
SLM-OLLAMA-MODEL = qwen2.5:3b
SLM-OLLAMA-URL = http://localhost:11434/api/generate
```

## Security & Privacy

**Local-First Design:**
- All queries execute locally (no cloud dependencies)
- LLM runs via Ollama (local inference)
- Dataset never leaves filesystem

**Optional Web Access:**
- Q3, Q5, Q6 fetch Wikipedia pages (user opt-in)
- No tracking, no API keys for basic queries

## Performance Characteristics

| Query | Steps | GGFs | Latency | API Calls | Token Usage |
|-------|-------|------|---------|-----------|-------------|
| Q1 | 1 | SLM-CSV | <1s | 0 | 0 |
| Q2 | 2 | SLM-CSV, LLM | ~30s | 50-100 | ~10k |
| Q3 | 2 | SLM-CSV, SLM-GETTEXT | ~5s | 1 HTTP | 0 |
| Q4 | 2 | SLM-CSV, LLM | ~20s | 20 | ~5k |
| Q5 | 3 | SLM-CSV, SEARCH, LLM | ~45s | 5-10 | ~3k |
| Q6 | 3 | SLM-CSV, SLM-GETTEXT, LLM | ~60s | 10 HTTP | ~8k |

## Extension Points

1. **Add new GGFs:** Register in `config.ini`, document in catalog
2. **Custom prompts:** Override system prompt in QueryGenerator
3. **Post-processing:** Chain with Python scripts for visualization
4. **Results export:** Save to CSV/JSON for further analysis
```

---

## Document 4.5: Troubleshooting Guide

**File:** `demo/serial_killers/docs/TROUBLESHOOTING.md`

**Content:** [See continuation in next section due to length...]

---

## Document 4.6: Demo Session Transcript

**File:** `demo/serial_killers/docs/DEMO_SESSION.md`

**Content:**
```markdown
# Demo Session Transcript

Example CLI interaction demonstrating all features.

## Session Start
```
$ python demo/serial_killers/serial_killers_demo.py

================================================================================
Serial Killers Dataset - Interactive CLI Demo
================================================================================

Dataset: Wikipedia Serial Killers List (Kaggle)
Rows: 485
Time range: 1870-2020
Total victims: 3241

LLM: qwen2.5:3b (local, zero cost)
Mode: Two-stage compilation (Natural Language → JSON Plan → SPARQL)
================================================================================

Options:
  [1-6] - Run preset question
  [Q]   - Ask custom question (natural language)
  [L]   - List all preset questions
  [S]   - Show dataset statistics
  [H]   - Help
  [X]   - Exit

Select option: L
```

[Continue with full session showing all menu options...]

---

## Implementation Tasks

### Task 4.1: Write Documentation
- [ ] README.md (main overview)
- [ ] QUICKSTART.md (5-minute guide)
- [ ] QUERIES.md (query walkthrough)
- [ ] ARCHITECTURE.md (system design)
- [ ] TROUBLESHOOTING.md (common issues)
- [ ] DEMO_SESSION.md (example interaction)

### Task 4.2: Generate Sample Outputs
- [ ] Run all 6 queries
- [ ] Save outputs to `examples/sample_outputs/`
- [ ] Document expected vs actual results
- [ ] Note any data quality issues

### Task 4.3: Create Diagrams
- [ ] Architecture diagram (ASCII or image)
- [ ] Data flow diagram
- [ ] GGF pattern diagrams

### Task 4.4: Record Demo Session
- [ ] Complete CLI interaction
- [ ] Show preset and custom questions
- [ ] Include error handling examples

### Task 4.5: Review & Polish
- [ ] Check all links work
- [ ] Verify code examples execute
- [ ] Test quick start guide with naive user
- [ ] Fix any discovered issues

---

## Deliverables

### Documentation Files
- [ ] `demo/serial_killers/README.md`
- [ ] `demo/serial_killers/docs/QUICKSTART.md`
- [ ] `demo/serial_killers/docs/QUERIES.md`
- [ ] `demo/serial_killers/docs/ARCHITECTURE.md`
- [ ] `demo/serial_killers/docs/TROUBLESHOOTING.md`
- [ ] `demo/serial_killers/docs/DEMO_SESSION.md`

### Example Outputs
- [ ] `demo/serial_killers/examples/sample_outputs/q1_top_victims.txt`
- [ ] `demo/serial_killers/examples/sample_outputs/q2_methods_by_decade.txt`
- [ ] [... all 6 queries]

### Diagrams
- [ ] Architecture diagram
- [ ] Data flow diagram

---

## Verification Commands

```bash
# Check all docs exist
ls demo/serial_killers/README.md
ls demo/serial_killers/docs/*.md

# Verify links in README
python -m pytest --doctest-glob="*.md" demo/serial_killers/README.md

# Test quick start guide (manually)
# Follow QUICKSTART.md step-by-step

# Generate sample outputs
for i in {1..6}; do
    slm-run -f demo/serial_killers/queries/q${i}_*.sparql \
        > demo/serial_killers/examples/sample_outputs/q${i}_output.txt
done
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation becomes stale | Medium | Link to actual code, minimize duplication |
| Quick start fails for naive users | High | Test with external user, collect feedback |
| Sample outputs differ from actual | Low | Re-generate before finalizing |
| Diagrams hard to maintain | Low | Use ASCII art or automated tools |

---

## Next Steps

After Phase 4 completion:
1. Use documentation for Phase 5 user testing
2. Incorporate feedback into docs
3. Create video demo (optional)
4. Publish to project documentation site
