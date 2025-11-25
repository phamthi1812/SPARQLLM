# Phase 5: Testing & Validation

**Duration:** 2 days
**Dependencies:** Phase 4 (documentation complete)
**Status:** Not Started

---

## Objectives

1. Create test suite for all 6 queries
2. Validate two-stage compilation pipeline
3. Test CLI interaction flows
4. Performance benchmarking
5. User acceptance testing

---

## Testing Strategy

### Test Pyramid

```
                  ┌────────────────┐
                  │   User Tests   │  (Manual)
                  │   - E2E flows  │
                  └────────────────┘
                         ↑
              ┌──────────────────────┐
              │  Integration Tests   │  (Automated)
              │  - Query execution   │
              │  - CLI commands      │
              └──────────────────────┘
                         ↑
       ┌──────────────────────────────────┐
       │         Unit Tests               │  (Automated)
       │  - Plan validation               │
       │  - SPARQL compilation            │
       │  - Data cleaning functions       │
       └──────────────────────────────────┘
```

---

## Test Suite 5.1: Unit Tests

**File:** `demo/serial_killers/tests/test_unit.py`

**Coverage:**
1. Data cleaning functions
2. Logical plan validation
3. SPARQL compilation
4. Results formatting

**Tests:**

```python
import json
import pytest
from pathlib import Path

from SPARQLLM.compiler import PhysicalCompiler
from demo.serial_killers.setup.clean_data import parse_years, parse_victims
from demo.serial_killers.utils.format_results import format_table, format_csv


class TestDataCleaning:
    """Test data cleaning functions"""

    def test_parse_years_range(self):
        """Test year range parsing"""
        assert parse_years("1972-1978") == (1972, 1978, "1970s")

    def test_parse_years_single(self):
        """Test single year parsing"""
        assert parse_years("1995") == (1995, 1995, "1990s")

    def test_parse_years_invalid(self):
        """Test invalid year format"""
        assert parse_years("Unknown") == (None, None, None)

    def test_parse_victims_exact(self):
        """Test exact victim count"""
        assert parse_victims("33") == (33, 33)

    def test_parse_victims_range(self):
        """Test victim range"""
        assert parse_victims("10-15") == (10, 15)

    def test_parse_victims_plus(self):
        """Test victim count with +"""
        assert parse_victims("50+") == (50, 50)

    def test_parse_victims_invalid(self):
        """Test invalid victim format"""
        assert parse_victims("Unknown") == (None, None)


class TestLogicalPlans:
    """Test logical plan validation"""

    @pytest.fixture
    def compiler(self):
        return PhysicalCompiler()

    @pytest.fixture
    def plans_dir(self):
        return Path(__file__).parent.parent / "queries" / "plans"

    def test_q1_plan_valid(self, compiler, plans_dir):
        """Test Q1 logical plan is valid"""
        plan_path = plans_dir / "q1_top_victims.json"
        with open(plan_path, 'r') as f:
            plan = json.load(f)

        # Should not raise exception
        compiler.compile(plan)

    def test_q2_plan_valid(self, compiler, plans_dir):
        """Test Q2 logical plan is valid"""
        plan_path = plans_dir / "q2_methods_by_decade.json"
        with open(plan_path, 'r') as f:
            plan = json.load(f)

        compiler.compile(plan)

    def test_all_plans_valid(self, compiler, plans_dir):
        """Test all 6 plans compile successfully"""
        for i in range(1, 7):
            plan_files = list(plans_dir.glob(f"q{i}_*.json"))
            assert len(plan_files) == 1, f"Expected 1 plan file for Q{i}"

            with open(plan_files[0], 'r') as f:
                plan = json.load(f)

            # Should compile without errors
            sparql = compiler.compile(plan)
            assert sparql is not None
            assert len(sparql) > 0


class TestSPARQLCompilation:
    """Test SPARQL query compilation"""

    @pytest.fixture
    def compiler(self):
        return PhysicalCompiler()

    def test_simple_csv_plan(self, compiler):
        """Test compilation of simple CSV read"""
        plan = {
            "version": "1.0",
            "steps": [
                {
                    "id": "step1",
                    "operation": "read_filesystem",
                    "ggf": {"name": "SLM-CSV", "args": {"file": "./data.csv"}},
                    "bindings": {"name": "?name"}
                }
            ],
            "output": {"variables": ["name"]}
        }

        sparql = compiler.compile(plan)
        assert "SLM-CSV" in sparql
        assert "GRAPH" in sparql
        assert "?name" in sparql

    def test_dependency_ordering(self, compiler):
        """Test steps ordered by dependencies"""
        plan = {
            "version": "1.0",
            "steps": [
                {
                    "id": "step2",
                    "operation": "llm_extract",
                    "ggf": {"name": "LLM", "args": {"prompt": "?text"}},
                    "depends_on": ["step1"],
                    "bindings": {"result": "?result"}
                },
                {
                    "id": "step1",
                    "operation": "read_filesystem",
                    "ggf": {"name": "SLM-READFILE", "args": {"file": "./data.txt"}},
                    "bindings": {"text": "?text"}
                }
            ],
            "output": {"variables": ["result"]}
        }

        sparql = compiler.compile(plan)
        # step1 should appear before step2 in SPARQL
        step1_pos = sparql.index("SLM-READFILE")
        step2_pos = sparql.index("LLM")
        assert step1_pos < step2_pos


class TestResultsFormatting:
    """Test results formatting functions"""

    def test_format_table(self):
        """Test table formatting"""
        results = [
            {"name": "Harold Shipman", "victims": 218},
            {"name": "Luis Garavito", "victims": 193}
        ]

        output = format_table(results)
        assert "Harold Shipman" in output
        assert "218" in output

    def test_format_csv(self):
        """Test CSV formatting"""
        results = [{"name": "Test", "value": 123}]
        output = format_csv(results)
        assert "name,value" in output
        assert "Test,123" in output

    def test_format_empty_results(self):
        """Test formatting empty results"""
        assert format_table([]) == "No results."
        assert format_csv([]) == ""
```

**Run:**
```bash
pytest demo/serial_killers/tests/test_unit.py -v
```

---

## Test Suite 5.2: Integration Tests

**File:** `demo/serial_killers/tests/test_integration.py`

**Coverage:**
1. Query execution (all 6 queries)
2. Two-stage compilation pipeline
3. GGF function calls
4. Results validation

**Tests:**

```python
import json
import os
import pytest
from pathlib import Path

from demo.query_generator import QueryGenerator
from SPARQLLM.compiler import PhysicalCompiler
import subprocess


class TestQueryExecution:
    """Test query execution via slm-run"""

    @pytest.fixture
    def data_dir(self):
        return Path(__file__).parent.parent / "data"

    @pytest.fixture
    def queries_dir(self):
        return Path(__file__).parent.parent / "queries"

    @pytest.fixture
    def csv_path(self, data_dir):
        path = data_dir / "serial_killers_clean.csv"
        if not path.exists():
            pytest.skip("Dataset not available")
        return path

    def test_q1_top_victims(self, queries_dir, csv_path):
        """Test Q1: Top 10 by victim count"""
        query_file = queries_dir / "q1_top_victims.sparql"

        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', str(query_file)],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert "Harold Shipman" in result.stdout or "name" in result.stdout

    @pytest.mark.slow
    def test_q2_methods_by_decade(self, queries_dir, csv_path):
        """Test Q2: Methods by decade (with LLM)"""
        query_file = queries_dir / "q2_methods_by_decade.sparql"

        # Skip if Ollama not available
        if not self._ollama_available():
            pytest.skip("Ollama not available")

        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', str(query_file)],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        # Check for decade and category columns
        assert "decade" in result.stdout.lower()

    def test_q3_wikipedia_summary(self, queries_dir, csv_path):
        """Test Q3: Wikipedia summary"""
        query_file = queries_dir / "q3_wikipedia_summary.sparql"

        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', str(query_file)],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert "Ted Bundy" in result.stdout or "summary" in result.stdout

    @pytest.mark.slow
    def test_q4_extract_methods(self, queries_dir, csv_path):
        """Test Q4: Extract methods with LLM"""
        if not self._ollama_available():
            pytest.skip("Ollama not available")

        query_file = queries_dir / "q4_extract_methods.sparql"

        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', str(query_file)],
            capture_output=True,
            text=True,
            timeout=90
        )

        assert result.returncode == 0

    @pytest.mark.slow
    @pytest.mark.web
    def test_q5_unsolved_patterns(self, queries_dir, csv_path):
        """Test Q5: Unsolved patterns (requires web search)"""
        pytest.skip("Web search requires MCP server")

    @pytest.mark.slow
    @pytest.mark.web
    def test_q6_verify_counts(self, queries_dir, csv_path):
        """Test Q6: Verify victim counts"""
        pytest.skip("Web scraping may hit rate limits")

    def _ollama_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            return response.status_code == 200
        except:
            return False


class TestTwoStageCompilation:
    """Test two-stage compilation pipeline"""

    @pytest.fixture
    def generator(self):
        # Use mock LLM for testing
        return QueryGenerator(mode='plan')

    @pytest.fixture
    def compiler(self):
        return PhysicalCompiler()

    def test_preset_plan_compiles(self, compiler):
        """Test preset plans compile successfully"""
        plans_dir = Path(__file__).parent.parent / "queries" / "plans"
        plan_path = plans_dir / "q1_top_victims.json"

        with open(plan_path, 'r') as f:
            plan = json.load(f)

        sparql = compiler.compile(plan)
        assert sparql is not None
        assert "SELECT" in sparql
        assert "WHERE" in sparql

    def test_compilation_preserves_dependencies(self, compiler):
        """Test dependency order preserved in compilation"""
        plan = {
            "version": "1.0",
            "steps": [
                {
                    "id": "step1",
                    "operation": "read_filesystem",
                    "ggf": {"name": "SLM-CSV", "args": {"file": "./data.csv"}},
                    "bindings": {"url": "?url"}
                },
                {
                    "id": "step2",
                    "operation": "web_scrape",
                    "ggf": {"name": "SLM-GETTEXT", "args": {"url": "?url"}},
                    "depends_on": ["step1"],
                    "bindings": {"text": "?text"}
                }
            ],
            "output": {"variables": ["text"]}
        }

        sparql = compiler.compile(plan)
        # Verify step1 appears before step2
        assert sparql.index("SLM-CSV") < sparql.index("SLM-GETTEXT")


class TestGGFFunctionCalls:
    """Test individual GGF function calls"""

    def test_slm_csv_reads_data(self):
        """Test SLM-CSV reads CSV correctly"""
        from SPARQLLM.udf.mycsv import slm_csv
        from rdflib import Graph, Namespace

        csv_path = Path(__file__).parent.parent / "data" / "serial_killers_clean.csv"
        if not csv_path.exists():
            pytest.skip("Dataset not available")

        # Mock context
        class MockCtx:
            pass

        ctx = MockCtx()

        # Call GGF
        graph_uri = slm_csv(ctx, str(csv_path))
        assert graph_uri is not None

        # Verify graph exists in store
        from SPARQLLM.udf.SPARQLLM import store
        assert (None, None, None, graph_uri) in store

    @pytest.mark.slow
    def test_llm_generates_response(self):
        """Test LLM GGF generates response"""
        if not self._ollama_available():
            pytest.skip("Ollama not available")

        from SPARQLLM.udf.mcp.alias import _alias_llm

        class MockCtx:
            pass

        ctx = MockCtx()
        prompt = "Say 'test' and nothing else."

        graph_uri = _alias_llm(ctx, prompt)
        assert graph_uri is not None

    def _ollama_available(self):
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            return response.status_code == 200
        except:
            return False
```

**Run:**
```bash
# Fast tests only (no LLM)
pytest demo/serial_killers/tests/test_integration.py -v -m "not slow"

# All tests including slow LLM calls
pytest demo/serial_killers/tests/test_integration.py -v

# Skip web-dependent tests
pytest demo/serial_killers/tests/test_integration.py -v -m "not web"
```

---

## Test Suite 5.3: CLI Interaction Tests

**File:** `demo/serial_killers/tests/test_cli.py`

**Coverage:**
1. Menu navigation
2. Preset question execution
3. Custom question flow
4. Error handling

**Tests:**

```python
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from demo.serial_killers.serial_killers_demo import SerialKillersDemo


class TestCLIInteraction:
    """Test CLI interaction flows"""

    @pytest.fixture
    def demo(self):
        with patch('demo.serial_killers.serial_killers_demo.QueryGenerator'):
            return SerialKillersDemo()

    def test_display_welcome(self, demo, capsys):
        """Test welcome message displays"""
        demo.display_welcome()
        captured = capsys.readouterr()
        assert "Serial Killers Dataset" in captured.out

    def test_display_menu(self, demo, capsys):
        """Test menu displays options"""
        demo.display_menu()
        captured = capsys.readouterr()
        assert "[1-6]" in captured.out
        assert "[Q]" in captured.out

    def test_list_preset_questions(self, demo, capsys):
        """Test listing preset questions"""
        demo.list_preset_questions()
        captured = capsys.readouterr()
        assert "top 10" in captured.out.lower()
        assert "methods" in captured.out.lower()

    def test_show_stats(self, demo, capsys):
        """Test showing statistics"""
        demo.show_stats()
        captured = capsys.readouterr()
        assert "Statistics" in captured.out

    @patch('builtins.input', return_value='n')
    def test_run_preset_question_abort(self, mock_input, demo, capsys):
        """Test aborting preset question"""
        demo.run_preset_question(1)
        captured = capsys.readouterr()
        # Should show plan but not execute
        assert "Logical Plan" in captured.out or "Question" in captured.out

    @patch('subprocess.run')
    @patch('builtins.input', return_value='y')
    def test_run_preset_question_execute(self, mock_input, mock_run, demo):
        """Test executing preset question"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Results", stderr="")
        demo.run_preset_question(1)
        # Should call slm-run
        assert mock_run.called

    def test_invalid_question_id(self, demo, capsys):
        """Test invalid question ID"""
        demo.run_preset_question(999)
        captured = capsys.readouterr()
        assert "Invalid" in captured.out or "Error" in captured.out


class TestErrorHandling:
    """Test error handling"""

    def test_missing_dataset(self):
        """Test error when dataset missing"""
        with patch('pathlib.Path.exists', return_value=False):
            demo = SerialKillersDemo()
            # Should not crash, but show warnings
            assert demo is not None

    @patch('demo.serial_killers.serial_killers_demo.QueryGenerator')
    def test_llm_unavailable(self, mock_generator):
        """Test handling when LLM unavailable"""
        mock_generator.side_effect = RuntimeError("LLM not available")
        demo = SerialKillersDemo()
        # Should handle gracefully
        assert demo is not None

    def test_query_timeout_handling(self, capsys):
        """Test query timeout handling"""
        # Mock query execution with timeout
        # Should display timeout error message
        pass  # TODO: Implement
```

**Run:**
```bash
pytest demo/serial_killers/tests/test_cli.py -v
```

---

## Test Suite 5.4: Performance Benchmarks

**File:** `demo/serial_killers/tests/test_performance.py`

**Coverage:**
1. Query execution times
2. LLM inference latency
3. CSV parsing speed
4. Memory usage

**Tests:**

```python
import pytest
import time
from pathlib import Path
import subprocess


class TestPerformance:
    """Performance benchmarks"""

    @pytest.fixture
    def csv_path(self):
        path = Path(__file__).parent.parent / "data" / "serial_killers_clean.csv"
        if not path.exists():
            pytest.skip("Dataset not available")
        return path

    def test_q1_execution_time(self, csv_path):
        """Test Q1 executes within time limit"""
        query_file = Path(__file__).parent.parent / "queries" / "q1_top_victims.sparql"

        start = time.time()
        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', str(query_file)],
            capture_output=True,
            timeout=10
        )
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 5.0, f"Q1 took {elapsed:.2f}s (expected <5s)"

    @pytest.mark.slow
    def test_q2_execution_time(self, csv_path):
        """Test Q2 executes within time limit"""
        if not self._ollama_available():
            pytest.skip("Ollama not available")

        query_file = Path(__file__).parent.parent / "queries" / "q2_methods_by_decade.sparql"

        start = time.time()
        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', str(query_file)],
            capture_output=True,
            timeout=120
        )
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 60.0, f"Q2 took {elapsed:.2f}s (expected <60s)"

    def test_csv_parsing_speed(self, csv_path):
        """Test CSV parsing is fast"""
        from SPARQLLM.udf.mycsv import slm_csv

        class MockCtx:
            pass

        start = time.time()
        slm_csv(MockCtx(), str(csv_path))
        elapsed = time.time() - start

        assert elapsed < 1.0, f"CSV parsing took {elapsed:.2f}s (expected <1s)"

    def _ollama_available(self):
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            return response.status_code == 200
        except:
            return False


class TestMemoryUsage:
    """Memory usage tests"""

    @pytest.mark.slow
    def test_query_memory_footprint(self):
        """Test query execution doesn't leak memory"""
        import psutil
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run multiple queries
        for i in range(5):
            subprocess.run(
                ['slm-run', '-f', 'demo/serial_killers/queries/q1_top_victims.sparql'],
                capture_output=True,
                timeout=10
            )
            gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"
```

**Run:**
```bash
pytest demo/serial_killers/tests/test_performance.py -v
```

---

## Test Suite 5.5: User Acceptance Tests (Manual)

**File:** `demo/serial_killers/tests/USER_ACCEPTANCE_TESTS.md`

**Test Cases:**

```markdown
# User Acceptance Test Cases

## Prerequisites
- Dataset downloaded and cleaned
- Ollama running with qwen2.5:3b model
- CLI demo script ready

## Test Case 1: First-Time Setup
**Goal:** New user can set up and run first query in 5 minutes

**Steps:**
1. Follow QUICKSTART.md exactly as written
2. Time each step
3. Note any confusing instructions

**Success Criteria:**
- [ ] Total time < 5 minutes
- [ ] No errors encountered
- [ ] Q1 executes successfully

---

## Test Case 2: Preset Questions
**Goal:** User can execute all preset questions

**Steps:**
1. Start CLI: `python serial_killers_demo.py`
2. Select option [L] to list questions
3. Execute Q1-Q4 (local only)
4. Verify outputs match expected results

**Success Criteria:**
- [ ] All questions listed clearly
- [ ] Q1-Q4 execute without errors
- [ ] Results are readable and correct

---

## Test Case 3: Custom Question
**Goal:** User can ask custom natural language question

**Steps:**
1. Start CLI
2. Select option [Q]
3. Enter: "Who killed the most people in the 1980s?"
4. Review generated plan
5. Confirm execution

**Success Criteria:**
- [ ] LLM generates valid plan
- [ ] Plan is understandable
- [ ] Query executes correctly
- [ ] Results answer the question

---

## Test Case 4: Error Handling
**Goal:** Errors are handled gracefully with helpful messages

**Steps:**
1. Stop Ollama: `killall ollama`
2. Start CLI
3. Try to execute Q2 (requires LLM)
4. Note error message

**Success Criteria:**
- [ ] Clear error message
- [ ] Suggests solution (start Ollama)
- [ ] CLI doesn't crash

---

## Test Case 5: Results Export
**Goal:** User can save results to file

**Steps:**
1. Execute Q1 via slm-run:
   ```bash
   slm-run -f demo/serial_killers/queries/q1_top_victims.sparql -o results.csv
   ```
2. Verify file created
3. Open in spreadsheet

**Success Criteria:**
- [ ] File created successfully
- [ ] CSV format valid
- [ ] Data matches screen output

---

## Test Case 6: Documentation Navigation
**Goal:** User can find answers in documentation

**Scenarios:**
- Dataset not found → Check QUICKSTART.md
- Query timeout → Check TROUBLESHOOTING.md
- Want to add new query → Check QUERIES.md

**Success Criteria:**
- [ ] Each scenario answered in <2 minutes
- [ ] Instructions are clear
- [ ] Links work correctly
```

---

## Implementation Tasks

### Task 5.1: Create Test Suites
- [ ] `test_unit.py` - Unit tests
- [ ] `test_integration.py` - Integration tests
- [ ] `test_cli.py` - CLI interaction tests
- [ ] `test_performance.py` - Performance benchmarks
- [ ] `USER_ACCEPTANCE_TESTS.md` - Manual test cases

### Task 5.2: Run Automated Tests
- [ ] Run unit tests (fast)
- [ ] Run integration tests (with dataset)
- [ ] Run CLI tests
- [ ] Run performance benchmarks
- [ ] Document results

### Task 5.3: Execute Manual Tests
- [ ] Perform user acceptance tests
- [ ] Record issues encountered
- [ ] Fix critical bugs
- [ ] Update documentation

### Task 5.4: Performance Analysis
- [ ] Benchmark all 6 queries
- [ ] Profile memory usage
- [ ] Identify bottlenecks
- [ ] Document findings

### Task 5.5: Test Coverage Report
- [ ] Generate coverage report
- [ ] Identify gaps
- [ ] Add missing tests
- [ ] Achieve >80% coverage

---

## Deliverables

### Test Files
- [ ] `demo/serial_killers/tests/test_unit.py`
- [ ] `demo/serial_killers/tests/test_integration.py`
- [ ] `demo/serial_killers/tests/test_cli.py`
- [ ] `demo/serial_killers/tests/test_performance.py`
- [ ] `demo/serial_killers/tests/USER_ACCEPTANCE_TESTS.md`

### Test Configuration
- [ ] `demo/serial_killers/tests/pytest.ini` - Pytest configuration
- [ ] `demo/serial_killers/tests/conftest.py` - Shared fixtures

### Reports
- [ ] Test coverage report
- [ ] Performance benchmark results
- [ ] User acceptance test results
- [ ] Bug report (if any)

---

## Verification Commands

```bash
# Run all unit tests
pytest demo/serial_killers/tests/test_unit.py -v

# Run integration tests (fast only)
pytest demo/serial_killers/tests/test_integration.py -v -m "not slow and not web"

# Run all tests with coverage
pytest demo/serial_killers/tests/ -v --cov=demo/serial_killers --cov-report=html

# Run performance benchmarks
pytest demo/serial_killers/tests/test_performance.py -v

# Generate coverage report
open htmlcov/index.html
```

---

## Pytest Configuration

**File:** `demo/serial_killers/tests/pytest.ini`

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    web: marks tests requiring web access (deselect with '-m "not web"')

testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Timeout for tests
timeout = 180

# Show warnings
addopts = -v --tb=short --strict-markers
```

---

## Conftest (Shared Fixtures)

**File:** `demo/serial_killers/tests/conftest.py`

```python
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory"""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture(scope="session")
def demo_dir():
    """Get demo directory"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def data_dir(demo_dir):
    """Get data directory"""
    return demo_dir / "data"


@pytest.fixture(scope="session")
def queries_dir(demo_dir):
    """Get queries directory"""
    return demo_dir / "queries"


@pytest.fixture(scope="session")
def csv_path(data_dir):
    """Get cleaned CSV path"""
    path = data_dir / "serial_killers_clean.csv"
    if not path.exists():
        pytest.skip("Dataset not available")
    return path


@pytest.fixture(scope="session")
def ollama_available():
    """Check if Ollama is available"""
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False
```

---

## Test Execution Matrix

| Test Suite | Duration | Dependencies | CI Ready |
|------------|----------|--------------|----------|
| Unit tests | <10s | None | Yes |
| Integration (fast) | <30s | Dataset | Yes |
| Integration (slow) | ~5min | Dataset, Ollama | No |
| CLI tests | <20s | Mock LLM | Yes |
| Performance | ~10min | Dataset, Ollama | No |
| User acceptance | ~30min | Full setup | No |

---

## Success Criteria

**Overall Test Suite:**
- [ ] 90%+ unit test coverage
- [ ] All integration tests pass (fast)
- [ ] CLI tests pass
- [ ] Performance benchmarks < expected times
- [ ] User acceptance tests complete successfully

**Individual Queries:**
- [ ] Q1: Executes in <5s
- [ ] Q2: Executes in <60s (with LLM)
- [ ] Q3: Executes in <10s
- [ ] Q4: Executes in <30s (with LLM)
- [ ] Q5: Documented as requiring web search
- [ ] Q6: Documented as requiring web scraping

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ollama unavailable in CI | High | Mock LLM for CI tests, real LLM for local |
| Web tests flaky | Medium | Mark as `@pytest.mark.web`, skip in CI |
| Performance tests slow | Medium | Run separately, not in main test suite |
| Dataset download manual | Low | Document clearly, provide validation |

---

## Next Steps

After Phase 5 completion:
1. Merge demo into main branch
2. Add to project test suite
3. Document in main README
4. Create demo video (optional)
5. Publish to documentation site
