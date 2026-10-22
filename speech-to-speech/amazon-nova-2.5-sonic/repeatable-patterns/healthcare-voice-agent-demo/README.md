# Healthcare Voice Agent Demo (Nova 2.5 Sonic + Strands)

A live voice-agent demo built on `amazon.nova-2-5-sonic` through a [Strands](https://github.com/strands-agents/harness-sdk) `BidiAgent`, showing accurate tool-calling for a fictional clinic phone line. The clinic, patient, and all data are made up for demo purposes.

## Use case

A caller rings in and the agent handles the call end to end by voice, picking the right tool for whatever the caller actually asks for, out of five:

- `lab_test` — reads back the caller's lab results.
- `check_specialist_availability` + `book_appointment` — if a lab result is flagged, offers to book a specialist and walks through picking a slot and confirming it.
- `request_prescription_refill` — sends a refill to the pharmacy, or tells the caller the medication isn't on file instead of guessing.
- `check_insurance_coverage` — looks up whether a specialist visit is covered.

The demo is built to exercise tool-calling accuracy specifically: the agent needs to pick the correct tool (and only that tool) even when a request is indirect ("what did my blood work show?"), buried next to an unrelated comment ("I'm having money troubles, but I also wanted to book a specialist"), or something it should decline instead of act on (a request for medical advice). It also books real-looking appointments using dates computed from the actual current date, and never states a confirmation code, appointment detail, or refill status it wasn't actually given by a tool.

The call opens with the agent greeting the caller by name, unprompted, via a hidden kickoff message sent right after connecting.

## Architecture

```
Browser (client/index.html)
  -- captures mic audio, base64-encodes it over a JSON WebSocket wire protocol --
  v
FastAPI WebSocket server (websocket/server.py)
  -- decodes audio, forwards to the Strands BidiAgent, translates GA events back to the
     client's stable wire format --
  v
Strands BidiAgent (websocket/agent.py) -- amazon.nova-2-5-sonic
  -- calls tools in websocket/tools.py as needed --
```

Built on Strands' GA Bidi Agents API (`strands.bidi.*`, released alongside Nova 2.5 Sonic). `agent.py` includes an `_EventTranslator` that converts the GA API's granular event taxonomy (e.g. `bidi_transcript_delta`/`bidi_transcript_block`, `bidi_tool_use_blocks`) into one stable wire format, so the browser client never has to track upstream API changes.

## Running it

Requires Python 3.11+ and AWS credentials with Bedrock access to `amazon.nova-2-5-sonic` in `us-east-1`.

```bash
# 1. Start the WebSocket server
cd websocket
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 server.py        # listens on ws://localhost:8083/ws

# 2. In a separate terminal, serve the browser client
cd client
python3 client.py        # opens http://localhost:3002 in your browser
```

Allow microphone access when prompted, then just talk — the agent greets you first.

To see the anti-pattern contrast (the agent explicitly says "since you prefer Friday appointments..." out loud, which we recommend against for production use), open `http://localhost:3002/?antiPattern=1` instead. This isn't exposed as a visible UI toggle on purpose — it's meant to be shown as a deliberate "before" contrast during a walkthrough, not discovered by a caller.

## Example things to say

- "What did my blood work show?" — indirect lab-results request.
- "I'm having some money troubles, but I also wanted to book a specialist appointment." — multi-intent distractor; the agent should act on the specialist request and not dwell on the unrelated remark.
- "Can you refill my metformin?" — prescription refill.
- "Does my insurance cover seeing a specialist?" — insurance coverage check.
- "Can you just tell me what medication I should take?" — out-of-scope request the agent should decline.

## Files

- `websocket/agent.py` — the Strands `BidiAgent` setup, system prompt, and GA-to-wire-format event translation.
- `websocket/tools.py` — the five tools and the fictional patient/clinic data they operate on.
- `websocket/server.py` — thin FastAPI WebSocket wrapper.
- `websocket/scenario_test.py` — a scripted pre-flight check covering the greeting kickoff, multi-intent distractor, explicit-vs-silent preference phrasing, out-of-scope decline, and natural call closing. Talks to the `BidiAgent` directly, not through the WebSocket server.
- `client/index.html` — the browser UI.
- `client/client.py` — a minimal static file server for `index.html`.
