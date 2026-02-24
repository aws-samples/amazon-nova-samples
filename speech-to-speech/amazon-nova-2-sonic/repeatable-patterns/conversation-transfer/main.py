"""Main entry point for Nova 2 Sonic multi-agent system."""
import asyncio
import argparse
from src.multi_agent import MultiAgentSonic
from src.core.config import DEFAULT_MODEL_ID, DEFAULT_REGION
from src.core import config


async def main(debug: bool = False):
    """Run multi-agent conversation."""
    config.DEBUG = debug
    
    sonic = MultiAgentSonic(
        model_id=DEFAULT_MODEL_ID,
        region=DEFAULT_REGION,
        debug=debug
    )
    
    await sonic.start_conversation()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Nova 2 Sonic Multi-Agent System')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    try:
        asyncio.run(main(debug=args.debug))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

