# Phase 4: Testing & Integration

**Status:** Ready
**Estimated Effort:** 2-3 hours
**Dependencies:** Phases 1-3 (prompt, generator, validator complete)

---

## Objective

End-to-end testing of LLM direct SPARQL generation with serial killers demo.

---

## Test Suite

### 1. Prompt-Only Tests (Isolated LLM)

**Purpose:** Validate prompt effectiveness without code dependencies

**Test Questions:**
1. "Show me the top 10 serial killers by victim count"
2. "Which serial killers killed more than 50 people?"
3. "List serial killers who operated in multiple countries"
4. "How many serial killers were active in each decade?"
5. "Find American serial killers from the 1980s"

**Execution:**
```bash
# Manual test with ollama
ollama run llama3.2:latest < test_prompt.txt
```

**test_prompt.txt:**
```
[Paste direct_system_prompt.txt]

Question: Show me the top 10 serial killers by victim count
```

**Success Criteria:**
- 5/5 questions generate valid SPARQL
- No markdown fences in output
- All queries use correct GGF syntax (BIND + GRAPH)

---

### 2. Unit Tests (QueryGenerator)

**File:** `tests/unit/test_query_generator_direct.py`

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../demo'))

import pytest
from query_generator import QueryGenerator
from SPARQLLM.compiler.sparql_validator import SPARQLValidator


@pytest.fixture
def generator():
    """Create QueryGenerator in direct mode."""
    return QueryGenerator(mode='direct', provider='ollama')


@pytest.fixture
def validator():
    """Create SPARQL validator."""
    return SPARQLValidator(strict=True)


def test_initialization(generator):
    """Test direct mode initialization."""
    assert generator.mode == 'direct'
    assert hasattr(generator, 'validator')


def test_prompt_loading(generator):
    """Test system prompt loads correctly."""
    prompt_path = os.path.join(
        os.path.dirname(generator.__file__),
        'serial_killers/prompts/direct_system_prompt.txt'
    )
    assert os.path.exists(prompt_path)

    with open(prompt_path) as f:
        prompt = f.read()

    assert 'PREFIX ggf:' in prompt
    assert 'ggf:SLM-CSV' in prompt
    assert 'Example' in prompt or 'example' in prompt


def test_markdown_cleaning(generator):
    """Test markdown fence removal."""
    test_cases = [
        ("```sparql\nSELECT ?s WHERE {}\n```", "SELECT ?s WHERE {}"),
        ("```\nSELECT ?s WHERE {}\n```", "SELECT ?s WHERE {}"),
        ("SELECT ?s WHERE {}", "SELECT ?s WHERE {}"),
    ]

    for input_text, expected in test_cases:
        result = generator._clean_sparql_response(input_text)
        assert result == expected


@pytest.mark.integration
def test_generate_sparql_basic(generator, validator):
    """Test basic SPARQL generation."""
    question = "Show me the top 10 serial killers by victim count"

    sparql = generator.generate_sparql(question)

    # Basic structure checks
    assert "PREFIX ggf:" in sparql
    assert "PREFIX ex:" in sparql
    assert "BIND(ggf:SLM-CSV" in sparql
    assert "GRAPH" in sparql
    assert "ORDER BY" in sparql
    assert "LIMIT" in sparql

    # Validation
    is_valid, errors = validator.validate(sparql)
    assert is_valid, f"Validation errors: {errors}"


@pytest.mark.integration
def test_generate_sparql_with_filter(generator, validator):
    """Test SPARQL generation with FILTER."""
    question = "Which serial killers killed more than 50 people?"

    sparql = generator.generate_sparql(question)

    assert "FILTER" in sparql
    assert "50" in sparql

    is_valid, errors = validator.validate(sparql)
    assert is_valid, f"Validation errors: {errors}"


@pytest.mark.integration
def test_generate_sparql_aggregation(generator, validator):
    """Test SPARQL generation with GROUP BY."""
    question = "How many serial killers were active in each decade?"

    sparql = generator.generate_sparql(question)

    assert "GROUP BY" in sparql
    assert "COUNT" in sparql or "SUM" in sparql

    is_valid, errors = validator.validate(sparql)
    assert is_valid, f"Validation errors: {errors}"


@pytest.mark.integration
def test_generate_sparql_pattern_matching(generator, validator):
    """Test SPARQL generation with CONTAINS."""
    question = "Which serial killers operated in multiple countries?"

    sparql = generator.generate_sparql(question)

    assert "FILTER" in sparql
    assert "CONTAINS" in sparql or "," in sparql  # Looking for comma pattern

    is_valid, errors = validator.validate(sparql)
    assert is_valid, f"Validation errors: {errors}"
```

---

### 3. Integration Tests (End-to-End)

**File:** `tests/integration/test_direct_sparql_e2e.py`

```python
import subprocess
import tempfile
import os
import json


def execute_sparql(sparql: str) -> dict:
    """Execute SPARQL via slm-run and return results."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sparql', delete=False) as f:
        f.write(sparql)
        temp_path = f.name

    try:
        # Execute query
        result = subprocess.run(
            ['slm-run', '--config', 'config.ini', '-f', temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    finally:
        os.unlink(temp_path)


def test_e2e_top_killers():
    """E2E test: Top 10 serial killers."""
    from demo.query_generator import QueryGenerator

    generator = QueryGenerator(mode='direct', provider='ollama')
    question = "Show me the top 10 serial killers by victim count"

    # Generate SPARQL
    sparql = generator.generate_sparql(question)

    # Execute
    result = execute_sparql(sparql)

    assert result['success'], f"Execution failed: {result['stderr']}"
    assert len(result['stdout']) > 0, "No output"

    # Parse results (basic check)
    lines = result['stdout'].strip().split('\n')
    assert len(lines) >= 10, f"Expected at least 10 results, got {len(lines)}"


def test_e2e_filtered_query():
    """E2E test: Filtered query."""
    from demo.query_generator import QueryGenerator

    generator = QueryGenerator(mode='direct', provider='ollama')
    question = "Serial killers with more than 100 victims"

    sparql = generator.generate_sparql(question)
    result = execute_sparql(sparql)

    assert result['success']
    assert len(result['stdout']) > 0


def test_e2e_aggregation():
    """E2E test: Aggregation query."""
    from demo.query_generator import QueryGenerator

    generator = QueryGenerator(mode='direct', provider='ollama')
    question = "How many serial killers per decade?"

    sparql = generator.generate_sparql(question)
    result = execute_sparql(sparql)

    assert result['success']
    # Should have results for multiple decades
    lines = result['stdout'].strip().split('\n')
    assert len(lines) >= 5, "Expected multiple decade aggregations"
```

---

### 4. Comparison Tests (Direct vs Plan Mode)

**File:** `tests/integration/test_mode_comparison.py`

```python
def test_same_question_both_modes():
    """Compare results from direct vs plan mode."""
    from demo.query_generator import QueryGenerator

    question = "Top 10 serial killers by victim count"

    # Direct mode
    direct_gen = QueryGenerator(mode='direct', provider='ollama')
    sparql_direct = direct_gen.generate_sparql(question)
    result_direct = execute_sparql(sparql_direct)

    # Plan mode
    plan_gen = QueryGenerator(mode='plan', provider='ollama')
    plan = plan_gen.generate_query(question)
    sparql_plan = compile_plan_to_sparql(plan)  # Use existing compiler
    result_plan = execute_sparql(sparql_plan)

    # Compare results (should be similar, not necessarily identical)
    assert result_direct['success']
    assert result_plan['success']

    # Parse and compare result counts
    count_direct = len(result_direct['stdout'].strip().split('\n'))
    count_plan = len(result_plan['stdout'].strip().split('\n'))

    # Both should return ~10 results
    assert 8 <= count_direct <= 12
    assert 8 <= count_plan <= 12
```

---

### 5. Ground Truth Validation

**File:** `demo/serial_killers/ground_truth/questions.json`

```json
[
  {
    "question": "Top 10 serial killers by victim count",
    "expected_top_result": "Luis Garavito",
    "min_results": 10,
    "max_results": 10
  },
  {
    "question": "Serial killers with more than 50 victims",
    "min_results": 20,
    "max_results": 50
  },
  {
    "question": "Serial killers who operated in multiple countries",
    "min_results": 10,
    "max_results": 30
  }
]
```

**Validation Script:** `demo/serial_killers/validate_direct_mode.py`

```python
import json
from query_generator import QueryGenerator
from execute_sparql import execute_sparql


def validate_ground_truth():
    """Validate generated queries against ground truth."""
    with open('ground_truth/questions.json') as f:
        test_cases = json.load(f)

    generator = QueryGenerator(mode='direct', provider='ollama')
    results = []

    for case in test_cases:
        question = case['question']
        print(f"\n{'='*80}")
        print(f"Question: {question}")

        # Generate and execute
        sparql = generator.generate_sparql(question)
        result = execute_sparql(sparql)

        if not result['success']:
            print(f"✗ Execution failed: {result['stderr']}")
            results.append({'question': question, 'status': 'failed'})
            continue

        # Parse results
        lines = result['stdout'].strip().split('\n')
        result_count = len(lines)

        # Check against expected
        min_expected = case.get('min_results', 0)
        max_expected = case.get('max_results', float('inf'))

        if min_expected <= result_count <= max_expected:
            print(f"✓ Passed ({result_count} results)")
            results.append({'question': question, 'status': 'passed'})
        else:
            print(f"✗ Failed: Expected {min_expected}-{max_expected}, got {result_count}")
            results.append({'question': question, 'status': 'failed'})

        # Check top result if specified
        if 'expected_top_result' in case and result_count > 0:
            top_result = lines[0]
            if case['expected_top_result'] in top_result:
                print(f"✓ Top result matches: {case['expected_top_result']}")
            else:
                print(f"⚠ Top result mismatch: expected '{case['expected_top_result']}'")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    passed = sum(1 for r in results if r['status'] == 'passed')
    total = len(results)
    print(f"Passed: {passed}/{total} ({100*passed//total}%)")

    return passed == total


if __name__ == '__main__':
    success = validate_ground_truth()
    exit(0 if success else 1)
```

---

## Manual Testing Checklist

**Prerequisites:**
- [ ] Ollama is running (`ollama serve`)
- [ ] slm-run is installed and working
- [ ] Serial killers dataset exists

**Test Flow:**
1. [ ] Run `python demo/query_generator.py`
2. [ ] Select option 2 (Direct SPARQL generation)
3. [ ] Enter test questions (5 questions from test suite)
4. [ ] Verify SPARQL is displayed without markdown fences
5. [ ] Execute query (answer Y to execution prompt)
6. [ ] Verify results are displayed
7. [ ] Check results match expectations (roughly)

---

## Automated Testing

**Run all tests:**
```bash
# Unit tests
pytest tests/unit/test_query_generator_direct.py -v

# Integration tests (requires ollama running)
pytest tests/integration/test_direct_sparql_e2e.py -v -m integration

# Ground truth validation
python demo/serial_killers/validate_direct_mode.py
```

---

## Performance Benchmarks

**Metrics to collect:**
1. Prompt construction time (<10ms)
2. LLM response time (~2-5s for Ollama)
3. Validation time (<20ms)
4. Execution time (varies by query complexity)
5. Total end-to-end time (<10s target)

**Benchmark Script:**
```python
import time
from query_generator import QueryGenerator

def benchmark():
    generator = QueryGenerator(mode='direct', provider='ollama')
    questions = [
        "Top 10 serial killers",
        "Killers with more than 50 victims",
        "Multi-country killers",
        "Killers per decade",
        "American killers from 1980s"
    ]

    times = []
    for question in questions:
        start = time.time()
        sparql = generator.generate_sparql(question)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"{question}: {elapsed:.2f}s")

    avg = sum(times) / len(times)
    print(f"\nAverage: {avg:.2f}s")

benchmark()
```

---

## Success Criteria

- ✅ 5/5 prompt-only tests generate valid SPARQL
- ✅ All unit tests pass
- ✅ 4/5 E2E tests produce correct results
- ✅ Ground truth validation: ≥80% passed
- ✅ Direct mode results comparable to plan mode
- ✅ Average query time <10s
- ✅ Validation catches intentional errors

---

## Troubleshooting

**Issue:** LLM generates SPARQL with markdown fences
**Fix:** Check `_clean_sparql_response()` method

**Issue:** Validation fails with "Unknown GGF"
**Fix:** Add GGF to KNOWN_GGFS list in validator

**Issue:** Query executes but returns no results
**Fix:** Check CSV path in BIND clause (must be absolute or relative to cwd)

**Issue:** Variable binding errors
**Fix:** Review prompt examples, ensure GRAPH clause is clear

---

## Files Created/Modified

**Created:**
- `tests/unit/test_query_generator_direct.py` (~150 lines)
- `tests/integration/test_direct_sparql_e2e.py` (~100 lines)
- `tests/integration/test_mode_comparison.py` (~50 lines)
- `demo/serial_killers/ground_truth/questions.json` (~30 lines)
- `demo/serial_killers/validate_direct_mode.py` (~80 lines)

**Modified:**
- `demo/query_generator.py` (add CLI for mode selection)
- `demo/serial_killers/demo_nl_to_sparql.py` (support direct mode)

**Total:** ~400 new lines

---

## Next Steps

1. Run tests and document results
2. Create implementation report summarizing findings
3. Update README with direct mode usage
4. Plan Phase 5 (optional): Multi-hop queries, error recovery
