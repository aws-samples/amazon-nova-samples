# Tool Integration

## Purpose
This folder demonstrates production tool integration patterns for Nova Act workflows using the `@workflow` decorator. Each tutorial defines a workflow (enabling AWS logging) that can be deployed to AgentCore (packaged into a container and deployed to AgentCore runtime). The tutorials cover Model Context Protocol (MCP) for standardized tool connections, AgentCore Gateway for enterprise tool registries, and security guardrails for controlling tool access.

## Tutorial Sequence

1. **1_mcp_integration.py**: Defines `mcp-integration-demo` workflow that connects Nova Act to MCP servers using the stdio transport protocol. Demonstrates AWS Documentation server integration without custom API development. Shows how MCP standardizes tool discovery and invocation across different server implementations.

2. **2_agentcore_gateway.py**: Defines `gateway-integration-demo` workflow that integrates with AgentCore Gateway for centralized enterprise tool management. Demonstrates tool discovery from the gateway registry, authentication with AWS credentials, and automatic tool availability in Nova Act workflows. Shows how gateway provides security, compliance, and governance for tool usage.

3. **3_security_guardrails.py**: Defines `security-guardrails-demo` workflow that implements URL-based security controls using State Guardrails. Demonstrates blocking real domains (google.com, facebook.com, twitter.com) while allowing Amazon/AWS domains. Shows three practical tests: (1) successful navigation to allowed domains, (2) blocked navigation to google.com, and (3) navigation within approved Amazon/AWS sites. Implements allow/block lists with wildcard pattern matching and default-deny security policy.

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
- **State Guardrails**: Documented Nova Act feature for URL access control
- **Block Lists**: Prevent navigation to social media (facebook.com, twitter.com) and search engines (google.com)
- **Allow Lists**: Define approved domains (nova.amazon.com, *.aws.amazon.com, amazon.com)
- **Pattern Matching**: Wildcard support (*.google.com blocks all Google subdomains)
- **Default Deny**: Unknown domains blocked automatically for maximum security
- **Real-time Validation**: Guardrails checked after each browser observation
- **Exception Handling**: ActStateGuardrailError raised when navigation blocked
- **Audit Logging**: All allow/block decisions logged for security monitoring
- **Three-Test Demo**: (1) Allow nova.amazon.com, (2) Block google.com, (3) Allow docs.aws.amazon.com

**Note**: File access restrictions and tool approval workflows should be implemented at the infrastructure/application level, not via Nova Act SDK.

## Next Steps
After completing this folder, proceed to `03-observability/` to learn how to monitor and debug tool usage in production workflows.
