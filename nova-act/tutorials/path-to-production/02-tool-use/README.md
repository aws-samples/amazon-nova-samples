# Tool Integration

## Purpose
This folder demonstrates production tool integration patterns for Nova Act workflows using the `@workflow` decorator. Each tutorial defines a workflow (enabling AWS logging) that can be deployed to AgentCore (packaged into a container and deployed to AgentCore runtime). The tutorials cover Model Context Protocol (MCP) for standardized tool connections, AgentCore Gateway for enterprise tool registries, and security guardrails for controlling tool access.

## Tutorial Sequence

1. **1_mcp_integration.py**: Defines `mcp-integration-demo` workflow that connects Nova Act to MCP servers using the stdio transport protocol. Demonstrates AWS Documentation server integration without custom API development. Shows how MCP standardizes tool discovery and invocation across different server implementations.

2. **2_agentcore_gateway.py**: Defines `gateway-integration-demo` workflow that integrates with AgentCore Gateway for centralized enterprise tool management. Demonstrates tool discovery from the gateway registry, authentication with AWS credentials, and automatic tool availability in Nova Act workflows. Shows how gateway provides security, compliance, and governance for tool usage.

3. **3_security_guardrails.py**: Defines `security-guardrails-demo` workflow that implements defense-in-depth security controls for tool usage. Demonstrates URL allow/block lists, file access restrictions, and tool usage policies. Shows how to configure SecurityOptions and create custom guardrail logic for production deployments.

## Prerequisites

- Understanding of workflow concepts (defining workflows enables AWS logging, deploying workflows packages into containers for AgentCore runtime)
- Nova Act installed: `pip install nova-act`
- Python 3.10+
- AWS credentials configured (for AgentCore Gateway)

### MCP Server Setup
```bash
# Install MCP dependencies
pip install strands-agents mcp

# AWS Knowledge MCP server is accessed via HTTP
# No local server installation required
```

### AgentCore Gateway
- AWS credentials with AgentCore Gateway permissions
- Gateway endpoint URL from your AWS account
- Tool definitions registered in gateway

### Security Configuration
- IAM policies for file access controls
- Network policies for URL restrictions
- Tool usage policies defined in your security framework

## Production Considerations

### MCP Integration
- AWS Knowledge MCP server accessed via HTTP transport (no local server needed)
- Strands Agents provides built-in HTTP transport support
- Error handling for server connection failures
- Multiple MCP servers can be connected simultaneously

### AgentCore Gateway
- Centralized tool registry reduces duplication across teams
- Gateway provides audit logging for tool invocations
- Tool versioning and deprecation managed at gateway level
- Authentication and authorization enforced by gateway

### Security Guardrails
- URL restrictions prevent data exfiltration and malicious site access
- File access controls limit filesystem exposure
- Tool usage policies enforce least-privilege access
- Guardrails evaluated before tool execution
- Failed guardrail checks logged for security monitoring

## Next Steps
After completing this folder, proceed to `04-observability/` to learn how to monitor and debug tool usage in production workflows.
