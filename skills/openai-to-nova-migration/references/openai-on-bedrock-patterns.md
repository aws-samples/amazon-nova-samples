# OpenAI on Amazon Bedrock → Nova 2 Lite

This covers the case where the customer already runs **OpenAI models hosted on
Amazon Bedrock** (not `api.openai.com`) and wants to migrate to Amazon Nova 2
Lite — a common step when a team is running a multi-model bake-off on Bedrock.

The migration is usually **lower-effort than migrating from the OpenAI API**,
because auth, Region, and billing are already AWS-native. What changes is the
API surface and, for some models, the SDK.

> API surfaces and model IDs change frequently. Treat the tables below as a
> starting point and confirm current model IDs, endpoints, and supported APIs
> against the [Bedrock OpenAI model cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-openai.html)
> or a live web search before finalizing a migration.

---

## The critical fork: two classes of OpenAI-on-Bedrock model

How the customer's model is invoked determines how hard the migration is.
Identify the model first.

| Class | Example model IDs | APIs supported | Endpoint |
|-------|-------------------|----------------|----------|
| **Proprietary (GPT-5.x)** | `openai.gpt-5.5`, `openai.gpt-5.4` | **Responses API only** | `bedrock-mantle` (OpenAI-compatible) |
| **Open weights (gpt-oss)** | `openai.gpt-oss-120b-1:0`, `openai.gpt-oss-20b-1:0` (runtime); `openai.gpt-oss-120b`, `openai.gpt-oss-20b` (mantle) | **Converse, InvokeModel, Responses, Chat Completions** | both `bedrock-runtime` and `bedrock-mantle` |

Two implications:

1. **gpt-oss customers may already be on Converse.** If so, migrating to Nova is
   close to trivial — change the `modelId` and adjust the prompt. See "Path A" below.
2. **GPT-5.5 / GPT-5.4 customers are on the Responses API** through an
   OpenAI-compatible `bedrock-mantle` endpoint. Migrating to Nova means moving
   from that Responses shape onto the native Converse API. See "Path B" below.

> Model IDs differ by endpoint. On `bedrock-runtime` (Converse/InvokeModel) the
> gpt-oss IDs carry a version suffix (`openai.gpt-oss-120b-1:0`); on
> `bedrock-mantle` (Responses/Chat Completions) they do not (`openai.gpt-oss-120b`).
> Nova 2 Lite is always `us.amazon.nova-2-lite-v1:0` on `bedrock-runtime`.

---

## How OpenAI-on-Bedrock is invoked (source shapes to detect)

### Responses API via bedrock-mantle (GPT-5.5/5.4, and gpt-oss if chosen)

Detected by an OpenAI SDK client pointed at a Bedrock base URL, or the
`BedrockOpenAI` client:

```python
# Option 1: standard OpenAI SDK + Bedrock base URL
from openai import OpenAI
client = OpenAI(
    base_url="https://bedrock-mantle.us-east-2.api.aws/openai/v1",
    api_key="<BEDROCK_API_KEY>",   # a Bedrock API key, not an OpenAI key
)
response = client.responses.create(
    model="openai.gpt-5.5",
    input=[
        {"role": "developer", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize cloud computing."},
    ],
    reasoning={"effort": "medium"},
    text={"verbosity": "low"},
)
print(response.output_text)

# Option 2: dedicated BedrockOpenAI client (derives the regional base URL)
from openai import BedrockOpenAI
client = BedrockOpenAI(aws_region="us-east-2")   # auth via AWS_BEARER_TOKEN_BEDROCK
response = client.responses.create(model="openai.gpt-5.5", input="...")
```

Notes that matter for migration:
- Auth is a **Bedrock API key** (`AWS_BEARER_TOKEN_BEDROCK`) or the AWS credential
  chain via a refreshable token provider — already AWS-native, no OpenAI key.
- Message roles are `developer` and `user` (Responses style), and input is an
  `input` array, not `messages`.
- Reasoning is a `reasoning={"effort": ...}` object; verbosity is `text={"verbosity": ...}`.
- GPT-5.5 uses a non-standard path: `.../openai/v1/responses` on `bedrock-mantle`.

### Chat Completions via bedrock-mantle (gpt-oss only)

```python
from openai import OpenAI
client = OpenAI(base_url="https://bedrock-mantle.us-east-2.api.aws/v1", api_key="...")
response = client.chat.completions.create(
    model="openai.gpt-oss-120b",
    messages=[{"role": "user", "content": "..."}],
)
```

### Converse / InvokeModel via bedrock-runtime (gpt-oss only)

```python
import boto3
client = boto3.client("bedrock-runtime", region_name="us-east-1")
response = client.converse(
    modelId="openai.gpt-oss-120b-1:0",
    messages=[{"role": "user", "content": [{"text": "..."}]}],
)
```

---

## Path A — gpt-oss already on Converse → Nova (trivial)

If the customer calls `client.converse(modelId="openai.gpt-oss-120b-1:0", ...)`,
the migration is almost entirely a `modelId` change:

```python
# Before
response = client.converse(
    modelId="openai.gpt-oss-120b-1:0",
    messages=[{"role": "user", "content": [{"text": "..."}]}],
    inferenceConfig={"temperature": 0.7, "maxTokens": 1024},
)

# After
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "..."}]}],
    inferenceConfig={"temperature": 0.7, "maxTokens": 1024},
)
```

Then apply the standard Nova adjustments from `SKILL.md`:
- Prompt: add `##Section##` structure (Step 4).
- Reasoning: if the gpt-oss call passed a reasoning param, map it to Nova's
  `additionalModelRequestFields.reasoningConfig` and apply the high-effort rule.
- Tools / structured output: same `toolSpec` / tool-forcing patterns as the main
  workflow — no change from the OpenAI-API path.

This is the easiest migration the skill handles. Call that out to the user.

## Path B — Responses API (GPT-5.x / gpt-oss on mantle) → Nova Converse

Here the source uses `client.responses.create(...)` against a `bedrock-mantle`
base URL. The plumbing that is *already done* (vs the api.openai.com path):
auth is AWS-native, Region is set, billing is consolidated. What still changes:

| From (Bedrock Responses) | To (Nova Converse) |
|--------------------------|--------------------|
| `OpenAI(base_url=...)` / `BedrockOpenAI(...)` | `boto3.client("bedrock-runtime")` |
| `client.responses.create(...)` | `client.converse(...)` |
| `model="openai.gpt-5.5"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `input=[...]` array | `messages=[...]` with typed content blocks |
| role `developer` (system-equivalent) | extract to `system=[{"text": ...}]` |
| role `user` with string content | `{"role": "user", "content": [{"text": ...}]}` |
| `reasoning={"effort": "low"/"medium"/"high"}` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": ...}}` |
| `text={"verbosity": "low"}` | no direct equivalent — express in the prompt's `##Response style and format requirements:##` |
| `tools=[...]` (Responses tools) | `toolConfig={"tools": [{"toolSpec": ...}]}` |
| `max_output_tokens` | `inferenceConfig.maxTokens` |
| `response.output_text` | `response["output"]["message"]["content"][0]["text"]` |

The `developer` → `system` extraction is the same idea as the main workflow's
`role: "system"` extraction — just a different source role name. Everything
downstream (content blocks, `inferenceConfig` nesting, reasoning high-effort
rule, `##Section##` prompt formatting, tool-forcing) is identical to the main
`SKILL.md` workflow.

### Example — GPT-5.5 (Responses) → Nova 2 Lite (Converse)

```python
# Before — GPT-5.5 on Bedrock via the Responses API
from openai import OpenAI
client = OpenAI(base_url="https://bedrock-mantle.us-east-2.api.aws/openai/v1",
                api_key="<BEDROCK_API_KEY>")
response = client.responses.create(
    model="openai.gpt-5.5",
    input=[
        {"role": "developer", "content": "You are a senior architect. Be concise."},
        {"role": "user", "content": "Compare microservices and monoliths."},
    ],
    reasoning={"effort": "medium"},
)
print(response.output_text)

# After — Nova 2 Lite via Converse
import boto3
# Preserve the source Region — the customer already chose it for data residency
# and billing. Confirm Nova 2 Lite is available there before committing.
client = boto3.client("bedrock-runtime", region_name="us-east-2")
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a senior architect. Be concise."}],   # was `developer`
    messages=[
        {"role": "user", "content": [{"text": (
            "##Task Summary:##\n"
            "Compare microservices and monoliths."
        )}]}
    ],
    inferenceConfig={"temperature": 0.7},
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}
    },
)
# With reasoning enabled, a reasoningContent block can precede the text block.
# Select the text block explicitly rather than indexing [0].
text = next(b["text"] for b in response["output"]["message"]["content"] if "text" in b)
print(text)
```

> **Preserve the source Region.** Carry the customer's existing `region_name`
> onto the boto3 client rather than relying on the ambient default. The Region
> was chosen for data residency and billing; only change it if Nova 2 Lite is not
> available there. The `developer` role maps to Nova's `system`; note OpenAI
> treats `developer` as higher-priority than `system`, but for Nova both collapse
> to the single `system` parameter.

---

## Reasoning effort: Bedrock OpenAI vs Nova

GPT-5.5/5.4 on Bedrock take `reasoning={"effort": "low"/"medium"/"high"}` (GPT-5.4
also has a `none` default — set effort explicitly). As with the api.openai.com
path, do **not** map the effort name across by number. Present Nova's
`low`/`medium`/`high` options and let the user choose, defaulting to `low`. The
high-effort rule still applies: at Nova `high`, omit `inferenceConfig` entirely
and set `read_timeout=3600`. See the main `SKILL.md` Step 2 precedence rule.

## What the customer keeps (why this path is lower-effort)

- **Auth** — already AWS (Bedrock API key or credential chain). No key rotation change.
- **Region / data residency** — already chosen; keep the same Region if Nova is available there.
- **Billing** — already consolidated in the AWS account.
- **IAM / networking** — unchanged.

The migration is therefore mostly about the **API call shape and the prompt**,
not the surrounding infrastructure. Frame it that way for the user.

## Model availability notes (verify against live docs)

- **GPT-5.5:** Responses API only, `bedrock-mantle`, 272K context. US East (Ohio),
  US East (N. Virginia).
- **GPT-5.4:** Responses API only, `bedrock-mantle`. US East (Ohio), US West
  (Oregon), and GovCloud.
- **gpt-oss-120b / 20b:** Converse + InvokeModel + Responses + Chat Completions;
  128K context, 16K max output; broad Regional availability.
- **Nova 2 Lite:** Converse (and other APIs) on `bedrock-runtime`; confirm the
  target Region supports Nova 2 Lite before committing.

Always confirm current model IDs, Regions, and API support from the
[Bedrock OpenAI model cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-openai.html)
and the [OpenAI-on-Bedrock guide](https://developers.openai.com/api/docs/guides/amazon-bedrock).
