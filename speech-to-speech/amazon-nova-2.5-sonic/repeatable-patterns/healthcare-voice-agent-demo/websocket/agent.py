"""Nova 2.5 Sonic live voice-agent demo: a healthcare clinic phone line.

Use case: a caller rings in and the agent -- running on amazon.nova-2-5-sonic
through a Strands BidiAgent -- handles the call end to end by voice, picking
the right tool for whatever the caller actually asks for, out of five:

- lab_test: reads back the caller's lab results.
- check_specialist_availability + book_appointment: if the lab result is
  flagged, offers to book a specialist and walks through picking a slot
  and confirming it.
- request_prescription_refill: sends a refill to the pharmacy, or tells
  the caller the medication isn't on file instead of guessing.
- check_insurance_coverage: looks up whether a specialist visit is covered.

The point of the demo is tool-calling accuracy: the agent picks the
correct tool (and only that tool) even when a request is indirect ("what
did my blood work show?"), buried next to an unrelated comment ("I'm
having money troubles, but I also wanted to book a specialist"), or
something it should decline instead of act on (a request for medical
advice). It also books real-looking appointments using dates computed
from the actual current date, and never states a confirmation code,
appointment detail, or refill status it wasn't actually given by a tool.

The call opens with the agent greeting the caller by name, unprompted --
done via one hidden kickoff message sent right after connecting, filtered
out of what the client displays so only the greeting itself is visible.

Built on Strands' GA Bidi Agents API (strands.bidi.*, released Oct 5,
2026 alongside Nova 2.5 Sonic itself) -- not the pre-GA
strands.experimental.bidi.* path. The GA API changed shape on both sides
of the wire, not just import paths:
  - send(): no longer a flat {"type": "bidi_audio_input", "audio": base64,
    ...} dict. Audio now goes in as {"audio_delta": {"format": "pcm",
    "source": {"bytes": <raw bytes, not base64>}}}; plain strings are
    still accepted directly for text.
  - receive(): yields granular Start/Delta/Stop/Block events per content
    type (e.g. bidi_transcript_delta, bidi_transcript_block) instead of
    one bidi_transcript_stream event with an is_final flag, and tool calls
    arrive as one bidi_tool_use_blocks event carrying a list, not a
    per-call tool_use_stream stream.
_translate_event() below converts the GA event shapes back into this
file's original stable wire format, so the browser client (client/
index.html) needed zero changes.
"""

import base64
import logging
import traceback

from fastapi import WebSocket, WebSocketDisconnect

from strands.bidi.agent import BidiAgent
from strands.bidi.models import BedrockNovaSonicModel

from tools import (
    book_appointment,
    check_insurance_coverage,
    check_specialist_availability,
    lab_test,
    request_prescription_refill,
    PATIENT_FIRST_NAME,
    PATIENT_LAST_NAME,
    PATIENT_MEDICATION,
    PATIENT_PHONE,
    PATIENT_PREFERRED_DAY,
)

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-2-5-sonic"
REGION = "us-east-1"
VOICE = "tiffany"
INPUT_RATE = 16000
OUTPUT_RATE = 16000

CLINIC_NAME = "Nova Care Clinic"

# Sent once, right after connecting, to make the model greet first. Filtered
# out of what gets forwarded to the client -- see _should_hide below.
KICKOFF_TEXT = "The caller has just connected. Greet them now."


def _build_system_prompt(attribute_preference_out_loud: bool) -> str:
    if attribute_preference_out_loud:
        preference_clause = (
            f'Present the slots and explicitly remind the caller this reflects their stored preference, e.g. '
            f'"Since you prefer {PATIENT_PREFERRED_DAY} appointments, I found these upcoming openings: ...". '
            f"This is the pattern we recommend AGAINST for real use -- it's shown here only as a live contrast "
            f"against the silent version."
        )
    else:
        preference_clause = (
            f'Just present the returned slots directly (e.g. "I have {PATIENT_PREFERRED_DAY} the 24th at 10 AM, '
            f'or {PATIENT_PREFERRED_DAY} the 31st at 2 PM -- which works better?"). Never say "since you usually '
            f'prefer..." or reference the caller\'s history out loud.'
        )

    return f"""You are a voice assistant for {CLINIC_NAME}, communicating with callers over a voice channel.

HOW YOU SHOULD RESPOND:
- Generate responses optimized for text-to-speech playback: plain spoken language only, no formatting symbols or lists.
- Keep replies short -- 1 to 2 sentences, expanding only enough to be clear. Warm, natural, conversational tone.

OPENING:
- The very first thing you receive each call is an instruction to begin, not something the caller said. When you receive it, greet the caller warmly by name and ask how you can help today, in one short line (e.g. "Hello {PATIENT_FIRST_NAME}, welcome to {CLINIC_NAME} -- how can I help you today?"). Do not repeat this greeting later in the call.

KNOWN CALLER (use directly, never ask the caller to provide or confirm it):
- First name: {PATIENT_FIRST_NAME}
- Last name: {PATIENT_LAST_NAME}
- Mobile phone: {PATIENT_PHONE}
- Preferred appointment day, if a specialist appointment is needed: {PATIENT_PREFERRED_DAY}
- Current medication on file: {PATIENT_MEDICATION}

AVAILABLE SERVICES:
- Lab results: if the caller wants their lab or blood test results, call lab_test.
- Specialist booking: if the caller wants a specialist appointment, call check_specialist_availability, then book_appointment once they pick a slot. This includes any request to book or schedule a specialist appointment, even when the caller mentions something unrelated in the same sentence -- act on the specialist request and don't dwell on the unrelated part.
- Prescription refills: if the caller wants to refill a medication, call request_prescription_refill with the medication name as they said it.
- Insurance coverage: if the caller asks whether their insurance covers a specialist visit, call check_insurance_coverage.

LAB RESULTS GUARDRAIL:
- Speak the result values exactly as returned. If hba1c_status is "elevated", state plainly that the value is above the normal range -- never say what it means medically, never suggest a diagnosis or condition.
- After an elevated result, ask a single direct question: whether the caller would like you to schedule a specialist appointment to discuss it further. Do not schedule anything until the caller says yes.

SPECIALIST BOOKING:
- Once the caller wants a specialist appointment, call check_specialist_availability right away -- do not ask the caller what day they want first. The caller's preferred day is {PATIENT_PREFERRED_DAY}; the slots returned already reflect upcoming {PATIENT_PREFERRED_DAY}s. {preference_clause}
- Once the caller picks a slot, call book_appointment with the exact date and time strings from that slot.
- Speak the confirmation using only the date, time, and confirmation code book_appointment actually returned -- never state a confirmation code or appointment detail you weren't given by the tool.

PRESCRIPTION REFILLS:
- If request_prescription_refill returns status "refill_sent", tell the caller the pharmacy and when it'll be ready, using only the values the tool returned.
- If it returns status "not_on_file", tell the caller that medication isn't on file for them and ask them to confirm the name or contact their doctor directly -- never confirm a refill for something not on file, and never guess at a ready date yourself.

INSURANCE COVERAGE:
- Speak the coverage result exactly as returned -- the specialist name, whether it's covered, and the copay -- never state a copay or coverage status you weren't given by the tool.

OUT-OF-SCOPE REQUESTS:
- You never give medical advice, diagnoses, or medication guidance, even if asked directly. If the caller asks for this, say plainly that you can't help with that and offer to connect them with a specialist instead.

TOOL EXECUTION RULES:
- When you call lab_test, check_specialist_availability, book_appointment, request_prescription_refill, or check_insurance_coverage, call the tool as your entire response for that turn -- speak no words at all that turn.
- After a tool result, speak only the natural-language outcome -- never narrate or echo the raw tool payload.

CALL END:
- If the caller indicates they're done (e.g. "that's all, thanks"), say a brief, warm goodbye. Don't ask if they need anything else after they've already said they're done.

FINAL CHECK (confirm before speaking):
- If I'm calling a tool this turn, am I saying nothing else in this turn?
- If I just got an elevated lab result, did I ask about scheduling rather than explaining what it means?
- If I'm confirming a booking, refill, or coverage check, is every detail I'm about to say exactly what the tool returned?
- Am I speaking in plain natural sentences, with no lists or symbols?
"""


class _EventTranslator:
    """Converts GA strands.bidi event shapes into this file's original
    stable wire format, so client/index.html needed zero changes. State
    (transcript accumulators) is scoped per-session, not module-level --
    see handle_websocket_session, which creates one of these per call.
    """

    def __init__(self) -> None:
        self._transcript_so_far: dict[str, str] = {}

    def translate(self, event: dict) -> list[dict]:
        etype = event.get("type")

        if etype == "bidi_transcript_delta":
            content_id = event["content_id"]
            accumulated = self._transcript_so_far.get(content_id, "") + event["delta"]
            self._transcript_so_far[content_id] = accumulated
            return [{"type": "bidi_transcript_stream", "role": event["role"], "text": accumulated, "is_final": False}]

        if etype == "bidi_transcript_block":
            content_id = event["content_id"]
            self._transcript_so_far.pop(content_id, None)
            return [{"type": "bidi_transcript_stream", "role": event["role"], "text": event["transcript"], "is_final": True}]

        if etype == "bidi_audio_delta":
            return [{"type": "bidi_audio_stream", "audio": event["audio"]}]

        if etype == "bidi_barge_in":
            return [{"type": "bidi_interruption", "reason": "barge_in"}]

        if etype == "bidi_tool_use_blocks":
            return [{"type": "tool_use_stream", "current_tool_use": tool_use} for tool_use in event.get("tool_uses", [])]

        if etype in ("tool_result", "error"):
            return [event]  # already in the shape the client expects

        return []  # connection/response/usage/reasoning events -- not relevant to the client


def _log_event(session_tag: str, event: dict) -> None:
    etype = event.get("type")
    if etype == "bidi_transcript_stream" and event.get("is_final"):
        logger.info(f"[{session_tag}] TRANSCRIPT role={event.get('role')} text={event.get('text')!r}")
    elif etype == "tool_use_stream":
        tool_use = event.get("current_tool_use", {}) or {}
        logger.info(f"[{session_tag}] TOOL_USE name={tool_use.get('name')} input={tool_use.get('input')}")
    elif etype == "tool_result":
        logger.info(f"[{session_tag}] TOOL_RESULT {event.get('tool_result')}")
    elif etype == "bidi_interruption":
        logger.info(f"[{session_tag}] INTERRUPTION reason={event.get('reason')}")
    elif etype == "error":
        logger.info(f"[{session_tag}] ERROR {event.get('message')}")


def _should_hide(event: dict) -> bool:
    """Hide the kickoff turn's own "user said this" transcript from the
    client -- the audience should only ever see the model's resulting
    greeting, not the mechanism that triggered it."""
    if event.get("type") != "bidi_transcript_stream":
        return False
    if event.get("role") != "user":
        return False
    return (event.get("text") or "").strip() == KICKOFF_TEXT


def _create_agent(attribute_preference_out_loud: bool = False) -> BidiAgent:
    model = BedrockNovaSonicModel(
        region=REGION,
        model_id=MODEL_ID,
        voice=VOICE,
        audio={
            "input": {"sample_rate": INPUT_RATE},
            "output": {"sample_rate": OUTPUT_RATE},
        },
    )
    return BidiAgent(
        model=model,
        tools=[
            lab_test,
            check_specialist_availability,
            book_appointment,
            request_prescription_refill,
            check_insurance_coverage,
        ],
        system_prompt=_build_system_prompt(attribute_preference_out_loud),
    )


async def handle_websocket_session(websocket: WebSocket, send_output=None) -> None:
    """Handle a single WebSocket voice session."""
    raw_output_fn = send_output or websocket.send_json
    session_tag = "nova25-demo"
    translator = _EventTranslator()

    async def output_fn(raw_event: dict):
        for event in translator.translate(raw_event):
            _log_event(session_tag, event)
            if _should_hide(event):
                continue
            await raw_output_fn(event)

    try:
        config_message = await websocket.receive_json()
        attribute_preference_out_loud = bool(config_message.get("attribute_preference_out_loud", False))

        agent = _create_agent(attribute_preference_out_loud)
        logger.info(
            f"Agent ready: model={MODEL_ID}, voice={VOICE}, "
            f"attribute_preference_out_loud={attribute_preference_out_loud}"
        )
        await raw_output_fn({"type": "system", "message": f"Ready: {MODEL_ID}"})

        greeted = False
        first_audio_sent = False

        async def handle_input():
            # Cross-modal text input (the greeting kickoff) requires an
            # already-active audio stream -- confirmed by testing: sending
            # it before any real audio chunk has gone through produces no
            # response at all. So the kickoff waits until right after the
            # first real audio chunk has already been forwarded, not before.
            nonlocal greeted, first_audio_sent
            if first_audio_sent and not greeted:
                greeted = True
                await agent.send(KICKOFF_TEXT)
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "text_input":
                    await agent.send(message.get("text", ""))
                    continue
                if message.get("type") == "bidi_audio_input":
                    first_audio_sent = True
                    raw_bytes = base64.b64decode(message["audio"])
                    return {"audio_delta": {"format": "pcm", "source": {"bytes": raw_bytes}}}
                # Unrecognized message type -- ignore rather than forward
                # something send() won't accept.
                continue

        await agent.run(inputs=[handle_input], outputs=[output_fn])

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        if "CANCELLED" in str(e):
            logger.warning(f"Cleanup error (ignored): {e}")
        else:
            logger.error(f"Error: {e}")
            traceback.print_exc()
            try:
                await raw_output_fn({"type": "error", "message": str(e)})
            except Exception:
                pass
    finally:
        logger.info("Session closed")
