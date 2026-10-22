"""Main entry point for Nova 2 Sonic multi-agent system."""
import asyncio
import argparse
import logging

from src.multi_agent import MultiAgentSonic
from src.config import DEFAULT_MODEL_ID, DEFAULT_REGION
from src import config


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quiet noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("smithy_aws_event_stream").setLevel(logging.WARNING)
    logging.getLogger("smithy_core").setLevel(logging.WARNING)
    logging.getLogger("smithy_aws_core").setLevel(logging.WARNING)
    logging.getLogger("aws_sdk_bedrock_runtime").setLevel(logging.WARNING)


async def main(debug: bool = False):
    """Run multi-agent conversation."""
    config.DEBUG = debug

    sonic = MultiAgentSonic(
        model_id=DEFAULT_MODEL_ID,
        region=DEFAULT_REGION,
        debug=debug,
    )

    await sonic.start_conversation()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nova 2 Sonic Multi-Agent System")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(debug=args.debug)

    try:
        asyncio.run(main(debug=args.debug))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
