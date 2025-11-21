"""Basic tests for SPARQLLM MCP Server (Phase 1)

Tests cover:
- Server initialization
- Tool listing
- Echo tool functionality
"""

import pytest
import asyncio
from SPARQLLM.mcp.server import SparqllmMCPServer
from SPARQLLM.mcp.tools.echo import echo_tool


class TestMCPServerInitialization:
    """Test server initialization"""

    def test_server_creates_successfully(self):
        """Test that server instance can be created"""
        server = SparqllmMCPServer(config_file="config.ini")
        assert server is not None
        assert server.server.name == "sparqllm"
        assert server.config_file == "config.ini"
        assert server.session_id is not None
        assert server.request_count == 0

    def test_server_has_session_id(self):
        """Test that server generates a unique session ID"""
        server1 = SparqllmMCPServer(config_file="config.ini")
        server2 = SparqllmMCPServer(config_file="config.ini")

        assert server1.session_id != server2.session_id


class TestToolListing:
    """Test tools/list functionality"""

    @pytest.mark.asyncio
    async def test_list_tools_returns_schemas(self):
        """Test that tools/list returns valid tool schemas"""
        server = SparqllmMCPServer(config_file="config.ini")
        tools = await server._list_tools()

        assert len(tools) >= 1
        assert any(t.name == "echo" for t in tools)

    @pytest.mark.asyncio
    async def test_echo_tool_has_required_fields(self):
        """Test that echo tool schema has all required fields"""
        server = SparqllmMCPServer(config_file="config.ini")
        tools = await server._list_tools()

        echo = next((t for t in tools if t.name == "echo"), None)
        assert echo is not None
        assert echo.description is not None
        assert "message" in echo.inputSchema["properties"]
        assert echo.inputSchema["required"] == ["message"]


class TestEchoTool:
    """Test echo tool implementation"""

    @pytest.mark.asyncio
    async def test_echo_tool_returns_message(self):
        """Test that echo tool returns the input message"""
        result = await echo_tool({"message": "test message"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "test message" in result[0].text

    @pytest.mark.asyncio
    async def test_echo_tool_handles_empty_message(self):
        """Test that echo tool handles empty message"""
        result = await echo_tool({"message": ""})

        assert len(result) == 1
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_echo_tool_handles_missing_message(self):
        """Test that echo tool handles missing message parameter"""
        result = await echo_tool({})

        assert len(result) == 1
        assert result[0].type == "text"


class TestErrorHandling:
    """Test error handling framework"""

    def test_error_code_enum_exists(self):
        """Test that ErrorCode enum is properly defined"""
        from SPARQLLM.mcp.errors import ErrorCode

        assert hasattr(ErrorCode, 'SPARQL_SYNTAX_ERROR')
        assert hasattr(ErrorCode, 'SPARQL_TIMEOUT')
        assert hasattr(ErrorCode, 'INVALID_FUNCTION')
        assert hasattr(ErrorCode, 'INTERNAL_ERROR')

    def test_sparqllm_error_structure(self):
        """Test that SparqllmError has correct structure"""
        from SPARQLLM.mcp.errors import SparqllmError, ErrorCode

        error = SparqllmError(
            ErrorCode.INTERNAL_ERROR,
            "Test error",
            {"detail": "test"}
        )

        error_dict = error.to_dict()
        assert "error" in error_dict
        assert error_dict["error"]["code"] == "INTERNAL_ERROR"
        assert error_dict["error"]["message"] == "Test error"
        assert error_dict["error"]["details"]["detail"] == "test"

    def test_handle_error_for_unknown_exception(self):
        """Test error handler for unknown exceptions"""
        from SPARQLLM.mcp.errors import handle_error

        test_exception = ValueError("Unknown error")
        result = handle_error(test_exception)

        assert "error" in result
        assert result["error"]["code"] == "INTERNAL_ERROR"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
