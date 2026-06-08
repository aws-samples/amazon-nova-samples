#!/usr/bin/env python3
"""Deterministic tests for the nova-migration skill — no Claude Code required.

What this validates (without an LLM):
  1. Structure/lint   — JSON valid, SKILL frontmatter, no dead reference links, marketplace paths.
  2. Router logic     — encodes the source-detection rules and asserts each sample snippet routes
                        to the correct sub-skill (gemini vs claude vs claude-on-bedrock vs unknown).
  3. Code examples    — every "Nova/After" Python block in the references parses as valid Python
                        and obeys the nova-target invariants (typed content blocks; inference params
                        nested in inferenceConfig, not at the top level of converse()).

What it CANNOT prove: that an LLM faithfully follows the skill. For that, run with --live to send a
real Gemini/Claude snippet to Bedrock Nova and eyeball the migration (needs AWS creds + model access).

Usage:
    python3 test_skill.py            # offline tests (1-3)
    python3 test_skill.py --live     # also run the live Bedrock migration smoke test
"""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))          # .../skills/nova-migration
REPO = os.path.abspath(os.path.join(ROOT, "..", ".."))     # repo root

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    mark = "ok  " if ok else "FAIL"
    line = f"  [{mark}] {name}"
    if detail and not ok:
        line += f"  -- {detail}"
    print(line)


# ---------------------------------------------------------------------------
# 1. Structure / lint
# ---------------------------------------------------------------------------
def test_structure():
    print("\n== 1. Structure / lint ==")

    # JSON files parse
    for rel in [".claude-plugin/marketplace.json", "skills/nova-migration/.claude-plugin/plugin.json"]:
        p = os.path.join(REPO, rel)
        try:
            json.load(open(p)); check(f"json valid: {rel}", True)
        except Exception as e:
            check(f"json valid: {rel}", False, str(e))

    # marketplace lists nova-migration and its source dir exists
    mp = json.load(open(os.path.join(REPO, ".claude-plugin/marketplace.json")))
    names = {p["name"]: p["source"].lstrip("./") for p in mp["plugins"]}
    check("marketplace lists nova-migration", "nova-migration" in names)
    if "nova-migration" in names:
        src = os.path.join(REPO, names["nova-migration"])
        check("marketplace source dir exists", os.path.isdir(src), src)
    # old standalone skills are gone
    for dead in ["skills/gemini-to-nova-migration", "skills/claude-to-nova-migration"]:
        check(f"removed old skill: {dead}", not os.path.isdir(os.path.join(REPO, dead)))

    # every SKILL.md has name + description frontmatter
    skills = []
    for dirpath, _, files in os.walk(ROOT):
        if "SKILL.md" in files:
            skills.append(os.path.join(dirpath, "SKILL.md"))
    check("found 3 SKILL.md (router + gemini + claude)", len(skills) == 3, f"found {len(skills)}")
    for sk in skills:
        rel = os.path.relpath(sk, ROOT)
        txt = open(sk).read()
        m = re.match(r"^---\n(.*?)\n---", txt, re.S)
        if not m:
            check(f"frontmatter: {rel}", False, "no --- block"); continue
        fm = m.group(1)
        check(f"frontmatter name+desc: {rel}",
              bool(re.search(r"^name:\s*\S+", fm, re.M)) and bool(re.search(r"^description:\s*\S+", fm, re.M)))

    # the shared target exists and is referenced by both source skills
    target = os.path.join(ROOT, "references", "nova-target.md")
    check("shared references/nova-target.md exists", os.path.isfile(target))
    for sub in ["gemini", "claude"]:
        sk = os.path.join(ROOT, sub, "SKILL.md")
        check(f"{sub} SKILL points to ../references/nova-target.md", "../references/nova-target.md" in open(sk).read())

    # no dead reference links in any SKILL.md
    for sk in skills:
        base = os.path.dirname(sk)
        for ref in re.findall(r"(?:\.\./)?references/[a-z0-9-]+\.md", open(sk).read()):
            tgt = os.path.normpath(os.path.join(base, ref))
            check(f"ref exists ({os.path.relpath(sk, ROOT)} -> {ref})", os.path.isfile(tgt), tgt)


# ---------------------------------------------------------------------------
# 2. Router logic — encode the detection rules from the top-level SKILL.md table
# ---------------------------------------------------------------------------
def route(source_code):
    """Mirror the router table in nova-migration/SKILL.md. Returns a route label."""
    s = source_code
    gemini = bool(re.search(r"from google import genai|import google\.generativeai|"
                            r"client\.models\.generate_content|client\.interactions\.create", s))
    anthropic_sdk = bool(re.search(r"from anthropic import|client\.messages\.create|AnthropicBedrock", s))
    claude_on_bedrock = bool(re.search(r'modelId\s*=\s*["\']anthropic\.claude', s))
    if gemini:
        return "gemini"
    if anthropic_sdk:
        return "claude:messages-api"
    if claude_on_bedrock:
        return "claude:on-bedrock"
    return "unknown"


def test_router():
    print("\n== 2. Router logic ==")
    cases = [
        ("from google import genai\nclient.models.generate_content(model='gemini-2.5-flash')", "gemini"),
        ("import google.generativeai as genai\nm.generate_content('hi')", "gemini"),
        ("client.interactions.create(model='gemini-3.5-flash', input='hi')", "gemini"),
        ("from anthropic import Anthropic\nclient.messages.create(model='claude-3-5-haiku')", "claude:messages-api"),
        ("from anthropic import AnthropicBedrock\nc = AnthropicBedrock()", "claude:messages-api"),
        ('resp = client.converse(modelId="anthropic.claude-3-5-haiku-20241022-v1:0")', "claude:on-bedrock"),
        ("import openai\nopenai.ChatCompletion.create(model='gpt-4o')", "unknown"),
    ]
    for src, expected in cases:
        got = route(src)
        check(f"route -> {expected}: {src.splitlines()[0][:48]!r}", got == expected, f"got {got}")


# ---------------------------------------------------------------------------
# 3. Code examples — validate the "Nova/After" Python blocks
# ---------------------------------------------------------------------------
def iter_python_blocks(md_path):
    """Yield fenced ```python blocks. Uses linear scan instead of non-greedy regex to avoid
    stopping at embedded ``` inside triple-quoted strings (e.g., JSON schemas in prompts)."""
    txt = open(md_path).read()
    pattern = r"```python\n"
    pos = 0
    while True:
        start_match = re.search(pattern, txt[pos:])
        if not start_match:
            break

        block_start = pos + start_match.end()
        remaining = txt[block_start:]

        # Find closing fence: ``` at line boundary
        close_match = re.search(r"(^|\n)```", remaining)
        if not close_match:
            break

        # Extract block (exclude leading newline if present)
        if close_match.group(0).startswith('\n'):
            block = remaining[:close_match.start() + 1][:-1]
        else:
            block = remaining[:close_match.start()]

        yield block
        pos = block_start + close_match.end()


def looks_like_nova(block):
    return "converse" in block or "bedrock-runtime" in block or "nova-2-lite" in block


def nova_portion(block):
    """Combined before/after snippets separate the two with a `# Nova` comment. Only the Nova
    half should obey the Nova invariants (the 'before' half is legitimate source code)."""
    m = re.search(r"#\s*Nova.*?\n", block)
    return block[m.end():] if m else block


def is_illustrative(block):
    """Skip the parse check for blocks that aren't meant to be standalone-valid Python:
       - bare `...` elisions (e.g. converse(modelId=..., ...))
       - inner ``` fences (inline JSON schema inside a triple-quoted prompt) that defeat the regex.
       - odd number of triple quotes (indicates truncated block / embedded fence problem)."""
    if bool(re.search(r"(^|\W)\.\.\.(\W|$)", block)) or "```" in block or "…" in block:
        return True
    # Detect truncation: odd triple-quote count means the block is incomplete
    if block.count('"""') % 2 != 0:
        return True
    return False


def test_code_examples():
    print("\n== 3. Code examples (Nova/After blocks) ==")
    ref_files = []
    for dirpath, _, files in os.walk(ROOT):
        for f in files:
            if f.endswith(".md"):
                ref_files.append(os.path.join(dirpath, f))

    total_nova, parsed, skipped = 0, 0, 0
    for md in sorted(ref_files):
        rel = os.path.relpath(md, ROOT)
        for i, block in enumerate(iter_python_blocks(md)):
            if not looks_like_nova(block):
                continue  # only scrutinize the Nova-side examples
            total_nova += 1
            tag = f"{rel} block#{i}"
            nova = nova_portion(block)

            # 3a. parses as Python — skip blocks that are deliberately illustrative/elided.
            if is_illustrative(block):
                skipped += 1
            else:
                try:
                    ast.parse(block)
                    parsed += 1
                except SyntaxError as e:
                    check(f"py-parse: {tag}", False, f"line {e.lineno}: {e.msg}")

            # 3b. invariant (Nova half only): no top-level max_tokens/temperature on converse().
            if "converse(" in nova:
                bad = re.search(r"\bmax_tokens\s*=", nova) or re.search(r"^\s*temperature\s*=", nova, re.M)
                check(f"invariant no-top-level-inference-params: {tag}", not bad,
                      "found max_tokens=/temperature= outside inferenceConfig")
            # 3c. invariant (Nova half only): message content is a list of typed blocks, not a string.
            if '"role"' in nova and "content" in nova:
                bad = re.search(r'"content"\s*:\s*"', nova)
                check(f"invariant typed-content-blocks: {tag}", not bad,
                      'found "content": "string" (must be a list of typed blocks)')

    fully = total_nova - skipped
    check(f"all parseable Nova blocks parse ({parsed}/{fully})", parsed == fully)
    print(f"     ({total_nova} Nova blocks scrutinized; {skipped} illustrative/elided skipped for parse)")


# ---------------------------------------------------------------------------
# 4. (opt-in) Live Bedrock smoke test — proves the host LLM can act on the skill
# ---------------------------------------------------------------------------
def test_live():
    print("\n== 4. Live Bedrock migration smoke test ==")
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        check("boto3 available", False, "pip install boto3 to run --live"); return

    model_id = os.environ.get("NOVA_MODEL_ID", "us.amazon.nova-2-lite-v1:0")
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region, config=Config(read_timeout=120))

    # Feed the skill content + a source snippet, ask for a migration, check the output shape.
    skill = open(os.path.join(ROOT, "references", "nova-target.md")).read()
    gem_skill = open(os.path.join(ROOT, "gemini", "SKILL.md")).read()
    source = ("from google import genai\n"
              "client = genai.Client()\n"
              "r = client.models.generate_content(model='gemini-2.5-flash',\n"
              "    contents='Summarize cloud computing in one sentence.',\n"
              "    config=types.GenerateContentConfig(system_instruction='Be concise', temperature=0.2))")
    system = [{"text": "You are a migration assistant. Follow the provided skill exactly. "
                       "Output ONLY the migrated Python code in a single ```python block."}]
    user = (f"# SKILL (gemini source guide)\n{gem_skill}\n\n# SKILL (nova target)\n{skill}\n\n"
            f"# MIGRATE THIS to Nova 2 Lite (use modelId us.amazon.nova-2-lite-v1:0):\n```python\n{source}\n```")
    try:
        resp = client.converse(
            modelId=model_id,
            system=system,
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 1200},
        )
    except Exception as e:
        check("bedrock converse call", False, f"{type(e).__name__}: {e}"); return
    out = resp["output"]["message"]["content"][0]["text"]
    print("\n----- model output -----\n" + out + "\n------------------------")
    code = "".join(re.findall(r"```python\n(.*?)```", out, re.S)) or out
    check("output calls boto3 converse", "converse(" in code)
    check("output targets nova-2-lite", "nova-2-lite" in code)
    check("output nests inferenceConfig", "inferenceConfig" in code)
    check("output drops google genai SDK", "genai" not in code)
    if "converse(" in code:
        check("output keeps inference params out of top-level", not re.search(r"\bmax_tokens\s*=", code))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_structure()
    test_router()
    test_code_examples()
    if "--live" in sys.argv:
        test_live()

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print("  - " + f)
        sys.exit(1)
    print("ALL GREEN")
