# SkyLab Manufacturing Intelligence — Notebooks

A collection of runnable notebooks that walk through the **chat multi-agent graph** at
the center of this project: a Supervisor + 3 Specialist pattern built on
[Strands Agents](https://github.com/strands-agents/sdk-python), backed by Amazon
Bedrock, a managed Knowledge Base, Amazon Nova Multimodal Embeddings, and
Amazon Bedrock AgentCore (Gateway + Runtime).

These notebooks are a teaching companion to the full application in the repo
root. They import from **`mei_core`** — a self-contained **copy** of the real
agent code (`agents.py`, `tools.py`), orchestration (`stream_adapter.py`,
`impact_assessment.py`), and config that ships inside this folder at
[`mei_core/`](mei_core/). It's a faithful copy of what the running app uses (not
a reimplementation), vendored here so this `notebooks/` folder is **fully
self-contained and portable** — you can lift it into another repo and it still
runs, with no dependency on the parent application's `agent/` or `api/`
packages. The app continues to run on its own modules; the two are independent
copies. (To refresh the copy after changing the app, re-vendor `mei_core` from
the parent `agent/` + `api/services/`.)

> The human decides; the system assembles evidence. These agents never
> recommend or approve a substitution — they gather and present evidence.

## What the chat graph looks like

```
         ┌──────────────────────────────────────────────┐
engineer │  "Compare the RW3 0.06 against the RW 0.03"   │
query    └───────────────────────┬──────────────────────┘
                                 ▼
                   PLANNER  (Claude Haiku 5.5)
                   routing-only classifier, no tools
                   emits an ordered specialist plan
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
   🔍 CATALOG            🔬 EVALUATION            📚 KNOWLEDGE
   (Sonnet 5.5)          (Sonnet 5.5)            (Sonnet 5.5)
   discovery +           deterministic           datasheet/ICD facts
   KB retrieval          spec-fit + visual       + live web/EOL
          └──────────────────────┼──────────────────────┘
                                 ▼
                 SUPERVISOR  (Claude Opus 5.5)
                 synthesis — ONLY when 2+ specialists ran
                 (a single specialist's answer is returned as-is)
```

The planner picks *which* specialists run and *in what order*. Each specialist
has a narrow prompt and a focused toolset. The supervisor merges multiple
specialists into one answer — and is deliberately skipped when only one
specialist ran, to avoid a redundant Opus round trip.

## Notebooks

| Notebook | What it covers |
|---|---|
| [`01_multi_agent_graph_walkthrough.ipynb`](01_multi_agent_graph_walkthrough.ipynb) | The core graph end-to-end: build the planner + 3 specialists + supervisor, parse a routing plan, run a single-specialist query and a chained multi-specialist query, and see where synthesis is skipped vs. run. |
| [`02_specialist_tools_deep_dive.ipynb`](02_specialist_tools_deep_dive.ipynb) | The deterministic `@tool` functions each specialist wraps — `kb_search`, `filter_parts_by_spec`, `score_substitution_fit`, `compare_parts`, part-name resolution — run directly with no LLM so you can see the evidence layer the agents reason over. §7 then **reproduces the visual-signal code inline and runs it**: the Nova MME image embedding (`invoke_model`) and the `visual_similarity_score` body (cosine similarity + Claude Vision physical analysis). |
| [`03_streaming_and_gateway.ipynb`](03_streaming_and_gateway.ipynb) | How the graph is exposed to the UI: the SSE event stream (`routing` → `specialist_start` → `content_delta` → `synthesis` → `images` → `done`), the **real AgentCore Gateway call reproduced inline** (SigV4-signed MCP `tools/list` + `tools/call` for web search), a short contrast with the Integration Impact Assessment's **fixed** (non-planned) specialist chain, and a **deployment section** (the ARM64 `Dockerfile`, `docker buildx` + ECR push, Runtime execution-role IAM incl. `s3vectors:QueryVectors`, and the Cedar policy). |
| [`04_capabilities_showcase.ipynb`](04_capabilities_showcase.ipynb) | The **full demo value** in one notebook: every query type from the demo script run through the real agent, with answers and datasheet/photo images rendered inline — catalog discovery, the EOL→find→score chain with live web, text→visual retrieval, the compound image-in multimodal pipeline, a formal substitution memo, two-model visual similarity, and the complete free-exploration query menu. §4.1 also **reproduces the image-as-query retrieval inline** — the Nova MME embed + S3 Vectors `query_vectors` call that identifies a part from an uploaded chart. |
| [`05_evaluation.ipynb`](05_evaluation.ipynb) | **Measures the deployed agent with AgentCore Runtime Evaluations** — the managed service that scores the Runtime's real OTel traces with built-in LLM evaluators (GoalSuccessRate, Correctness, Helpfulness, Faithfulness, ResponseRelevance, Tool-Selection/Parameter Accuracy). Sends labeled traffic to the live Runtime, runs on-demand `Evaluation.run()` scoring (with judge explanations + a chart), grounds scoring in your own `ReferenceInputs` assertions (incl. the safety "must refuse to recommend" check), and shows the continuous online-config path to CloudWatch. **Requires a deployed Runtime.** |

Run them in order — each builds on the previous. `01` is the one to read first;
`04` is the one to run (or present) when you want to *see what the system does*;
`05` is the one that *measures* how well it does it.

## Prerequisites

- **An AWS account with Amazon Bedrock access in `us-east-1`**, with model access
  enabled for the models the graph uses:
  - `us.anthropic.claude-haiku-5-5` (planner)
  - `us.anthropic.claude-sonnet-5-5` (specialists)
  - `us.anthropic.claude-opus-5-5` (supervisor synthesis)
  - `amazon.nova-2-multimodal-embeddings-v1:0` (visual similarity / image-as-query)
- AWS credentials configured locally (`aws configure`, SSO, or an attached role)
  with `bedrock:InvokeModel` (and, for the Gateway/visual sections,
  `bedrock:Retrieve`, `bedrock-agentcore:InvokeGateway`, `s3vectors:QueryVectors`).
- Python 3.10+.

Everything the notebooks need ships **inside this folder** — nothing points at
the parent repo:

- **`mei_core/`** — the vendored agent + tools + orchestration (synthetic-only).
- **`data/synthetic-parts-data/`** — the bundled catalog (7 AnyCompany reaction
  wheels: specs, photos, datasheet pages + cropped charts, ICDs).
- **`demo-crops/`** — ready-made chart crops for the image-as-query demo (04).
- **`evals/queries.synthetic.json`** — the labeled query set used by 05.

The notebook setup cells put this folder on `sys.path`, `import mei_core`, and
point `PARTS_DATA_DIR` at the bundled catalog. Some cells also **reproduce key
code inline** (02 §7 Nova MME + visual similarity, 03 the Gateway call, 04 §4.1
S3 Vectors image-as-query) so you can read and run the mechanism directly; those
depend only on `boto3`/`numpy` + the bundled data.

The notebooks use a **single synthetic catalog** (AnyCompany) — there is no
dataset switching here; `mei_core` is deliberately synthetic-only.

The tool/evidence sections work with **no** Knowledge Base or Gateway
configured. The live Bedrock calls in `01`–`04` need Bedrock access (and the
S3 Vectors / Nova MME sections need those resources). **Notebook `05` is the
exception**: it evaluates the *deployed* agent, so it needs a live **AgentCore
Runtime** (`AGENTCORE_RUNTIME_ARN`) emitting traces — it does not run purely
locally.

## Setup

Because the folder is self-contained, you can run it from **inside
`notebooks/`** (or from a repo it's been copied into):

```bash
cd notebooks
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # Jupyter + the agent runtime deps (boto3, strands, numpy, matplotlib)

export BEDROCK_REGION=us-east-1
# PARTS_DATA_DIR is set automatically to the bundled catalog by each notebook's
# setup cell; no DATASET switch to configure — the notebooks are synthetic-only.

jupyter lab   # or: jupyter notebook
```

> The setup cells resolve this folder (wherever it lives) via
> `NB_DIR = Path.cwd() if (Path.cwd() / "mei_core").exists() else Path.cwd() / "notebooks"`,
> add it to `sys.path`, and `import mei_core`. That means launching Jupyter from
> **either** the repo root **or** from inside `notebooks/` works — the imports
> and the bundled `data/`, `demo-crops/`, `evals/` paths resolve the same way.

### Optional: route KB + web search through AgentCore Gateway

Notebook `03` shows the Gateway path. It's optional — without it, retrieval
falls back to a direct Bedrock `Retrieve` call (or local JSON in demo mode).

```bash
export AGENTCORE_GATEWAY_ID=<your-gateway-id>   # see agentcore/setup_web_search.py + setup_kb_target.py
```

## A note on cost and latency

Every specialist is a full agentic turn with its own reasoning latency. A
single-specialist query runs in a few seconds; a chained 3-specialist query
(e.g. *EOL check → find alternatives → score them*) can take 60–140 seconds and
makes several Bedrock calls. Start with the single-specialist examples.

Notebook `05` is the slowest and needs a **deployed AgentCore Runtime**
(`AGENTCORE_RUNTIME_ARN`). It sends a handful of queries to the Runtime, then
**waits ~90s for OTel traces to propagate to CloudWatch** before scoring —
evaluating a session too early returns *"no spans to evaluate."* Each managed
`Evaluation.run()` is itself LLM-powered (~1–3 min), so the full notebook runs
~12–18 minutes. It writes a scores JSON to the bundled `notebooks/evals/results/`,
plots a chart (needs `matplotlib`, already in `requirements.txt`), and leaves the
continuous online-config creation behind an opt-in flag (off by default).

## Relationship to the rest of the repo

- `mei_core/` is a **vendored copy** of the parent app's `agent/` + relevant
  `api/services/` modules — the same code the FastAPI backend and the deployed
  AgentCore Runtime run, copied here so the notebooks are portable. The copy is
  trimmed to be synthetic-only; otherwise it's faithful. Editing `mei_core/`
  does not affect the running app, and vice versa.
- The Integration Impact Assessment (`mei_core/impact_assessment.py`, a copy of
  `api/services/impact_assessment.py`) reuses the **same specialist factories**
  but runs them in a **fixed** order with no planner — it is *not* part of this
  planned chat graph. Notebook `03` contrasts the two briefly; the chat graph is
  the focus of this collection.

## License

Shared under the same license as the parent repository.
