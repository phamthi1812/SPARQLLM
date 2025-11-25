"""
GGF Metadata Annotation System

Provides @ggf_metadata decorator for manual annotation of Graph Generating Functions.
Use when automatic extraction from code is insufficient or when adding custom cost/capability metadata.

Example usage:
    @ggf_metadata(
        latency_ms=800,
        tokens=500,
        data_sources=["llm"],
        deterministic=False,
        env_var="GROQ_API_KEY"
    )
    def my_ggf_function(ctx, prompt):
        ...
"""

from typing import List, Optional


def ggf_metadata(
    latency_ms: Optional[int] = None,
    tokens: Optional[int] = None,
    rate_limit: Optional[int] = None,
    data_sources: Optional[List[str]] = None,
    deterministic: Optional[bool] = None,
    cacheable: Optional[bool] = None,
    requires_network: Optional[bool] = None,
    env_var: Optional[str] = None,
    config_key: Optional[str] = None,
    description: Optional[str] = None,
    example: Optional[str] = None,
    mcp_server: Optional[str] = None,
    mcp_tool: Optional[str] = None
):
    """
    Decorator to annotate GGFs with catalog metadata.

    Args:
        latency_ms: Estimated P50 latency in milliseconds
        tokens: Estimated token consumption (LLM calls only)
        rate_limit: API rate limit in calls per hour
        data_sources: List of accessed data sources (filesystem, llm, web, sql, vector, mcp, graph)
        deterministic: True if same input always produces same output
        cacheable: True if results can be cached between query executions
        requires_network: True if function requires network access
        env_var: Required environment variable name (e.g., GROQ_API_KEY)
        config_key: Required config.ini parameter name
        description: Human-readable description
        example: SPARQL usage example
        mcp_server: MCP server name (if wrapping MCP tool)
        mcp_tool: MCP tool name (if wrapping MCP tool)

    Returns:
        Decorated function with _ggf_metadata attribute
    """
    def decorator(func):
        metadata = {}

        if latency_ms is not None:
            metadata['latency_ms'] = latency_ms
        if tokens is not None:
            metadata['tokens'] = tokens
        if rate_limit is not None:
            metadata['rate_limit'] = rate_limit
        if data_sources is not None:
            metadata['data_sources'] = data_sources
        if deterministic is not None:
            metadata['deterministic'] = deterministic
        if cacheable is not None:
            metadata['cacheable'] = cacheable
        if requires_network is not None:
            metadata['requires_network'] = requires_network
        if env_var is not None:
            metadata['env_var'] = env_var
        if config_key is not None:
            metadata['config_key'] = config_key
        if description is not None:
            metadata['description'] = description
        if example is not None:
            metadata['example'] = example
        if mcp_server is not None:
            metadata['mcp_server'] = mcp_server
        if mcp_tool is not None:
            metadata['mcp_tool'] = mcp_tool

        func._ggf_metadata = metadata
        return func

    return decorator


# Predefined metadata defaults for common data source types
DATA_SOURCE_DEFAULTS = {
    'filesystem': {
        'latency_ms': 50,
        'deterministic': True,
        'cacheable': True,
        'requires_network': False
    },
    'llm': {
        'latency_ms': 1500,
        'tokens': 500,
        'deterministic': False,
        'cacheable': False,
        'requires_network': True
    },
    'web': {
        'latency_ms': 800,
        'deterministic': False,
        'cacheable': True,
        'requires_network': True
    },
    'vector': {
        'latency_ms': 200,
        'deterministic': True,
        'cacheable': True,
        'requires_network': False
    },
    'sql': {
        'latency_ms': 300,
        'deterministic': True,
        'cacheable': True,
        'requires_network': True
    },
    'mcp': {
        'latency_ms': 1000,
        'deterministic': False,
        'cacheable': False,
        'requires_network': True
    }
}
