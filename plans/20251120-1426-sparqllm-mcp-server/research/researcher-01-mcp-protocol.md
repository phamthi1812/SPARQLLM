# MCP Protocol Research: Specification & Best Practices

## 1. MCP Protocol Specification

**Standard**: JSON-RPC 2.0 over stdio transport (primary) or HTTP with SSE fallback.

**Core Message Flow**: Clients send JSON-RPC requests (with method, params, id); servers respond with result or error objects. Stateful protocol maintains connection between host (LLM application), client (connector), and server (context provider).

**Key Features**:
- Capability negotiation during initialization
- Three server-provided capabilities: tools, resources, prompts
- Composable integrations for modular workflows

*Source: https://modelcontextprotocol.io/specification/2025-06-18*

## 2. Stdio Transport & JSON-RPC

**Message Format**: Newline-delimited JSON-RPC 2.0 messages. Each message contains method, params, and id for stateful correlation.

**Transport Advantages**:
- Universal compatibility (any language supporting text I/O)
- Process isolation (natural security boundaries)
- Debugging transparency (all messages visible)
- No custom framing complexity

**Robust Implementation**: Uses Content-Length headers with explicit framing (`Content-Length: NNN\r\n\r\n` followed by JSON payload) to handle streaming edge cases.

*Source: https://modelcontextprotocol.io/docs/concepts/transports*

## 3. Tool Schema Design

**Input Schema**: Uses JSON Schema format to define parameters. Each tool includes:
- `name`: Unique identifier (snake_case preferred, 90%+ adoption)
- `description`: High-level functionality explanation
- `inputSchema`: JSON Schema object defining parameters with type, description, constraints, required fields

**Best Practices**:
- Keep schemas flat; avoid deeply nested properties (use lazy loading for large APIs)
- Separate tool description from parameter descriptions
- Include validation constraints (patterns, min/max, enum values)
- Use flexible designs with optional/extensible fields
- Handle errors within result objects, not protocol level

**Naming**: snake_case (GPT-4o tokenization compatible); avoid spaces, dots, brackets. Prefix tools with service name in multi-server environments (e.g., `github-add_issue_comment`).

*Sources: https://www.merge.dev/blog/mcp-tool-schema; https://zazencodes.com/blog/mcp-server-naming-conventions*

## 4. Resource Providers

**Resource Listing**: `resources/list` endpoint exposes:
- `uri`: Unique identifier
- `name`: Human-readable name
- `description`: Optional resource metadata
- `mimeType`: Content type

**Resource Templates** (RFC 6570): Enable dynamic resources via URI templates (e.g., `weather://{city}/forecast`). Clients construct valid URIs from patterns.

**Reading Resources**: Clients request via `resources/read` with specific URI; server provides text or blob content for LLM context.

*Source: https://modelcontextprotocol.info/docs/concepts/resources/*

## 5. State Management Patterns

**Stateful Architecture** (recommended for most cases):
- Server maintains session context in memory per client connection
- Long-lived stdio/SSE connections enable persistent state
- Connection resumability for dropped connections
- Session state is instance-local (no external persistence in current SDKs)

**Stateless Architecture**:
- No session context; each request self-contained
- Simplified routing (any instance handles any request)
- Use for high-traffic/load-balanced deployments

**Best Practice**: In-memory state suffices for most MCP servers. Consider Redis/database only for: multiple server instances behind load balancer, survive restarts, very high concurrency (1000s of sessions).

*Source: https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/102*

## 6. Error Handling Conventions

**Three Error Levels**:
1. Transport errors: timeouts, broken pipes, auth failures
2. Protocol errors: JSON-RPC 2.0 violations
3. Application errors: within tool implementations

**Best Practices**:
- Use standardized error codes to signal temporary vs. permanent failures
- Report tool errors within result objects (not protocol level)
- Log to stderr only; stdout reserved for JSON-RPC messages
- Never include sensitive data (keys, passwords) in errors
- Craft agent-focused messages (what to do next, not just what failed)
- Implement graceful degradation: alternative tools, retry logic, timeouts, circuit breakers

*Source: https://mcpcat.io/guides/error-handling-custom-mcp-servers/*

## 7. Tool Discoverability & Naming

**Tool Identification**: Unique names + descriptions via `tools/list` endpoint.

**Naming Conventions**:
- **Format**: snake_case (90%+ standard)
- **Clarity**: Name reflects conceptual purpose, not implementation details
- **Consistency**: Same naming style across all tools
- **Prefixing**: Use service name prefix for multi-server environments
- **Parameter names**: Consistent naming for similar-function parameters across tools

**Description Strategy**: Highlight function, purpose, and specific actions. High quality descriptions maximize LLM interoperability and improve discovery.

*Source: https://snyk.io/articles/5-best-practices-for-building-mcp-servers/*

## 8. Security Framework (Specification)

MCP spec emphasizes four critical areas:
1. **User Consent**: Explicit approval for all data access and operations
2. **Data Privacy**: Host requires consent before exposing user data to servers
3. **Tool Safety**: Code execution requires authorization; tool descriptions untrusted unless verified
4. **LLM Sampling Controls**: User approval for sampling; controlled prompts

Implementors must establish robust authorization flows, clear documentation, and appropriate access controls.

*Source: https://modelcontextprotocol.io/specification/2025-06-18*

## Summary

MCP is a standardized, JSON-RPC 2.0-based protocol enabling LLM applications to integrate external tools and data sources. Success requires: (1) clean stdio transport with proper framing, (2) schema-driven tools with flat inputs and clear naming, (3) resource templating for dynamic data, (4) stateful session management for context preservation, (5) protocol-level error handling with agent-focused messaging, and (6) rigorous security/consent patterns.

---

**Key Sources**:
- Official Spec: https://modelcontextprotocol.io/specification/2025-06-18
- Docs: https://modelcontextprotocol.io/
- GitHub: https://github.com/modelcontextprotocol/
- Best Practices: Snyk, Merge.dev, MCPcat, official MCP discussion forums
