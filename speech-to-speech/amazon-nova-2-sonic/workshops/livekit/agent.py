from livekit import agents
from livekit.agents import AgentSession, Agent, AutoSubscribe
from livekit.plugins.aws.experimental.realtime import RealtimeModel

async def entrypoint(ctx: agents.JobContext):
    # Connect to the LiveKit server
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Initialize the Amazon Nova Sonic agent
    agent = Agent(instructions="You are a helpful voice AI assistant.")
    session = AgentSession(llm=RealtimeModel())
    
    # Start the session in the specified room
    await session.start(
        room=ctx.room,
        agent=agent,
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))