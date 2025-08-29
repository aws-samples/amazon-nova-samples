from livekit import agents
from livekit.agents import AgentSession, Agent, AutoSubscribe
from livekit.plugins.aws.experimental.realtime import RealtimeModel
from livekit.agents.llm.chat_context import ChatContext
from livekit.agents import function_tool, Agent, RunContext
import json
from typing import Any

@function_tool()
async def lookup_weather(
    context: RunContext,
    location: str,
) -> dict[str, Any]:
    """Look up weather information for a given location.
    
    Args:
        location: The location to look up weather information for.
    """

    return {"weather": "sunny", "temperature_f": 70}


async def entrypoint(ctx: agents.JobContext):
    # Connect to the LiveKit server
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    chat_ctx = ChatContext.empty()
    chat_ctx.add_message(role="user", content="hey sonic, my name is John Doe.")

    # Initialize the Amazon Nova Sonic agent
    agent = Agent(
        instructions="You are a helpful voice AI assistant helping user to check weather information.", 
        chat_ctx=chat_ctx, 
        tools=[lookup_weather]
    )
    session = AgentSession(llm=RealtimeModel(voice="matthew"))
    
    # Start the session in the specified room
    await session.start(
        room=ctx.room,
        agent=agent,
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))