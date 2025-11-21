"""
Unit tests for SPARQL query validation.

Tests validation layer: syntax validation, function whitelist, GGF extraction.
"""

import pytest
from SPARQLLM.mcp.validation import (
    validate_sparql_syntax,
    validate_function_whitelist,
    extract_ggf_functions,
    validate_query,
)
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode
from SPARQLLM.config import ConfigSingleton


@pytest.fixture(scope="module")
def config():
    """Initialize config singleton."""
    return ConfigSingleton(config_file="config.ini")


class TestExtractGGFFunctions:
    """Test GGF function extraction from SPARQL queries."""

    def test_extract_single_function(self):
        """Test extracting single GGF function."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-CSV(?file) AS ?g)
        }
        """
        functions = extract_ggf_functions(query)
        assert functions == {"SLM-CSV"}

    def test_extract_multiple_functions(self):
        """Test extracting multiple GGF functions."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-CSV(?file) AS ?g)
            BIND(ggf:SLM-LLM(?prompt) AS ?g2)
            BIND(ggf:SLM-READFILE(?path) AS ?g3)
        }
        """
        functions = extract_ggf_functions(query)
        assert functions == {"SLM-CSV", "SLM-LLM", "SLM-READFILE"}

    def test_extract_no_functions(self):
        """Test query without GGF functions."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        functions = extract_ggf_functions(query)
        assert functions == set()

    def test_extract_case_insensitive(self):
        """Test case-insensitive extraction."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:slm-csv(?file) AS ?g)
            BIND(GGF:SLM-LLM(?prompt) AS ?g2)
        }
        """
        functions = extract_ggf_functions(query)
        assert "SLM-CSV" in functions or "slm-csv" in functions
        assert "SLM-LLM" in functions or "slm-llm" in functions

    def test_extract_hyphenated_functions(self):
        """Test functions with hyphens and underscores."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-SEARCH-FAISS(?q) AS ?g)
            BIND(ggf:SLM_GRAPH(?data) AS ?g2)
        }
        """
        functions = extract_ggf_functions(query)
        assert len(functions) >= 1  # At least hyphenated ones


class TestValidateSPARQLSyntax:
    """Test SPARQL syntax validation."""

    def test_valid_select_query(self):
        """Test valid SELECT query passes."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        validate_sparql_syntax(query)  # Should not raise

    def test_valid_construct_query(self):
        """Test valid CONSTRUCT query passes."""
        query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
        validate_sparql_syntax(query)  # Should not raise

    def test_valid_ask_query(self):
        """Test valid ASK query passes."""
        query = "ASK { ?s ?p ?o }"
        validate_sparql_syntax(query)  # Should not raise

    def test_valid_describe_query(self):
        """Test valid DESCRIBE query passes."""
        query = "DESCRIBE <http://example.org/resource>"
        validate_sparql_syntax(query)  # Should not raise

    def test_invalid_syntax_raises_error(self):
        """Test invalid SPARQL syntax raises error."""
        query = "INVALID SPARQL QUERY"
        with pytest.raises(SparqllmError) as exc_info:
            validate_sparql_syntax(query)
        assert exc_info.value.code == ErrorCode.SPARQL_SYNTAX_ERROR

    def test_empty_query_raises_error(self):
        """Test empty query raises error."""
        query = ""
        with pytest.raises(SparqllmError) as exc_info:
            validate_sparql_syntax(query)
        assert exc_info.value.code == ErrorCode.SPARQL_SYNTAX_ERROR

    def test_incomplete_query_raises_error(self):
        """Test incomplete query raises error."""
        query = "SELECT ?s WHERE {"
        with pytest.raises(SparqllmError) as exc_info:
            validate_sparql_syntax(query)
        assert exc_info.value.code == ErrorCode.SPARQL_SYNTAX_ERROR


class TestValidateFunctionWhitelist:
    """Test function whitelist validation."""

    def test_registered_function_passes(self, config):
        """Test registered GGF function passes."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-CSV(?file) AS ?g)
        }
        """
        validate_function_whitelist(query, config)  # Should not raise

    def test_multiple_registered_functions_pass(self, config):
        """Test multiple registered functions pass."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-CSV(?file) AS ?g)
            BIND(ggf:SLM-FILE(?path) AS ?g2)
        }
        """
        validate_function_whitelist(query, config)  # Should not raise

    def test_unknown_function_raises_error(self, config):
        """Test unknown GGF function raises error."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:UNKNOWN-FUNCTION(?x) AS ?g)
        }
        """
        with pytest.raises(SparqllmError) as exc_info:
            validate_function_whitelist(query, config)
        assert exc_info.value.code == ErrorCode.INVALID_FUNCTION
        assert "unknown" in exc_info.value.details
        assert "UNKNOWN-FUNCTION" in str(exc_info.value.details["unknown"])

    def test_mixed_registered_and_unknown(self, config):
        """Test mix of registered and unknown functions raises error."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-CSV(?file) AS ?g)
            BIND(ggf:TOTALLY-FAKE-FUNC(?x) AS ?g2)
        }
        """
        with pytest.raises(SparqllmError) as exc_info:
            validate_function_whitelist(query, config)
        assert exc_info.value.code == ErrorCode.INVALID_FUNCTION

    def test_no_functions_passes(self, config):
        """Test query without GGF functions passes whitelist."""
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        validate_function_whitelist(query, config)  # Should not raise


class TestValidateQuery:
    """Test combined query validation."""

    def test_valid_query_with_registered_functions(self, config):
        """Test fully valid query passes all validation."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:SLM-FILE("./data/file.csv") AS ?file)
            BIND(ggf:SLM-CSV(?file) AS ?g)
            GRAPH ?g { ?row ?prop ?val }
        }
        """
        validate_query(query, config)  # Should not raise

    def test_syntax_error_raised_first(self, config):
        """Test syntax errors raised before whitelist check."""
        query = """
        PREFIX ggf: <http://example.org/>
        INVALID SYNTAX ggf:SLM-CSV(?file)
        """
        with pytest.raises(SparqllmError) as exc_info:
            validate_query(query, config)
        assert exc_info.value.code == ErrorCode.SPARQL_SYNTAX_ERROR

    def test_whitelist_error_after_syntax(self, config):
        """Test whitelist errors raised for valid syntax."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:FAKE-FUNCTION(?x) AS ?g)
        }
        """
        with pytest.raises(SparqllmError) as exc_info:
            validate_query(query, config)
        assert exc_info.value.code == ErrorCode.INVALID_FUNCTION


class TestValidationErrorMessages:
    """Test error messages provide useful guidance."""

    def test_syntax_error_includes_details(self):
        """Test syntax error includes query details."""
        query = "INVALID QUERY"
        with pytest.raises(SparqllmError) as exc_info:
            validate_sparql_syntax(query)

        error = exc_info.value
        assert "syntax" in error.message.lower()
        assert "details" in error.details

    def test_whitelist_error_lists_unknown_functions(self, config):
        """Test whitelist error lists all unknown functions."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:FAKE1(?x) AS ?g)
            BIND(ggf:FAKE2(?y) AS ?g2)
        }
        """
        with pytest.raises(SparqllmError) as exc_info:
            validate_function_whitelist(query, config)

        error = exc_info.value
        assert "unknown" in error.details
        unknown_funcs = error.details["unknown"]
        # At least one fake function should be listed
        assert len(unknown_funcs) > 0

    def test_whitelist_error_suggests_registered_functions(self, config):
        """Test whitelist error suggests available functions."""
        query = """
        PREFIX ggf: <http://example.org/>
        SELECT ?s WHERE {
            BIND(ggf:UNKNOWN-FUNC(?x) AS ?g)
        }
        """
        with pytest.raises(SparqllmError) as exc_info:
            validate_function_whitelist(query, config)

        error = exc_info.value
        assert "registered" in error.details or "available" in error.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
