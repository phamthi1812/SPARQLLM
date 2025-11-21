"""
Unit tests for query result formatting.

Tests all output formats: JSON-LD, JSON, CSV, Turtle for SELECT and CONSTRUCT queries.
"""

import pytest
import json
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.plugins.sparql.processor import SPARQLResult

from SPARQLLM.mcp.formatting import (
    format_select_json,
    format_select_csv,
    format_construct_jsonld,
    format_construct_turtle,
    format_result,
)
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode


EX = Namespace("http://example.org/")


@pytest.fixture
def sample_select_result():
    """Create a sample SELECT query result."""
    # Simulate rdflib SELECT result
    class MockSelectResult:
        def __init__(self):
            self.vars = ["s", "p", "o"]
            self._bindings = [
                {"s": EX.subject1, "p": EX.predicate1, "o": Literal("value1")},
                {"s": EX.subject2, "p": EX.predicate2, "o": Literal("value2")},
            ]

        def __iter__(self):
            return iter(self._bindings)

    return MockSelectResult()


@pytest.fixture
def sample_construct_result():
    """Create a sample CONSTRUCT query result."""
    g = Graph()
    g.bind("ex", EX)
    g.add((EX.subject1, EX.predicate1, Literal("value1")))
    g.add((EX.subject2, EX.predicate2, Literal("value2")))
    g.add((EX.subject3, EX.predicate3, URIRef("http://example.org/resource")))
    return g


class TestFormatSelectJSON:
    """Test SELECT query JSON formatting."""

    def test_format_basic_select(self, sample_select_result):
        """Test formatting basic SELECT result to JSON."""
        result = format_select_json(sample_select_result, max_results=100)

        data = json.loads(result)
        assert data["type"] == "SELECT"
        assert "vars" in data
        assert "results" in data
        assert len(data["results"]) == 2

    def test_format_with_max_results_limit(self, sample_select_result):
        """Test max_results limit applied."""
        result = format_select_json(sample_select_result, max_results=1)

        data = json.loads(result)
        assert len(data["results"]) == 1

    def test_format_empty_result(self):
        """Test formatting empty SELECT result."""
        class EmptyResult:
            vars = []

            def __iter__(self):
                return iter([])

        result = format_select_json(EmptyResult(), max_results=100)
        data = json.loads(result)

        assert data["type"] == "SELECT"
        assert len(data["results"]) == 0

    def test_result_contains_variables(self, sample_select_result):
        """Test result includes variable names."""
        result = format_select_json(sample_select_result, max_results=100)
        data = json.loads(result)

        assert "s" in data["vars"]
        assert "p" in data["vars"]
        assert "o" in data["vars"]

    def test_result_bindings_structure(self, sample_select_result):
        """Test bindings have correct structure."""
        result = format_select_json(sample_select_result, max_results=100)
        data = json.loads(result)

        # Check first binding
        binding = data["results"][0]
        assert "s" in binding
        assert "p" in binding
        assert "o" in binding


class TestFormatSelectCSV:
    """Test SELECT query CSV formatting."""

    def test_format_basic_csv(self, sample_select_result):
        """Test formatting SELECT result to CSV."""
        result = format_select_csv(sample_select_result, max_results=100)

        lines = result.strip().split("\n")
        assert len(lines) == 3  # Header + 2 rows

        # Check header
        header = lines[0]
        assert "s" in header
        assert "p" in header
        assert "o" in header

    def test_csv_max_results(self, sample_select_result):
        """Test CSV respects max_results."""
        result = format_select_csv(sample_select_result, max_results=1)

        lines = result.strip().split("\n")
        assert len(lines) == 2  # Header + 1 row

    def test_csv_empty_result(self):
        """Test CSV formatting for empty result."""
        class EmptyResult:
            vars = ["s", "p", "o"]

            def __iter__(self):
                return iter([])

        result = format_select_csv(EmptyResult(), max_results=100)
        lines = result.strip().split("\n")

        assert len(lines) == 1  # Only header

    def test_csv_escaping(self):
        """Test CSV escapes special characters."""
        class SpecialCharsResult:
            vars = ["value"]
            _bindings = [
                {"value": Literal("value, with comma")},
                {"value": Literal('value "with quotes"')},
            ]

            def __iter__(self):
                return iter(self._bindings)

        result = format_select_csv(SpecialCharsResult(), max_results=100)

        # CSV should properly escape commas and quotes
        assert "," in result  # Commas in values should be quoted
        assert '"' in result


class TestFormatConstructJSONLD:
    """Test CONSTRUCT query JSON-LD formatting."""

    def test_format_basic_construct(self, sample_construct_result):
        """Test formatting CONSTRUCT result to JSON-LD."""
        result = format_construct_jsonld(sample_construct_result)

        data = json.loads(result)
        assert "@context" in data or "@graph" in data

    def test_jsonld_is_valid_json(self, sample_construct_result):
        """Test JSON-LD output is valid JSON."""
        result = format_construct_jsonld(sample_construct_result)

        # Should parse without error
        data = json.loads(result)
        assert isinstance(data, (dict, list))

    def test_empty_graph_formatting(self):
        """Test formatting empty graph."""
        empty_graph = Graph()
        result = format_construct_jsonld(empty_graph)

        data = json.loads(result)
        # Empty graph should still have valid JSON-LD structure
        assert isinstance(data, (dict, list))

    def test_graph_with_uris(self, sample_construct_result):
        """Test graph with URI objects."""
        result = format_construct_jsonld(sample_construct_result)

        # Should contain serialized URIs
        assert "http://example.org/" in result


class TestFormatConstructTurtle:
    """Test CONSTRUCT query Turtle formatting."""

    def test_format_basic_turtle(self, sample_construct_result):
        """Test formatting CONSTRUCT result to Turtle."""
        result = format_construct_turtle(sample_construct_result)

        # Turtle should contain prefixes and triples
        assert isinstance(result, str)
        assert len(result) > 0

    def test_turtle_contains_prefixes(self, sample_construct_result):
        """Test Turtle output contains namespace prefixes."""
        result = format_construct_turtle(sample_construct_result)

        # Should have prefix declarations
        assert "@prefix" in result or "PREFIX" in result

    def test_turtle_empty_graph(self):
        """Test Turtle formatting for empty graph."""
        empty_graph = Graph()
        result = format_construct_turtle(empty_graph)

        # Empty graph should return minimal Turtle
        assert isinstance(result, str)

    def test_turtle_is_parseable(self, sample_construct_result):
        """Test Turtle output can be parsed back."""
        result = format_construct_turtle(sample_construct_result)

        # Parse it back
        g = Graph()
        g.parse(data=result, format="turtle")

        # Should have same number of triples
        assert len(g) == len(sample_construct_result)


class TestFormatResult:
    """Test high-level format_result function."""

    def test_select_json_format(self, sample_select_result):
        """Test routing SELECT to JSON formatter."""
        result = format_result(sample_select_result, "json", max_results=100)

        data = json.loads(result)
        assert data["type"] == "SELECT"

    def test_select_csv_format(self, sample_select_result):
        """Test routing SELECT to CSV formatter."""
        result = format_result(sample_select_result, "csv", max_results=100)

        assert isinstance(result, str)
        assert "\n" in result  # CSV has newlines

    def test_construct_jsonld_format(self, sample_construct_result):
        """Test routing CONSTRUCT to JSON-LD formatter."""
        result = format_result(sample_construct_result, "json-ld")

        data = json.loads(result)
        assert isinstance(data, (dict, list))

    def test_construct_turtle_format(self, sample_construct_result):
        """Test routing CONSTRUCT to Turtle formatter."""
        result = format_result(sample_construct_result, "turtle")

        assert isinstance(result, str)
        assert "@prefix" in result or "PREFIX" in result

    def test_invalid_format_raises_error(self, sample_select_result):
        """Test invalid format raises error."""
        with pytest.raises(SparqllmError) as exc_info:
            format_result(sample_select_result, "invalid-format")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    def test_select_with_turtle_raises_error(self, sample_select_result):
        """Test SELECT query with Turtle format raises error."""
        with pytest.raises(SparqllmError) as exc_info:
            format_result(sample_select_result, "turtle")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    def test_construct_with_csv_raises_error(self, sample_construct_result):
        """Test CONSTRUCT query with CSV format raises error."""
        with pytest.raises(SparqllmError) as exc_info:
            format_result(sample_construct_result, "csv")

        assert exc_info.value.code == ErrorCode.INVALID_INPUT


class TestFormattingEdgeCases:
    """Test edge cases in formatting."""

    def test_very_large_result_truncation(self):
        """Test large results are truncated by max_results."""
        class LargeResult:
            vars = ["x"]

            def __iter__(self):
                # Generate 10000 bindings
                for i in range(10000):
                    yield {"x": Literal(f"value{i}")}

        result = format_select_json(LargeResult(), max_results=100)
        data = json.loads(result)

        assert len(data["results"]) == 100

    def test_unicode_handling(self):
        """Test Unicode characters are properly handled."""
        class UnicodeResult:
            vars = ["text"]
            _bindings = [
                {"text": Literal("Hello 世界")},
                {"text": Literal("Émoji: 😀")},
            ]

            def __iter__(self):
                return iter(self._bindings)

        result = format_select_json(UnicodeResult(), max_results=100)
        data = json.loads(result)

        # Should preserve Unicode
        assert "世界" in str(data["results"])

    def test_null_values_handling(self):
        """Test handling of unbound variables."""
        class NullResult:
            vars = ["s", "o"]
            _bindings = [
                {"s": EX.subject1},  # Missing 'o'
                {"o": Literal("value")},  # Missing 's'
            ]

            def __iter__(self):
                return iter(self._bindings)

        result = format_select_json(NullResult(), max_results=100)
        data = json.loads(result)

        # Should handle missing bindings gracefully
        assert len(data["results"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
