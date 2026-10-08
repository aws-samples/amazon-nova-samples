# ============================================================
# VENDORED COPY — do not edit here.
# This is a copy of api/services/stream_adapter.py from the parent SkyLab Manufacturing
# Intelligence app, vendored into notebooks/mei_core/ so the notebooks run
# standalone (e.g. when this folder is moved to another repo). The app
# still runs on its own agent/ + api/ modules; this is an independent copy.
# Intra-package imports were rewritten to be package-relative.
# To refresh: re-run the vendoring step (see notebooks/README.md).
# ============================================================

"""Stream adapter service for running the multi-agent flow with event emission.

Replicates the orchestration logic of run_multi_agent from agent/agents.py
but emits events to a Queue at each stage for real-time SSE streaming.

Does NOT import or modify run_multi_agent. Instead, imports the factory
functions and replicates the orchestration with event hooks.
"""

import asyncio
import json
import re
from queue import Queue
from typing import Optional

from .part_file_urls import build_part_file_url
from .agents import (
    create_supervisor,
    create_planner,
    create_catalog_specialist,
    create_evaluation_specialist,
    create_knowledge_specialist,
    _parse_specialist_plan,
    _auto_log_evaluations,
)

# Matches references like "rw_rl_0060/datasheet_page.png" or
# "s3://bucket/parts/rw_rl_0060/icd_page1.png" that the agent's text may
# contain (either from its own reasoning or from tool results like
# retrieve_visual_content, whose results include S3 URIs as plain text).
_PART_IMAGE_REF_RE = re.compile(
    r"([a-zA-Z0-9_]+)/(datasheet_page|icd_page\d*|photo)\.(png|jpg|jpeg|webp)"
)


_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

# Tools whose results carry part-image references we want to surface in the UI.
# retrieve_visual_content returns results[] with part_id + source_file;
# visual_similarity_score returns part_a/part_b with photo_path.
_IMAGE_BEARING_TOOLS = ("retrieve_visual_content", "visual_similarity_score")


# Words that signal the engineer actually wants to SEE something visual, as
# opposed to just naming a part in a spec/compare/EOL question. Only when a
# TEXT query carries this intent do we attach a part's datasheet/chart image.
# This keeps spec-fit, comparison, and lookup answers text-only (naming a wheel
# like "RW4 0.4" no longer drags in its datasheet), while "show me the torque
# curve for the RW3 0.06" still renders the chart.
_VISUAL_INTENT_RE = re.compile(
    r"\b("
    r"show|see|view|display|render|look at|pull up|bring up|"
    r"image|picture|photo|visual|"
    r"chart|graph|plot|curve|diagram|figure|datasheet|data sheet|"
    r"torque curve|torque box|power curve"
    r")\b",
    re.IGNORECASE,
)


def _has_visual_intent(text: str) -> bool:
    """True when the query is actually asking to see a visual (chart, curve,
    diagram, datasheet, photo, etc.), rather than merely mentioning a part.

    Gates the TEXT-query image paths so spec/compare/EOL questions that happen
    to name a part stay text-only. Does NOT gate the image-UPLOAD path — an
    uploaded image is itself an explicit "what/where is this" request and
    always renders its match.
    """
    if not text:
        return False
    return bool(_VISUAL_INTENT_RE.search(text))


def _prefer_chart_crop(part_id: str, filename: str) -> str:
    """Prefer a part's cropped chart (datasheet_chart.png) over the full
    datasheet page (datasheet_page.png) when the crop exists on disk.

    The chat UI renders a part's datasheet whenever a visual query resolves to
    it (a text query that names a part, or an image-upload match). The full
    page is mostly boilerplate; a cropped chart band is a far cleaner thing to
    show. native/make_chart_crops.py writes datasheet_chart.png for the parts
    that actually have a chart; parts without one (e.g. "inquire for test data"
    sheets, star trackers with no datasheet page) have no crop file and are
    left on the full page.

    This only swaps the DISPLAYED file — it never touches retrieval/matching.
    Only datasheet_page.png is ever substituted; photos, ICDs, and anything
    else pass through unchanged. If the crop file is missing for any reason,
    the original filename is returned, so this can never produce a broken ref.
    """
    if filename.lower() != "datasheet_page.png":
        return filename
    try:
        from .tools import PARTS_DATA_DIR
        if (PARTS_DATA_DIR / part_id / "datasheet_chart.png").exists():
            return "datasheet_chart.png"
    except Exception:
        pass
    return filename


def _image_ref(part_id: str, filename: str) -> Optional[dict]:
    """Build a frontend-servable image ref dict, or None if inputs are unusable.

    Routes through _prefer_chart_crop so a resolved datasheet page is rendered
    as its cropped chart when one exists (falling back to the full page). This
    is the single choke point every image ref flows through, so both the
    text-query (query_images) and image-upload (preproc/tool) paths get the
    crop automatically.
    """
    if not part_id or not filename:
        return None
    if not filename.lower().endswith(_IMAGE_EXTS):
        return None
    filename = _prefer_chart_crop(part_id, filename)
    return {
        "part_id": part_id,
        "filename": filename,
        "url": build_part_file_url(part_id, filename),
    }


def _extract_image_refs(text: str) -> list[dict]:
    """Find part-image references in agent text and resolve them to
    frontend-servable API URLs (the frontend cannot load s3:// URIs
    directly; the backend serves the same local files via /api/parts).

    Returns a de-duplicated list of {"part_id", "filename", "url"} dicts.

    This is the FALLBACK path — it depends on the model happening to write the
    filename into its prose. The primary, deterministic path is
    _extract_images_from_agent (below), which reads the actual tool results.
    """
    seen = set()
    images = []
    for part_id, base_name, ext in _PART_IMAGE_REF_RE.findall(text):
        filename = f"{base_name}.{ext}"
        # Route through _image_ref so this fallback path also renders the
        # cropped chart (datasheet_chart.png) instead of the full page, and
        # de-dupe on the final (possibly crop-swapped) filename.
        ref = _image_ref(part_id, filename)
        if ref is None:
            continue
        key = (ref["part_id"], ref["filename"])
        if key in seen:
            continue
        seen.add(key)
        images.append(ref)
    return images


def _extract_images_from_agent(agent) -> list[dict]:
    """Deterministically collect part-image references from a specialist's
    tool-call results, by reading the agent's message history rather than its
    prose. This is robust: an image surfaces whenever retrieve_visual_content /
    visual_similarity_score actually returned one, regardless of whether the
    model mentioned the filename in its answer.

    Strands stores each tool return as a `toolResult` block whose
    content[0]["text"] is the JSON-serialized tool output, keyed to the
    originating `toolUse` by toolUseId. We match the two, parse the JSON, and
    pull out (part_id, filename) pairs where the filename is an image.

    Returns a list of {"part_id", "filename", "url"} dicts (caller de-dupes).
    """
    messages = getattr(agent, "messages", None)
    if not messages:
        return []

    # 1) Which toolUseIds belong to image-bearing tools?
    image_tool_use_ids: set[str] = set()
    for msg in messages:
        for block in msg.get("content", []):
            tool_use = block.get("toolUse")
            if tool_use and tool_use.get("name") in _IMAGE_BEARING_TOOLS:
                tid = tool_use.get("toolUseId") or tool_use.get("id")
                if tid:
                    image_tool_use_ids.add(tid)

    if not image_tool_use_ids:
        return []

    # 2) Find the matching toolResult blocks and parse their JSON payloads.
    images: list[dict] = []
    for msg in messages:
        for block in msg.get("content", []):
            tool_result = block.get("toolResult")
            if not tool_result:
                continue
            if tool_result.get("toolUseId") not in image_tool_use_ids:
                continue
            for content_item in tool_result.get("content", []):
                raw = content_item.get("text")
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                images.extend(_image_refs_from_tool_payload(payload))
    return images


def _image_refs_from_tool_payload(payload: dict) -> list[dict]:
    """Pull image refs out of a parsed tool-result payload.

    Handles both shapes:
      - retrieve_visual_content: {"results": [{"part_id", "source_file", ...}]}
      - visual_similarity_score: {"part_a": {"id", "photo_path"}, "part_b": {...}}
    """
    if not isinstance(payload, dict):
        return []
    refs: list[dict] = []

    # retrieve_visual_content — surface ONLY the single best-matching part's
    # image. Results are score-ordered, and a query like "show me the torque
    # curve for the RW3 0.06" also pulls lower-scoring near-miss parts (e.g. a
    # different wheel at 0.95 vs the right one at 0.98); surfacing those would
    # render an unrelated part's datasheet alongside the intended one. So we
    # take the first part that yields a valid image ref and stop. (The
    # authoritative image-upload match is handled separately via
    # preproc_images.)
    for r in payload.get("results", []) or []:
        ref = _image_ref(r.get("part_id", ""), r.get("source_file", ""))
        if ref:
            refs.append(ref)
            break

    # visual_similarity_score
    for side in ("part_a", "part_b"):
        part = payload.get(side)
        if isinstance(part, dict):
            photo_path = part.get("photo_path", "")
            filename = photo_path.split("/")[-1] if photo_path else ""
            ref = _image_ref(part.get("id", ""), filename)
            if ref:
                refs.append(ref)
    return refs


def _run_specialist_streaming(
    specialist,
    prompt: str,
    spec_name: str,
    event_queue: Queue,
) -> str:
    """Run a specialist agent with token-level streaming, emitting a
    "content_delta" event per chunk as it's generated.

    Uses Strands' `stream_async`, which yields incremental events as the
    model generates text (as opposed to calling the agent synchronously and
    only getting the full response once generation is complete). This
    function itself stays synchronous (via asyncio.run) since it's invoked
    from run_agent_with_events, which runs in a background thread — the SSE
    event loop that eventually reads from event_queue lives elsewhere.

    Returns the full accumulated text once the specialist finishes, for
    callers that still need the complete string (e.g. building
    accumulated_context for the next specialist, or the "content" event
    used for the collapsed specialist-contributions history view).
    """
    async def _consume() -> str:
        chunks: list[str] = []
        async for event in specialist.stream_async(prompt):
            text_chunk = event.get("data")
            if text_chunk:
                chunks.append(text_chunk)
                event_queue.put({
                    "event": "content_delta",
                    "data": {"text": text_chunk, "specialist": spec_name},
                })
        return "".join(chunks)

    return asyncio.run(_consume())


def run_agent_with_events(
    user_input: str,
    image_b64: Optional[str],
    event_queue: Queue,
) -> None:
    """Execute the multi-agent flow, emitting events to the queue.

    Replicates the logic of run_multi_agent() but emits events at each stage.
    Does NOT import or modify run_multi_agent — it calls the same create_*
    factory functions and replicates the orchestration to insert event hooks.

    Args:
        user_input: The engineer's query text.
        image_b64: Optional base64-encoded image for multimodal retrieval.
        event_queue: Queue to emit structured SSE events into.
    """
    try:
        # --- Image pre-processing: run multimodal retrieval before the agent flow ---
        image_context = ""
        # Images from the pre-processing retrieval — this is the authoritative
        # image-as-query match (e.g. the datasheet page whose chart matched the
        # upload). Collected here and prioritized over any images a downstream
        # specialist tool surfaces (e.g. evaluation's visual_similarity_score,
        # which returns product photos of runner-up candidates), so the UI
        # renders the actual matched document, not a different part's photo.
        preproc_images: list[dict] = []
        if image_b64:
            from .tools import retrieve_visual_content

            visual_results = retrieve_visual_content(
                query_text=user_input,
                query_image_b64=image_b64,
                top_k=3,
            )
            if visual_results.get("results"):
                # Only surface the single best match's image. This is a
                # discovery query ("which part is this?") — showing runner-up
                # images would be misleading, so cap at the top result.
                preproc_images = _image_refs_from_tool_payload(
                    {"results": visual_results["results"][:1]}
                )
                matches = []
                for vr in visual_results["results"]:
                    part_id = vr.get("part_id", "unknown")
                    source_file = vr.get("source_file", "?")
                    score = vr.get("score", 0)
                    content_type = vr.get("content_type", "?")
                    matches.append(
                        f"- Part: {part_id}, Source: {source_file}, "
                        f"Score: {score:.3f}, Type: {content_type}"
                    )
                image_context = (
                    "\n\n[VISUAL SEARCH RESULTS via Nova MME multimodal retrieval: "
                    "The uploaded image was matched against indexed datasheet pages "
                    "and diagrams. Top matches (highest score = best match):\n"
                    + "\n".join(matches)
                    + "\n\nBased on these results, identify which part the uploaded "
                    "image belongs to and provide relevant information about that part.]"
                )
            elif visual_results.get("image_search_supported") is False:
                # Managed KB can't take an image as the query. Not an error —
                # tell the specialist to read the image with vision and match
                # via TEXT/spec search instead, so it degrades gracefully.
                image_context = (
                    "\n\n[NOTE: An image was uploaded, but image-as-query retrieval "
                    "is not available on this knowledge base. Do NOT report this as an "
                    "error. Instead: read the values, axes, and shape visible in the "
                    "uploaded chart/diagram yourself, then identify the matching part by "
                    "reasoning over the catalog specs (use filter_parts_by_spec or a text "
                    "retrieve_visual_content query with the values you read off the image).]"
                )
            elif visual_results.get("error"):
                image_context = (
                    f"\n\n[Visual search error: {visual_results['error']}]"
                )

        # Combine user input with image context
        agent_input = user_input + image_context

        # --- Create agents using factory functions ---
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

        # --- Step 1: Planner (fast model) plans routing (same prompt as agents.py) ---
        # Only synthesis uses the larger Opus supervisor model — planning is a
        # pure classification task with no tools, so the faster specialist
        # model handles it just as well with meaningfully lower latency.
        planning_prompt = (
            f'An engineer asks: "{agent_input}"\n\n'
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

        # --- Parse which specialists to call (shared with agents.py) ---
        ordered_specialists = _parse_specialist_plan(plan_text)

        # Emit routing event
        event_queue.put({
            "event": "routing",
            "data": {"plan": plan_text, "specialists": ordered_specialists},
        })

        # --- Step 2: Execute specialists in sequence with events ---
        accumulated_context = ""
        last_specialist_text = ""
        tool_images: list[dict] = []  # images pulled from tool results (robust)
        for spec_name in ordered_specialists:
            specialist = specialists[spec_name]

            # Emit specialist_start
            event_queue.put({
                "event": "specialist_start",
                "data": {"name": spec_name},
            })

            try:
                # Build the specialist prompt with context from prior steps
                if accumulated_context:
                    spec_prompt = (
                        f'Engineer\'s original question: "{agent_input}"\n\n'
                        f"Context from prior specialists:\n{accumulated_context}\n\n"
                        f"Now do your part. Use your tools to add your contribution."
                    )
                else:
                    spec_prompt = agent_input

                # Stream token-by-token so the UI can show live "thinking"
                # text as it's generated, rather than only a single chunk
                # once the specialist finishes. Emits a "content_delta" per
                # chunk (specialist name attached so the frontend knows
                # which panel to replace, not append to), and still emits
                # the final "content" event with the full text once done —
                # unchanged for specialist contribution history / context.
                specialist_text = _run_specialist_streaming(
                    specialist, spec_prompt, spec_name, event_queue
                )

                # Deterministic audit logging — mirrors what the Evaluator
                # panel and IIA endpoints already do automatically. Runs
                # regardless of whether the model chose to log/mention it,
                # and is the reason the Evaluation Specialist's prompt no
                # longer asks the engineer whether to log (dead-end question
                # in a stateless chat session anyway).
                if spec_name == "evaluation":
                    _auto_log_evaluations(specialist)

                # Emit content event (full text — same as before, used for
                # the collapsed "specialist contributions" history view)
                event_queue.put({
                    "event": "content",
                    "data": {"text": specialist_text, "specialist": spec_name},
                })

                # Emit specialist_done
                event_queue.put({
                    "event": "specialist_done",
                    "data": {"name": spec_name},
                })

                # Deterministically collect any images this specialist's tools
                # returned (retrieve_visual_content / visual_similarity_score),
                # reading the actual tool results rather than the model's prose.
                tool_images.extend(_extract_images_from_agent(specialist))

                # Accumulate context for subsequent specialists
                accumulated_context += f"\n[{spec_name.upper()}]: {specialist_text}\n"
                last_specialist_text = specialist_text

            except Exception as e:
                # Emit error event and continue with remaining specialists
                event_queue.put({
                    "event": "error",
                    "data": {"specialist": spec_name, "message": str(e)},
                })

        # --- Step 3: Synthesize the specialists' outputs into a final response ---
        # When only ONE specialist ran, skip the extra Opus synthesis call —
        # there's nothing to merge, so a second full model round trip just to
        # reword an already-complete answer is pure redundant latency
        # (measured ~8s on its own with no real quality benefit). Use that
        # specialist's response directly. Synthesis is only genuinely needed
        # when multiple specialists' outputs must be combined into one answer.
        if len(ordered_specialists) == 1:
            final_text = last_specialist_text
        else:
            synthesis_prompt = (
                f'The engineer asked: "{agent_input}"\n\n'
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

        # Emit synthesis event
        event_queue.put({
            "event": "synthesis",
            "data": {"text": final_text},
        })

        # Emit part-image references so the chat UI can render actual <img>
        # tags. Priority order (first wins on de-dup by (part_id, filename)):
        #   1. preproc_images — the authoritative image-as-query match from the
        #      pre-processing retrieve_visual_content call (e.g. the matched
        #      datasheet page). For an image upload this is what the engineer
        #      expects to see, so it leads.
        #   2. tool_images — images from specialists' actual tool results
        #      (deterministic, independent of how the model phrases its answer).
        #   3. _extract_image_refs — regex scan of the final text, a fallback
        #      for any filename the model cites that no tool result carried.
        # When an image upload produced an authoritative match, show ONLY that
        # (the matched datasheet page). Suppressing specialist tool_images here
        # avoids cluttering a "which part is this?" result with runner-up
        # product photos from evaluation's visual_similarity_score.
        #
        # For a TEXT query that names a specific part ("show me the torque curve
        # for the RW 0.4"), resolve that part from the user's own words and make
        # its datasheet the authoritative image. This is deterministic and does
        # NOT depend on how the model called its tools or phrased its answer —
        # which otherwise varies run to run and can surface a wrong-part chart.
        # If the query doesn't name a resolvable part (e.g. a broad discovery
        # query), we fall back to the specialists' tool results as before.
        # Visual-intent gate for TEXT queries: only attach a part's image when
        # the engineer actually asked to SEE something ("show me the torque
        # curve for the RW3 0.06"). A spec-fit, comparison, or EOL question
        # that merely names a wheel ("compare the RW4 0.4 candidates") stays
        # text-only — naming a part no longer drags its datasheet into the
        # answer. The image-UPLOAD path (preproc_images) is exempt: an uploaded
        # image is itself an explicit request to identify/show the match.
        text_visual_intent = _has_visual_intent(user_input)

        query_images: list[dict] = []
        if not preproc_images and text_visual_intent:
            try:
                from .tools import _resolve_part_from_text, PARTS_DATA_DIR
                q_part = _resolve_part_from_text(user_input)
                if q_part:
                    ds = PARTS_DATA_DIR / q_part / "datasheet_page.png"
                    if ds.exists():
                        ref = _image_ref(q_part, "datasheet_page.png")
                        if ref:
                            query_images = [ref]
            except Exception:
                query_images = []

        # If we authoritatively resolved the part from the query text, that
        # image leads and specialist/regex images are suppressed (same "show
        # ONLY the intended part" principle as the image-upload path).
        if preproc_images:
            specialist_images = []
            regex_images = []
        elif query_images:
            specialist_images = []
            regex_images = []
        elif text_visual_intent:
            # Visual intent but no part resolved from the text (e.g. "show me
            # the torque curve" with the part named earlier in context): fall
            # back to whatever the specialists' tools / prose surfaced.
            specialist_images = tool_images
            regex_images = _extract_image_refs(final_text + "\n" + accumulated_context)
        else:
            # No visual intent → text-only answer. Suppress specialist and
            # regex images so a spec/compare/EOL query never renders a part
            # image (incl. visual_similarity_score's product photos) just
            # because a part was named.
            specialist_images = []
            regex_images = []

        images = []
        seen_keys = set()
        for img in (
            preproc_images
            + query_images
            + specialist_images
            + regex_images
        ):
            key = (img["part_id"], img["filename"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            images.append(img)
        if images:
            event_queue.put({
                "event": "images",
                "data": {"images": images},
            })

        # Emit done event
        event_queue.put({
            "event": "done",
            "data": {},
        })

    except Exception as e:
        # Top-level error — emit error and done so the stream terminates cleanly
        event_queue.put({
            "event": "error",
            "data": {"specialist": "system", "message": str(e)},
        })
        event_queue.put({
            "event": "done",
            "data": {},
        })
