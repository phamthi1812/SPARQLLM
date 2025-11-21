"""Tool schema definitions for SPARQLLM MCP Server

Following MCP best practices:
- snake_case naming
- Flat JSON Schema format
- Clear, actionable descriptions
"""

from mcp.types import Tool


# Phase 1: Echo tool for testing
ECHO_TOOL = Tool(
    name="echo",
    description="Echo test tool - returns input message. Used for testing MCP connectivity.",
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


# Phase 2: SPARQL query tool
SPARQL_QUERY_TOOL = Tool(
    name="sparql_query",
    description=(
        "Execute SPARQL query with Graph Generating Functions (GGFs). "
        "Supports SELECT, CONSTRUCT, ASK, DESCRIBE queries. "
        "Use ggf:FUNCTION(?args) to call registered UDFs (filesystem, LLM, search, etc.). "
        "Available functions depend on config.ini [Associations] section."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SPARQL query string (SELECT, CONSTRUCT, ASK, DESCRIBE, UPDATE)"
            },
            "output_format": {
                "type": "string",
                "enum": ["json-ld", "json", "csv", "turtle"],
                "default": "json-ld",
                "description": "Result format: json-ld/json for SELECT, json-ld/turtle for CONSTRUCT"
            },
            "timeout": {
                "type": "number",
                "default": 30,
                "minimum": 1,
                "maximum": 300,
                "description": "Query timeout in seconds (1-300)"
            },
            "max_results": {
                "type": "number",
                "default": 1000,
                "minimum": 1,
                "maximum": 10000,
                "description": "Maximum rows for SELECT queries (1-10000)"
            },
            "preload_data": {
                "type": "string",
                "description": "Optional RDF data to load before query execution"
            },
            "preload_format": {
                "type": "string",
                "enum": ["turtle", "xml", "json-ld", "nquads"],
                "default": "turtle",
                "description": "Format of preload_data (turtle, xml, json-ld, nquads)"
            }
        },
        "required": ["query"]
    }
)


# Phase 3: Convenience tools
EXTRACT_STRUCTURED_DATA_TOOL = Tool(
    name="extract_structured_data",
    description=(
        "Extract structured data from files (CSV, HTML, TXT, PDF). "
        "Automatically parses file format and extracts data. "
        "Returns JSON with extracted entities and properties."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to file (local path or URL)"
            },
            "format_hint": {
                "type": "string",
                "enum": ["csv", "html", "txt", "auto"],
                "default": "auto",
                "description": "File format hint (auto-detected if not provided)"
            },
            "limit": {
                "type": "number",
                "default": 100,
                "minimum": 1,
                "maximum": 10000,
                "description": "Max results to return"
            },
            "timeout": {
                "type": "number",
                "default": 60,
                "minimum": 1,
                "maximum": 300,
                "description": "Timeout in seconds"
            }
        },
        "required": ["file_path"]
    }
)

WEB_TO_KNOWLEDGE_TOOL = Tool(
    name="web_to_knowledge",
    description=(
        "Fetch and extract content from webpages. "
        "Scrapes URL and returns text content as structured data."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Webpage URL to fetch"
            },
            "text_max_chars": {
                "type": "number",
                "default": 10000,
                "minimum": 100,
                "maximum": 50000,
                "description": "Max characters to extract from page"
            },
            "timeout": {
                "type": "number",
                "default": 60,
                "minimum": 1,
                "maximum": 300,
                "description": "Timeout in seconds"
            }
        },
        "required": ["url"]
    }
)


# Export all tool schemas
TOOL_SCHEMAS = [
    ECHO_TOOL,
    SPARQL_QUERY_TOOL,
    EXTRACT_STRUCTURED_DATA_TOOL,
    WEB_TO_KNOWLEDGE_TOOL,
]
