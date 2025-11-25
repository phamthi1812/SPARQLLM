# Serial Killers Dataset - Interactive CLI Demo

**Date:** 2025-11-20
**Status:** Planning Complete
**Effort:** 5 phases, ~2-3 weeks
**LLM:** qwen2.5:3b (local, zero cost)

---

## Vision

Build production-ready interactive CLI showcasing SPARQLLM's two-stage compilation (natural language → JSON logical plan → SPARQL) using real-world criminal dataset with hybrid reasoning (CSV + web scraping + LLM analysis).

**Goal:** Demonstrate neuro-symbolic RAG capabilities on Kaggle Wikipedia Serial Killers dataset

---

## Dataset

**Source:** https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list
**Format:** CSV with columns: name, years_active, victims, methods, notes, wikipedia_url
**Size:** ~500 entries
**Challenges:** Missing data, temporal analysis, unstructured notes field

---

## Core Architecture

```
User Question (natural language)
    ↓
[QueryGenerator] ← LLM generates JSON logical plan
    ↓
[PhysicalCompiler] ← Compiles plan → SPARQL + GGF calls
    ↓
[User Confirmation] ← Shows plan, cost estimate, explanation
    ↓
[slm-run Execution] ← Existing evaluator with lazy joins
    ↓
Results (CSV/JSON/table format)
```

---

## Query Coverage (6 Examples)

| Query | Pattern | GGFs Used | Complexity |
|-------|---------|-----------|------------|
| Q1 | Basic aggregation | SLM-CSV | Low |
| Q2 | Temporal analysis + LLM | SLM-CSV, LLM | Medium |
| Q3 | CSV → web scraping | SLM-CSV, SLM-GETTEXT | Medium |
| Q4 | LLM extraction from CSV | SLM-CSV, LLM | Medium |
| Q5 | Multi-step reasoning | SLM-CSV, SEARCH, LLM | High |
| Q6 | Cross-reference validation | SLM-CSV, SLM-GETTEXT, LLM | High |

---

## Implementation Phases

| Phase | Focus | Duration | Dependencies | Status |
|-------|-------|----------|--------------|--------|
| **Phase 1** | Dataset Prep & Validation | 2 days | None | ✅ COMPLETED |
| **Phase 2** | Query Creation (6 SPARQL) | 3 days | Phase 1 | Pending |
| **Phase 3** | Interactive CLI Demo | 2 days | Phase 2 | Pending |
| **Phase 4** | Documentation | 1 day | Phase 3 | Pending |
| **Phase 5** | Testing & Validation | 2 days | Phase 4 | Pending |

**Overall Progress:** Phase 1/5 Complete (20%)

---

## Success Criteria

1. Dataset loads correctly (500+ entries, validation passes)
2. 6 SPARQL queries execute successfully via two-stage compilation
3. Interactive CLI accepts natural language, generates logical plans, compiles to SPARQL
4. Zero external costs (local LLM only)
5. Comprehensive README with quick start guide
6. Test suite validates all queries

---

## Technical Constraints

- **Dataset acquisition:** Manual download from Kaggle (requires free account)
- **No new UDFs:** Use existing 39 GGFs only
- **Local LLM:** qwen2.5:3b via Ollama (config.ini already configured)
- **Two-stage pipeline:** All queries use QueryGenerator → PhysicalCompiler → execution
- **No API keys:** Filesystem + CSV + local LLM only (optional web search if user enables)

---

## Key Components

### 1. Dataset Preparation Scripts
- Download instructions (Kaggle CLI or manual)
- Data cleaning script (handle missing values, normalize columns)
- Validation script (schema check, row count, data quality)

### 2. Query Library (6 SPARQL Files)
- Covering different GGF combinations
- Include both JSON logical plans + compiled SPARQL
- Progressive complexity (simple → hybrid → multi-step)

### 3. Interactive CLI Demo
- Extends `demo/query_generator.py`
- Custom prompt with dataset context
- Preset questions (quick start) + free-form input
- Cost estimation before execution

### 4. Documentation
- Quick start guide (5 minutes to first query)
- Query walkthrough (explains each of 6 examples)
- Architecture diagram
- Troubleshooting guide

### 5. Test Suite
- Fixture-based tests (following Phase 4 pattern)
- Integration tests for all 6 queries
- Data validation tests
- CLI smoke tests

---

## File Structure

```
plans/20251120-1721-serial-killers-demo/
├── plan.md                          # This file
├── phase-01-dataset-prep.md         # Download, cleaning, validation
├── phase-02-query-creation.md       # 6 SPARQL queries + logical plans
├── phase-03-cli-demo.md             # Interactive demo architecture
├── phase-04-documentation.md        # README, guides, examples
└── phase-05-testing.md              # Test suite design

demo/serial_killers/
├── README.md                        # Quick start guide
├── serial_killers_demo.py           # Interactive CLI script
├── setup/
│   ├── download_data.py             # Dataset acquisition helper
│   ├── clean_data.py                # Data cleaning script
│   └── validate_data.py             # Validation checks
├── data/
│   └── serial_killers.csv           # Dataset (user downloads)
├── queries/
│   ├── q1_top_victims.sparql        # Basic aggregation
│   ├── q2_methods_by_decade.sparql  # Temporal + LLM
│   ├── q3_wikipedia_summary.sparql  # CSV → web
│   ├── q4_extract_methods.sparql    # LLM extraction
│   ├── q5_unsolved_patterns.sparql  # Multi-step
│   └── q6_verify_counts.sparql      # Cross-reference
└── tests/
    └── test_serial_killers_queries.py

tests/integration/
└── test_serial_killers_demo.py      # Integration tests
```

---

## Unresolved Questions

1. CSV column names - match actual Kaggle dataset or normalize during cleaning?
2. Web scraping rate limits - add delays between Wikipedia requests?
3. Missing data handling - filter out or mark as NULL in results?
4. LLM prompt engineering - generic or dataset-specific prompts?
5. Results format - CSV, JSON, or formatted table output?
