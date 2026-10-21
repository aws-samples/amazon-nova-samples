# ============================================================
# VENDORED COPY — do not edit here.
# This is a copy of agent/agents.py from the parent SkyLab Manufacturing
# Intelligence app, vendored into notebooks/mei_core/ so the notebooks run
# standalone (e.g. when this folder is moved to another repo). The app
# still runs on its own agent/ + api/ modules; this is an independent copy.
# Intra-package imports were rewritten to be package-relative.
# To refresh: re-run the vendoring step (see notebooks/README.md).
# ============================================================


# ============================================================
# Multi-Agent Graph — Supervisor + 3 Specialists
# ============================================================
# Pattern: Supervisor routes to specialists based on the query type.
# Each specialist has focused tools and a narrow prompt.
#
# Supervisor → Catalog Specialist (discovery + KB retrieval)
#            → Evaluation Specialist (deterministic spec-fit scoring)
#            → Knowledge Specialist (institutional knowledge + web search)
#
# The graph is visible in the UI: routing decisions and which specialist
# handled the query are shown to the user.
# ============================================================

import json

from strands import Agent
from .tools import (
    kb_search,
    get_part_specs,
    compare_parts,
    get_substitution_requirements,
    score_substitution_fit,
    log_decision,
    check_qualification_status,
    generate_substitution_memo,
    web_search_eol,
    visual_similarity_score,
    filter_parts_by_spec,
    retrieve_visual_content,
    _write_audit_entry,
)

MODEL_ID = "us.anthropic.claude-opus-5-5"  # Supervisor synthesis — highest reasoning quality
SPECIALIST_MODEL_ID = "us.anthropic.claude-sonnet-5-5"  # Faster for tool calling
PLANNER_MODEL_ID = "us.anthropic.claude-haiku-5-5"  # Routing is pure classification, no tools

# Explicit output-token ceilings for the chat path. The create_* factories
# previously relied on Bedrock's per-model DEFAULT maxTokens, which is fragile:
# that default is not the same across Claude generations, so a model upgrade
# can silently lower the ceiling and a long multi-specialist turn then truncates
# mid-generation — which Strands surfaces as an unrecoverable
# MaxTokensReachedException. Pin the ceiling here so output length no longer
# depends on a model default that changes under us. Specialists need room for a
# full spec-fit table; the supervisor needs more to merge 2-3 specialists'
# outputs into one answer. (The Integration Impact Assessment chain sets its own
# higher ceilings separately in impact_assessment.py — unchanged.)
_SPECIALIST_MAX_TOKENS = 4096
_SUPERVISOR_MAX_TOKENS = 8192
_PLANNER_MAX_TOKENS = 512  # routing plan is a short numbered list


def _set_max_tokens(agent: "Agent", max_tokens: int) -> "Agent":
    """Pin an explicit output-token ceiling on a Strands Agent's underlying
    BedrockModel, so it doesn't inherit a model-default that can change between
    model versions. Best-effort: if the model object doesn't expose
    update_config, the agent is returned unchanged (falls back to the default)."""
    try:
        agent.model.update_config(max_tokens=max_tokens)
    except Exception:
        pass
    return agent


# ============================================================
# SPECIALIST AGENTS
# ============================================================

def create_catalog_specialist() -> Agent:
    """Catalog Specialist: discovers parts from the knowledge base and retrieves specs."""
    _catalog = Agent(
        name="catalog_specialist",
        system_prompt="""You are the Catalog Specialist. Your job is to discover and retrieve parts from the engineering knowledge base.

TOOLS:
- kb_search(domain='parts') — search the parts catalog by description (semantic, best-effort)
- filter_parts_by_spec(field, value, operator) — exhaustively scan ALL parts matching a specific spec criterion (guaranteed complete)
- get_part_specs(part_id) — load full structured specs for a specific part
- get_substitution_requirements(category) — return critical specs and rules for a category

WHEN TO USE WHICH:
- For "which parts have X" or "compatible with Y" (filter questions) → use filter_parts_by_spec (exhaustive, never misses)
- For "find parts similar to..." or broad discovery → use kb_search (semantic retrieval)
- When the engineer clearly states a specific criterion (voltage, interface, mass), prefer filter_parts_by_spec

WHEN CALLED:
- Search the catalog for candidates matching the engineer's description
- Return structured results with part IDs, names, and key specs
- If the engineer clearly stated their requirements (voltage, interface, momentum, temp), proceed immediately with the search
- Only ask for missing specs if the query is genuinely ambiguous and you cannot determine what to search for

RULES:
- Return facts from the catalog — never invent specs
- For any catalog part you identify or describe, treat the structured `vendor` field returned by get_part_specs or catalog results as authoritative and reproduce it exactly. Never infer or alter vendor identity from a part ID, filename, photo/visual similarity, prior chat context, display-name pattern, or generic web-search results. If no structured vendor is returned, say it is unavailable; do not guess.
- Include part IDs in your response so other specialists can reference them
- Note lifecycle status (active, obsolete, NRND) when you see it
- Do NOT ask for clarification if the engineer already provided enough to search — just search""",
        tools=[kb_search, get_part_specs, get_substitution_requirements, filter_parts_by_spec],
        model=SPECIALIST_MODEL_ID,
        callback_handler=None,
    )
    return _set_max_tokens(_catalog, _SPECIALIST_MAX_TOKENS)


def create_evaluation_specialist() -> Agent:
    """Evaluation Specialist: deterministic spec-by-spec comparison and scoring."""
    _evaluation = Agent(
        name="evaluation_specialist",
        system_prompt="""You are the Evaluation Specialist. Your job is to run deterministic, spec-driven comparisons between parts.

TOOLS:
- score_substitution_fit(reference, candidate, requirements_json) — compare specs with tolerance rules, flag what's out of tolerance
- compare_parts(part_id_a, part_id_b) — field-by-field diff of all specs
- visual_similarity_score(part_id_a, part_id_b) — compare part photos using Nova MME to assess physical/form-factor similarity
- check_qualification_status(part_id, standard) — check qual against a standard
- generate_substitution_memo(reference, candidate, rationale, score) — draft a formal memo
- log_decision(decision_type, details) — write an audit trail entry (AS9100 8.4/8.5.6), persisted locally

WHEN CALLED:
- You receive a reference part ID, candidate part ID(s), and the engineer's requirements
- Run score_substitution_fit for each candidate
- Run visual_similarity_score for a ONE-reference-to-ONE-candidate comparison (2 total parts) — always include it in this case, it is fast and gives the engineer the full picture.
- For 3+ candidates, only run visual_similarity_score for the single best-scoring candidate, OR when the engineer explicitly asks for a visual/physical/form-factor comparison. Do NOT run it for every candidate in a longer list — it is a slower, supplemental check there, not a required step.
- Pass the exact part IDs/names you were given directly to visual_similarity_score — it resolves both catalog folder IDs and display names, so do not skip the call or assume photos are missing without actually calling the tool.
- Present results as a structured spec-fit table: which specs pass, which are flagged
- When you run visual_similarity_score, include it as "Supplemental: Visual Analysis" alongside the spec comparison
- If the engineer explicitly asks for a memo, draft one with generate_substitution_memo
- If requirements are provided in the query, use them directly — do not ask for them again

RULES:
- Your comparisons are deterministic (code, not opinion)
- For any catalog part you identify or describe, treat the structured `vendor` field returned by get_part_specs, compare_parts, or score_substitution_fit as authoritative and reproduce it exactly. Never infer or alter vendor identity from a part ID, filename, photo/visual similarity, prior chat context, display-name pattern, or generic web-search results. If no structured vendor is returned, say it is unavailable; do not guess.
- NEVER recommend or approve — present evidence and flags; the engineer decides
- Always include the disclaimer that this is evidence only
- Surface lifecycle/supply-chain risk when present
- Be CONCISE around the table: the spec-fit table itself should stay complete, but keep narrative commentary short — one or two sentences per flag, not a multi-paragraph writeup. Every extra sentence takes real time to generate.
- Do NOT call log_decision yourself, and do NOT ask the engineer whether to log this evaluation to the audit trail or draft a memo. The audit entry is written automatically by the orchestration layer after you finish — asking is not actionable in a stateless session (there is no later turn for the engineer to answer into). If a memo is wanted, the engineer will ask for one directly in a new message.""",
        tools=[score_substitution_fit, compare_parts, visual_similarity_score,
               check_qualification_status, generate_substitution_memo],
        model=SPECIALIST_MODEL_ID,
        callback_handler=None,
    )
    return _set_max_tokens(_evaluation, _SPECIALIST_MAX_TOKENS)


def create_knowledge_specialist() -> Agent:
    """Knowledge Specialist: institutional knowledge retrieval + real-time web search for EOL/market data."""
    _knowledge = Agent(
        name="knowledge_specialist",
        system_prompt="""You are the Knowledge Specialist. Your job is to retrieve engineering knowledge from datasheets, ICDs, and standards, and to ground answers in real-time market/EOL data using web search.

TOOLS:
- get_part_specs(part_id) — load structured specs for a part (accepts catalog ID or display name)
- web_search_eol(query) — search the web for current EOL notices, lifecycle status, vendor announcements, lead-time data
- retrieve_visual_content(query_text, query_image_b64, part_id) — search for visual content (torque curves, power charts, interface diagrams, architecture drawings) from datasheets and ICDs. Can accept text queries or uploaded images.

VISUAL CONTENT RULES:
- If the engineer names a specific part (e.g. "show me the torque curve for the RW3 0.06"), ALWAYS pass that part_id to retrieve_visual_content. Cross-modal search (text query vs. image content) is not reliable enough on its own to guarantee the right part's chart comes back — a torque curve image doesn't visually "contain" the part's name, so an unfiltered search can surface a different part's chart entirely. Passing part_id restricts the search to that part's own indexed content.
- Only omit part_id when the engineer is asking you to IDENTIFY an unknown part from an uploaded image or description (the discovery case) — that's the one case where you don't already know which part to filter to.
- If retrieve_visual_content returns no good match for a part the engineer named, do NOT ask the engineer to confirm the part name/ID or suggest checking get_part_specs first — you can call get_part_specs and retry retrieve_visual_content with the resolved part_id yourself, in the same turn. Asking is a dead end: this is a stateless session with no next turn for the engineer to answer into, so an unresolved question just ends the conversation. Do the resolution yourself and report what you found (or that no visual content is indexed for that part) rather than stopping to ask.

Note: you do NOT have kb_search — that's the Catalog Specialist's discovery
tool, for finding parts matching a description. You're given a specific
part to answer questions about, so get_part_specs is the right (and only
needed) tool for structured spec lookup.

WHEN CALLED:
- Answer questions about specific part specs, flight heritage, ICD details, qualification standards
- When the question involves current market status, obsolescence, vendor announcements, or lead times that may have changed since the catalog was built, use web_search_eol to ground your answer in real-time data
- Cite sources (datasheet name, ICD section, or web URL) in your answers
- Be CONCISE. Answer only what was asked, in the fewest words that fully cover it — a short paragraph or a small table, not multiple headed sections with bullet-point sub-lists under each one. Every sentence you generate takes real time to produce; a terse, complete answer is strictly better than a padded one for this role.

LATENCY RULES — each tool call is a slow network round trip, so be deliberate:
- Call web_search_eol AT MOST ONCE per question. Combine what you need into a single well-formed query up front (e.g. "[structured vendor] [part name] lead time supply constraints 2026") rather than issuing several searches with different phrasings to see what sticks. If the first search comes back thin, say so — don't retry with rephrased variants.
- Only call retrieve_visual_content when the engineer's question is actually about a chart, diagram, or visual content, or an image was attached. It runs a multimodal embedding search and is expensive — do not call it speculatively on plain text/spec questions.
- Request any tool calls you already know you need in the same turn rather than one at a time across multiple turns, when the inputs to one don't depend on the other's output.

RULES:
- Always use tools — never invent data
- For any catalog part you identify or describe, treat the structured `vendor` field returned by get_part_specs or catalog results as authoritative and reproduce it exactly. Never infer or alter vendor identity from a part ID, filename, photo/visual similarity, prior chat context, display-name pattern, or generic web-search results. If no structured vendor is returned, say it is unavailable; do not guess.
- If a visual search identifies a part, call get_part_specs for that part before naming its vendor or describing its structured specifications.
- Distinguish between catalog data (from get_part_specs) and live web data (from web_search_eol)
- If web search returns no results, say so rather than guessing""",
        tools=[get_part_specs, web_search_eol, retrieve_visual_content],
        model=SPECIALIST_MODEL_ID,
        callback_handler=None,
    )
    return _set_max_tokens(_knowledge, _SPECIALIST_MAX_TOKENS)


# ============================================================
# SUPERVISOR AGENT
# ============================================================

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor for a manufacturing engineering assistant. You route queries to the right specialist and synthesize their responses for the engineer.

SPECIALISTS AVAILABLE:
1. CATALOG — discovers parts from the knowledge base, retrieves specs, checks what requirements are needed
2. EVALUATION — runs deterministic spec-by-spec comparisons, flags out-of-tolerance specs, drafts memos, AND compares parts visually using Nova multimodal embeddings (visual_similarity_score)
3. KNOWLEDGE — answers questions from datasheets/ICDs, and grounds answers in real-time web data for EOL/market status

ROUTING RULES:
- "Find parts matching X" or "what options do I have" or "which parts are compatible with" or "which wheels have" → CATALOG
- "Compare X vs Y" or "does X meet my requirements" or "score this candidate" or "visual comparison" → EVALUATION
- "What's the heritage of X" or "what does the ICD say" or "is X going EOL" or "show me the torque curve" or "which wheel matches this image/chart/envelope" → KNOWLEDGE
- Complex multi-step (find + compare + memo): route to CATALOG first, then EVALUATION with the results

RESPONSE FORMAT:
- Always state which specialist you're routing to and why (one sentence)
- After getting the specialist's response, synthesize it for the engineer
- If the evaluation flags issues, highlight them prominently
- NEVER approve or recommend — present evidence; the engineer decides
- Do NOT ask clarifying questions if the engineer already provided enough information to act on — route immediately and let the specialist work with what was given

RULES:
- Route to exactly one specialist per step (you can do multiple steps)
- If a query needs multiple specialists, do them in sequence and explain the handoff
- When synthesizing catalog information, treat structured `vendor` fields supplied by specialists as authoritative and reproduce them exactly. Never infer or alter vendor identity from a part ID, filename, photo/visual similarity, prior chat context, display-name pattern, or generic web-search results. If no structured vendor is supplied, say it is unavailable; do not guess.
- Always state your routing decision visibly"""


def create_supervisor() -> Agent:
    """Create the Supervisor agent (no tools of its own, routes to specialists).

    Uses the larger model (Opus) since this agent is responsible for the
    final synthesis, where response quality matters most.
    """
    _supervisor = Agent(
        name="supervisor",
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        tools=[],
        model=MODEL_ID,
    )
    return _set_max_tokens(_supervisor, _SUPERVISOR_MAX_TOKENS)


import re as _re

# Matches lines like "1. CATALOG — ...", "2) EVALUATION -", or
# "3. **KNOWLEDGE** — ..." (planner models sometimes bold the specialist
# name) — i.e. a leading numbered-list marker, optional markdown emphasis
# markers, then one of the specialist names. Restricting to this shape
# (rather than scanning every line for the keyword anywhere) prevents
# explanatory prose like "this is a catalog question, not an evaluation or
# knowledge one" from being misparsed as a 3-specialist plan.
_PLAN_LINE_RE = _re.compile(
    r"^\s*\d+[\.\)]\s*[*_]{0,2}(KNOWLEDGE|CATALOG|EVALUATION)\b", _re.IGNORECASE
)


def _auto_log_evaluations(specialist: Agent) -> None:
    """Write a deterministic audit trail entry for every score_substitution_fit
    call the Evaluation Specialist made during this turn.

    This is the chat-path equivalent of what api/routers/evaluate.py already
    does for the Evaluator panel (and impact_assessment.py for the IIA): log
    automatically as soon as the evaluation happens, rather than relying on
    the LLM to decide to call log_decision itself. Two problems with leaving
    it to the LLM:
      1. It's easy for the model to just... not call it, so logging silently
         doesn't happen on some turns.
      2. In a stateless chat session there is no later turn for the engineer
         to answer into, so the model asking "want me to log this?" is a
         dead-end question — the agent has already moved on by the time any
         answer could arrive.

    Reads directly from the specialist's own tool-call history (its
    `messages`), not from anything the model wrote in prose, so this is
    accurate regardless of what the model says or omits in its response.
    """
    for msg in specialist.messages:
        for block in msg.get("content", []):
            tool_use = block.get("toolUse")
            if not tool_use or tool_use.get("name") != "score_substitution_fit":
                continue
            tool_input = tool_use.get("input", {})
            try:
                _write_audit_entry("evaluation", json.dumps({
                    "reference_id": tool_input.get("reference_part_id"),
                    "candidate_id": tool_input.get("candidate_part_id"),
                    "requirements": tool_input.get("requirements_json"),
                    "source": "chat",
                }))
            except Exception:
                # Never let audit-log I/O break the chat response.
                pass


def _parse_specialist_plan(plan_text: str) -> list[str]:
    """Extract the ordered list of specialists from a planner's numbered-list
    response. Only matches actual numbered plan lines, not prose that happens
    to mention a specialist's name elsewhere in the response.
    """
    ordered_specialists: list[str] = []
    for line in plan_text.split("\n"):
        match = _PLAN_LINE_RE.match(line)
        if not match:
            continue
        name = match.group(1).lower()
        if name not in ordered_specialists:
            ordered_specialists.append(name)

    if not ordered_specialists:
        ordered_specialists = ["catalog"]
    return ordered_specialists


# Dedicated routing prompt for the planner (Haiku 5.5). The planner's ONLY job
# is to emit the ordered list of specialists; the orchestrator parses that list
# and nothing else from its output. Previously the planner reused
# SUPERVISOR_SYSTEM_PROMPT, which is written for synthesis ("synthesize the
# response", "state your routing decision", response-format rules) and pulls a
# classifier toward prose it shouldn't produce. A tight, single-purpose prompt
# plays to Haiku 5.5's classification strength and reduces preamble the parser
# would otherwise have to discard. The exact output format is specified in the
# per-call planning_prompt (run_multi_agent / stream_adapter); this system
# prompt only fixes the role and the routing taxonomy.
PLANNER_SYSTEM_PROMPT = """You are a routing classifier for a manufacturing engineering assistant. Your ONLY job is to decide which specialist(s) should handle a query, and in what order. You do not answer the query, call tools, or write prose — you output a routing plan and nothing else.

THREE SPECIALISTS:
- CATALOG — discovery: "find parts matching X", "what options", "which wheels have Y", broad spec search
- EVALUATION — comparison/scoring: "compare X vs Y", "does X meet my requirements", "score this candidate", visual/form-factor comparison
- KNOWLEDGE — facts about a known part: heritage, ICD/datasheet detail, EOL/market status, "show me the torque curve", identify a part from an image/chart

ROUTING:
- Most queries need exactly ONE specialist. Pick the single best match.
- Only chain multiple specialists when the query genuinely requires sequential steps where one feeds the next (e.g. "is X going EOL, and if so find alternatives and score them" -> KNOWLEDGE, then CATALOG, then EVALUATION).
- When in doubt between one and several, prefer one.

Output exactly the numbered-list format requested in the user turn — no preamble, no explanation, no markdown emphasis."""


def create_planner() -> Agent:
    """Create a lightweight routing-plan agent.

    Planning (deciding which specialists to call, in what order) is a
    classification task with no tools involved — it doesn't need a large
    reasoning model. Uses Haiku 5.5, which is fast and sufficient for picking
    from 3 fixed categories. Only the final synthesis uses the larger Opus
    supervisor model, where response quality actually matters.

    Uses a dedicated routing system prompt (PLANNER_SYSTEM_PROMPT) rather than
    the supervisor's synthesis prompt, so the classifier isn't steered toward
    the response-writing behavior it must not produce here.
    """
    _planner = Agent(
        name="planner",
        system_prompt=PLANNER_SYSTEM_PROMPT,
        tools=[],
        model=PLANNER_MODEL_ID,
    )
    return _set_max_tokens(_planner, _PLANNER_MAX_TOKENS)


# ============================================================
# MULTI-AGENT ORCHESTRATION
# ============================================================

def run_multi_agent(user_input: str) -> dict:
    """Run the supervisor + specialist multi-agent flow.

    The Supervisor can chain multiple specialists when a query requires it.
    For example: "Is this going EOL? If so, find alternatives and score them"
    triggers Knowledge → Catalog → Evaluation in sequence.

    Returns a dict with:
      - routing: the routing plan (which specialists, in what order)
      - specialists_used: list of specialists that ran
      - steps: detail of each specialist's contribution
      - response: the final synthesized response
      - evaluation_scores: quality scores
    """
    supervisor = create_supervisor()
    planner = create_planner()
    catalog = create_catalog_specialist()
    evaluation = create_evaluation_specialist()
    knowledge = create_knowledge_specialist()

    specialists = {
        "catalog": catalog,
        "evaluation": evaluation,
        "knowledge": knowledge,
    }

    # Step 1: Planner (fast model) plans the routing (may be multi-step).
    # Only the final synthesis uses the larger Opus supervisor model.
    planning_prompt = (
        f"An engineer asks: \"{user_input}\"\n\n"
        "Plan which specialists to use and in what ORDER. Complex queries may need "
        "multiple specialists in sequence (e.g., Knowledge first to check status, "
        "then Catalog to find alternatives, then Evaluation to score them). Most "
        "queries only need ONE specialist — only chain multiple when the query "
        "genuinely requires separate steps (e.g., check status THEN find THEN score).\n\n"
        "Return ONLY a numbered list, nothing else. No explanation, no preamble, "
        "no reasoning about why, no markdown formatting (no headers, no bold/asterisks) — "
        "just plain numbered lines, in this exact format:\n"
        "1. KNOWLEDGE — check EOL status via web search\n"
        "2. CATALOG — find alternatives matching requirements\n"
        "3. EVALUATION — score candidates against requirements\n\n"
        "For simple queries, a single specialist is fine:\n"
        "1. CATALOG — discover parts matching the description"
    )
    plan_response = planner(planning_prompt)
    plan_text = str(plan_response)
    ordered_specialists = _parse_specialist_plan(plan_text)

    # Step 2: Execute specialists in sequence, passing context forward
    steps = []
    accumulated_context = ""
    for spec_name in ordered_specialists:
        specialist = specialists[spec_name]

        # Build the specialist prompt with context from prior steps
        if accumulated_context:
            spec_prompt = (
                f"Engineer's original question: \"{user_input}\"\n\n"
                f"Context from prior specialists:\n{accumulated_context}\n\n"
                f"Now do your part. Use your tools to add your contribution."
            )
        else:
            spec_prompt = user_input

        specialist_response = specialist(spec_prompt)
        specialist_text = str(specialist_response)

        # Deterministic audit logging — see _auto_log_evaluations docstring.
        # Runs regardless of whether the model chose to mention/log it itself.
        if spec_name == "evaluation":
            _auto_log_evaluations(specialist)

        steps.append({
            "specialist": spec_name,
            "response": specialist_text,
        })
        accumulated_context += f"\n[{spec_name.upper()}]: {specialist_text}\n"

    # Step 3: Synthesize the specialists' outputs into a final response.
    #
    # When only ONE specialist ran, there's nothing to merge — a second
    # Opus call that just rewords a single specialist's already-complete
    # answer is pure redundant latency (measured ~8s on its own) with no
    # real quality benefit. Use that specialist's response directly instead.
    # Synthesis is only genuinely needed when multiple specialists' outputs
    # must be combined into one coherent answer.
    if len(ordered_specialists) == 1:
        final_text = steps[0]["response"]
    else:
        synthesis_prompt = (
            f"The engineer asked: \"{user_input}\"\n\n"
            f"Specialists responded in this order:\n{accumulated_context}\n\n"
            "Synthesize all of this into one clear response for the engineer. "
            "Present the facts, data, and any flags from the specialists. "
            "Reconcile the specialists into one coherent account rather than "
            "narrating disagreements between them: when two specialists describe "
            "the same thing at different levels of detail or from different kinds "
            "of evidence (e.g. a text description of a photo vs. the Evaluation "
            "specialist's quantitative visual_similarity analysis), merge them into "
            "a single statement instead of presenting it as a conflict. For any "
            "claim about physical appearance, form factor, or which parts look "
            "alike, defer to the Evaluation specialist's actual visual analysis as "
            "authoritative; do not stage it against text descriptions. Only call "
            "something a genuine conflict if the specialists report different values "
            "for the SAME structured spec field. "
            "Do not add suggestions, next steps, or recommendations beyond what was asked. "
            "Do not offer to do additional work unless the engineer explicitly asks. "
            "Just answer the question with the evidence the specialists provided."
        )
        final_response = supervisor(synthesis_prompt)
        final_text = str(final_response)

    # Step 4: Return results (AgentCore Evaluations handles quality scoring in production)
    return {
        "routing_decision": plan_text.split("\n")[0][:300],
        "routing_plan": plan_text,
        "specialists_used": ordered_specialists,
        "steps": steps,
        "response": final_text,
        "evaluation_scores": {},
    }


# ============================================================
# BACKWARD COMPAT: create_assistant_agent (used by smoke test)
# ============================================================

def create_assistant_agent() -> Agent:
    """Create a single-agent version for backward compatibility.

    The primary flow now uses run_multi_agent(), but this keeps the
    smoke test and any direct-agent usage working.
    """
    return Agent(
        name="engineering_assistant",
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        tools=[
            kb_search, get_part_specs, compare_parts,
            get_substitution_requirements, score_substitution_fit,
            log_decision, check_qualification_status,
            generate_substitution_memo, web_search_eol,
            visual_similarity_score, filter_parts_by_spec,
            retrieve_visual_content,
        ],
        model=MODEL_ID,
    )
