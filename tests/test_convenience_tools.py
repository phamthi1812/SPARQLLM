"""
Unit tests for convenience tools (Phase 3).

Tests for extract_structured_data and web_to_knowledge wrapper tools.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from mcp.types import TextContent

from SPARQLLM.mcp.tools.extract_structured_data import extract_structured_data_tool
from SPARQLLM.mcp.tools.web_to_knowledge import web_to_knowledge_tool
from SPARQLLM.mcp.errors import SparqllmError, ErrorCode


class TestExtractStructuredDataTool:
    """Test extract_structured_data convenience tool."""

    @pytest.mark.asyncio
    async def test_missing_file_path_returns_error(self):
        """Test that missing file_path parameter returns error."""
        result = await extract_structured_data_tool({})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        error_data = json.loads(result[0].text)
        assert "error" in error_data
        assert error_data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_file_path_parameter_passed(self):
        """Test that file_path is properly passed to SPARQL tool."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await extract_structured_data_tool({
                "file_path": "./test.csv"
            })

            # Verify sparql_query_tool was called
            assert mock_sparql.called
            call_args = mock_sparql.call_args[0][0]
            assert "query" in call_args

    @pytest.mark.asyncio
    async def test_csv_format_uses_csv_template(self):
        """Test CSV files use CSV-specific template."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await extract_structured_data_tool({
                "file_path": "./data/test.csv"
            })

            call_args = mock_sparql.call_args[0][0]
            query = call_args["query"]

            # CSV template should contain SLM-CSV function
            assert "SLM-CSV" in query

    @pytest.mark.asyncio
    async def test_non_csv_uses_generic_template(self):
        """Test non-CSV files use generic extraction template."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await extract_structured_data_tool({
                "file_path": "./data/test.html"
            })

            call_args = mock_sparql.call_args[0][0]
            query = call_args["query"]

            # Should not contain CSV-specific logic
            assert "SLM-CSV" not in query

    @pytest.mark.asyncio
    async def test_limit_parameter_passed(self):
        """Test limit parameter is passed to query."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await extract_structured_data_tool({
                "file_path": "./test.csv",
                "limit": 50
            })

            call_args = mock_sparql.call_args[0][0]
            assert call_args.get("max_results") == 50

    @pytest.mark.asyncio
    async def test_timeout_parameter_passed(self):
        """Test timeout parameter is passed to query."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await extract_structured_data_tool({
                "file_path": "./test.csv",
                "timeout": 90
            })

            call_args = mock_sparql.call_args[0][0]
            assert call_args.get("timeout") == 90

    @pytest.mark.asyncio
    async def test_sparql_error_bubbles_up(self):
        """Test SPARQL errors are returned to caller."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            # Simulate SPARQL error
            error = SparqllmError(
                ErrorCode.SPARQL_TIMEOUT,
                "Query timeout",
                {"suggestion": "Increase timeout"}
            )
            mock_sparql.side_effect = error

            result = await extract_structured_data_tool({
                "file_path": "./test.csv"
            })

            error_data = json.loads(result[0].text)
            assert error_data["error"]["code"] == "SPARQL_TIMEOUT"

    @pytest.mark.asyncio
    async def test_format_hint_parameter(self):
        """Test format_hint parameter affects template selection."""
        with patch('SPARQLLM.mcp.tools.extract_structured_data.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            # Force CSV template via format_hint
            await extract_structured_data_tool({
                "file_path": "./data/test.txt",
                "format_hint": "csv"
            })

            call_args = mock_sparql.call_args[0][0]
            query = call_args["query"]
            assert "SLM-CSV" in query


class TestWebToKnowledgeTool:
    """Test web_to_knowledge convenience tool."""

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self):
        """Test that missing URL parameter returns error."""
        result = await web_to_knowledge_tool({})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        error_data = json.loads(result[0].text)
        assert "error" in error_data
        assert error_data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_url_parameter_passed(self):
        """Test that URL is properly passed to SPARQL tool."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await web_to_knowledge_tool({
                "url": "https://example.com"
            })

            assert mock_sparql.called
            call_args = mock_sparql.call_args[0][0]
            assert "query" in call_args
            assert "example.com" in call_args["query"]

    @pytest.mark.asyncio
    async def test_timeout_parameter_passed(self):
        """Test timeout parameter is passed."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await web_to_knowledge_tool({
                "url": "https://example.com",
                "timeout": 120
            })

            call_args = mock_sparql.call_args[0][0]
            assert call_args.get("timeout") == 120

    @pytest.mark.asyncio
    async def test_text_max_chars_parameter(self):
        """Test text_max_chars parameter is accepted."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            # Parameter should be accepted without error
            result = await web_to_knowledge_tool({
                "url": "https://example.com",
                "text_max_chars": 5000
            })

            assert mock_sparql.called

    @pytest.mark.asyncio
    async def test_sparql_error_with_suggestion(self):
        """Test SPARQL errors get tool-specific suggestions."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            error = SparqllmError(
                ErrorCode.SPARQL_TIMEOUT,
                "Query timeout",
                {}
            )
            mock_sparql.side_effect = error

            result = await web_to_knowledge_tool({
                "url": "https://example.com"
            })

            error_data = json.loads(result[0].text)
            assert "suggestion" in error_data["error"]["details"]

    @pytest.mark.asyncio
    async def test_invalid_function_error_suggestion(self):
        """Test invalid function errors get helpful suggestions."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            error = SparqllmError(
                ErrorCode.INVALID_FUNCTION,
                "Function not found",
                {}
            )
            mock_sparql.side_effect = error

            result = await web_to_knowledge_tool({
                "url": "https://example.com"
            })

            error_data = json.loads(result[0].text)
            assert "suggestion" in error_data["error"]["details"]
            # Should mention SLM-GETTEXT registration
            assert "SLM-GETTEXT" in error_data["error"]["details"]["suggestion"]

    @pytest.mark.asyncio
    async def test_uses_web_template(self):
        """Test that web scraping uses appropriate template."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await web_to_knowledge_tool({
                "url": "https://example.com"
            })

            call_args = mock_sparql.call_args[0][0]
            query = call_args["query"]

            # Web template should reference web-related functions
            assert "http" in query.lower() or "url" in query.lower()

    @pytest.mark.asyncio
    async def test_output_format_json(self):
        """Test that output format is JSON for easy parsing."""
        with patch('SPARQLLM.mcp.tools.web_to_knowledge.sparql_query_tool', new_callable=AsyncMock) as mock_sparql:
            mock_sparql.return_value = [TextContent(type="text", text=json.dumps({"results": []}))]

            await web_to_knowledge_tool({
                "url": "https://example.com"
            })

            call_args = mock_sparql.call_args[0][0]
            assert call_args.get("output_format") == "json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
