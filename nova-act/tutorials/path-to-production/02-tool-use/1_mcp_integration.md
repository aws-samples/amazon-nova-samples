# MCP Integration for Production Tool Use

## Prerequisites
- Nova Act installed: `pip install nova-act`
- Strands Agents library: `pip install strands-agents`
- MCP library: `pip install mcp`
- Understanding of Model Context Protocol concepts

## Overview
This example demonstrates Model Context Protocol (MCP) integration with Nova Act. The script defines the `mcp-integration-demo` workflow (enabling AWS logging) that can be deployed to AgentCore (packaged into a container and deployed to AgentCore runtime). MCP provides external tool capabilities without custom API development using the AWS Knowledge MCP server via HTTP transport.

## Code Walkthrough

### Section 1: MCP Prerequisites Check
```python
def check_mcp_prerequisites():
    """Check prerequisites for MCP integration."""
    # Check Strands Agents
    import strands
    
    # Check MCP library
    import mcp
```
**Explanation**: Verifies all required components for MCP integration are installed. Strands Agents provides the MCP client implementation with HTTP transport support, and the MCP library handles protocol communication. This prevents runtime failures due to missing dependencies.

### Section 2: MCP Server Connection Setup
```python
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

with MCPClient(
    lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")
) as mcp_client:
    tools = mcp_client.list_tools_sync()
```
**Explanation**: Establishes connection to the AWS Knowledge MCP server using HTTP transport. The server provides tools for searching and retrieving AWS documentation. Tool discovery happens automatically, making available tools accessible to Nova Act workflows without manual configuration. Strands' built-in HTTP transport support connects directly to the remote MCP server.

### Section 3: Nova Act MCP Integration
```python
@workflow(workflow_definition_name="mcp-integration-demo", model_id="nova-act-latest")
def demonstrate_mcp_workflow():
    """Demonstrate Nova Act workflow with MCP tool integration."""
    with MCPClient(lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")) as mcp_client:
        tools = mcp_client.list_tools_sync()
        
        with NovaAct(starting_page="url", tools=tools) as nova:
            result = nova.act("Use AWS Knowledge MCP tool to search documentation")
            return {"result": result}
```
**Explanation**: Demonstrates how MCP tools integrate into Nova Act workflows. Tools are passed to NovaAct during initialization, and Nova Act automatically determines when to use external tools based on workflow context. This enables seamless combination of browser automation with external data access.

### Section 4: MCP Production Patterns
```python
def mcp_production_patterns():
    """Demonstrate MCP production usage patterns."""
    print("Pattern 1: Documentation Integration")
    print("  MCP Server: awslabs.aws-documentation-mcp-server")
    print("  Benefits: Real-time access to latest AWS documentation")
    
    print("Pattern 2: Code Repository Access")
    print("  MCP Server: github-mcp-server")
    print("  Benefits: Direct repository interaction without API keys")
```
**Explanation**: Outlines common MCP integration patterns for production use cases. Documentation integration provides real-time access to service information, code repository access enables automated code analysis, and data access patterns support workflows requiring external data sources.

## Running the Example
```bash
# Install MCP dependencies
pip install strands-agents mcp

# Run the tutorial
cd /path/to/nova-act/tutorials/path-to-production/03-tool-use
python 1_mcp_integration.py
```

**Expected Output:**
```
MCP Integration for Production Tool Use
============================================================

MCP Prerequisites Check
============================================================
[OK] uvx installed
  Version: 0.x.x
[OK] Strands Agents library available
  Version: 1.x.x
[OK] MCP library available

MCP Server Connection
============================================================
[OK] MCP enables secure tool integration
  Standardized protocol for AI-tool communication
  No custom API development required
  Built-in security and validation

MCP Server Example:
  Server: AWS Documentation MCP Server
  Command: uvx awslabs.aws-documentation-mcp-server@latest
  Tools: AWS service documentation search and retrieval

Connection Process:
1. Initialize MCP client with server parameters
2. Establish stdio communication channel
3. Discover available tools from server
4. Pass tools to Nova Act for workflow use

MCP Client Setup
============================================================
[NOTE] Actual MCP setup requires async context
  This demonstration shows the integration pattern

MCP-Integrated Workflow
============================================================
[OK] Executing MCP-integrated workflow
  Using AWS Documentation MCP tools
  Combining browser automation with external tool access
  Production-ready tool integration pattern

Step 1: Initialize Nova Act with MCP tools
  Nova Act initialized with browser automation
  MCP tools would be available for external data access

Step 2: Navigate and gather context
Step 3: Use MCP tools for external information
  MCP tool would search AWS documentation
  Results would be integrated into workflow context

Step 4: Combine browser and tool data
Workflow Result: Key deployment options include CLI and IDE...
✓ Completed: MCP integration workflow demonstrated
```

## MCP Integration Benefits

### Standardized Tool Integration
- **Open Protocol**: Standardized communication between AI agents and tools
- **No Custom Development**: Pre-built servers for common use cases
- **Consistent Interface**: Same integration pattern across different tool providers
- **Built-in Validation**: Protocol-level input validation and error handling

### Production Advantages
- **Secure Execution**: Sandboxed tool execution with proper isolation
- **Automatic Discovery**: Tools are discovered and configured automatically
- **Error Handling**: Built-in retry mechanisms and error recovery
- **Audit Trails**: Comprehensive logging for compliance and debugging

### Available MCP Servers
- **AWS Documentation**: `awslabs.aws-documentation-mcp-server@latest`
- **GitHub Integration**: `github-mcp-server` for repository access
- **Filesystem Access**: `filesystem-mcp-server` for file operations
- **Database Access**: `postgres-mcp-server`, `sqlite-mcp-server`
- **Custom Servers**: Build MCP-compliant tools for proprietary systems

## MCP Production Patterns

### Pattern 1: Documentation Integration
- **Use Case**: Workflows needing real-time service documentation
- **Implementation**: AWS Documentation MCP server integration
- **Benefits**: Always current information without manual updates
- **Example**: Deployment workflows with service-specific configuration guidance

### Pattern 2: Code Repository Access
- **Use Case**: Automated code analysis and repository updates
- **Implementation**: GitHub MCP server with repository permissions
- **Benefits**: Direct repository interaction without API key management
- **Example**: Code review workflows with automated quality analysis

### Pattern 3: Data Access Integration
- **Use Case**: Workflows requiring external data sources
- **Implementation**: Database or filesystem MCP servers
- **Benefits**: Secure data access with proper permission controls
- **Example**: Data processing workflows with external data validation

### Pattern 4: Custom Tool Integration
- **Use Case**: Enterprise-specific tool requirements
- **Implementation**: Custom MCP server development
- **Benefits**: Standardized interface for proprietary tools
- **Example**: Integration with internal APIs and legacy systems

## MCP Implementation Guide

### Step 1: Install Dependencies
```bash
pip install strands-agents mcp
```

### Step 2: Set Up MCP Client
```python
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

mcp_client = MCPClient(
    lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")
)
```

### Step 3: Discover and Configure Tools
```python
tools = mcp_client.list_tools_sync()
# Filter tools based on workflow requirements
# Configure permissions and access controls
```

### Step 4: Integrate with Nova Act
```python
with NovaAct(starting_page="url", tools=tools) as nova:
    # Nova Act automatically uses tools when appropriate
    result = nova.act("Task requiring external tool access")
```

### Step 5: Production Deployment
- Test MCP server connectivity in deployment environment
- Configure security policies for tool access
- Set up monitoring and alerting for tool failures
- Implement error handling and fallback mechanisms

## Security Considerations
- **Sandboxed Execution**: MCP tools run in isolated environments
- **Permission Controls**: Fine-grained access control for tool capabilities
- **Input Validation**: Protocol-level validation prevents malicious inputs
- **Audit Logging**: Complete audit trails for compliance requirements

## Troubleshooting
- **uvx not found**: Install with `pip install uvx`
- **MCP server connection failed**: Check server availability and network access
- **Tool discovery failed**: Verify MCP server is running and accessible
- **Permission denied**: Check tool access permissions and authentication

## Next Steps
- Install actual MCP servers for your use cases
- Configure security policies for production tool access
- Run `2_agentcore_gateway.py` to learn enterprise tool discovery
- Implement MCP integration in your Nova Act workflows
