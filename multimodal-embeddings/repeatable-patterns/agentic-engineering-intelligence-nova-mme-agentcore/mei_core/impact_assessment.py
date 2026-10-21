# ============================================================
# VENDORED COPY — do not edit here.
# This is a copy of api/services/impact_assessment.py from the parent SkyLab Manufacturing
# Intelligence app, vendored into notebooks/mei_core/ so the notebooks run
# standalone (e.g. when this folder is moved to another repo). The app
# still runs on its own agent/ + api/ modules; this is an independent copy.
# Intra-package imports were rewritten to be package-relative.
# To refresh: re-run the vendoring step (see notebooks/README.md).
# ============================================================

"""Integration Impact Assessment (IIA) service.

Runs a FIXED specialist chain (not supervisor-planned like chat) to produce
a formal Integration Impact Assessment document for a proposed part
substitution:

  1. Knowledge Specialist  -> pulls ICD/datasheet interface detail on both
     parts (pinout, command protocol, mechanical drawing references) that
     isn't captured in structured specs.json fields.
  2. Evaluation Specialist -> runs compare_parts (structured field delta)
     and check_qualification_status (qual gap) for the deterministic half
     of the assessment.
  3. Supervisor            -> synthesizes both into the six-section IIA
     document: interface, mechanical, electrical, thermal, qualification,
     supply chain.

The chain order is fixed because we already know what this task requires
(unlike chat, where the Supervisor dynamically plans routing). This reuses
the same create_* factory functions from agent/agents.py — no changes to
the existing agent module.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from .agents import create_evaluation_specialist, create_knowledge_specialist, create_supervisor
from .tools import _write_audit_entry, compare_parts, get_part_specs

# The IIA's prompts demand more output than typical chat turns: Knowledge is
# asked to report four detail categories for BOTH parts, Evaluation is asked
# to echo the FULL field-by-field comparison (not just differences), and the
# Supervisor must produce a rigid six-section document. None of the Agent()
# factories in agent/agents.py set an explicit max_tokens (they rely on
# Bedrock's per-model default), which is enough for open-ended chat turns but
# not always enough here — a response getting cut off mid-tool-call raises
# strands.types.exceptions.MaxTokensReachedException. Bump the ceiling only
# for this fixed chain, scoped via BedrockModel.update_config() after
# creation, so chat's specialist/supervisor behavior is untouched.
_SPECIALIST_MAX_TOKENS = 4096
_SYNTHESIS_MAX_TOKENS = 8192


def _with_max_tokens(agent, max_tokens: int):
    """Raise the output token ceiling on an already-created Strands Agent's
    underlying BedrockModel. Scoped to a single agent instance — does not
    affect the create_* factory defaults used elsewhere (e.g. chat)."""
    agent.model.update_config(max_tokens=max_tokens)
    return agent


IIA_SYNTHESIS_INSTRUCTIONS = """You are drafting a formal Integration Impact Assessment (IIA) for an aerospace \
engineering review package. An engineer is evaluating substituting a REFERENCE part with a CANDIDATE part.

You have been given:
1. Knowledge Specialist findings — ICD/datasheet interface detail (pinout, command protocol, mechanical drawing \
references, electrical interface specifics) for both parts.
2. Evaluation Specialist findings — a deterministic field-by-field spec comparison and qualification-standard check.

Write the IIA as a markdown document with EXACTLY these sections, in this order:

# Integration Impact Assessment

## 1. Interface Changes
Does the pinout change? Does the command protocol/frame format change? Do electrical interface signal types differ? \
Cite the ICD/datasheet detail from the Knowledge findings.

## 2. Mechanical Integration
Mounting pattern, mass delta (impact on mass budget / center of gravity), dimensional/envelope fit.

## 3. Electrical Integration
Voltage range, power draw delta (impact on power budget), bus interface compatibility.

## 4. Thermal Integration
Operating temperature range, power dissipation changes.

## 5. Qualification Delta
Qual standard differences. State plainly whether an equivalence review is required.

## 6. Supply Chain Impact
Lead time change, lifecycle/obsolescence risk change.

RULES:
- Base every claim on the Knowledge/Evaluation findings provided. Never invent pinout, protocol, or mechanical detail \
not present in the findings — if the ICD/datasheet detail wasn't found, say so explicitly in that section.
- Be factual and specific (cite actual values: voltages, masses, lead times) wherever the findings provide them.
- NEVER recommend, approve, or say the substitution "should" happen. Present findings only — the engineer decides.
- Do not add a summary/conclusion section beyond the six above.
- Do not offer to do additional work.
"""


def _part_ref(part_id: str) -> dict:
    """Build a {id, name, vendor} dict for a part, tolerating missing specs."""
    specs = get_part_specs(part_id)
    if isinstance(specs, dict) and "error" in specs:
        return {"id": part_id, "name": part_id, "vendor": "Unknown"}
    return {
        "id": part_id,
        "name": specs.get("name", part_id),
        "vendor": specs.get("vendor", "Unknown"),
    }


def run_integration_impact_assessment(reference_id: str, candidate_id: str) -> dict:
    """Run the fixed Knowledge -> Evaluation -> Supervisor chain and return
    a structured IIA result (dict matching IntegrationImpactResponse).

    Raises:
        ValueError: if either part_id is not found in the catalog.
    """
    ref_specs = get_part_specs(reference_id)
    if isinstance(ref_specs, dict) and "error" in ref_specs:
        raise ValueError(f"Reference part '{reference_id}' not found")

    cand_specs = get_part_specs(candidate_id)
    if isinstance(cand_specs, dict) and "error" in cand_specs:
        raise ValueError(f"Candidate part '{candidate_id}' not found")

    ref_name = ref_specs.get("name", reference_id)
    cand_name = cand_specs.get("name", candidate_id)

    # --- Step 1: Knowledge Specialist — ICD/datasheet interface detail ---
    knowledge = _with_max_tokens(create_knowledge_specialist(), _SPECIALIST_MAX_TOKENS)
    knowledge_prompt = (
        f'An engineer is assessing the integration impact of substituting "{ref_name}" ({reference_id}) '
        f'with "{cand_name}" ({candidate_id}).\n\n'
        "Search the knowledge base (datasheets and ICDs) for BOTH parts and report:\n"
        "- Pinout / connector interface details\n"
        "- Command protocol or frame format (if documented)\n"
        "- Mechanical drawing references (mounting pattern, mounting holes, envelope)\n"
        "- Electrical interface specifics not already in structured specs (signal types, bus protocol)\n\n"
        "Report findings for the reference part, then the candidate part, separately. "
        "If a detail isn't found in the KB for a part, say so explicitly rather than guessing."
    )
    knowledge_response = knowledge(knowledge_prompt)
    knowledge_text = str(knowledge_response)

    # --- Step 2: Evaluation Specialist — structured delta + qual check ---
    evaluation = _with_max_tokens(create_evaluation_specialist(), _SPECIALIST_MAX_TOKENS)
    evaluation_prompt = (
        f"Run a field-by-field comparison between the reference part {reference_id} and the candidate part "
        f"{candidate_id} using compare_parts. Then check the candidate's qualification status against the "
        f"reference part's qualification standard using check_qualification_status. Report the full comparison "
        "and the qualification result. Do not draft a memo — just report the comparison and qualification data."
    )
    evaluation_response = evaluation(evaluation_prompt)
    evaluation_text = str(evaluation_response)

    # Deterministic structured delta (used for exact summary stats — not
    # parsed from LLM text, so document_id stats are always accurate)
    comparison = compare_parts(reference_id, candidate_id)
    matches_count = comparison.get("matches", 0) if isinstance(comparison, dict) else 0
    total_fields = comparison.get("total_fields", 0) if isinstance(comparison, dict) else 0
    differences_count = comparison.get("differences", 0) if isinstance(comparison, dict) else 0

    # --- Step 3: Supervisor — synthesize into the formal IIA document ---
    supervisor = _with_max_tokens(create_supervisor(), _SYNTHESIS_MAX_TOKENS)
    synthesis_prompt = (
        f"{IIA_SYNTHESIS_INSTRUCTIONS}\n\n"
        f"REFERENCE PART: {ref_name} ({reference_id})\n"
        f"CANDIDATE PART: {cand_name} ({candidate_id})\n\n"
        f"--- Knowledge Specialist findings ---\n{knowledge_text}\n\n"
        f"--- Evaluation Specialist findings ---\n{evaluation_text}\n\n"
        "Write the IIA document now."
    )
    synthesis_response = supervisor(synthesis_prompt)
    markdown = str(synthesis_response)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    document_id = f"IIA-{reference_id[:12]}-{candidate_id[:12]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Deterministic audit entry: an IIA document was generated for this
    # reference/candidate pair. Never let a logging failure break the
    # assessment response.
    try:
        _write_audit_entry("impact_assessment", json.dumps({
            "document_id": document_id,
            "reference_id": reference_id,
            "candidate_id": candidate_id,
            "matches_count": matches_count,
            "differences_count": differences_count,
            "total_fields": total_fields,
        }))
    except Exception:
        pass

    return {
        "document_id": document_id,
        "date": date_str,
        "reference_part": _part_ref(reference_id),
        "candidate_part": _part_ref(candidate_id),
        "markdown": markdown,
        "matches_count": matches_count,
        "differences_count": differences_count,
        "total_fields": total_fields,
    }
