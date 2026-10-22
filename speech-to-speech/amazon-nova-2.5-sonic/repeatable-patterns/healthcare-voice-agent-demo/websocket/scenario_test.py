"""One-off scripted test covering the new demo scenarios: greeting kickoff,
multi-intent distractor, explicit-vs-silent preference phrasing, out-of-scope
decline, and natural call closing. Not part of the demo itself -- a
pre-flight check, same pattern as completion_cadence_test.py.

Talks to the GA BidiAgent directly (not through handle_websocket_session),
so it uses the GA send()/receive() shapes raw -- audio_delta with real
bytes going in, bidi_tool_use_blocks/bidi_transcript_block coming out --
rather than this file's translated wire format (that translation only
happens inside agent.py's own output_fn).
"""

import asyncio

import boto3

from agent import KICKOFF_TEXT, _create_agent

SAMPLE_RATE = 16000
_polly = boto3.client("polly", region_name="us-east-1")


def synth(text: str) -> bytes:
    return _polly.synthesize_speech(
        Text=text, OutputFormat="pcm", SampleRate=str(SAMPLE_RATE), VoiceId="Joanna", Engine="neural",
    )["AudioStream"].read()


async def send_audio(agent, pcm: bytes) -> None:
    chunk = 4096 * 2
    for i in range(0, len(pcm), chunk):
        await agent.send({"audio_delta": {"format": "pcm", "source": {"bytes": pcm[i:i + chunk]}}})
        await asyncio.sleep(4096 / SAMPLE_RATE)


async def send_silence(agent, seconds: float) -> None:
    silence = b"\x00\x00" * 4096
    elapsed = 0.0
    while elapsed < seconds:
        await agent.send({"audio_delta": {"format": "pcm", "source": {"bytes": silence}}})
        await asyncio.sleep(4096 / SAMPLE_RATE)
        elapsed += 4096 / SAMPLE_RATE


async def drain(agent, window: float) -> None:
    agen = agent.receive()
    loop = asyncio.get_event_loop()
    deadline = loop.time() + window
    while loop.time() < deadline:
        try:
            ev = await asyncio.wait_for(agen.__anext__(), timeout=max(0.1, deadline - loop.time()))
        except (asyncio.TimeoutError, StopAsyncIteration):
            break
        t = ev.get("type") if isinstance(ev, dict) else None
        if t == "bidi_tool_use_blocks":
            for tool_use in ev.get("tool_uses", []):
                print("  TOOL_CALL:", tool_use.get("name"), tool_use.get("input"))
        elif t == "bidi_transcript_block":
            print("  TRANSCRIPT", ev.get("role"), ev.get("transcript"))


async def run_turn(agent, phrase: str, window: float = 16) -> None:
    pcm = synth(phrase)
    await send_audio(agent, pcm)
    silence_task = asyncio.create_task(send_silence(agent, window))
    await drain(agent, window)
    silence_task.cancel()


async def scenario_greeting() -> None:
    print("=== SCENARIO: proactive greeting ===")
    agent = _create_agent()
    await agent.start()
    # Mirror the production fix: one real (silent) audio chunk must go
    # through first to establish the audio stream, THEN the kickoff --
    # sending the kickoff with zero prior audio produces no response at all.
    silence_chunk = b"\x00\x00" * 4096
    await agent.send({"audio_delta": {"format": "pcm", "source": {"bytes": silence_chunk}}})
    await agent.send(KICKOFF_TEXT)
    silence_task = asyncio.create_task(send_silence(agent, 10))
    await drain(agent, 10)
    silence_task.cancel()
    await agent.stop()


async def scenario_multi_intent() -> None:
    print("\n=== SCENARIO: multi-intent distractor ===")
    agent = _create_agent()
    await agent.start()
    await run_turn(agent, "I'm having some money troubles, but I also wanted to book a specialist appointment.")
    await agent.stop()


async def scenario_explicit_preference() -> None:
    print("\n=== SCENARIO: explicit preference ('since you prefer Friday...') ===")
    agent = _create_agent(attribute_preference_out_loud=True)
    await agent.start()
    await run_turn(agent, "I'd like to book a specialist appointment.")
    await agent.stop()


async def scenario_out_of_scope() -> None:
    print("\n=== SCENARIO: out-of-scope medical advice request ===")
    agent = _create_agent()
    await agent.start()
    await run_turn(agent, "Can you just tell me what medication I should take?")
    await agent.stop()


async def scenario_call_closing() -> None:
    print("\n=== SCENARIO: natural call closing ===")
    agent = _create_agent()
    await agent.start()
    await run_turn(agent, "I need my lab results.")
    await run_turn(agent, "That's all, thanks.")
    await agent.stop()


async def main() -> None:
    await scenario_greeting()
    await scenario_multi_intent()
    await scenario_explicit_preference()
    await scenario_out_of_scope()
    await scenario_call_closing()


if __name__ == "__main__":
    asyncio.run(main())
