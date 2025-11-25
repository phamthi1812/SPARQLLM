# Serial Killers Demo - Implementation Plan Summary

**Created:** 2025-11-20
**Status:** Ready for Implementation
**Total Effort:** 10 days (2-3 weeks)

---

## Executive Summary

Build production-ready interactive CLI demonstrating SPARQLLM's two-stage compilation (Natural Language → JSON Logical Plan → SPARQL) using real-world Kaggle Wikipedia Serial Killers dataset. Showcases hybrid reasoning (CSV + web scraping + LLM analysis) with zero external costs (local LLM only).

**Key Deliverable:** Interactive demo where users ask natural language questions about serial killers dataset, system generates logical plans via LLM, compiles to SPARQL, and executes queries with full transparency.

---

## Quick Links

- **Plan Overview:** [plan.md](plan.md)
- **Phase 1:** [Dataset Preparation](phase-01-dataset-prep.md)
- **Phase 2:** [Query Creation (6 SPARQL)](phase-02-query-creation.md)
- **Phase 3:** [Interactive CLI Demo](phase-03-cli-demo.md)
- **Phase 4:** [Documentation](phase-04-documentation.md)
- **Phase 5:** [Testing & Validation](phase-05-testing.md)

---

## Phase Breakdown

### Phase 1: Dataset Preparation (2 days)
**Goal:** Acquire and clean Kaggle dataset for SPARQL consumption

**Key Tasks:**
- Manual download from Kaggle (requires free account)
- Data cleaning script (parse dates, victim counts, add derived columns)
- Validation script (schema checks, row counts)
- Generate statistics (temporal analysis, victim distribution)

**Deliverables:**
- `serial_killers_clean.csv` (~500 rows, 11 columns)
- `stats.json` (dataset summary)
- Cleaning and validation scripts

**Success Criteria:**
- 400+ valid rows
- All required columns present
- Derived columns (decade, victim_min/max) computed

---

### Phase 2: Query Creation (3 days)
**Goal:** Create 6 SPARQL queries demonstrating different GGF patterns

**Queries:**
1. **Q1:** Top 10 by victim count (basic CSV aggregation)
2. **Q2:** Methods by decade (temporal + LLM categorization)
3. **Q3:** Wikipedia summary for Ted Bundy (CSV → web scraping)
4. **Q4:** Extract methods from notes (LLM extraction)
5. **Q5:** Unsolved cases with similar patterns (multi-step: CSV → search → LLM)
6. **Q6:** Verify victim counts vs Wikipedia (cross-reference validation)

**Deliverables:**
- 6 JSON logical plans
- 6 compiled SPARQL queries
- Post-processing scripts (aggregation, comparison)
- Query library documentation

**Success Criteria:**
- All plans validate against schema
- All queries compile successfully
- Q1-Q4 execute locally (no web)

---

### Phase 3: Interactive CLI Demo (2 days)
**Goal:** Build user-facing interactive CLI

**Features:**
- Menu-driven interface (preset questions + custom input)
- Two-stage compilation flow with user confirmation
- Cost estimation and plan explanation
- Results display (table/CSV/JSON format)
- Environment validation (dataset, Ollama, model)

**Deliverables:**
- `serial_killers_demo.py` (main CLI script)
- Dataset-specific system prompt
- Results formatting utilities
- Environment validation functions

**Success Criteria:**
- All 6 preset questions work
- Custom questions generate valid plans
- Error handling is graceful
- User can execute queries and see results

---

### Phase 4: Documentation (1 day)
**Goal:** Comprehensive user guide and examples

**Documents:**
- Main README (overview, quick start, features)
- QUICKSTART.md (5-minute getting started)
- QUERIES.md (detailed query walkthrough)
- ARCHITECTURE.md (system design diagram)
- TROUBLESHOOTING.md (common issues + fixes)
- DEMO_SESSION.md (example CLI interaction)

**Deliverables:**
- 6 documentation files
- Sample query outputs
- Architecture diagrams
- Troubleshooting guide

**Success Criteria:**
- New user can run first query in 5 minutes
- All documentation links work
- Quick start guide tested with naive user

---

### Phase 5: Testing & Validation (2 days)
**Goal:** Comprehensive test suite and validation

**Test Suites:**
1. **Unit tests:** Data cleaning, plan validation, SPARQL compilation
2. **Integration tests:** Query execution, two-stage pipeline, GGF calls
3. **CLI tests:** Menu navigation, preset questions, error handling
4. **Performance benchmarks:** Execution times, memory usage
5. **User acceptance tests:** Manual test cases

**Deliverables:**
- 4 automated test files
- User acceptance test checklist
- Test coverage report
- Performance benchmark results

**Success Criteria:**
- 90%+ unit test coverage
- All integration tests pass (fast subset)
- Q1 < 5s, Q2 < 60s execution times
- User acceptance tests complete successfully

---

## Technical Architecture

### Two-Stage Compilation Pipeline

```
User Question (Natural Language)
    ↓
[Stage 1: Plan Generation]
    QueryGenerator + qwen2.5:3b (local LLM)
    Input: NL question + dataset context
    Output: JSON logical plan
    ↓
[User Confirmation]
    Display: Plan, cost estimate, explanation
    ↓
[Stage 2: Compilation]
    PhysicalCompiler
    Input: JSON logical plan
    Output: Executable SPARQL query
    ↓
[Execution Engine]
    slm-run + custom evaluator
    GGF calls: SLM-CSV, LLM, SLM-GETTEXT, etc.
    ↓
Results (table/CSV/JSON)
```

### Key Components

1. **SerialKillersDemo:** Interactive CLI, menu system, context management
2. **QueryGenerator:** LLM integration, plan generation, retry logic
3. **PhysicalCompiler:** JSON → SPARQL translation, dependency resolution
4. **CostEstimator:** Latency/token estimation, parallelism detection
5. **Execution Engine:** SPARQL evaluation, GGF dispatch, graph storage

### GGF Usage

| GGF | Purpose | Queries | Cost |
|-----|---------|---------|------|
| SLM-CSV | Read CSV to RDF | Q1-Q6 | <100ms |
| LLM | Text generation/extraction | Q2, Q4, Q5, Q6 | ~3s/call |
| SLM-GETTEXT | Web scraping | Q3, Q6 | ~2s/page |
| SEARCH | Web search | Q5 | ~5s |

---

## File Structure

```
demo/serial_killers/
├── README.md                        # Main documentation
├── serial_killers_demo.py           # Interactive CLI script
├── setup/
│   ├── download_data.py             # Dataset acquisition helper
│   ├── clean_data.py                # Data cleaning script
│   ├── validate_data.py             # Validation checks
│   └── generate_stats.py            # Statistics generation
├── data/
│   ├── serial_killers.csv           # Raw dataset (user downloads)
│   ├── serial_killers_clean.csv     # Cleaned dataset
│   ├── serial_killers_complete.csv  # Complete cases only
│   └── stats.json                   # Dataset statistics
├── queries/
│   ├── plans/                       # JSON logical plans
│   │   ├── q1_top_victims.json
│   │   ├── q2_methods_by_decade.json
│   │   └── ... (6 total)
│   ├── q1_top_victims.sparql        # Compiled SPARQL
│   ├── q2_methods_by_decade.sparql
│   └── ... (6 total)
├── prompts/
│   └── serial_killers_system_prompt.txt  # Dataset-specific prompt
├── utils/
│   ├── format_results.py            # Results formatting
│   └── validate_env.py              # Environment checks
├── docs/
│   ├── QUICKSTART.md                # 5-minute guide
│   ├── QUERIES.md                   # Query walkthrough
│   ├── ARCHITECTURE.md              # System design
│   ├── TROUBLESHOOTING.md           # Common issues
│   └── DEMO_SESSION.md              # Example interaction
├── examples/
│   └── sample_outputs/              # Expected query results
└── tests/
    ├── test_unit.py                 # Unit tests
    ├── test_integration.py          # Integration tests
    ├── test_cli.py                  # CLI tests
    ├── test_performance.py          # Benchmarks
    └── USER_ACCEPTANCE_TESTS.md     # Manual test cases

plans/20251120-1721-serial-killers-demo/
├── plan.md                          # This plan overview
├── phase-01-dataset-prep.md
├── phase-02-query-creation.md
├── phase-03-cli-demo.md
├── phase-04-documentation.md
├── phase-05-testing.md
└── SUMMARY.md                       # This file
```

---

## Dataset Details

**Source:** [Kaggle Wikipedia Serial Killers List](https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list)

**Schema (after cleaning):**
- `name` (string): Serial killer name
- `years_active` (string): Active period (e.g., "1972-1978")
- `decade` (string): Decade (e.g., "1970s") - DERIVED
- `year_start` (int): Start year - DERIVED
- `year_end` (int): End year - DERIVED
- `victims` (string): Victim count or range (original)
- `victim_min` (int): Minimum victim count - DERIVED
- `victim_max` (int): Maximum victim count - DERIVED
- `methods` (string): Killing methods
- `notes` (text): Additional information
- `wikipedia_url` (string): Wikipedia page URL

**Statistics:**
- Rows: ~500 serial killers
- Time range: 1870-2020
- Total victims: ~3000+
- Most active decade: 1980s
- Complete cases: ~400 (no missing critical fields)

---

## Query Showcase

| Query | Question | Pattern | Time | Complexity |
|-------|----------|---------|------|------------|
| Q1 | "Top 10 by victim count" | CSV aggregation | <1s | Low |
| Q2 | "How did methods change by decade?" | CSV → LLM categorization | ~30s | Medium |
| Q3 | "Get Wikipedia summary for Ted Bundy" | CSV → web scraping | ~5s | Medium |
| Q4 | "Extract methods from notes field" | CSV → LLM extraction | ~20s | Medium |
| Q5 | "Find unsolved cases with similar patterns" | CSV → search → LLM | ~45s | High |
| Q6 | "Verify victim counts vs Wikipedia" | CSV → web → LLM | ~60s | High |

---

## Technical Constraints

### Requirements
- Python 3.10+
- Ollama (local LLM server)
- qwen2.5:3b model (~2GB)
- Kaggle account (free, for dataset download)
- SPARQLLM installed

### No New Development
- Uses existing 39 GGFs only
- No new UDF creation needed
- All queries use standard GGF catalog

### Zero External Costs
- Local LLM only (qwen2.5:3b via Ollama)
- No API keys required for Q1-Q4
- Q5-Q6 optional (web search)

### Limitations
- Manual dataset download (Kaggle API requires setup)
- Web queries (Q5-Q6) may hit rate limits
- LLM inference slow on CPU (3-5s per call)
- Dataset has missing/inconsistent data

---

## Success Metrics

### Technical Metrics
- [ ] 6/6 queries execute successfully
- [ ] Q1-Q4 work with zero API keys
- [ ] Logical plans validate against schema (100%)
- [ ] SPARQL queries compile without errors (100%)
- [ ] Test coverage > 80%

### User Experience Metrics
- [ ] New user runs first query in < 5 minutes
- [ ] Custom questions generate valid plans (90%+)
- [ ] Clear error messages for common issues
- [ ] Documentation answers common questions

### Performance Metrics
- [ ] Q1 execution time < 5s
- [ ] Q2 execution time < 60s (with LLM)
- [ ] CSV parsing < 1s
- [ ] Memory usage < 500MB per query

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Kaggle dataset unavailable | High | Low | Document alternative sources (Wikipedia API) |
| CSV schema differs from assumptions | High | Medium | Flexible inspection script, adapt to actual schema |
| Local LLM too slow | Medium | Low | Document expected times, suggest GPU acceleration |
| Web scraping rate limits | Low | Medium | Add delays, use `--keep-store` to cache |
| Missing data affects queries | Medium | High | Create `complete_cases.csv` subset |
| Ollama setup issues | High | Medium | Detailed setup instructions, environment validation |

---

## Implementation Checklist

### Phase 1: Dataset Prep
- [ ] Download dataset from Kaggle
- [ ] Create cleaning script
- [ ] Create validation script
- [ ] Generate statistics
- [ ] Document data quality issues

### Phase 2: Query Creation
- [ ] Design 6 logical plans (JSON)
- [ ] Validate plans against schema
- [ ] Compile to SPARQL
- [ ] Test execution (Q1-Q4)
- [ ] Create post-processing scripts
- [ ] Document query patterns

### Phase 3: CLI Demo
- [ ] Implement SerialKillersDemo class
- [ ] Create dataset-specific prompt
- [ ] Extend QueryGenerator for custom prompts
- [ ] Build results formatting utilities
- [ ] Add environment validation
- [ ] Test interactive flow

### Phase 4: Documentation
- [ ] Write README.md
- [ ] Write QUICKSTART.md
- [ ] Write QUERIES.md
- [ ] Write ARCHITECTURE.md
- [ ] Write TROUBLESHOOTING.md
- [ ] Create demo session transcript
- [ ] Generate sample outputs

### Phase 5: Testing
- [ ] Create unit tests
- [ ] Create integration tests
- [ ] Create CLI tests
- [ ] Create performance benchmarks
- [ ] Execute user acceptance tests
- [ ] Generate coverage report

---

## Estimated Effort

| Phase | Days | Developer Hours | Notes |
|-------|------|-----------------|-------|
| Phase 1 | 2 | 12-16 | Includes manual dataset download |
| Phase 2 | 3 | 18-24 | Includes testing all queries |
| Phase 3 | 2 | 12-16 | Includes CLI integration |
| Phase 4 | 1 | 6-8 | Includes example generation |
| Phase 5 | 2 | 12-16 | Includes manual testing |
| **Total** | **10** | **60-80** | 2-3 weeks for 1 developer |

---

## Dependencies

### External Dependencies
- Kaggle account (free)
- Ollama (free, open-source)
- qwen2.5:3b model (free)

### Internal Dependencies
- SPARQLLM core (already implemented)
- QueryGenerator (Phase 3 from compiler project)
- PhysicalCompiler (Phase 2 from compiler project)
- GGF catalog (Phase 1 from compiler project)

### Phase Dependencies
- Phase 2 depends on Phase 1 (dataset ready)
- Phase 3 depends on Phase 2 (queries created)
- Phase 4 depends on Phase 3 (CLI working)
- Phase 5 depends on Phase 4 (docs complete)

---

## Next Steps

### Immediate (Day 1)
1. Get approval on this plan
2. Download dataset from Kaggle
3. Start Phase 1: dataset preparation

### Week 1
- Complete Phase 1 (dataset prep)
- Complete Phase 2 (query creation)
- Start Phase 3 (CLI demo)

### Week 2
- Complete Phase 3 (CLI demo)
- Complete Phase 4 (documentation)
- Start Phase 5 (testing)

### Week 3
- Complete Phase 5 (testing)
- Bug fixes and polish
- Final review and merge

---

## Questions for User

1. **Dataset Access:** Do you already have a Kaggle account, or should we document alternative dataset sources?

2. **Web Queries:** Should Q5-Q6 be implemented, or focus on local-only queries (Q1-Q4)?

3. **LLM Provider:** Confirm qwen2.5:3b (local) is acceptable, or prefer different model?

4. **Scope:** Should we include video demo or just written documentation?

5. **Testing:** Should CI/CD integration be included, or manual testing sufficient?

---

## Resources

### Documentation
- [SPARQLLM CLAUDE.md](../../CLAUDE.md) - Project overview
- [Kaggle Dataset](https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list)
- [Ollama Installation](https://ollama.com/)

### Related Plans
- [LLM as SPARQLLM Compiler](../20251120-1351-llm-sparqllm-compiler/plan.md) - Two-stage compilation architecture

### External References
- [SPARQL 1.1 Specification](https://www.w3.org/TR/sparql11-query/)
- [RDFlib Documentation](https://rdflib.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-20 | 1.0 | Initial plan created |

---

## Sign-Off

**Plan Author:** Claude Code (AI Assistant)
**Plan Reviewer:** [Awaiting User Review]
**Approval Date:** [Pending]

---

**Ready to proceed? Review this summary and approve to begin Phase 1 implementation.**
