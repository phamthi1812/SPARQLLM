# Phase 4: Testing & Validation

**Duration:** 2 weeks
**Dependencies:** Phase 1, 2, 3 (all components ready)
**Owner:** QA + Backend Developer

---

## Context

Need comprehensive validation of two-stage compiler before production. Test plan generation accuracy, compilation correctness, cost estimation precision, end-to-end integration.

---

## Overview

Build test suite with:
1. **Unit Tests:** Catalog, compiler, cost estimator, explainer (isolated components)
2. **Integration Tests:** 20 diverse queries (filesystem + LLM + web + SQL + hybrid)
3. **Benchmarking:** Direct vs compiled performance, cost accuracy
4. **Regression Tests:** Ensure backward compatibility (existing SPARQL queries still work)
5. **Error Recovery Tests:** Invalid plans, missing GGFs, execution failures

**Metrics:**
- Correctness (% queries producing valid results)
- Efficiency (latency overhead of compiler vs direct)
- Cost accuracy (MAE between estimated vs actual)

---

## Key Insights (from Research)

1. **Multi-hop reasoning needs iterative validation** (researcher-01 L62-70): Test queries requiring 3+ chained steps.
2. **Error patterns from text-to-SPARQL** (researcher-01 L11-13): Missing relations, over-specified filters, incomplete UNIONs. Include adversarial tests.
3. **Heterogeneous cost regimes** (researcher-01 L36-47): Test mix of fast (filesystem) + slow (LLM) operations.

---

## Requirements

### Functional
- [ ] 20 integration tests covering all GGF types
- [ ] Unit tests for all compiler components (>80% coverage)
- [ ] Benchmark suite: direct vs compiled (10 queries)
- [ ] Regression tests: 10 existing demo queries unchanged
- [ ] Error recovery: 10 adversarial cases (invalid GGFs, cycles, etc.)

### Non-Functional
- [ ] Test suite runs in <5 minutes (local execution)
- [ ] CI integration (GitHub Actions): runs on every commit
- [ ] Test data fixtures <10MB (no large downloads)
- [ ] Deterministic results (no flaky tests)

---

## Architecture

### 1. Test Data Structure

```
tests/
├── unit/
│   ├── test_catalog.py
│   ├── test_compiler.py
│   ├── test_cost_estimator.py
│   └── test_explainer.py
├── integration/
│   ├── test_queries.py
│   ├── fixtures/
│   │   ├── data/                  # Test CSV, TXT files
│   │   │   ├── events.txt
│   │   │   ├── data.csv
│   │   │   └── multi_file/
│   │   ├── plans/                 # Pre-written logical plans
│   │   │   ├── simple_filesystem.json
│   │   │   ├── llm_extraction.json
│   │   │   └── hybrid_web_llm.json
│   │   ├── expected_sparql/       # Ground truth SPARQL queries
│   │   │   ├── simple_filesystem.sparql
│   │   │   └── ...
│   │   └── expected_results/      # Ground truth query outputs
│   │       ├── simple_filesystem.json
│   │       └── ...
├── benchmarks/
│   ├── test_performance.py
│   └── results/
│       └── benchmark_report.md
├── regression/
│   └── test_existing_queries.py
└── error_recovery/
    └── test_adversarial.py
```

### 2. Integration Test Suite

**File:** `tests/integration/test_queries.py`

```python
"""
20 diverse integration tests covering all GGF combinations.
"""

import pytest
import json
from pathlib import Path
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler
from SPARQLLM.compiler.cost_estimator import CostEstimator
from SPARQLLM.catalog.query import load_catalog
from demo.query_generator import execute_query

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="module")
def compiler():
    catalog = load_catalog()
    return PhysicalCompiler(catalog)

@pytest.fixture(scope="module")
def cost_estimator():
    catalog = load_catalog()
    return CostEstimator(catalog)

# --- Test Cases ---

def test_01_simple_filesystem(compiler):
    """List CSV files in directory."""
    plan = load_plan("simple_filesystem.json")
    sparql = compiler.compile(plan)

    # Validate SPARQL syntax
    from rdflib.plugins.sparql.parser import parseQuery
    parseQuery(sparql)

    # Execute and check results
    success, stdout, stderr = execute_query(sparql)
    assert success, f"Query failed: {stderr}"
    assert "data.csv" in stdout

def test_02_csv_read(compiler):
    """Parse CSV and extract column values."""
    plan = load_plan("csv_read.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success
    # Verify expected columns present
    assert "city" in stdout.lower()

def test_03_llm_extraction(compiler):
    """Read text file, extract structured data with LLM."""
    plan = load_plan("llm_extraction.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success
    # Check for schema.org Event properties
    assert "schema:Event" in stdout or "eventName" in stdout

def test_04_web_search(compiler):
    """DuckDuckGo search, extract URLs."""
    plan = load_plan("web_search.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success
    # Verify URLs returned
    assert "http" in stdout

def test_05_vector_search_faiss(compiler):
    """FAISS similarity search."""
    # Requires pre-built FAISS index (skip if not available)
    pytest.skip("FAISS index not built (run slm-index-faiss)")

def test_06_hybrid_filesystem_llm(compiler):
    """Multi-stage: read files → LLM extract → aggregate."""
    plan = load_plan("hybrid_filesystem_llm.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success

def test_07_hybrid_web_llm(compiler):
    """Web search → snapshot page → LLM extract."""
    plan = load_plan("hybrid_web_llm.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success

def test_08_multi_source_join(compiler):
    """Join data from filesystem + LLM + web."""
    plan = load_plan("multi_source_join.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success

def test_09_filter_pushdown(compiler):
    """Verify FILTER applied early (before expensive LLM call)."""
    plan = load_plan("filter_pushdown.json")
    sparql = compiler.compile(plan)

    # Check SPARQL structure: FILTER before BIND(ggf:LLM(...))
    assert sparql.index("FILTER") < sparql.index("ggf:LLM")

def test_10_optional_binding(compiler):
    """Handle OPTIONAL clauses in plan."""
    plan = load_plan("optional_binding.json")
    sparql = compiler.compile(plan)

    success, stdout, stderr = execute_query(sparql)
    assert success

# Test 11-20: More complex scenarios (SQL, UNION, aggregation, etc.)
# ...

def test_cost_estimation_accuracy(compiler, cost_estimator):
    """Compare estimated vs actual cost for 10 queries."""
    test_cases = [
        "simple_filesystem.json",
        "llm_extraction.json",
        "web_search.json",
        "hybrid_filesystem_llm.json",
        "hybrid_web_llm.json"
    ]

    errors = []
    for case in test_cases:
        plan = load_plan(case)

        # Estimate cost
        estimated = cost_estimator.estimate(plan)

        # Execute and measure actual cost
        sparql = compiler.compile(plan)
        import time
        start = time.time()
        success, stdout, stderr = execute_query(sparql)
        actual_latency = (time.time() - start) * 1000  # ms

        # Calculate error
        error_pct = abs(estimated['latency_ms'] - actual_latency) / actual_latency * 100
        errors.append(error_pct)

    # Mean Absolute Error
    mae = sum(errors) / len(errors)
    assert mae < 30, f"Cost estimation MAE {mae:.1f}% exceeds 30% threshold"

# Helper functions
def load_plan(filename: str) -> dict:
    """Load logical plan from fixtures."""
    with open(FIXTURES / "plans" / filename) as f:
        return json.load(f)

def load_expected_sparql(filename: str) -> str:
    """Load expected SPARQL query."""
    with open(FIXTURES / "expected_sparql" / filename) as f:
        return f.read()
```

### 3. Unit Tests

**File:** `tests/unit/test_compiler.py`

```python
"""
Unit tests for physical compiler (isolated from LLM/execution).
"""

import pytest
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler
from SPARQLLM.catalog.query import load_catalog

@pytest.fixture
def compiler():
    catalog = load_catalog()
    return PhysicalCompiler(catalog)

def test_validate_plan_version(compiler):
    """Reject plans with unsupported version."""
    plan = {"version": "0.9", "steps": [], "output": {"variables": []}}
    with pytest.raises(ValueError, match="Unsupported plan version"):
        compiler._validate_plan(plan)

def test_validate_unknown_ggf(compiler):
    """Reject plans referencing non-existent GGFs."""
    plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "read_filesystem",
                "ggf": {"name": "INVALID_GGF", "args": {}},
                "bindings": {}
            }
        ],
        "output": {"variables": []}
    }
    with pytest.raises(ValueError, match="Unknown GGF"):
        compiler._validate_plan(plan)

def test_topological_sort_linear(compiler):
    """Sort steps with linear dependencies."""
    steps = [
        {"id": "step3", "depends_on": ["step2"]},
        {"id": "step1", "depends_on": []},
        {"id": "step2", "depends_on": ["step1"]}
    ]
    graph = compiler._build_dependency_graph(steps)
    sorted_steps = compiler._topological_sort(graph)

    assert [s['id'] for s in sorted_steps] == ["step1", "step2", "step3"]

def test_topological_sort_parallel(compiler):
    """Sort steps with parallel branches."""
    steps = [
        {"id": "step1", "depends_on": []},
        {"id": "step2", "depends_on": ["step1"]},
        {"id": "step3", "depends_on": ["step1"]},  # Parallel to step2
        {"id": "step4", "depends_on": ["step2", "step3"]}
    ]
    graph = compiler._build_dependency_graph(steps)
    sorted_steps = compiler._topological_sort(graph)

    # Verify step1 first, step4 last, step2/step3 in middle (order flexible)
    ids = [s['id'] for s in sorted_steps]
    assert ids[0] == "step1"
    assert ids[-1] == "step4"
    assert set(ids[1:3]) == {"step2", "step3"}

def test_detect_circular_dependency(compiler):
    """Reject plans with circular dependencies."""
    steps = [
        {"id": "step1", "depends_on": ["step2"]},
        {"id": "step2", "depends_on": ["step1"]}
    ]
    graph = compiler._build_dependency_graph(steps)

    with pytest.raises(ValueError, match="Circular dependency"):
        compiler._topological_sort(graph)

def test_compile_simple_plan(compiler):
    """Compile minimal valid plan to SPARQL."""
    plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "read_filesystem",
                "ggf": {
                    "name": "SLM-READDIR",
                    "args": {"path": "./data"}
                },
                "bindings": {"fileUri": "?fileUri"}
            }
        ],
        "output": {"variables": ["fileUri"]}
    }

    sparql = compiler.compile(plan)

    # Verify structure
    assert "PREFIX ggf:" in sparql
    assert "BIND(ggf:SLM-READDIR" in sparql
    assert "GRAPH ?dirGraph" in sparql
    assert "SELECT ?fileUri" in sparql
```

**File:** `tests/unit/test_cost_estimator.py`

```python
"""
Unit tests for cost estimator.
"""

import pytest
from SPARQLLM.compiler.cost_estimator import CostEstimator
from SPARQLLM.catalog.query import load_catalog

@pytest.fixture
def estimator():
    catalog = load_catalog()
    return CostEstimator(catalog)

def test_estimate_simple_filesystem(estimator):
    """Low-cost filesystem operation."""
    plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "read_filesystem",
                "ggf": {"name": "SLM-READDIR", "args": {}},
            }
        ],
        "output": {"variables": []}
    }

    cost = estimator.estimate(plan)

    assert cost['latency_ms'] < 100  # Fast operation
    assert cost['tokens'] == 0  # No LLM calls
    assert cost['api_calls'] == 0

def test_estimate_llm_call(estimator):
    """High-cost LLM operation."""
    plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "llm_extract",
                "ggf": {"name": "LLM", "args": {"prompt": "..."}},
            }
        ],
        "output": {"variables": []}
    }

    cost = estimator.estimate(plan)

    assert cost['latency_ms'] > 500  # Slow operation
    assert cost['tokens'] > 0
    assert cost['api_calls'] == 1
    assert cost['cost_usd'] > 0

def test_estimate_multi_step(estimator):
    """Aggregate costs across multiple steps."""
    plan = {
        "version": "1.0",
        "steps": [
            {"id": "step1", "operation": "read_filesystem", "ggf": {"name": "SLM-READDIR", "args": {}}},
            {"id": "step2", "operation": "llm_extract", "ggf": {"name": "LLM", "args": {}}},
            {"id": "step3", "operation": "web_search", "ggf": {"name": "SEARCH", "args": {}}}
        ],
        "output": {"variables": []}
    }

    cost = estimator.estimate(plan)

    # Sum of all steps
    assert cost['api_calls'] == 2  # LLM + web search
    assert cost['latency_ms'] > 1000  # LLM + web combined
```

### 4. Benchmark Suite

**File:** `tests/benchmarks/test_performance.py`

```python
"""
Compare direct vs compiled execution paths.
"""

import time
import pytest
from demo.query_generator import QueryGenerator, execute_query

BENCHMARK_QUERIES = [
    ("List CSV files", {"files": ["./data"], "sources": []}),
    ("Extract events with LLM", {"files": ["./data/events"], "sources": ["llm"]}),
    ("Web search concerts", {"files": [], "sources": ["web_search"]}),
    ("Hybrid: files + LLM + web", {"files": ["./data"], "sources": ["llm", "web_search"]})
]

@pytest.mark.parametrize("question,context", BENCHMARK_QUERIES)
def test_benchmark_direct_vs_compiled(question, context):
    """Measure latency overhead of compiler."""
    # Direct path
    gen_direct = QueryGenerator(mode='direct')
    start = time.time()
    sparql_direct = gen_direct.generate_query(question, context, verbose=False)
    success1, stdout1, stderr1 = execute_query(sparql_direct)
    time_direct = time.time() - start

    # Compiled path
    gen_plan = QueryGenerator(mode='plan')
    start = time.time()
    plan, sparql_compiled = gen_plan.two_stage_flow(question, context)
    success2, stdout2, stderr2 = execute_query(sparql_compiled)
    time_compiled = time.time() - start

    # Verify correctness
    assert success1 and success2, "Both paths must succeed"

    # Measure overhead
    overhead = (time_compiled / time_direct) - 1
    print(f"\n{question}: Direct={time_direct:.2f}s, Compiled={time_compiled:.2f}s, Overhead={overhead*100:.1f}%")

    # Threshold: compiled should be within 1.5x of direct
    assert overhead < 0.5, f"Compiler overhead {overhead*100:.1f}% exceeds 50% threshold"
```

### 5. Regression Tests

**File:** `tests/regression/test_existing_queries.py`

```python
"""
Ensure existing demo queries still work (backward compatibility).
"""

import pytest
from pathlib import Path
from demo.query_generator import execute_query

DEMO_QUERIES = Path(__file__).parent.parent.parent / "queries"

@pytest.mark.parametrize("query_file", [
    "filesystem/simple-csv.sparql",
    "filesystem/readfile.sparql",
    "ReadDir.sparql",
    # Add 7 more existing queries
])
def test_existing_query_unchanged(query_file):
    """Run existing SPARQL query, verify it still executes."""
    with open(DEMO_QUERIES / query_file) as f:
        sparql = f.read()

    success, stdout, stderr = execute_query(sparql)

    assert success, f"Query {query_file} failed: {stderr}"
    assert stdout.strip(), f"Query {query_file} returned empty results"
```

### 6. Error Recovery Tests

**File:** `tests/error_recovery/test_adversarial.py`

```python
"""
Adversarial test cases: invalid plans, missing GGFs, cycles.
"""

import pytest
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler
from SPARQLLM.catalog.query import load_catalog

@pytest.fixture
def compiler():
    catalog = load_catalog()
    return PhysicalCompiler(catalog)

def test_invalid_json_plan(compiler):
    """Reject malformed JSON."""
    plan = {"invalid": "structure"}
    with pytest.raises((ValueError, KeyError)):
        compiler.compile(plan)

def test_missing_ggf_in_catalog(compiler):
    """Reject plan with non-existent GGF."""
    plan = {
        "version": "1.0",
        "steps": [{"id": "step1", "operation": "read_filesystem", "ggf": {"name": "NONEXISTENT", "args": {}}}],
        "output": {"variables": []}
    }
    with pytest.raises(ValueError, match="Unknown GGF"):
        compiler._validate_plan(plan)

def test_circular_dependencies(compiler):
    """Reject plan with circular step dependencies."""
    plan = {
        "version": "1.0",
        "steps": [
            {"id": "step1", "depends_on": ["step2"]},
            {"id": "step2", "depends_on": ["step1"]}
        ],
        "output": {"variables": []}
    }
    with pytest.raises(ValueError, match="Circular"):
        compiler.compile(plan)

def test_unbound_variable(compiler):
    """Reject plan referencing unbound variable."""
    plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "llm_extract",
                "ggf": {"name": "LLM", "args": {"prompt": "Use {?undefinedVar}"}},
                "bindings": {}
            }
        ],
        "output": {"variables": ["result"]}
    }
    with pytest.raises(ValueError, match="Unbound variable"):
        compiler.compile(plan)
```

---

## Implementation Steps

### Week 1: Unit + Integration Tests

1. **Day 1-3:** Write unit tests
   - Catalog query tests (5 test cases)
   - Compiler tests (10 test cases: validation, topological sort, compilation)
   - Cost estimator tests (5 test cases)
   - Explainer tests (3 test cases)

2. **Day 4-5:** Build integration test fixtures
   - Create 20 test plans (JSON)
   - Create 20 expected SPARQL queries
   - Prepare test data (CSV, TXT files)
   - Document test case coverage matrix

### Week 2: Benchmarks + Regression + CI

3. **Day 6-7:** Write integration tests
   - Implement 20 test functions (one per fixture)
   - Run test suite, fix failures
   - Achieve 18/20 passing (90% success rate)

4. **Day 8:** Benchmarking
   - Implement performance comparison tests
   - Run benchmarks on 10 queries
   - Generate performance report (markdown table)

5. **Day 9:** Regression + error recovery
   - Test 10 existing demo queries
   - Write 10 adversarial test cases
   - Verify graceful error handling

6. **Day 10:** CI integration
   - Add GitHub Actions workflow
   - Configure test matrix (Python 3.10, 3.11, 3.12)
   - Add coverage reporting (codecov)

---

## Todo List

- [ ] Write 30 unit tests (catalog, compiler, cost, explainer)
- [ ] Create 20 integration test fixtures (plans + expected outputs)
- [ ] Prepare test data (CSV, TXT files <10MB total)
- [ ] Implement 20 integration tests
- [ ] Build benchmark suite (direct vs compiled, 10 queries)
- [ ] Write 10 regression tests (existing demo queries)
- [ ] Create 10 adversarial tests (error recovery)
- [ ] Add GitHub Actions CI workflow
- [ ] Generate test coverage report (target >80%)
- [ ] Document test suite usage (README)

---

## Success Criteria

1. 90% integration tests pass (18/20)
2. Unit test coverage >80% (compiler, cost estimator, explainer)
3. Benchmark: compiler overhead <50% (vs direct path)
4. Cost estimation MAE <30% (5 test queries)
5. Regression: 10/10 existing queries still work
6. Error recovery: 10/10 adversarial cases handled gracefully
7. CI: tests run in <5 minutes

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test data too large (slow CI) | Medium | Use synthetic data; mock external APIs |
| LLM variability (flaky tests) | High | Use deterministic temperature=0; retry on failure |
| Cost estimation highly inaccurate | High | Relax threshold to 50% MAE initially; refine in production |
| Integration tests fail due to missing API keys | Medium | Mock MCP providers; skip tests requiring keys |

---

## Security Considerations

- **Test data sanitization**: No real API keys or PII in fixtures
- **Isolated test environment**: Use separate config.ini for tests
- **Rate limit respect**: Mock external APIs (DuckDuckGo, Groq) to avoid bans

---

## Unresolved Questions

1. Should benchmarks include LLM generation latency or only execution?
2. How to test MCP tools without actual API access (mocking strategy)?
3. Cost estimation: use fixed catalog values or empirical averages from test runs?
