# Phase 1: Core MCP Server Infrastructure

**Duration:** 3-5 days
**Status:** Ready for implementation
**Dependencies:** None

## Overview

Build foundational MCP server using STDIO transport. Focus: JSON-RPC 2.0 protocol handling, tool registration, session lifecycle, error framework. Outcome: `slm-mcp-server` CLI responds to basic MCP requests.

## Context & Key Insights

**From research:**
- MCP uses JSON-RPC 2.0 over STDIO with Content-Length headers
- Tool schemas require flat JSON Schema format
- snake_case naming convention (90%+ adoption)
- Error handling at 3 levels: transport, protocol, application
- Stateful session management standard for STDIO connections

**From codebase analysis:**
- Existing CLI uses Click framework (`slm.py`)
- ConfigSingleton loads UDFs from config.ini [Associations]
- Global store must be reset per request to prevent contamination
- Echo server example exists (`SPARQLLM/servers/echo_mcp_server.py`)

## Architecture Decisions

### 1. Transport Layer
**Decision:** Use official Python MCP SDK (`mcp` package) for STDIO server
- Handles Content-Length framing automatically
- Provides `@server.call_tool()` decorator pattern
- Built-in error handling for protocol violations

**Alternative rejected:** Raw JSON-RPC implementation (too much boilerplate)

### 2. Tool Registration
**Decision:** Decorator-based registration pattern
```python
@server.call_tool()
async def sparql_query(arguments: dict) -> list[TextContent]:
    # Implementation
```

**Rationale:** Matches official SDK patterns, auto-generates tools/list response

### 3. Session Management
**Decision:** Per-connection state tracking
- Track session_id per STDIO connection
- Isolate store per session (call `reset_store()` on connection close)
- Store session metadata: config_file, start_time, request_count

**Rationale:** STDIO connections naturally isolated by OS process boundaries

### 4. Error Framework
**Decision:** Structured error objects with agent-focused messages
```json
{
  "error": {
    "code": "SPARQL_SYNTAX_ERROR",
    "message": "Invalid SPARQL: Expected SELECT/CONSTRUCT/ASK/DESCRIBE",
    "details": {
      "line": 5,
      "column": 12,
      "suggestion": "Add SELECT clause before WHERE"
    }
  }
}
```

**Rationale:** Research emphasizes "agent-focused messages" - tell agents what to fix

## Implementation Steps

### Step 1: Project Structure Setup (1 hour)
Create new files:
```
SPARQLLM/
├── mcp/
│   ├── __init__.py
│   ├── server.py
│   ├── tools/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── tool_schemas.py
│   └── errors.py
└── cli/
    ├── slm_mcp_server.py
    └── shared.py
```

### Step 2: Extract Shared CLI Logic (3-4 hours)
**File:** `SPARQLLM/cli/shared.py`

Extract from `slm.py`:
- `execute_query(query_str, config_file, load_file, format, timeout)` function
- `is_update_query()` function
- Result formatting logic

Keep in `slm.py`:
- Click decorators
- Terminal output formatting

Update `slm_cmd()` to call `execute_query()`.

**Success criteria:** Existing CLI still works, tests pass

### Step 3: MCP Server Core (4-6 hours)
**File:** `SPARQLLM/mcp/server.py`

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio
import logging
from SPARQLLM.config import ConfigSingleton
from SPARQLLM.udf.SPARQLLM import store, reset_store

logger = logging.getLogger("SPARQLLM.mcp")

class SparqllmMCPServer:
    def __init__(self, config_file: str):
        self.server = Server("sparqllm")
        self.config_file = config_file
        self.session_id = None
        self.request_count = 0

        # Register handlers
        self.server.list_tools = self._list_tools

    async def _list_tools(self) -> list[Tool]:
        """Return available tools."""
        from SPARQLLM.mcp.schemas.tool_schemas import TOOL_SCHEMAS
        return TOOL_SCHEMAS

    async def _on_connection_close(self):
        """Cleanup on connection close."""
        logger.info(f"Session {self.session_id} closed after {self.request_count} requests")
        reset_store()

    async def run(self):
        """Start STDIO server."""
        # Initialize config
        ConfigSingleton(config_file=self.config_file)

        async with stdio_server() as (read_stream, write_stream):
            logger.info(f"MCP server started with config: {self.config_file}")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
```

### Step 4: Tool Schema Definitions (2-3 hours)
**File:** `SPARQLLM/mcp/schemas/tool_schemas.py`

Define schemas for Phase 1 (echo tool only):
```python
from mcp.types import Tool

TOOL_SCHEMAS = [
    Tool(
        name="echo",
        description="Echo test tool - returns input message",
        inputSchema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back"
                }
            },
            "required": ["message"]
        }
    )
]
```

### Step 5: Error Handling Framework (3-4 hours)
**File:** `SPARQLLM/mcp/errors.py`

```python
from enum import Enum
from typing import Optional, Dict, Any

class ErrorCode(Enum):
    SPARQL_SYNTAX_ERROR = "SPARQL_SYNTAX_ERROR"
    SPARQL_TIMEOUT = "SPARQL_TIMEOUT"
    INVALID_FUNCTION = "INVALID_FUNCTION"
    STORE_OVERFLOW = "STORE_OVERFLOW"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class SparqllmError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }

def handle_error(e: Exception) -> dict:
    """Convert exception to MCP-friendly error response."""
    if isinstance(e, SparqllmError):
        return e.to_dict()

    # Map known exceptions
    if "ParseException" in str(type(e)):
        return SparqllmError(
            ErrorCode.SPARQL_SYNTAX_ERROR,
            f"Invalid SPARQL syntax: {str(e)}",
            {"suggestion": "Check query syntax"}
        ).to_dict()

    # Unknown error
    return SparqllmError(
        ErrorCode.INTERNAL_ERROR,
        f"Unexpected error: {str(e)}"
    ).to_dict()
```

### Step 6: CLI Entry Point (2-3 hours)
**File:** `SPARQLLM/cli/slm_mcp_server.py`

```python
import click
import asyncio
import logging
from SPARQLLM.mcp.server import SparqllmMCPServer

@click.command()
@click.option(
    "-c", "--config",
    type=click.STRING,
    default="config.ini",
    help="Config file for UDF registration"
)
@click.option(
    "-d", "--debug",
    is_flag=True,
    help="Enable debug logging"
)
def main(config: str, debug: bool):
    """Start SPARQLLM MCP server (STDIO transport)."""

    # Configure logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()]  # stderr only, stdout for MCP
    )

    # Start server
    server = SparqllmMCPServer(config_file=config)
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
```

### Step 7: Update setup.py (30 minutes)
Add entry point:
```python
entry_points={
    'console_scripts': [
        'slm-run=SPARQLLM.cli.slm:slm_cmd',
        'slm-mcp-server=SPARQLLM.cli.slm_mcp_server:main',  # NEW
    ],
}
```

### Step 8: Implement Echo Tool (2 hours)
**File:** `SPARQLLM/mcp/tools/echo.py`

```python
from mcp.types import TextContent
import logging

logger = logging.getLogger("SPARQLLM.mcp.tools")

async def echo_tool(arguments: dict) -> list[TextContent]:
    """Echo test tool."""
    message = arguments.get("message", "")
    logger.info(f"Echo tool called with message: {message}")

    return [
        TextContent(
            type="text",
            text=f"Echo: {message}"
        )
    ]
```

Register in `server.py`:
```python
from SPARQLLM.mcp.tools.echo import echo_tool

class SparqllmMCPServer:
    def __init__(self, config_file: str):
        # ...
        self.server.call_tool("echo")(echo_tool)
```

### Step 9: Basic Testing (2-3 hours)
**File:** `tests/test_mcp_server_basic.py`

```python
import pytest
import asyncio
from SPARQLLM.mcp.server import SparqllmMCPServer

@pytest.mark.asyncio
async def test_server_initialization():
    """Test server starts without errors."""
    server = SparqllmMCPServer(config_file="config.ini")
    assert server.server.name == "sparqllm"

@pytest.mark.asyncio
async def test_list_tools():
    """Test tools/list returns valid schemas."""
    server = SparqllmMCPServer(config_file="config.ini")
    tools = await server._list_tools()

    assert len(tools) >= 1
    assert any(t.name == "echo" for t in tools)

@pytest.mark.asyncio
async def test_echo_tool():
    """Test echo tool returns message."""
    from SPARQLLM.mcp.tools.echo import echo_tool

    result = await echo_tool({"message": "test"})
    assert len(result) == 1
    assert "test" in result[0].text
```

### Step 10: Integration Test with MCP Inspector (2 hours)
Use official MCP inspector to test STDIO communication:

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Start server via inspector
mcp-inspector slm-mcp-server --config config.ini

# Verify:
# 1. Server initializes
# 2. tools/list returns echo tool
# 3. echo tool call returns message
```

## Success Criteria

- [ ] `slm-mcp-server --config config.ini` starts without errors
- [ ] Logs show "MCP server started" message
- [ ] `tools/list` returns valid JSON with echo tool schema
- [ ] Echo tool call returns correct message
- [ ] Existing `slm-run` CLI still works
- [ ] Tests pass: `pytest tests/test_mcp_server_basic.py -v`
- [ ] MCP inspector shows server as "connected"

## Testing Strategy

1. **Unit tests**: Each component isolated
2. **Integration tests**: STDIO communication via subprocess
3. **Manual testing**: MCP inspector for protocol validation
4. **Regression tests**: Existing CLI must still pass all tests

## Security Considerations

- **Logging**: Never log to stdout (reserved for JSON-RPC), stderr only
- **Input validation**: JSON Schema validates all tool arguments
- **Error messages**: Never expose internal paths or config details
- **Process isolation**: Each STDIO connection runs in isolated process

## Performance Notes

- **Startup time**: <500ms (ConfigSingleton initialization)
- **Memory baseline**: ~50MB (Python + rdflib)
- **Connection overhead**: Minimal (STDIO native to OS)

## Rollback Plan

If Phase 1 fails:
1. Existing CLI unaffected (shared logic extracted, not removed)
2. New files can be deleted without breaking existing functionality
3. Entry point in setup.py can be commented out

## Next Steps

After Phase 1 completion:
- Phase 2: Implement `sparql.query` tool (core functionality)
- Validate tool schema design with early users
- Gather feedback on error message quality

## References

- MCP STDIO Transport: https://modelcontextprotocol.io/docs/concepts/transports
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Tool Schema Best Practices: https://www.merge.dev/blog/mcp-tool-schema
- Existing echo server: `SPARQLLM/servers/echo_mcp_server.py`
