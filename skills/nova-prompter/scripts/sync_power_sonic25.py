#!/usr/bin/env python3
"""Regenerate powers/nova-sonic25-prompt/POWER.md from
plugins/nova-sonic25-prompting/skills/nova-sonic25-prompt/SKILL.md.

Scoped to this one skill/power pair only -- not a generic multi-skill sync
tool. The original scripts/sync_powers.py (referenced by the GENERATED
banner this script also writes) isn't present in this checkout; this script
reproduces the one transform that was already baked into the committed
POWER.md, inferred by diffing it against its SKILL.md source:

  - Frontmatter: SKILL.md's simple (name, description, argument-hint) becomes
    POWER.md's richer form (quoted name, displayName, "skill" -> "power" in
    the description, keywords, author). displayName/keywords/author aren't
    derivable from SKILL.md, so they're fixed constants below -- update them
    here if they ever need to change.
  - Insert the GENERATED banner right after frontmatter.
  - Body substitutions: $ARGUMENTS -> "the provided input"; /nova-sonic25-prompt,
    /nova1-prompt, /nova2-prompt -> "<name> power".
  - Append the static Privacy/License trailer sections, which are
    Kiro-power boilerplate with no SKILL.md equivalent.

Usage:
    python3 scripts/sync_power_sonic25.py
Run from anywhere; paths are resolved relative to this script's location.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = ROOT / "plugins/nova-sonic25-prompting/skills/nova-sonic25-prompt/SKILL.md"
POWER_PATH = ROOT / "powers/nova-sonic25-prompt/POWER.md"

DISPLAY_NAME = "Nova Sonic 2.5 Prompt Optimizer"
KEYWORDS = ["nova", "nova-sonic", "amazon nova", "voice agent", "prompt", "prompt engineering", "bedrock"]
AUTHOR = "Amazon Nova"

GENERATED_BANNER = (
    "<!-- GENERATED from plugins/nova-sonic25-prompting/skills/nova-sonic25-prompt/SKILL.md "
    "by scripts/sync_power_sonic25.py -- do not edit by hand. Edit the SKILL.md and re-run the script. -->"
)

TRAILER = """
---

## Privacy and telemetry

This power does not collect telemetry. All processing happens inside your local Kiro session — no prompt content, output, or usage data is sent to AWS, Amazon, or any third party by this power. Your Kiro session may, separately, send the prompt content to whichever model your Kiro session is configured to use.

## License

MIT-0 (MIT No Attribution). This power is distributed as part of [aws-samples/amazon-nova-samples](https://github.com/aws-samples/amazon-nova-samples); the repository's root `LICENSE` file applies. The power packages prompt-engineering guidance generalized from field work on Nova Sonic 2.5 voice agents. It does not bundle any MCP servers, so no third-party MCP licenses apply.
"""


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError("SKILL.md has no frontmatter block")
    raw_fm, body = m.group(1), m.group(2)
    fields = {}
    for line in raw_fm.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, body


def build_power_frontmatter(skill_fields: dict) -> str:
    name = skill_fields["name"]
    description = skill_fields["description"]
    description = description.replace(
        "Use this skill when", "Use this power when"
    ).replace(
        "use /nova1-prompt or /nova2-prompt instead", "use nova1-prompt or nova2-prompt power instead"
    )
    # Drop the trailing sentence about scaffolding app code -- not present in
    # the committed POWER.md's description (powers don't scaffold either,
    # but that sentence was apparently cut for brevity there; preserve as-is).
    description = re.sub(
        r"\s*Do NOT use this to scaffold.*?prompt content only\.$", "", description
    )
    keywords_str = ", ".join(f'"{k}"' for k in KEYWORDS)
    if '"' in description:
        raise ValueError("description contains a double quote; update the YAML-quoting logic before proceeding")
    return (
        "---\n"
        f'name: "{name}"\n'
        f'displayName: "{DISPLAY_NAME}"\n'
        f'description: "{description}"\n'
        f"keywords: [{keywords_str}]\n"
        f'author: "{AUTHOR}"\n'
        "---\n"
    )


def transform_body(body: str) -> str:
    body = body.replace("`$ARGUMENTS`", "`the provided input`")
    body = body.replace("/nova-sonic25-prompt", "nova-sonic25-prompt power")
    body = body.replace("/nova1-prompt", "nova1-prompt power")
    body = body.replace("/nova2-prompt", "nova2-prompt power")
    return body


def main() -> None:
    skill_text = SKILL_PATH.read_text()
    fields, body = split_frontmatter(skill_text)

    power_frontmatter = build_power_frontmatter(fields)
    power_body = transform_body(body)

    power_text = power_frontmatter + "\n" + GENERATED_BANNER + "\n" + power_body.rstrip("\n") + "\n" + TRAILER
    POWER_PATH.write_text(power_text)
    print(f"Wrote {POWER_PATH.relative_to(ROOT)} from {SKILL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
