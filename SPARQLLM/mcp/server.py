"""SPARQLLM MCP Server Core

Implements MCP protocol server using STDIO transport.
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource, ResourceTemplate
import asyncio
import logging
from typing import Optional, List
import uuid
from datetime import datetime

from SPARQLLM.config import ConfigSingleton
from SPARQLLM.udf.SPARQLLM import store, reset_store
from SPARQLLM.mcp.schemas.tool_schemas import TOOL_SCHEMAS
from SPARQLLM.mcp.tools.echo import echo_tool
from SPARQLLM.mcp.tools.sparql_query import sparql_query_tool
from SPARQLLM.mcp.tools.extract_structured_data import extract_structured_data_tool
from SPARQLLM.mcp.tools.web_to_knowledge import web_to_knowledge_tool
from SPARQLLM.mcp.errors import handle_error

logger = logging.getLogger("SPARQLLM.mcp.server")


class SparqllmMCPServer:
    """
    SPARQLLM MCP Server implementing Model Context Protocol.

    Exposes neuro-symbolic RAG capabilities as MCP tools over STDIO transport.
    """

    def __init__(self, config_file: str):
        """
        Initialize MCP server.

        Args:
            config_file: Path to SPARQLLM config.ini
        """
        self.server = Server("sparqllm")
        self.config_file = config_file
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self.session_start = datetime.utcnow()
        self.request_count = 0

        # Register tool handlers
        self._register_tools()

        # Register resource handlers (Phase 4)
        self._register_resources()

    def _register_tools(self):
        """Register all available tools with the server."""
        # Echo tool (Phase 1)
        @self.server.call_tool()
        async def echo(arguments: dict) -> list[TextContent]:
            """Echo tool for testing connectivity."""
            try:
                self.request_count += 1
                logger.debug(f"Echo tool called (request {self.request_count})")
                return await echo_tool(arguments)
            except Exception as e:
                logger.error(f"Error in echo tool: {e}", exc_info=True)
                error_dict = handle_error(e)
                return [TextContent(type="text", text=str(error_dict))]

        # SPARQL query tool (Phase 2)
        @self.server.call_tool()
        async def sparql_query(arguments: dict) -> list[TextContent]:
            """Execute SPARQL query with UDFs."""
            try:
                self.request_count += 1
                logger.info(f"SPARQL query tool called (request {self.request_count})")
                return await sparql_query_tool(arguments)
            except Exception as e:
                logger.error(f"Error in sparql_query tool: {e}", exc_info=True)
                error_dict = handle_error(e)
                return [TextContent(type="text", text=str(error_dict))]

        # Convenience tools (Phase 3)
        @self.server.call_tool()
        async def extract_structured_data(arguments: dict) -> list[TextContent]:
            """Extract structured data from files."""
            try:
                self.request_count += 1
                logger.info(f"Extract tool called (request {self.request_count})")
                return await extract_structured_data_tool(arguments)
            except Exception as e:
                logger.error(f"Error in extract_structured_data tool: {e}", exc_info=True)
                error_dict = handle_error(e)
                return [TextContent(type="text", text=str(error_dict))]

        @self.server.call_tool()
        async def web_to_knowledge(arguments: dict) -> list[TextContent]:
            """Convert webpage to knowledge graph."""
            try:
                self.request_count += 1
                logger.info(f"Web tool called (request {self.request_count})")
                return await web_to_knowledge_tool(arguments)
            except Exception as e:
                logger.error(f"Error in web_to_knowledge tool: {e}", exc_info=True)
                error_dict = handle_error(e)
                return [TextContent(type="text", text=str(error_dict))]

    def _register_resources(self):
        """Register resource handlers (Phase 4)."""
        # Register resource listing
        self.server.list_resources = self._list_resources

        # Register resource reading
        self.server.read_resource = self._read_resource

        # Register resource templates
        self.server.list_resource_templates = self._list_resource_templates

    async def _list_resources(self) -> List[Resource]:
        """
        List available resources (named graphs in store).

        Returns:
            List of Resource objects
        """
        from SPARQLLM.mcp.resources.store_resource import list_store_resources
        try:
            resources = await list_store_resources(self.session_id)
            logger.debug(f"Listed {len(resources)} resources")
            return resources
        except Exception as e:
            logger.error(f"Error listing resources: {e}", exc_info=True)
            return []

    async def _read_resource(self, uri: str) -> str:
        """
        Read resource content.

        Args:
            uri: Resource URI to read

        Returns:
            Resource content as string
        """
        from SPARQLLM.mcp.resources.store_resource import read_store_resource
        try:
            content = await read_store_resource(uri, self.session_id)
            logger.debug(f"Read resource: {uri} ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            raise

    async def _list_resource_templates(self) -> List[ResourceTemplate]:
        """
        List resource URI templates.

        Returns:
            List of ResourceTemplate objects
        """
        return [
            ResourceTemplate(
                uriTemplate=f"store://{self.session_id}/graphs/{{graph_id}}",
                name="Store Graph",
                description="Named graph in the SPARQL store (generated by GGF execution)",
                mimeType="application/ld+json"
            )
        ]

    async def _list_tools(self) -> list[Tool]:
        """
        Return list of available tools.

        Returns:
            List of Tool schema objects
        """
        return TOOL_SCHEMAS

    async def _on_connection_close(self):
        """Cleanup on connection close."""
        logger.info(
            f"Session {self.session_id} closed after {self.request_count} requests"
        )
        # Clean up store to prevent cross-contamination
        reset_store()

    async def run(self):
        """
        Start MCP server with STDIO transport.

        This method blocks until the server is shut down.
        """
        # Initialize config and UDFs
        try:
            logger.info(f"Initializing config from {self.config_file}")
            ConfigSingleton(config_file=self.config_file)
            logger.info("Config initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize config: {e}", exc_info=True)
            raise

        # Set up tool listing
        self.server.list_tools = self._list_tools

        # Start STDIO server
        logger.info(f"Starting MCP server (session: {self.session_id})")

        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("MCP server ready, awaiting connections...")

                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            await self._on_connection_close()
