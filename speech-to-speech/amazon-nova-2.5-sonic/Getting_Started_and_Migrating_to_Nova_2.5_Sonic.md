# Getting Started / Migrating to Nova 2.5 Sonic

Nova 2.5 Sonic is Amazon's speech-to-speech model for building real-time, human-like conversational AI on Amazon Bedrock, with better reasoning, lower latency, and higher cost efficiency.

Nova 2.5 Sonic is designed for teams building voice agents, agentic calling, support automation, and other interactive voice experiences where users expect fast responses, reliable instruction following, and accurate tool use. Sonic 2.5 is built with a newer reasoning component and closes the #1 gap customers flag in Sonic 2 on reasoning capabilities: it is smarter (AudioMC +43%, ComplexFuncBench +25%, tau3-bench +20%), faster (TTFA P50 -28%, P99 -41%), and cheaper per hour at the same per-token pricing in IAD with terser output.

## What's new

Nova 2.5 Sonic is the reasoning upgrade to Nova Sonic. Compared with Nova 2 Sonic, it is built to make voice agents:

- **More reliable in real workflows**: better tool calling, stronger instruction following, and better multi-step task completion.
- **Faster to start speaking**: lower time to first audio on short conversational turns.
- **More efficient in conversation**: terser answers can reduce cost per hour even when per-token pricing is unchanged.
- **Easy to deploy from Sonic 2**: same API surface, voices, and language/locale coverage; migration is primarily a model ID change plus prompt tuning.

The main migration consideration is prompt tuning. Nova 2.5 Sonic follows instructions more strictly and tends to answer more concisely, so prompts written for Nova 2 Sonic may need adjustment to preserve the right amount of detail and avoid unnecessary refusals.

## Performance overview

Nova 2.5 Sonic brings performance improvements over Nova 2 Sonic on many dimensions, all targeting questions that customers care most about.

| Customer question | What improved | Result (vs Nova 2 Sonic) |
|---|---|---|
| Will my voice agent follow instructions better? | Audio MultiChallenge | +43% |
| Will tool calling be more reliable? | ComplexFuncBench | +25% |
| Can it complete multi-step agentic tasks? | tau3-bench, Airline and Telecom domains | +20% |
| Will users hear responses sooner? | Time to first audio, P50 | 1.50s to 1.08s, a 28% reduction |
| What about tail latency? | Time to first audio, P99 | 2.45s to 1.45s, a 41% reduction |
| Is the conversation quality better? | Human blind-vote win rate | 68.3% for male voice and 65.6% for female voice |
| Will it cost less to run? | Estimated cost per hour | Lower expected cost per hour because responses are shorter; external measurement pending |

Early testing showed the same pattern in real applications from our customers:

- A production evaluation saw tool calling improve from 73% on Sonic 2 to 90%+ on Sonic 2.5, with latency within 1.5 seconds.
- An agentic calling evaluation saw task completion improve by 18% versus Sonic 2 and reach parity with GPT Realtime in its evaluation.
- A telephone-audio evaluation of 308 identical real 8 kHz cases saw accepted answers improve from 58% to 70%, invented content drop from 58 cases to 7, and answers become about 50% shorter.
- A retail tool-calling audio A/B benchmark improved from 47.8% to 78.3%, winning every category with zero regressions.

## How to start

- **Select a representative Sonic 2 workflow.** Start with a voice-agent flow that uses your real system prompt, tools, function schemas, and downstream APIs.
- **Change the model ID.** Use the Nova 2.5 Sonic model ID `amazon.nova-2-5-sonic` provided for your Bedrock environment and run in an available launch region. Planned GA launch regions are `us-east-1`, `us-west-2`, `eu-north-1`, and `ap-northeast-1`.
- **Re-tune the system prompt.** Review instructions that control brevity, refusal behavior, tool use, and persona. Sonic 2.5 may follow terse or restrictive instructions more literally than Sonic 2. See [Migrating from Nova 2 Sonic → Update your system prompt](#update-your-system-prompt) below.
- **Test the flows customers actually notice.** Prioritize tool selection, parameter accuracy, multi-turn context, agentic task completion, latency feel, concise-but-complete answers, and correct handling of benign and unsafe requests.
- **Compare against your Sonic 2 baseline.** Track task completion, tool-call success, turn-level latency, user-perceived responsiveness, escalation or fallback rate, and total session cost.

Below are some example evaluation metrics you could use to understand how Nova 2.5 Sonic works with your use case — adjust the list based on your business and technical requirements.

- **Tool calls**: correct function, correct parameters, no unnecessary calls.
- **Instruction following**: stays in persona, honors formatting and brevity requirements, preserves required detail.
- **Agentic flows**: completes multi-step tasks without losing state.
- **Latency**: first audio feels responsive on short conversational turns.
- **Safety behavior**: fewer benign over-refusals while still handling unsafe requests correctly.
- **Cost**: compare cost per completed task or cost per hour, not only per-token price.

Nova 2.5 Sonic helps teams build more reliable, intelligent voice-first applications with the same Sonic API experience. It improves the parts customers most often notice in production voice agents: instruction following, tool calling, task completion, latency, and conversational efficiency.

---

## Migrating from Nova 2 Sonic

If you have an existing Nova 2 Sonic integration, migrating is primarily: (1) point at the new model ID, (2) re-tune your system prompt for a stricter, terser model, and (3) if you're on a voice-agent framework (LiveKit, Pipecat, Strands), make sure you're on a library version that supports the Nova 2.5 Sonic model ID.

### Update your system prompt

Nova 2.5 Sonic follows instructions more literally and answers more concisely than Nova 2 Sonic. A prompt that relied on Sonic 2 "filling in" unstated behavior, or that over-corrected for a looser model with heavy-handed phrasing, is the most common source of migration regressions — not the model swap itself. Before shipping, re-review:

- **Brevity and refusal behavior** — instructions written to counteract Sonic 2's verbosity or over-refusal may now be too aggressive and cause unwanted terseness or benign refusals on Sonic 2.5.
- **Tool-calling and tool descriptions** — Sonic 2.5's stronger instruction-following means ambiguous or conflicting tool guidance surfaces faster as a visible bug rather than being smoothed over.
- **Persona and formatting constraints** — restrictive phrasing ("never," "always," "do not") is followed more literally; checking it still produces the intended behavior rather than an over-correction.

Don't re-tune by trial and error against the old prompt. Use the **[Nova Sonic 2.5 Prompt Engineering — Best Practices Guide](Nova_Sonic_2.5_Prompting_Guide.md)** in this folder — it covers the mental models behind these behavior shifts, prescriptive rules for system-prompt and tool-description authoring, and a review checklist to run before you ship the migrated prompt.

### If you're using LiveKit

**Upgrade to `livekit-plugins-aws` 1.8.5 or later.** This sets the plugin's default model to Nova 2 Sonic (`amazon.nova-2-sonic-v1:0`) and adds support for Nova 2.5 Sonic.

```bash
uv add "livekit-plugins-aws[realtime]>=1.8.5"
# or: pip install "livekit-plugins-aws[realtime]>=1.8.5"
```
The `[realtime]` extra is required specifically for Nova Sonic — installing the base package without it only gets you the Bedrock LLM / Polly / Transcribe plugins, not speech-to-speech. Also requires **Python 3.12+**, and `livekit-agents` `>=1.8`.

**Auth** — set these three environment variables (`.env` file or your usual AWS credential mechanism):
```
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>
AWS_REGION=<your-aws-region>
```

**To use Nova 2.5 Sonic specifically**, use the `with_nova_sonic_2_5()` constructor:
```python
from livekit.plugins import aws

model = aws.realtime.RealtimeModel.with_nova_sonic_2_5(
    voice="tiffany",
    turn_detection="MEDIUM",
)
session = AgentSession(llm=model)
```
This points at the `amazon.nova-2-5-sonic` Bedrock model ID — a distinct ID from the default `amazon.nova-2-sonic-v1:0` Nova 2 Sonic uses, so you have to opt in explicitly; just upgrading the package doesn't switch you to 2.5 on its own. If `amazon.nova-2-5-sonic` isn't directly invokable in your account/region, try the cross-region inference profile form, `us.amazon.nova-2-5-sonic`.

For comparison, the other two constructors:
```python
# Nova 2 Sonic (audio + text input) — the plugin's default as of 1.8.5
model = aws.realtime.RealtimeModel.with_nova_sonic_2(voice="tiffany", turn_detection="MEDIUM")

# Nova Sonic 1.0 (audio-only, original model)
model = aws.realtime.RealtimeModel.with_nova_sonic_1(voice="matthew")
```

**Known gotchas:**
- Nova Sonic needs a duplex-capable HTTP transport (the AWS CRT client), not `aiohttp` — a version mismatch here has caused import/transport errors in practice.
- If AWS credentials are misconfigured, the plugin doesn't raise an exception — it silently hangs on `receive()` with no events, rather than failing fast. Verify credentials separately if a session seems to connect but never produces output.
- Nova Sonic (any version) is only available in `us-east-1`, `us-west-2`, `eu-north-1`, and `ap-northeast-1` — same regions as the rest of this guide.

Once upgraded, migration is otherwise the same as described in [How to start](#how-to-start) above, just expressed as calling `with_nova_sonic_2_5()` instead of the default constructor.

### If you're using Pipecat

The Bedrock/Nova Sonic transport lives in `AWSNovaSonicLLMService`, under the `aws-nova-sonic` extra:
```bash
pip install "pipecat-ai[aws-nova-sonic]"
```

**On any version, you can already point at Nova 2.5 Sonic explicitly** — `model` is a plain string parameter with no version allowlist, so passing `model="amazon.nova-2-5-sonic"` (via `AWSNovaSonicLLMService.Settings`) works even on older releases.

**Upgrade to `pipecat-ai>=1.13.0`** if you want Nova 2.5 Sonic as the *default* without passing `model` explicitly:
```python
from pipecat.services.aws.nova_sonic.llm import AWSNovaSonicLLMService

llm = AWSNovaSonicLLMService(
    access_key_id=...,
    secret_access_key=...,
    region="us-east-1",
    voice_id="matthew",
    # model left unset — defaults to amazon.nova-2-5-sonic as of 1.13.0
)
```
As of 1.13.0, `AWSNovaSonicLLMService`'s default model changed from `amazon.nova-2-sonic-v1:0` to `amazon.nova-2-5-sonic`.

### If you're using Strands

**Upgrade to the latest `strands-agents` (1.59.0 or newer).** This gets you Bidi Agents, Strands' GA voice-agent API (`strands.bidi.*`), released Oct 5, 2026 alongside Nova 2.5 Sonic itself.

```bash
pip install "strands-agents[bidi,bidi-io,bidi-pyaudio]"
```
This pulls in Nova Sonic support plus audio I/O helpers. You'll also need the PortAudio system library installed separately for local microphone/speaker access. Python 3.12+ is required.

**Usage:**
```python
from strands.bidi.agent import BidiAgent
from strands.bidi.models import BedrockNovaSonicModel

model = BedrockNovaSonicModel(model_id="amazon.nova-2-5-sonic")

agent = BidiAgent(
    model=model,
    system_prompt="You are a helpful voice assistant. Keep responses concise and conversational.",
)
```

**Session length:** Nova 2.5 Sonic enforces an 8-minute session limit. `BidiAgent` can restart the underlying session in the background before that cap is hit, so a conversation can continue indefinitely without the caller noticing — check Strands' Bidi Agent docs for how to configure this if you need sessions longer than 8 minutes.

Once upgraded, migration is otherwise the same model-ID swap described in [How to start](#how-to-start) above.
