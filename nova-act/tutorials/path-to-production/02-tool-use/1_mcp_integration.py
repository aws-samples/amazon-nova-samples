#!/usr/bin/env python3
"""
MCP Integration for Production Tool Use

This script demonstrates Model Context Protocol (MCP) integration with Nova Act
for production workflows requiring external tool capabilities.

Prerequisites:
- Nova Act installed: pip install nova-act
- Strands Agents library: pip install strands-agents
- MCP library: pip install mcp
- Understanding of MCP concepts

Setup:
1. Install MCP dependencies: pip install strands-agents mcp
2. Run this script to demonstrate AWS Knowledge MCP integration

Note: Uses AWS Knowledge MCP server (https://knowledge-mcp.global.api.aws) via HTTP transport.
"""

import subprocess
import json
import boto3
from nova_act import NovaAct, workflow


def create_workflow_definition():
    """Interactively create workflow definition in Nova Act Service."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWorkflow Definition Setup\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    workflow_name = "mcp-integration-demo"
    
    # Check if workflow already exists
    try:
        result = subprocess.run(
            ['act', 'workflow', 'describe', workflow_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"\033[93m[OK]\033[0m Workflow definition '{workflow_name}' already exists")
            return True
    except Exception:
        pass
    
    print(f"\nThis script uses the @workflow decorator to define a workflow:")
    print(f"\n\033[96m@workflow(workflow_definition_name=\"{workflow_name}\", model_id=\"nova-act-latest\")\033[0m")
    print(f"\033[96mdef demonstrate_mcp_workflow():\033[0m")
    print(f"\033[96m    with MCPClient(lambda: streamablehttp_client(\"https://knowledge-mcp.global.api.aws\")) as mcp_client:\033[0m")
    print(f"\033[96m        tools = mcp_client.list_tools_sync()\033[0m")
    print(f"\033[96m        with NovaAct(starting_page=\"...\", tools=tools) as nova:\033[0m")
    print(f"\033[96m            result = nova.act(\"Search AWS Knowledge for docs\")\033[0m")
    print(f"\033[96m            return {{\"result\": result}}\033[0m")
    
    print(f"\n\033[93m[ACTION REQUIRED]\033[0m Create workflow definition in Nova Act Service?")
    print(f"  This enables AWS logging for workflow execution")
    print(f"  Workflow name: {workflow_name}")
    
    response = input(f"\nCreate workflow definition? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print(f"\033[91m[SKIPPED]\033[0m Workflow definition not created")
        print(f"  Script will fail without workflow definition")
        return False
    
    try:
        print(f"\n\033[93m[CREATING]\033[0m Creating workflow definition...")
        result = subprocess.run(
            ['act', 'workflow', 'create', '--name', workflow_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\033[92m✓ Created:\033[0m Workflow definition '{workflow_name}'")
            
            # Get workflow details
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            region = boto3.session.Session().region_name or 'us-east-1'
            
            print(f"\n  ARN: arn:aws:nova-act:{region}:{identity['Account']}:workflow-definition/{workflow_name}")
            print(f"  Logging: Enabled (CloudWatch Logs)")
            return True
        else:
            print(f"\033[91m[ERROR]\033[0m Failed to create workflow definition")
            print(f"  {result.stderr}")
            return False
            
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Failed to create workflow definition: {e}")
        return False


def check_mcp_prerequisites():
    """Check prerequisites for MCP integration."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Prerequisites Check\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    prerequisites_met = True
    
    # Check Strands Agents
    try:
        import strands
        print(f"\033[93m[OK]\033[0m Strands Agents library available")
    except ImportError:
        print(f"\033[91m[ERROR]\033[0m Strands Agents not found")
        print("  Install: pip install strands-agents")
        prerequisites_met = False
    
    # Check MCP library
    try:
        import mcp
        print(f"\033[93m[OK]\033[0m MCP library available")
    except ImportError:
        print(f"\033[91m[ERROR]\033[0m MCP library not found")
        print("  Install: pip install mcp")
        prerequisites_met = False
    
    return prerequisites_met


def demonstrate_mcp_server_connection():
    """Demonstrate MCP server connection and tool discovery."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Server Connection\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print("\n\033[93m[OK]\033[0m MCP enables secure tool integration")
    print("  Standardized protocol for AI-tool communication")
    print("  No custom API development required")
    print("  Built-in security and validation")
    
    print(f"\n\033[38;5;214mMCP Server Example:\033[0m")
    print("  Server: AWS Documentation MCP Server")
    print("  Command: uvx awslabs.aws-documentation-mcp-server@latest")
    print("  Tools: AWS service documentation search and retrieval")
    
    print(f"\n\033[38;5;214mConnection Process:\033[0m")
    print("1. Initialize MCP client with server parameters")
    print("2. Establish stdio communication channel")
    print("3. Discover available tools from server")
    print("4. Pass tools to Nova Act for workflow use")


async def setup_aws_docs_mcp_client():
    """Set up AWS Documentation MCP client."""
    print(f"\n\033[93m[OK]\033[0m Setting up AWS Documentation MCP client")
    print("  Server: awslabs.aws-documentation-mcp-server@latest")
    print("  Protocol: stdio communication")
    print("  Tools: AWS documentation search and retrieval")
    
    try:
        # Initialize MCP client for AWS Documentation
        mcp_client = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["awslabs.aws-documentation-mcp-server@latest"]
                )
            )
        )
        
        print(f"\033[93m[OK]\033[0m MCP client initialized")
        print("  Connection established with AWS Documentation server")
        
        # Get available tools
        tools = await mcp_client.list_tools_async()
        print(f"\033[93m[OK]\033[0m Available tools discovered: {len(tools)}")
        
        for tool in tools[:3]:  # Show first 3 tools
            print(f"  • {tool.name}: {tool.description[:60]}...")
        
        return mcp_client, tools
        
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m MCP client setup failed: {e}")
        print("  This is expected without uvx and MCP server installed")
        return None, []


@workflow(workflow_definition_name="mcp-integration-demo", model_id="nova-act-latest")
def demonstrate_mcp_workflow():
    """Verify AWS documentation exists for Nova Act path-to-production using AWS Knowledge MCP."""
    
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from strands.tools.mcp import MCPClient
        
        print(f"\n\033[93m[CONNECTING]\033[0m Starting AWS Knowledge MCP server...")
        
        with MCPClient(
            lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")
        ) as mcp_client:
            tools = mcp_client.list_tools_sync()
            print(f"\033[92m✓ Connected:\033[0m AWS Knowledge MCP server running")
            print(f"  Available tools: {len(tools)}")
            
            with NovaAct(
                starting_page="https://aws.amazon.com/blogs/machine-learning/amazon-nova-act-sdk-preview-path-to-production-for-browser-automation-agents/",
                tools=tools
            ) as nova:
                result = nova.act(
                    "Use the AWS Knowledge MCP tool to search for 'Nova Act path to production' documentation. "
                    "Return ONLY the URL where documentation was found, nothing else. "
                    "If no documentation exists, return only the word 'false'."
                )
                
                # Parse URLs from the result string
                import re
                result_str = str(result)
                urls = re.findall(r'https://[^\s\'"<>]+', result_str)
                
                # Filter out the starting page URL
                filtered_urls = [url for url in urls if 'amazon-nova-act-sdk-preview-path-to-production-for-browser-automation-agents' not in url]
                
                result_value = filtered_urls[0] if filtered_urls else "false"
                
                return {
                    "status": "completed",
                    "result": result_value,
                    "mcp_tools_used": len(tools)
                }
                
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m MCP workflow failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }



def explain_mcp_benefits():
    """Explain benefits of MCP integration for production."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Integration Benefits\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mStandardized Tool Integration:\033[0m")
    print("  • Open protocol for AI-tool communication")
    print("  • No custom API development required")
    print("  • Consistent tool interface across providers")
    print("  • Built-in security and validation")
    
    print(f"\n\033[38;5;214mProduction Advantages:\033[0m")
    print("  • Secure tool execution with proper isolation")
    print("  • Automatic tool discovery and capability detection")
    print("  • Error handling and retry mechanisms")
    print("  • Logging and audit trails for tool usage")
    
    print(f"\n\033[38;5;214mAvailable MCP Servers:\033[0m")
    print("  • AWS Documentation: awslabs.aws-documentation-mcp-server")
    print("  • GitHub: github-mcp-server")
    print("  • Filesystem: filesystem-mcp-server")
    print("  • Database: postgres-mcp-server, sqlite-mcp-server")
    print("  • Custom servers: Build your own MCP-compliant tools")
    
    print(f"\n\033[38;5;214mSecurity Features:\033[0m")
    print("  • Sandboxed tool execution")
    print("  • Permission-based access control")
    print("  • Input validation and sanitization")
    print("  • Audit logging for compliance")


def mcp_production_patterns():
    """Demonstrate MCP production usage patterns."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Production Patterns\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mPattern 1: Documentation Integration\033[0m")
    print("  Use Case: Workflows needing AWS service documentation")
    print("  MCP Server: awslabs.aws-documentation-mcp-server")
    print("  Benefits: Real-time access to latest AWS documentation")
    print("  Example: Deployment workflows with service-specific guidance")
    
    print(f"\n\033[38;5;214mPattern 2: Code Repository Access\033[0m")
    print("  Use Case: Workflows needing code analysis or updates")
    print("  MCP Server: github-mcp-server")
    print("  Benefits: Direct repository interaction without API keys")
    print("  Example: Code review workflows with automated analysis")
    
    print(f"\n\033[38;5;214mPattern 3: Data Access Integration\033[0m")
    print("  Use Case: Workflows needing database or file system access")
    print("  MCP Server: postgres-mcp-server, filesystem-mcp-server")
    print("  Benefits: Secure data access with proper permissions")
    print("  Example: Data processing workflows with external data sources")
    
    print(f"\n\033[38;5;214mPattern 4: Custom Tool Integration\033[0m")
    print("  Use Case: Enterprise-specific tool requirements")
    print("  MCP Server: Custom MCP server implementation")
    print("  Benefits: Standardized interface for proprietary tools")
    print("  Example: Integration with internal APIs and services")


def mcp_implementation_guide():
    """Provide MCP implementation guide for production."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Implementation Guide\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mStep 1: Install MCP Dependencies\033[0m")
    print("  pip install strands-agents")
    print("  pip install uvx")
    print("  pip install mcp")
    
    print(f"\n\033[38;5;214mStep 2: Set Up MCP Client\033[0m")
    print("  from mcp import StdioServerParameters, stdio_client")
    print("  from strands.tools.mcp import MCPClient")
    print("  Initialize client with server parameters")
    
    print(f"\n\033[38;5;214mStep 3: Discover and Configure Tools\033[0m")
    print("  tools = mcp_client.list_tools_sync()")
    print("  Filter tools based on workflow requirements")
    print("  Configure tool permissions and access controls")
    
    print(f"\n\033[38;5;214mStep 4: Integrate with Nova Act\033[0m")
    print("  with NovaAct(starting_page=url, tools=tools) as nova:")
    print("  Nova Act automatically uses tools when appropriate")
    print("  Monitor tool usage through logging and metrics")
    
    print(f"\n\033[38;5;214mStep 5: Production Deployment\033[0m")
    print("  Test MCP server connectivity in deployment environment")
    print("  Configure security policies for tool access")
    print("  Set up monitoring and alerting for tool failures")
    print("  Implement error handling and fallback mechanisms")


def main(payload):
    """
    Main function demonstrating MCP integration for production.
    
    Args:
        payload: Input parameters for workflow execution
    """
    print(f"\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Integration for Production Tool Use\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Create workflow definition
    if not create_workflow_definition():
        print(f"\n\033[91m[STOPPED]\033[0m Cannot proceed without workflow definition")
        return
    
    # Check prerequisites
    if not check_mcp_prerequisites():
        print(f"\n\033[93m[WARNING]\033[0m Prerequisites not fully met")
        print("Install: pip install strands-agents mcp")
        return
    
    # Execute MCP workflow
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP-Integrated Workflow\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    result = demonstrate_mcp_workflow()
    
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mResults\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    if result.get("status") == "completed":
        result_value = result.get("result", "")
        
        if result_value.lower() == "false":
            print(f"\n\033[91mDocumentation Found: FALSE\033[0m")
            print(f"  No AWS documentation found for Nova Act path to production")
        else:
            print(f"\n\033[92mDocumentation Found: TRUE\033[0m")
            print(f"\n\033[38;5;214mURLs Found:\033[0m")
            # Split by newlines or commas to handle multiple URLs
            urls = [url.strip() for url in result_value.replace(',', '\n').split('\n') if url.strip()]
            for url in urls:
                print(f"  • {url}")
        
        print(f"\n\033[38;5;214mMCP Tools Used:\033[0m {result.get('mcp_tools_used', 0)}")
    else:
        print(f"\n\033[91mStatus: {result.get('status')}\033[0m")
        print(f"  Message: {result.get('message', 'Unknown error')}")
    
    print(f"\n\033[38;5;214m{'='*60}\033[0m")

    
    # Display completion
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMCP Integration Complete\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[92m✓ Completed:\033[0m MCP integration patterns and implementation guide")
    print(f"\033[38;5;214m→ Next:\033[0m Learn AgentCore Gateway for enterprise tool discovery")
    
    print(f"\n\033[38;5;214mMCP Production Benefits:\033[0m")
    print("1. Standardized tool integration protocol")
    print("2. Secure tool execution with proper isolation")
    print("3. No custom API development required")
    print("4. Built-in error handling and validation")
    
    print(f"\n\033[38;5;214mNext Tutorial:\033[0m")
    print("Run: python 2_agentcore_gateway.py")


if __name__ == "__main__":
    # Execute with empty payload for local testing
    main({})
