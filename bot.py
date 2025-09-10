import asyncio
import os
import argparse
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.aws_nova_sonic.aws import AWSNovaSonicLLMService
from pipecat.services.aws.llm import AWSBedrockLLMContext
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.services.daily import DailyParams, DailyTransport

load_dotenv(override=True)


async def fetch_weather_from_api(params: FunctionCallParams):
    temperature = 75 if params.arguments["format"] == "fahrenheit" else 24
    await params.result_callback(
        {
            "conditions": "nice",
            "temperature": temperature,
            "format": params.arguments["format"],
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        }
    )


weather_function = FunctionSchema(
    name="get_current_weather",
    description="Get the current weather",
    properties={
        "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
        },
        "format": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The temperature unit to use. Infer this from the users location.",
        },
    },
    required=["location", "format"],
)

# Create tools schema
tools = ToolsSchema(standard_tools=[weather_function])


async def main(room_url, token):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Set up WebRTC transport
    - Speech-to-text and text-to-speech services
    - Language model integration
    """
    async with aiohttp.ClientSession() as session:
        print(f"Starting server with room: {room_url}")

        # Set up Daily transport with audio parameters
        transport = DailyTransport(
            room_url,
            token,
            "Amazon Voice AI Agent",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                camera_in_enabled=False,
                camera_out_enabled=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
                transcription_enabled=True,
            ),
        )

        # Initialize LLM service
        llm = AWSNovaSonicLLMService(
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("AWS_REGION"),
            voice_id="tiffany",  # matthew, tiffany, amy
        )

        # Register function for function calls
        llm.register_function("get_current_weather", fetch_weather_from_api)

        # Set up context and context management.
        system_instruction = (
            "You are a friendly assistant. The user and you will engage in a spoken dialog exchanging "
            "the transcripts of a natural real-time conversation. Keep your responses short, generally "
            "two or three sentences for chatty scenarios. "
            "Start by greeting the user."
        )
        context = AWSBedrockLLMContext(
            messages=[{"role": "system", "content": f"{system_instruction}"}],
            tools=tools,
        )
        context_aggregator = llm.create_context_aggregator(context)

        await asyncio.sleep(0.1)  # Give Nova Sonic time to initialise

        # Build the pipeline
        pipeline = Pipeline(
            [
                transport.input(),
                context_aggregator.user(),
                llm,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        # Configure the pipeline task
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            print(f"Participant left: {participant}")
            await task.cancel()

        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)


if __name__ == "__main__":
    # Parse command line arguments for server configuration
    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "7860"))

    parser = argparse.ArgumentParser(description="Daily FastAPI server")
    parser.add_argument("-u", "--url", type=str, help="Daily room url")
    parser.add_argument("-t", "--token", type=str, help="Daily room token")

    config = parser.parse_args()

    asyncio.run(main(config.url, config.token))
