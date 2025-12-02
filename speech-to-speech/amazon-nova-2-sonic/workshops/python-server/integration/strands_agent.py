from mcp import stdio_client, StdioServerParameters
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel
import boto3 
import os
import json
import requests
import re

@tool
def weather(lat, lon: float) -> str:
    """Get weather information for a given lat and lon

    Args:
        lat: latitude of the location
        lon: logitude of the location
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "current_weather": True
    }
    # Default weather response in case of open-meteo call failure
    result = {"generationtime_ms": 0.07450580596923828, "utc_offset_seconds": 0, "timezone": "GMT", "timezone_abbreviation": "GMT", "elevation": 76.0, "current_weather_units": {"time": "iso8601", "interval": "seconds", "temperature": "\u00b0C", "windspeed": "km/h", "winddirection": "\u00b0", "is_day": "", "weathercode": "wmo code"}, "current_weather": {"time": "2025-07-11T12:30", "interval": 900, "temperature": 21.6, "windspeed": 6.1, "winddirection": 360, "is_day": 1, "weathercode": 2}}
    try:
        response = requests.get(url, params=params)
        result = response.json()["current_weather"]
    except Exception as ex:
        print(ex)
    return result

class StrandsAgent:

    def __init__(self):
        # Launch AWS Location Service MCP Server and create a client object
        aws_profile = os.getenv("AWS_PROFILE")
        env = {"FASTMCP_LOG_LEVEL": "ERROR"}
        if aws_profile:
            env["AWS_PROFILE"] = aws_profile

        self.aws_location_srv_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="uvx", 
                args=["awslabs.aws-location-mcp-server@latest"],
                env=env)
            ))
        self._server_context = self.aws_location_srv_client.__enter__()
        self.aws_location_srv_tools = self.aws_location_srv_client.list_tools_sync()

        session = boto3.Session(
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        # Specify Bedrock LLM for the Agent
        bedrock_model = BedrockModel(
            model_id="amazon.nova-lite-v1:0",
            boto_session=session
        )
        # Create a Strands Agent
        tools = self.aws_location_srv_tools
        tools.append(weather)
        self.agent = Agent(
            tools=tools, 
            model=bedrock_model,
            system_prompt="You are a chat agent tasked with answering location and weather-related questions. Please include your response within the <response></response> tag."
        )


    '''
    Send the input to the agent, allowing it to handle tool selection and invocation. 
    The response will be generated after the selected LLM performs reasoning. 
    This approach is suitable when you want to delegate tool selection logic to the agent, and have a generic toolUse definition in Sonic ToolUse.
    Note that the reasoning process may introduce latency, so it's recommended to use a lightweight model such as Nova Lite.
    Sample parameters: input="largest zoo in Seattle?"
    '''
    def query(self, input):
        output = str(self.agent(input))
        if "<response>" in output and "</response>" in output:
            match = re.search(r"<response>(.*?)</response>", output, re.DOTALL)
            if match:
                output = match.group(1)
        elif "<answer>" in output and "</answer>" in output:
            match = re.search(r"<answer>(.*?)</answer>", output, re.DOTALL)
            if match:
                output = match.group(1)
        return output

    '''
    Invoke the tool directly and return the raw response without any reasoning.
    This approach is suitable when tool selection is managed within Sonic and the exact toolName is already known. 
    It offers lower query latency, as no additional reasoning is performed by the agent.
    Sample parameters: tool_name="search_places", input="largest zoo in Seattle"
    '''
    def call_tool(self, tool_name, input):
        if isinstance(input, str):
            input = json.loads(input)
        if "query" in input:
            input = input.get("query")

        tool_func = getattr(self.agent.tool, tool_name)
        return tool_func(query=input)

    def close(self):
        # Cleanup the MCP server context
        self.aws_location_srv_client.__exit__(None, None, None)