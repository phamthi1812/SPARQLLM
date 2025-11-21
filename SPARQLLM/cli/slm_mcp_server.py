"""CLI entry point for SPARQLLM MCP Server

Usage:
    slm-mcp-server --config config.ini
    slm-mcp-server --config config.ini --debug
"""

import click
import asyncio
import logging
import sys

from SPARQLLM.mcp.server import SparqllmMCPServer


@click.command()
@click.option(
    "-c", "--config",
    type=click.STRING,
    default="config.ini",
    help="Config file for UDF registration (default: config.ini)"
)
@click.option(
    "-d", "--debug",
    is_flag=True,
    help="Enable debug logging"
)
def main(config: str, debug: bool):
    """
    Start SPARQLLM MCP server with STDIO transport.

    The server exposes SPARQLLM's neuro-symbolic RAG capabilities
    as Model Context Protocol tools for AI agents.

    Examples:
        slm-mcp-server
        slm-mcp-server --config myconfig.ini
        slm-mcp-server --debug
    """
    # Configure logging - CRITICAL: only log to stderr, stdout is for MCP protocol
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]  # stderr only!
    )

    logger = logging.getLogger("SPARQLLM.mcp")
    logger.info(f"SPARQLLM MCP Server starting with config: {config}")

    # Start server
    try:
        server = SparqllmMCPServer(config_file=config)
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
