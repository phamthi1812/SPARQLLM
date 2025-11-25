# Phase 3: Validation Layer

**Status:** Ready
**Estimated Effort:** 1.5-2 hours
**Dependencies:** Phase 2 (generate_sparql must work)

---

## Objective

Create `SPARQLLM/compiler/sparql_validator.py` to validate LLM-generated SPARQL before execution.

---

## Validation Levels

### 1. Syntax Validation (Critical)
- Parse SPARQL with rdflib.plugins.sparql.prepareQuery
- Catch: missing keywords, malformed clauses, invalid operators

### 2. Semantic Validation (Important)
- Check GGF function names exist in catalog
- Verify PREFIX declarations (ggf, ex)
- Validate argument patterns

### 3. Variable Binding Validation (Nice-to-have)
- Detect unbound variables in FILTER
- Check variable consistency (?name vs ?Name)

---

## Implementation

### File Structure

```python
# SPARQLLM/compiler/sparql_validator.py

import re
from typing import Tuple, List
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import ParseException


class SPARQLValidator:
    """Validates LLM-generated SPARQL queries."""

    # Known GGF functions (can be expanded or loaded from catalog)
    KNOWN_GGFS = [
        'SLM-CSV', 'SLM-READFILE', 'SLM-LISTDIR',
        'SLM-LLM', 'LLMGRAPH_OLLAMA', 'LLMGRAPH_OPENAI',
        'SLM-SPARQL', 'SLM-SEARCH',
        'SLM-FAISS', 'SLM-WHOOSH',
        'SLM-GRAPH'
    ]

    def __init__(self, strict: bool = True):
        """
        Args:
            strict: If True, fail on semantic issues. If False, warn only.
        """
        self.strict = strict


    def validate(self, sparql: str) -> Tuple[bool, List[str]]:
        """
        Validate SPARQL query.

        Args:
            sparql: SPARQL query string

        Returns:
            (is_valid, error_messages)
            - is_valid: True if query is valid, False otherwise
            - error_messages: List of error/warning messages
        """
        errors = []

        # 1. Syntax validation
        syntax_ok, syntax_error = self._validate_syntax(sparql)
        if not syntax_ok:
            errors.append(f"Syntax error: {syntax_error}")
            return False, errors

        # 2. PREFIX validation
        prefix_ok, prefix_error = self._validate_prefixes(sparql)
        if not prefix_ok:
            errors.append(f"PREFIX error: {prefix_error}")
            if self.strict:
                return False, errors

        # 3. GGF validation
        ggf_ok, ggf_errors = self._validate_ggfs(sparql)
        if not ggf_ok:
            errors.extend(ggf_errors)
            if self.strict:
                return False, errors

        # 4. Variable binding validation (heuristic)
        var_ok, var_warnings = self._validate_variables(sparql)
        if not var_ok:
            errors.extend(var_warnings)
            # Don't fail for variable warnings (too many false positives)

        # If we reached here and no critical errors, it's valid
        is_valid = len(errors) == 0 or not self.strict
        return is_valid, errors


    def _validate_syntax(self, sparql: str) -> Tuple[bool, str]:
        """Validate SPARQL syntax using rdflib parser."""
        try:
            prepareQuery(sparql)
            return True, ""
        except ParseException as e:
            return False, str(e)
        except Exception as e:
            return False, f"Parse error: {e}"


    def _validate_prefixes(self, sparql: str) -> Tuple[bool, str]:
        """Check required PREFIX declarations."""
        required_prefixes = ['ggf:', 'ex:']
        missing = []

        for prefix in required_prefixes:
            if f"PREFIX {prefix}" not in sparql.upper():
                missing.append(prefix)

        if missing:
            return False, f"Missing PREFIX declarations: {', '.join(missing)}"

        return True, ""


    def _validate_ggfs(self, sparql: str) -> Tuple[bool, List[str]]:
        """Validate GGF function names."""
        errors = []

        # Extract GGF calls: ggf:FUNCTION_NAME(
        ggf_pattern = r'ggf:([A-Z][A-Z0-9_-]*)\s*\('
        matches = re.findall(ggf_pattern, sparql, re.IGNORECASE)

        for ggf_name in matches:
            # Normalize to uppercase
            ggf_upper = ggf_name.upper()

            if ggf_upper not in self.KNOWN_GGFS:
                errors.append(f"Unknown GGF: {ggf_name} (not in catalog)")

        # Check for BIND pattern
        if 'ggf:' in sparql and 'BIND(' not in sparql.upper():
            errors.append("GGF call found but no BIND clause (missing BIND(ggf:... AS ?var))")

        # Check for GRAPH pattern
        if 'BIND(' in sparql.upper() and 'GRAPH' not in sparql.upper():
            errors.append("BIND clause found but no GRAPH clause (missing GRAPH ?var { ... })")

        is_valid = len(errors) == 0
        return is_valid, errors


    def _validate_variables(self, sparql: str) -> Tuple[bool, List[str]]:
        """Heuristic validation of variable bindings."""
        warnings = []

        # Extract FILTER variables
        filter_pattern = r'FILTER\s*\([^)]*\?(\w+)'
        filter_vars = re.findall(filter_pattern, sparql, re.IGNORECASE)

        # Extract bound variables (in triple patterns)
        # Simplified: look for ?var in triple-like contexts
        bound_pattern = r'\?\w+\s+\w+:\w+\s+\?(\w+)'
        bound_vars = re.findall(bound_pattern, sparql)

        # Check if FILTER variables are bound
        for var in filter_vars:
            if var not in bound_vars and var not in sparql[:sparql.find('FILTER')]:
                warnings.append(f"Variable ?{var} used in FILTER may not be bound")

        # Case sensitivity check (SPARQL is case-sensitive for variables)
        all_vars = re.findall(r'\?(\w+)', sparql)
        var_lower = {v.lower(): v for v in all_vars}

        if len(var_lower) < len(set(all_vars)):
            warnings.append("Possible case inconsistency in variable names")

        is_valid = len(warnings) == 0
        return is_valid, warnings


    def get_query_info(self, sparql: str) -> dict:
        """Extract metadata from query (for debugging)."""
        info = {
            'has_ggf': 'ggf:' in sparql,
            'has_bind': 'BIND(' in sparql.upper(),
            'has_graph': 'GRAPH' in sparql.upper(),
            'has_filter': 'FILTER' in sparql.upper(),
            'has_order': 'ORDER BY' in sparql.upper(),
            'has_limit': 'LIMIT' in sparql.upper(),
            'has_group': 'GROUP BY' in sparql.upper(),
        }

        # Extract GGFs
        ggf_pattern = r'ggf:([A-Z][A-Z0-9_-]*)'
        info['ggfs_used'] = list(set(re.findall(ggf_pattern, sparql, re.IGNORECASE)))

        # Extract variables
        info['variables'] = list(set(re.findall(r'\?(\w+)', sparql)))

        return info
```

---

## Usage Example

```python
from SPARQLLM.compiler.sparql_validator import SPARQLValidator

validator = SPARQLValidator(strict=True)

sparql = """
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?victims
WHERE {
    BIND(ggf:SLM-CSV("data.csv") AS ?g)

    GRAPH ?g {
        ?row ex:name ?name .
        ?row ex:victims ?victims .
    }

    FILTER(?victims > 50)
}
LIMIT 10
"""

is_valid, errors = validator.validate(sparql)

if is_valid:
    print("✓ Query is valid")
else:
    print("✗ Query validation failed:")
    for error in errors:
        print(f"  - {error}")

# Get query metadata
info = validator.get_query_info(sparql)
print(f"\nQuery info: {info}")
```

---

## Integration with QueryGenerator

**Modify `demo/query_generator.py`:**

```python
from SPARQLLM.compiler.sparql_validator import SPARQLValidator

class QueryGenerator:
    def __init__(self, mode='plan', provider='ollama'):
        # ... existing init ...

        # Initialize validator for direct mode
        if mode == 'direct':
            self.validator = SPARQLValidator(strict=True)


    def generate_sparql(self, question: str, context: dict = None) -> str:
        """Generate and validate SPARQL."""
        # ... existing generation logic ...
        sparql = self._clean_sparql_response(response)

        # Validate
        is_valid, errors = self.validator.validate(sparql)

        if not is_valid:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise ValueError(f"Generated invalid SPARQL:\n{error_msg}\n\nQuery:\n{sparql}")

        print("[Validation] ✓ SPARQL is valid")
        return sparql
```

---

## Testing

### Unit Tests

**File:** `tests/unit/test_sparql_validator.py`

```python
import pytest
from SPARQLLM.compiler.sparql_validator import SPARQLValidator


def test_valid_query():
    """Test validation of valid query."""
    validator = SPARQLValidator()

    sparql = """
    PREFIX ggf: <http://ggf.org/>
    PREFIX ex: <http://example.org/>

    SELECT ?name WHERE {
        BIND(ggf:SLM-CSV("data.csv") AS ?g)
        GRAPH ?g { ?row ex:name ?name . }
    }
    """

    is_valid, errors = validator.validate(sparql)
    assert is_valid
    assert len(errors) == 0


def test_syntax_error():
    """Test detection of syntax errors."""
    validator = SPARQLValidator()

    sparql = "SELECT ?name WHERE { INVALID SYNTAX }"

    is_valid, errors = validator.validate(sparql)
    assert not is_valid
    assert any("Syntax error" in e for e in errors)


def test_missing_prefix():
    """Test detection of missing PREFIX."""
    validator = SPARQLValidator()

    sparql = """
    SELECT ?name WHERE {
        BIND(ggf:SLM-CSV("data.csv") AS ?g)
        GRAPH ?g { ?row ex:name ?name . }
    }
    """

    is_valid, errors = validator.validate(sparql)
    assert not is_valid
    assert any("PREFIX" in e for e in errors)


def test_unknown_ggf():
    """Test detection of unknown GGF."""
    validator = SPARQLValidator()

    sparql = """
    PREFIX ggf: <http://ggf.org/>
    PREFIX ex: <http://example.org/>

    SELECT ?name WHERE {
        BIND(ggf:UNKNOWN_FUNCTION("data.csv") AS ?g)
        GRAPH ?g { ?row ex:name ?name . }
    }
    """

    is_valid, errors = validator.validate(sparql)
    assert not is_valid
    assert any("Unknown GGF" in e for e in errors)


def test_missing_graph():
    """Test detection of missing GRAPH clause."""
    validator = SPARQLValidator()

    sparql = """
    PREFIX ggf: <http://ggf.org/>
    PREFIX ex: <http://example.org/>

    SELECT ?name WHERE {
        BIND(ggf:SLM-CSV("data.csv") AS ?g)
        ?row ex:name ?name .
    }
    """

    is_valid, errors = validator.validate(sparql)
    assert not is_valid
    assert any("GRAPH" in e for e in errors)


def test_query_info():
    """Test query metadata extraction."""
    validator = SPARQLValidator()

    sparql = """
    PREFIX ggf: <http://ggf.org/>
    SELECT ?name WHERE {
        BIND(ggf:SLM-CSV("data.csv") AS ?g)
        GRAPH ?g { ?row ex:name ?name . }
        FILTER(?name != "")
    }
    ORDER BY ?name
    LIMIT 10
    """

    info = validator.get_query_info(sparql)

    assert info['has_ggf'] == True
    assert info['has_filter'] == True
    assert info['has_order'] == True
    assert info['has_limit'] == True
    assert 'SLM-CSV' in info['ggfs_used']
    assert 'name' in info['variables']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

## Error Messages

**Design for actionable feedback:**

```python
# Bad
"Invalid query"

# Good
"Syntax error at line 5: Expected 'WHERE' but found 'WERE'"
"Missing PREFIX declaration: ggf:"
"Unknown GGF: SLM-CSVV (did you mean SLM-CSV?)"
"Variable ?victims used in FILTER but not bound in GRAPH clause"
```

---

## Performance

**Optimization:**
- Cache prepareQuery results (parsing is expensive)
- Use compiled regex patterns (re.compile)
- Skip variable validation if syntax check fails (fail fast)

**Benchmarks:**
- Syntax validation: <10ms per query
- Semantic validation: <5ms per query
- Total overhead: <20ms (acceptable for interactive use)

---

## Success Criteria

- ✅ Validator catches syntax errors (rdflib parser)
- ✅ Validator catches missing PREFIX declarations
- ✅ Validator catches unknown GGF names
- ✅ Validator catches missing BIND/GRAPH patterns
- ✅ Unit tests cover all validation levels
- ✅ Error messages are actionable
- ✅ Integration with QueryGenerator works

---

## Files Created

- `SPARQLLM/compiler/sparql_validator.py` (~200 lines)
- `tests/unit/test_sparql_validator.py` (~150 lines)

---

## Next Steps

Proceed to Phase 4 (Testing & Integration) after unit tests pass.
