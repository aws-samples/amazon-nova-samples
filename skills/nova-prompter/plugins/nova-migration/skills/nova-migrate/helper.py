"""Migration helper — provider-dispatch layer for /nova-migrate.

Subcommands:
  invoke  — single prompt → one model → JSON result
  batch   — prompt + test set → model → JSONL results (parallel)
  judge   — rubric + baseline + candidate → per-test scores JSONL

Model IDs:
  bedrock:   "anthropic.claude-3-5-sonnet-20240620-v1:0"
             "us.amazon.nova-lite-v1:0"
             "meta.llama3-1-70b-instruct-v1:0"
  openai:    "openai:gpt-4o-mini"          (needs OPENAI_API_KEY)
  anthropic: "anthropic:claude-sonnet-4-5" (needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


# ── provider dispatch ────────────────────────────────────────────────────────

@dataclass
class ModelRef:
    provider: str
    model_id: str


def parse_model(spec: str) -> ModelRef:
    if spec.startswith("openai:"):
        return ModelRef("openai", spec.split(":", 1)[1])
    if spec.startswith("anthropic:"):
        return ModelRef("anthropic", spec.split(":", 1)[1])
    return ModelRef("bedrock", spec)


def _require_env(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        sys.exit(
            f"error: {var} is not set. Either export it, switch to a Bedrock "
            f"model, or re-run with --baseline-from-tests."
        )
    return val


def call_model(
    model: ModelRef,
    system: str,
    user: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Return {output, usage, latency_ms, stop_reason}. Dispatches by provider."""
    t0 = time.perf_counter()
    if model.provider == "bedrock":
        result = _call_bedrock(model.model_id, system, user, max_tokens, temperature)
    elif model.provider == "openai":
        result = _call_openai(model.model_id, system, user, max_tokens, temperature)
    elif model.provider == "anthropic":
        result = _call_anthropic(model.model_id, system, user, max_tokens, temperature)
    else:
        sys.exit(f"error: unknown provider '{model.provider}'")
    result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return result


def _call_bedrock(
    model_id: str, system: str, user: str, max_tokens: int, temperature: float
) -> dict[str, Any]:
    import boto3  # noqa: WPS433
    from botocore.config import Config

    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 5, "mode": "adaptive"}),
    )
    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    resp = client.converse(**kwargs)
    output_text = "".join(
        block.get("text", "")
        for block in resp["output"]["message"]["content"]
        if "text" in block
    )
    return {
        "output": output_text,
        "usage": resp.get("usage", {}),
        "stop_reason": resp.get("stopReason"),
    }


def _call_openai(
    model_id: str, system: str, user: str, max_tokens: int, temperature: float
) -> dict[str, Any]:
    _require_env("OPENAI_API_KEY")
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit(
            "error: `openai` package not installed. Run: "
            "uv sync --extra migration-openai"
        )
    client = OpenAI()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    resp = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return {
        "output": resp.choices[0].message.content or "",
        "usage": resp.usage.model_dump() if resp.usage else {},
        "stop_reason": resp.choices[0].finish_reason,
    }


def _call_anthropic(
    model_id: str, system: str, user: str, max_tokens: int, temperature: float
) -> dict[str, Any]:
    _require_env("ANTHROPIC_API_KEY")
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit(
            "error: `anthropic` package not installed. Run: "
            "uv sync --extra migration-anthropic"
        )
    client = Anthropic()
    kwargs: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    output_text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    return {
        "output": output_text,
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        },
        "stop_reason": resp.stop_reason,
    }


# ── I/O helpers ──────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def read_tests(path: Path) -> list[dict[str, Any]]:
    """Load tests from JSONL or YAML. Schema in test_schema.md."""
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    if path.suffix in (".yaml", ".yml"):
        import yaml  # noqa: WPS433
        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, list) else data.get("tests", [])
    sys.exit(f"error: unsupported test file extension: {path.suffix}")


# ── judge prompt ─────────────────────────────────────────────────────────────

_JUDGE_SYSTEM = """\
You are a strict, fair LLM-as-judge. You score a candidate model's output
against a rubric and (when provided) a baseline output from a reference model.

Output ONLY a single JSON object, no prose, no markdown fence. Schema:

{
  "scores": { "<criterion_name>": <integer 1-5>, ... },
  "critique": "<one to three sentences explaining the scores, especially any regressions>"
}

Scale (apply per criterion):
  5 — fully meets the criterion; equal to or better than baseline
  4 — minor issue, still acceptable
  3 — noticeable gap vs baseline or criterion
  2 — significant regression or failure
  1 — criterion not met at all

Use the exact criterion names from the rubric. Do not invent new criteria.
"""


def _build_judge_user(
    rubric: str,
    test_input: Any,
    baseline_output: str | None,
    candidate_output: str,
) -> str:
    parts = [
        "## Rubric",
        rubric.strip(),
        "",
        "## Test input",
        json.dumps(test_input) if not isinstance(test_input, str) else test_input,
        "",
    ]
    if baseline_output is not None:
        parts += ["## Baseline output (reference model)", baseline_output, ""]
    parts += ["## Candidate output (Nova)", candidate_output, "", "Return the JSON object now."]
    return "\n".join(parts)


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_judge_response(raw: str) -> dict[str, Any]:
    """Tolerate judges that wrap JSON in prose or code fences."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_RE.search(raw)
        if not m:
            return {"scores": {}, "critique": f"parse_error: {raw[:200]}"}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"scores": {}, "critique": f"parse_error: {raw[:200]}"}


# ── subcommands ──────────────────────────────────────────────────────────────

def cmd_invoke(args: argparse.Namespace) -> None:
    model = parse_model(args.model)
    system = Path(args.system_file).read_text() if args.system_file else ""
    user = Path(args.input_file).read_text()
    result = call_model(model, system, user, args.max_tokens, args.temperature)
    payload = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(payload)
    else:
        print(payload)


def cmd_batch(args: argparse.Namespace) -> None:
    model = parse_model(args.model)
    system = Path(args.prompt_file).read_text()
    tests = read_tests(Path(args.tests))

    def run_one(i_t: tuple[int, dict[str, Any]]) -> dict[str, Any]:
        i, t = i_t
        test_id = t.get("id", f"t{i:03d}")
        user_input = t["input"] if isinstance(t["input"], str) else json.dumps(t["input"])
        try:
            r = call_model(model, system, user_input, args.max_tokens, args.temperature)
            return {"test_id": test_id, "input": t["input"], **r}
        except Exception as e:  # noqa: BLE001
            return {"test_id": test_id, "input": t["input"], "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(run_one, enumerate(tests)))
    write_jsonl(Path(args.out), results)
    print(f"wrote {len(results)} results → {args.out}", file=sys.stderr)


def cmd_judge(args: argparse.Namespace) -> None:
    rubric = Path(args.rubric).read_text()
    baseline = {r["test_id"]: r for r in read_jsonl(Path(args.baseline))}
    candidate = read_jsonl(Path(args.candidate))
    judge_model = parse_model(args.judge_model)

    def score_one(c: dict[str, Any]) -> dict[str, Any]:
        tid = c["test_id"]
        if "error" in c:
            return {"test_id": tid, "scores": {}, "critique": f"candidate_error: {c['error']}"}
        b = baseline.get(tid)
        baseline_out = b.get("output") if b else None
        user = _build_judge_user(rubric, c.get("input", ""), baseline_out, c.get("output", ""))
        try:
            r = call_model(judge_model, _JUDGE_SYSTEM, user, max_tokens=1024, temperature=0.0)
            parsed = _parse_judge_response(r["output"])
            return {"test_id": tid, **parsed}
        except Exception as e:  # noqa: BLE001
            return {"test_id": tid, "scores": {}, "critique": f"judge_error: {e}"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        scored = list(pool.map(score_one, candidate))
    write_jsonl(Path(args.out), scored)
    print(f"wrote {len(scored)} scores → {args.out}", file=sys.stderr)


# ── argparse wiring ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Nova migration helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("invoke", help="Single model call")
    pi.add_argument("--model", required=True)
    pi.add_argument("--system-file")
    pi.add_argument("--input-file", required=True)
    pi.add_argument("--out")
    pi.add_argument("--max-tokens", type=int, default=4096)
    pi.add_argument("--temperature", type=float, default=0.7)
    pi.set_defaults(func=cmd_invoke)

    pb = sub.add_parser("batch", help="Run prompt over a test set")
    pb.add_argument("--model", required=True)
    pb.add_argument("--prompt-file", required=True)
    pb.add_argument("--tests", required=True)
    pb.add_argument("--out", required=True)
    pb.add_argument("--max-tokens", type=int, default=4096)
    pb.add_argument("--temperature", type=float, default=0.7)
    pb.add_argument("--concurrency", type=int, default=4)
    pb.set_defaults(func=cmd_batch)

    pj = sub.add_parser("judge", help="LLM-as-judge scoring")
    pj.add_argument("--rubric", required=True)
    pj.add_argument("--baseline", required=True)
    pj.add_argument("--candidate", required=True)
    pj.add_argument("--out", required=True)
    pj.add_argument(
        "--judge-model",
        default="us.anthropic.claude-sonnet-4-6",
        help="Model used as the judge. Default: Claude Sonnet 4.6 on Bedrock.",
    )
    pj.add_argument("--concurrency", type=int, default=4)
    pj.set_defaults(func=cmd_judge)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
