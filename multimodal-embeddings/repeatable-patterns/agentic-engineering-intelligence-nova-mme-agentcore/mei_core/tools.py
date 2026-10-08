# ============================================================
# VENDORED COPY — do not edit here.
# This is a copy of agent/tools.py from the parent SkyLab Manufacturing
# Intelligence app, vendored into notebooks/mei_core/ so the notebooks run
# standalone (e.g. when this folder is moved to another repo). The app
# still runs on its own agent/ + api/ modules; this is an independent copy.
# Intra-package imports were rewritten to be package-relative.
# To refresh: re-run the vendoring step (see notebooks/README.md).
# ============================================================


# ============================================================
# Agent Tools — @tool functions for QPS, ASR, and Compliance
# ============================================================
# Each tool wraps an AWS service call (Bedrock KB, DynamoDB, S3).
# Tools return deterministic, structured data — no generative
# content in the retrieval path.
#
# For demo mode, tools use local JSON files and simulated responses.
# For production, swap to real AWS service calls.
# ============================================================

import json
import os
import re
import time
import base64
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from strands import tool

# Seed dataset-profile defaults (PARTS_DATA_DIR / PARTS_KB_ID / S3_VECTOR_*)
# from the active DATASET before any of the module-level env reads below.
# resolve() only fills UNSET vars, so explicit exports still win. Import is
# best-effort so the module still loads if the resolver is ever absent.
try:
    import sys as _sys
    _repo_root = str(Path(__file__).resolve().parent.parent)
    if _repo_root not in _sys.path:
        _sys.path.insert(0, _repo_root)
    from . import dataset_profiles as _dataset_profiles
    _dataset_profiles.resolve()
except Exception:
    pass

# ============================================================
# CONFIG
# ============================================================
# Set these via environment variables or override for production
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
PARTS_KNOWLEDGE_BASE_ID = os.environ.get("PARTS_KB_ID", "")
PROCEDURES_KNOWLEDGE_BASE_ID = os.environ.get("PROCEDURES_KB_ID", "")

# Cache for AgentCore Gateway tool names, discovered via tools/list on first
# use. Avoids paying for a tools/list round trip on every single kb_search /
# web_search_eol call — this was doubling the HTTPS round trips (and latency)
# for every Gateway-routed tool invocation. Tool names are stable for the
# lifetime of a Gateway, so a per-process cache is safe.
_GATEWAY_TOOL_NAME_CACHE: dict = {}

DATA_DIR = Path(__file__).parent.parent / "data"
# Local parts catalog directory. Defaults to the bundled synthetic AnyCompany
# catalog; dataset_profiles.resolve() and the notebook setup cells set
# PARTS_DATA_DIR before this module is used, and an explicit value always wins.
# All local part reads (specs, photos, ICDs, name resolution) go through this.
PARTS_DATA_DIR = Path(os.environ.get("PARTS_DATA_DIR", str(DATA_DIR / "synthetic-parts-data")))
# Local audit trail persistence (JSON Lines). No DynamoDB table exists in this
# app today, so log_decision writes here instead of claiming a production
# backend it doesn't have. Override via AUDIT_LOG_PATH if needed.
AUDIT_LOG_PATH = Path(os.environ.get("AUDIT_LOG_PATH", str(DATA_DIR / "audit_log.jsonl")))


def _part_id_from_s3_uri(s3_uri: str) -> str:
    """Extract a catalog part ID from a KB result's S3 URI.

    The KB source bucket can use any prefix layout — e.g.
    s3://bucket/synthetic-parts-data/<part_id>/file, or an https:// form.
    Rather than assume a fixed path segment, match each path segment against
    the actual part folders in the local catalog. This returns the segment that
    corresponds to a real local part, so item_id resolves regardless of the
    bucket's prefix.

    Falls back to the legacy "/parts/<id>/" parse if no local match is found
    (e.g. running without the local catalog present).
    """
    if not s3_uri:
        return ""
    # Strip scheme + host, split into path segments.
    path = re.sub(r"^[a-z]+://[^/]+/", "", s3_uri)
    segments = [seg for seg in path.split("/") if seg]

    parts_dir = PARTS_DATA_DIR
    if parts_dir.exists():
        for seg in segments:
            if (parts_dir / seg).is_dir():
                return seg

    # Legacy fallback: explicit /parts/<id>/ convention.
    if "/parts/" in s3_uri:
        tail = s3_uri.split("/parts/")[-1].split("/")
        return tail[0] if tail else ""
    return ""


# ============================================================
# SHARED: Knowledge Base Search
# ============================================================
@tool
def kb_search(query_text: str = "", query_image_b64: str = "",
              domain: str = "parts", top_k: int = 5) -> dict:
    """Search Bedrock Knowledge Base with text query.
    Returns ranked results from the parts catalog or work instructions.

    Args:
        query_text: Text description of what to search for.
        query_image_b64: Base64-encoded image to search with (optional, requires multimodal KB).
        domain: Which knowledge base to search — 'parts' for the parts catalog or 'procedures' for work instructions.
        top_k: Number of results to return.
    """
    kb_id = PARTS_KNOWLEDGE_BASE_ID if domain == "parts" else PROCEDURES_KNOWLEDGE_BASE_ID

    # ---- GATEWAY PATH: route KB retrieval through AgentCore Gateway ----
    gateway_id = os.environ.get("AGENTCORE_GATEWAY_ID", "")
    if gateway_id and query_text and domain == "parts":
        try:
            import boto3 as _boto3
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            import requests as _requests

            region = os.environ.get("BEDROCK_REGION", "us-east-1")
            session = _boto3.Session()
            credentials = session.get_credentials().get_frozen_credentials()
            gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"

            # Discover the KB Retrieve tool name (cached after first lookup —
            # avoids a tools/list round trip on every kb_search call)
            cache_key = (gateway_id, "kb_retrieve")
            retrieve_tool_name = _GATEWAY_TOOL_NAME_CACHE.get(cache_key)
            if retrieve_tool_name is None:
                list_payload = {"jsonrpc": "2.0", "id": "list-tools", "method": "tools/list", "params": {}}
                list_req = AWSRequest(method="POST", url=gateway_url, data=json.dumps(list_payload), headers={"Content-Type": "application/json"})
                SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(list_req)
                list_resp = _requests.post(gateway_url, headers=dict(list_req.headers), data=list_req.body, timeout=15)

                if list_resp.status_code == 200:
                    for t in list_resp.json().get("result", {}).get("tools", []):
                        if "Retrieve" in t.get("name", "") and "search" not in t.get("name", "").lower():
                            retrieve_tool_name = t["name"]
                            break
                if retrieve_tool_name:
                    _GATEWAY_TOOL_NAME_CACHE[cache_key] = retrieve_tool_name

            if retrieve_tool_name:
                # Call the KB Retrieve tool through Gateway
                payload = {
                    "jsonrpc": "2.0",
                    "id": "kb-retrieve",
                    "method": "tools/call",
                    "params": {
                        "name": retrieve_tool_name,
                        "arguments": {"retrievalQuery": {"text": query_text}}
                    }
                }
                call_req = AWSRequest(method="POST", url=gateway_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
                SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(call_req)
                call_resp = _requests.post(gateway_url, headers=dict(call_req.headers), data=call_req.body, timeout=30)

                if call_resp.status_code == 200:
                    rpc_result = call_resp.json().get("result", {})
                    content = rpc_result.get("content", [])

                    # Parse the nested retrievalResults from the response
                    results = []
                    for item in content if isinstance(content, list) else [content]:
                        text = item.get("text", "") if isinstance(item, dict) else str(item)
                        try:
                            parsed = json.loads(text) if text.startswith("{") else None
                        except (json.JSONDecodeError, TypeError):
                            parsed = None

                        if parsed and "retrievalResults" in parsed:
                            for r in parsed["retrievalResults"]:
                                r_content = r.get("content", {})
                                r_location = r.get("location", {})
                                r_score = r.get("score", 0.0)
                                s3_uri = r_location.get("s3Location", {}).get("uri", "")

                                item_id = _part_id_from_s3_uri(s3_uri)

                                local_meta = {}
                                if item_id:
                                    specs_file = PARTS_DATA_DIR / item_id / "specs.json"
                                    if specs_file.exists():
                                        local_meta = json.loads(specs_file.read_text())

                                results.append({
                                    "content": r_content.get("text", ""),
                                    "score": r_score,
                                    "source": s3_uri,
                                    "item_id": item_id,
                                    "metadata": local_meta if local_meta else {},
                                    "retrieval_path": "AgentCore Gateway",
                                })

                    if results:
                        results.sort(key=lambda x: x.get("score", 0), reverse=True)
                        return {"results": results[:top_k], "count": min(top_k, len(results))}

        except Exception:
            pass  # Fall through to direct path

    # ---- DIRECT PATH: call Bedrock Knowledge Bases Retrieve API ----
    if kb_id:
        import boto3
        client = boto3.client("bedrock-agent-runtime", region_name=BEDROCK_REGION)

        retrieval_query = {}
        if query_image_b64:
            # image.inlineContent expects raw bytes, not base64 string
            image_bytes = base64.b64decode(query_image_b64)
            # Detect format from magic bytes
            if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                img_format = "png"
            elif image_bytes[:2] == b'\xff\xd8':
                img_format = "jpeg"
            elif image_bytes[:4] == b'GIF8':
                img_format = "gif"
            elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
                img_format = "webp"
            else:
                img_format = "png"  # default for screenshots
            retrieval_query = {
                "type": "IMAGE",
                "image": {
                    "format": img_format,
                    "inlineContent": image_bytes
                }
            }
        else:
            # The standard Retrieve API expects retrievalQuery = {"text": ...}
            retrieval_query = {"text": query_text}

        # Managed Knowledge Bases require `managedSearchConfiguration`; classic
        # (vector) KBs require `vectorSearchConfiguration`. This asset uses
        # Managed KBs, so try that first and fall back for classic KBs.
        search_configs = [
            {"managedSearchConfiguration": {"numberOfResults": top_k}},
            {"vectorSearchConfiguration": {"numberOfResults": top_k}},
        ]
        response = None
        last_error = None
        for cfg in search_configs:
            try:
                response = client.retrieve(
                    knowledgeBaseId=kb_id,
                    retrievalQuery=retrieval_query,
                    retrievalConfiguration=cfg,
                )
                break
            except Exception as e:
                code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
                msg = str(e)
                # Only fall through on the specific "wrong config shape" error;
                # surface anything else (permissions, region, bad ID, etc.).
                if code == "ValidationException" and (
                    "managedSearchConfiguration" in msg or "vectorSearchConfiguration" in msg
                ):
                    last_error = e
                    continue
                return {
                    "results": [],
                    "count": 0,
                    "error": f"Knowledge Base retrieve failed ({type(e).__name__}): {e}",
                    "knowledge_base_id": kb_id,
                    "region": BEDROCK_REGION,
                    "query_type": "image" if query_image_b64 else "text",
                }

        if response is None:
            return {
                "results": [],
                "count": 0,
                "error": f"Knowledge Base retrieve failed: {last_error}",
                "knowledge_base_id": kb_id,
                "region": BEDROCK_REGION,
            }

        results = []
        for r in response.get("retrievalResults", []):
            # Extract metadata from KB response
            meta = r.get("metadata", {})
            content = r.get("content", {})
            location = r.get("location", {})
            score = r.get("score", 0.0)

            # Get source file info
            s3_uri = location.get("s3Location", {}).get("uri", "")
            source_type = meta.get("x-amz-bedrock-kb-source-file-mime-type", "")
            modality = meta.get("x-amz-bedrock-kb-source-file-modality", "")

            # Try to extract part/step ID from the S3 path. Parts are matched
            # against real catalog folders (works under any bucket prefix);
            # procedures keep the legacy path convention.
            item_id = ""
            if domain == "parts":
                item_id = _part_id_from_s3_uri(s3_uri)
            elif "/procedures/" in s3_uri:
                parts = s3_uri.split("/procedures/")[-1].split("/")
                item_id = "/".join(parts[:2]) if len(parts) >= 2 else parts[0] if parts else ""

            # Load local specs/meta if available for richer display
            local_meta = {}
            if domain == "parts" and item_id:
                specs_file = PARTS_DATA_DIR / item_id / "specs.json"
                if specs_file.exists():
                    local_meta = json.loads(specs_file.read_text())
            elif domain == "procedures" and item_id:
                meta_file = DATA_DIR / "procedures" / item_id / "step_meta.json"
                if meta_file.exists():
                    local_meta = json.loads(meta_file.read_text())

            results.append({
                "content": content.get("text", ""),
                "score": score,
                "source": s3_uri,
                "source_type": source_type,
                "modality": modality,
                "item_id": item_id,
                "metadata": local_meta if local_meta else meta,
                "raw_metadata": meta,
            })
        return {"results": results, "count": len(results)}

    # Demo mode: search local JSON files
    return _demo_search(query_text, domain, top_k)


def _demo_search(query_text: str, domain: str, top_k: int) -> dict:
    """Demo-mode search using local JSON files when no KB is configured."""
    results = []
    if domain == "parts":
        parts_dir = PARTS_DATA_DIR
        if parts_dir.exists():
            for part_dir in sorted(parts_dir.iterdir()):
                if not part_dir.is_dir():
                    continue
                specs_file = part_dir / "specs.json"
                if specs_file.exists():
                    specs = json.loads(specs_file.read_text())
                    # Simple keyword match for demo
                    spec_text = json.dumps(specs).lower()
                    query_lower = query_text.lower() if query_text else ""
                    relevance = sum(1 for word in query_lower.split() if word in spec_text)
                    results.append({
                        "content": json.dumps(specs, indent=2),
                        "score": min(0.95, 0.5 + relevance * 0.1),
                        "source": str(specs_file),
                        "item_id": part_dir.name,
                        "metadata": specs
                    })
    else:
        procs_dir = DATA_DIR / "procedures"
        if procs_dir.exists():
            for proc_dir in sorted(procs_dir.iterdir()):
                if not proc_dir.is_dir():
                    continue
                for step_dir in sorted(proc_dir.iterdir()):
                    if not step_dir.is_dir():
                        continue
                    meta_file = step_dir / "step_meta.json"
                    if meta_file.exists():
                        meta = json.loads(meta_file.read_text())
                        meta_text = json.dumps(meta).lower()
                        query_lower = query_text.lower() if query_text else ""
                        relevance = sum(1 for word in query_lower.split() if word in meta_text)
                        results.append({
                            "content": json.dumps(meta, indent=2),
                            "score": min(0.95, 0.5 + relevance * 0.1),
                            "source": str(meta_file),
                            "metadata": meta
                        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results[:top_k], "count": min(top_k, len(results))}


# ============================================================
# QPS TOOLS
# ============================================================
def _resolve_part_id(identifier: str) -> Optional[str]:
    """Resolve a human-friendly part name (e.g. 'RW 0.03', 'RW3 0.06') to its
    catalog folder ID (e.g. 'rw_rl_0030'). Falls back to None if no match.

    Looks up by exact folder name first (fast path for callers that already
    have the ID), then falls back to a case-insensitive match against each
    part's `name` field in specs.json. This lets specialists that received a
    display name directly from the engineer (rather than an ID surfaced by a
    prior Catalog step) still resolve it without another specialist hop.
    """
    parts_dir = PARTS_DATA_DIR
    if not parts_dir.exists():
        return None

    # Fast path: identifier is already a valid folder ID
    if (parts_dir / identifier / "specs.json").exists():
        return identifier

    identifier_norm = identifier.strip().lower()
    exact_matches = []
    substring_matches = []
    for part_dir in sorted(parts_dir.iterdir()):
        if not part_dir.is_dir():
            continue
        specs_file = part_dir / "specs.json"
        if not specs_file.exists():
            continue
        try:
            specs = json.loads(specs_file.read_text())
        except json.JSONDecodeError:
            continue
        name = str(specs.get("name", "")).strip().lower()
        model = str(specs.get("model", "")).strip().lower()

        if identifier_norm in (name, model):
            exact_matches.append(part_dir.name)
        # Catalog names are typically "<vendor> <model>" (e.g. "AnyCompany
        # RW3 0.06"), so an engineer-provided name like "RW3 0.06" or
        # "AnyCompany RW3 0.06" won't exact-match but will substring-match.
        elif identifier_norm and (identifier_norm in name or identifier_norm in model):
            substring_matches.append(part_dir.name)

    # Prefer an exact match; only fall back to substring match if unambiguous
    # (exactly one candidate) to avoid silently picking the wrong part.
    if len(exact_matches) == 1:
        return exact_matches[0]
    if not exact_matches and len(substring_matches) == 1:
        return substring_matches[0]

    # Numeric-value fallback. Reaction-wheel display names carry an inconsistent
    # family prefix (e.g. "RW 0.03", "RW3 0.06", "RW4 0.4"), so an engineer who
    # types "RW 0.4" (correct value, wrong/absent family digit) won't substring-
    # match the stored "RW4 0.4". But the momentum VALUE (0.003, 0.01, ... 5.0)
    # is unique per part, so match on that instead. Extract the decimal number
    # from the query and from each part's name/model; if exactly one part shares
    # that value, resolve to it. This makes "RW 0.4", "RW4 0.4", "RW4-0.4",
    # "0.4 Nms" all resolve to the same part.
    query_val = _extract_momentum_value(identifier_norm)
    if query_val is not None:
        value_matches = []
        for part_dir in sorted(parts_dir.iterdir()):
            if not part_dir.is_dir():
                continue
            specs_file = part_dir / "specs.json"
            if not specs_file.exists():
                continue
            try:
                specs = json.loads(specs_file.read_text())
            except json.JSONDecodeError:
                continue
            name = str(specs.get("name", ""))
            model = str(specs.get("model", ""))
            for field in (name, model):
                fv = _extract_momentum_value(field.lower())
                if fv is not None and abs(fv - query_val) < 1e-9:
                    value_matches.append(part_dir.name)
                    break
        if len(set(value_matches)) == 1:
            return value_matches[0]

    return None


def _extract_momentum_value(text: str) -> Optional[float]:
    """Pull the reaction-wheel momentum value (a decimal like 0.4, 0.06, 5.0)
    out of a string. Ignores a leading family prefix digit that is glued to
    'rw' (e.g. the '4' in 'rw4 0.4') so it doesn't get mistaken for the value.
    Returns the float, or None if no decimal number is present.

    Examples: 'rw4 0.4' -> 0.4, 'rw 0.4' -> 0.4, 'rw4-0.4' -> 0.4,
              '0.4 nms' -> 0.4, 'rw3 0.06' -> 0.06, 'rw 5.0' -> 5.0.
    """
    if not text:
        return None
    # Strip a family prefix like 'rw4' / 'rw3' -> 'rw' so its digit isn't read
    # as the value. Only when the digit is directly attached to 'rw'.
    cleaned = re.sub(r'\brw(\d)\b', 'rw', text)
    cleaned = re.sub(r'\brw(\d)\s', 'rw ', cleaned)
    # Find decimal numbers (require a dot so we don't grab voltages/counts like
    # '28' or '5' spuriously; momentum values in this catalog are all decimals).
    matches = re.findall(r'\d+\.\d+', cleaned)
    if not matches:
        return None
    # If multiple decimals appear, prefer the first — the momentum is typically
    # the leading spec token in these names/queries.
    try:
        return float(matches[0])
    except ValueError:
        return None


def _resolve_part_from_text(text: str) -> Optional[str]:
    """Best-effort resolve a part from free-form query text (e.g. the whole
    sentence "show me the torque curve for the RW 0.4"). Tries the momentum
    value first (unique per reaction wheel), then a whole-string name/model
    substring. Returns a folder ID only when the match is unambiguous, else
    None — so an ambiguous query never silently filters to a wrong part.
    """
    if not text:
        return None
    parts_dir = PARTS_DATA_DIR
    if not parts_dir.exists():
        return None

    # Gather (part_id, momentum_value) once.
    catalog = []
    for part_dir in sorted(parts_dir.iterdir()):
        if not part_dir.is_dir():
            continue
        specs_file = part_dir / "specs.json"
        if not specs_file.exists():
            continue
        try:
            specs = json.loads(specs_file.read_text())
        except json.JSONDecodeError:
            continue
        name = str(specs.get("name", ""))
        model = str(specs.get("model", ""))
        val = _extract_momentum_value(name.lower())
        if val is None:
            val = _extract_momentum_value(model.lower())
        catalog.append((part_dir.name, val))

    q_val = _extract_momentum_value(text.strip().lower())
    if q_val is not None:
        hits = [pid for pid, v in catalog if v is not None and abs(v - q_val) < 1e-9]
        if len(set(hits)) == 1:
            return hits[0]

    return None


@tool
def get_part_specs(part_id: str) -> dict:
    """Retrieve structured specifications for a part.
    Returns all spec fields from the parts catalog.

    Accepts either the catalog folder ID (e.g. 'rw_rl_0030') or the
    human-friendly display name as it appears in the catalog (e.g.
    'RW 0.03' or 'Vendor Name RW 0.03') — both resolve to the same part.

    Args:
        part_id: The part's catalog folder ID or display name.
    """
    resolved_id = _resolve_part_id(part_id)
    if resolved_id is None:
        return {"error": f"Part '{part_id}' not found"}
    specs_file = PARTS_DATA_DIR / resolved_id / "specs.json"
    result = json.loads(specs_file.read_text())
    result["part_id"] = resolved_id
    return result


@tool
def compare_parts(part_id_a: str, part_id_b: str) -> dict:
    """Deterministic field-by-field comparison of two parts' specs.
    Returns structured diff with match/mismatch status per field.
    No generative AI — pure data comparison.

    Args:
        part_id_a: First part — catalog folder ID or display name (both resolve).
        part_id_b: Second part — catalog folder ID or display name (both resolve).
    """
    specs_a = get_part_specs(part_id_a)
    specs_b = get_part_specs(part_id_b)

    if "error" in specs_a or "error" in specs_b:
        return {"error": "One or both parts not found",
                "part_a": specs_a, "part_b": specs_b}

    all_keys = sorted(set(list(specs_a.keys()) + list(specs_b.keys())))
    comparison = []
    matches = 0
    for key in all_keys:
        val_a = str(specs_a.get(key, "—"))
        val_b = str(specs_b.get(key, "—"))
        is_match = val_a == val_b
        if is_match:
            matches += 1
        comparison.append({
            "field": key,
            "part_a": val_a,
            "part_b": val_b,
            "status": "match" if is_match else "different"
        })

    return {
        "part_a_name": specs_a.get("name", part_id_a),
        "part_b_name": specs_b.get("name", part_id_b),
        "total_fields": len(all_keys),
        "matches": matches,
        "differences": len(all_keys) - matches,
        "comparison": comparison
    }


# ============================================================
# ASR TOOLS
# ============================================================
@tool
def get_step_info(procedure_id: str, step_number: int) -> dict:
    """Get full metadata for a specific assembly step.

    Args:
        procedure_id: The procedure identifier (e.g., 'proc_001_cubesat_stack').
        step_number: The step number within the procedure.
    """
    proc_dir = DATA_DIR / "procedures" / procedure_id
    if not proc_dir.exists():
        return {"error": f"Procedure '{procedure_id}' not found"}

    for step_dir in proc_dir.iterdir():
        if not step_dir.is_dir():
            continue
        meta_file = step_dir / "step_meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            if meta.get("step_number") == step_number:
                meta["has_reference_image"] = (step_dir / "reference.jpg").exists()
                meta["has_instruction"] = (step_dir / "instruction.png").exists()
                return meta

    return {"error": f"Step {step_number} not found in procedure '{procedure_id}'"}


@tool
def get_procedure_steps(procedure_id: str) -> dict:
    """Get the ordered list of all steps for an assembly procedure.

    Args:
        procedure_id: The procedure identifier (e.g., 'proc_001_cubesat_stack').
    """
    proc_dir = DATA_DIR / "procedures" / procedure_id
    if not proc_dir.exists():
        return {"error": f"Procedure '{procedure_id}' not found"}

    steps = []
    for step_dir in sorted(proc_dir.iterdir()):
        if not step_dir.is_dir():
            continue
        meta_file = step_dir / "step_meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            steps.append({
                "step_number": meta.get("step_number"),
                "step_name": meta.get("step_name"),
                "critical_step": meta.get("critical_step", False),
                "estimated_time_min": meta.get("estimated_time_min"),
            })

    steps.sort(key=lambda x: x["step_number"])
    return {
        "procedure_id": procedure_id,
        "procedure_name": steps[0].get("step_name", procedure_id) if steps else procedure_id,
        "total_steps": len(steps),
        "steps": steps
    }


@tool
def check_step_prerequisites(procedure_id: str, step_number: int) -> dict:
    """Check whether prior steps have been verified before allowing
    the current step to proceed. Enforces sequential process control.

    Args:
        procedure_id: The procedure identifier.
        step_number: The step to check prerequisites for.
    """
    # In production, this queries DynamoDB for verification records.
    # Demo mode: return simulated prerequisite status.
    if step_number <= 1:
        return {
            "procedure_id": procedure_id,
            "step_number": step_number,
            "prerequisites_met": True,
            "message": "First step — no prerequisites required."
        }

    # Simulate: all prior steps are verified except the immediately preceding one
    unverified = []
    for i in range(1, step_number):
        # In production: check DynamoDB for verification record
        # Demo: randomly mark some as unverified for demonstration
        pass

    return {
        "procedure_id": procedure_id,
        "step_number": step_number,
        "prerequisites_met": len(unverified) == 0,
        "prior_steps_required": list(range(1, step_number)),
        "unverified_steps": unverified,
        "message": "All prior steps verified." if not unverified
                   else f"Steps {unverified} have not been verified yet."
    }


# ============================================================
# COMPLIANCE TOOLS
# ============================================================
@tool
def log_decision(decision_type: str, details: str) -> dict:
    """Write an audit trail entry for a part substitution decision (AS9100
    8.4 External Providers / 8.5.6 Control of Changes). Appends a JSON Lines
    record to the local audit log so evaluation decisions are retained.

    Args:
        decision_type: The kind of substitution decision being logged, e.g.
            'evaluation' (spec-fit scoring ran), 'memo' (justification memo
            drafted), or 'impact_assessment' (IIA document generated).
        details: JSON string with decision details (part IDs, vendors,
            scores, qualification standards, rationale).
    """
    return _write_audit_entry(decision_type, details)


def _write_audit_entry(decision_type: str, details) -> dict:
    """Shared audit-write path used by log_decision (LLM tool call) and by
    the deterministic call sites (Evaluator panel, IIA synthesis) that log
    automatically without going through the LLM."""
    try:
        detail_data = json.loads(details) if isinstance(details, str) else details
    except (json.JSONDecodeError, TypeError):
        detail_data = {"raw": details}

    log_entry = {
        "decision_id": f"{decision_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}",
        "decision_type": decision_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": detail_data,
        "compliance_standard": "AS9100 Rev D",
        # This app evaluates part substitutions (a change decision involving
        # externally-provided parts) — it does not run production/inspection
        # workflows, so only the clauses that actually apply are cited.
        "applicable_sections": ["8.4 (External Providers)", "8.5.6 (Control of Changes)"],
    }

    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        status = "logged"
    except OSError as e:
        # Never let audit-log I/O break the calling evaluation/memo/IIA flow.
        status = f"log_write_failed: {e}"

    return {
        "status": status,
        "entry": log_entry,
    }


@tool
def check_qualification_status(part_id: str, standard: str = "") -> dict:
    """Check whether a part has valid qualification records against
    a specific standard (e.g., MIL-DTL-83513, ECSS-E-ST-33-01C).

    Args:
        part_id: The part identifier to check.
        standard: The qualification standard to verify against (optional).
    """
    specs_file = PARTS_DATA_DIR / part_id / "specs.json"
    if not specs_file.exists():
        return {"error": f"Part '{part_id}' not found"}

    specs = json.loads(specs_file.read_text())
    part_standard = specs.get("qual_standard", "Unknown")

    if standard:
        is_qualified = standard.lower() in part_standard.lower()
        return {
            "part_id": part_id,
            "part_name": specs.get("name", part_id),
            "requested_standard": standard,
            "part_qualification": part_standard,
            "is_qualified": is_qualified,
            "message": f"Part is qualified to {part_standard}."
                       if is_qualified
                       else f"Part qualification ({part_standard}) does not match requested standard ({standard})."
        }

    return {
        "part_id": part_id,
        "part_name": specs.get("name", part_id),
        "qualification_standard": part_standard,
        "message": f"Part is qualified to {part_standard}."
    }


# ============================================================
# WORKFLOW TOOLS (multi-step agent support)
# ============================================================
@tool
def generate_substitution_memo(reference_part_id: str, candidate_part_id: str,
                                rationale: str, similarity_score: float = 0.0) -> dict:
    """Generate a Part Substitution Justification (PSJ) memo for engineering review.
    Returns both structured data and a formatted markdown document.

    Args:
        reference_part_id: The original part being replaced.
        candidate_part_id: The proposed substitute part.
        rationale: Engineer's rationale for the substitution.
        similarity_score: The crossmodal similarity score from the search.
    """
    ref_specs = get_part_specs(reference_part_id)
    cand_specs = get_part_specs(candidate_part_id)
    comparison = compare_parts(reference_part_id, candidate_part_id)

    doc_id = f"PSJ-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ref_name = ref_specs.get("name", reference_part_id)
    cand_name = cand_specs.get("name", candidate_part_id)
    ref_vendor = ref_specs.get("vendor", "Unknown")
    cand_vendor = cand_specs.get("vendor", "Unknown")
    ref_qual = ref_specs.get("qual_standard", "Unknown")
    cand_qual = cand_specs.get("qual_standard", "Unknown")
    ref_lifecycle = ref_specs.get("lifecycle", {}).get("lifecycle_status", "Unknown")
    cand_lifecycle = cand_specs.get("lifecycle", {}).get("lifecycle_status", "Unknown")

    differences = [c for c in comparison.get("comparison", []) if c.get("status") == "different"]
    matches = comparison.get("matches", 0)
    total = comparison.get("total_fields", 0)

    # Build the spec comparison table rows
    spec_table_rows = ""
    for c in comparison.get("comparison", []):
        verdict = "Match" if c["status"] == "match" else "DIFFERENT"
        spec_table_rows += f"| {c['field']} | {c['part_a']} | {c['part_b']} | {verdict} |\n"

    # Build the formatted markdown document
    markdown = f"""# PART SUBSTITUTION JUSTIFICATION

**Document No:** {doc_id}
**Date:** {date_str}
**Status:** DRAFT — Pending Engineering Review

---

## 1. Reference Part (being replaced)

| Field | Value |
|-------|-------|
| Name | {ref_name} |
| Part ID | {reference_part_id} |
| Vendor | {ref_vendor} |
| Qualification Standard | {ref_qual} |
| Lifecycle Status | {ref_lifecycle} |

## 2. Proposed Substitute

| Field | Value |
|-------|-------|
| Name | {cand_name} |
| Part ID | {candidate_part_id} |
| Vendor | {cand_vendor} |
| Qualification Standard | {cand_qual} |
| Lifecycle Status | {cand_lifecycle} |

## 3. Justification

{rationale}

## 4. Technical Comparison

**Summary:** {matches}/{total} fields match. {len(differences)} differences identified.

| Spec | Reference | Candidate | Verdict |
|------|-----------|-----------|---------|
{spec_table_rows}

## 5. Key Differences (require engineering review)

"""
    if differences:
        for d in differences:
            markdown += f"- **{d['field']}**: Reference = `{d['part_a']}` → Candidate = `{d['part_b']}`\n"
    else:
        markdown += "No differences identified.\n"

    markdown += f"""
## 6. Qualification Delta

- Reference standard: {ref_qual}
- Candidate standard: {cand_qual}
- {"Standards match." if ref_qual.lower() == cand_qual.lower() else "**Standards differ. Requalification assessment required.**"}

## 7. Risk Assessment

- Reference lifecycle: {ref_lifecycle}
- Candidate lifecycle: {cand_lifecycle}
- Candidate lead time: {cand_specs.get('lifecycle', {}).get('typical_lead_time_weeks', 'Unknown')} weeks
- Candidate lead time risk: {cand_specs.get('lifecycle', {}).get('lead_time_risk', 'Unknown')}

## 8. Required Approvals

| Role | Signature | Date |
|------|-----------|------|
| Lead Systems Engineer | _______________ | _______ |
| Quality Assurance Manager | _______________ | _______ |
| Program Manager (if cost impact > $10K) | _______________ | _______ |

## 9. Applicable Standards

- AS9100 Rev D Section 8.5.6 — Control of Changes
- AS9100 Rev D Section 8.4 — Control of Externally Provided Processes

## 10. References

- {ref_name} datasheet ({ref_vendor})
- {cand_name} datasheet ({cand_vendor})
- Interface Control Documents (ICDs) for both parts

---

*This document was generated as a DRAFT for engineering review. It does not constitute approval of the substitution. The signing engineer accepts responsibility for the technical decision.*
"""

    return {
        "document_id": doc_id,
        "date": date_str,
        "status": "DRAFT — Pending Engineering Review",
        "markdown": markdown,
        "reference_part": {"id": reference_part_id, "name": ref_name, "vendor": ref_vendor},
        "proposed_substitute": {"id": candidate_part_id, "name": cand_name, "vendor": cand_vendor},
        "differences_count": len(differences),
        "matches_count": matches,
        "total_fields": total,
    }



# SPEC-DRIVEN SUBSTITUTION TOOLS
# ============================================================
# These make substitution a spec-driven engineering decision, not an
# image-similarity match. The requirements schema (data/requirements_schema.json)
# defines the critical specs per category and how each is compared.
#
# The tools assemble EVIDENCE and flag out-of-tolerance specs. They never
# recommend or approve a substitution — the engineer decides.
# ============================================================

REQUIREMENTS_SCHEMA_FILE = DATA_DIR / "requirements_schema.json"


def _load_requirements_schema() -> dict:
    """Load the per-category critical-spec requirements schema."""
    if REQUIREMENTS_SCHEMA_FILE.exists():
        try:
            return json.loads(REQUIREMENTS_SCHEMA_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _to_float(value):
    """Extract the first numeric value from a spec value. None if not numeric."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(m.group()) if m else None


def _parse_range(value):
    """Parse an operating range like '-65 to +200' or 'up to 28' into (lo, hi)."""
    s = str(value)
    nums = re.findall(r"-?\d+(?:\.\d+)?", s)
    if not nums:
        return (None, None)
    if "up to" in s.lower():
        return (None, float(nums[-1]))
    if len(nums) >= 2:
        return (float(nums[0]), float(nums[1]))
    return (float(nums[0]), float(nums[0]))


def _norm(value):
    """Normalize a categorical value for comparison.
    Handles numeric-vs-string mismatches (e.g., 28.0 vs "28")."""
    if value is None:
        return ""
    # If both sides might be numeric, normalize to avoid "28.0" != "28"
    try:
        f = float(value)
        # If it's a whole number, format without decimal
        if f == int(f):
            return str(int(f))
        return str(f)
    except (ValueError, TypeError):
        return str(value).strip().lower()


def _evaluate_spec(rule, candidate, reference, required, tolerance_pct):
    """Apply one comparison rule. Returns (status, note).

    status: 'pass' | 'flag' | 'review' | 'unknown'
    """
    # Choose the comparison target: user requirement takes precedence for
    # the *_required / match / range rules; *_reference rules use the reference part.
    if rule == "match":
        target = required if required is not None else reference
        if candidate is None or target is None:
            return ("unknown", "missing candidate or target value")
        # Check if the target is contained in the candidate (handles "RS-422" matching
        # "RS-422 or Redundant RS-485") or if they're equal after normalization.
        cand_norm = str(candidate).strip().lower()
        target_norm = str(target).strip().lower()
        if cand_norm == target_norm or target_norm in cand_norm:
            return ("pass", f"matches ('{target}' found in '{candidate}')")
        return ("flag", f"candidate '{candidate}' does not match required '{target}'")

    if rule in ("candidate_gte_required", "candidate_gte_reference"):
        target_raw = required if (rule == "candidate_gte_required" and required is not None) else reference
        c, t = _to_float(candidate), _to_float(target_raw)
        if c is None or t is None:
            return ("unknown", "non-numeric or missing value")
        if c >= t:
            return ("pass", f"{c} >= {t}")
        return ("flag", f"{c} < required {t}")

    if rule == "candidate_lte_reference_within_pct":
        c, r = _to_float(candidate), _to_float(reference)
        if c is None or r is None:
            return ("unknown", "non-numeric or missing value")
        tol = (tolerance_pct or 0) / 100.0
        limit = r * (1 + tol)
        if c <= limit:
            return ("pass", f"{c} <= {limit:g} (ref {r} +{tolerance_pct or 0}%)")
        return ("flag", f"{c} exceeds {limit:g} (ref {r} +{tolerance_pct or 0}%)")

    if rule == "range_envelops_required":
        target_raw = required if required is not None else reference
        c_lo, c_hi = _parse_range(candidate)
        t_lo, t_hi = _parse_range(target_raw)
        if c_lo is None or c_hi is None or t_lo is None or t_hi is None:
            return ("unknown", "could not parse one or both ranges")
        if c_lo <= t_lo and c_hi >= t_hi:
            return ("pass", f"[{c_lo}, {c_hi}] envelops [{t_lo}, {t_hi}]")
        return ("flag", f"[{c_lo}, {c_hi}] does not cover required [{t_lo}, {t_hi}]")

    if rule == "qual_review":
        if candidate is None or reference is None:
            return ("unknown", "missing qualification standard")
        if _norm(candidate) == _norm(reference):
            return ("pass", f"same standard ({candidate})")
        return ("review", f"differs from reference ({reference}); requires engineering review")

    return ("unknown", f"unknown rule '{rule}'")


@tool
def get_substitution_requirements(category: str) -> dict:
    """Return the critical specs an engineer must consider for a substitution
    in the given part category, split into what to ask the user for versus
    what is compared automatically from the catalog.

    Use this BEFORE assessing candidates: prompt the engineer for any of the
    'required_from_user' specs they haven't provided, so no recommendation is
    made on incomplete data.

    Args:
        category: Part category, e.g. 'reaction_wheel', 'connector', 'solar_panel', 'earth_horizon_sensor'.
    """
    schema = _load_requirements_schema()
    cats = schema.get("categories", {})
    if category not in cats:
        return {
            "error": f"No requirements schema for category '{category}'.",
            "available_categories": sorted(cats.keys()),
        }

    specs = cats[category]["critical_specs"]
    required = [
        {"field": s["field"], "label": s["label"], "rule": s["rule"]}
        for s in specs if s.get("required_from_user")
    ]
    auto = [
        {"field": s["field"], "label": s["label"], "rule": s["rule"],
         "tolerance_pct": s.get("tolerance_pct")}
        for s in specs if not s.get("required_from_user")
    ]
    return {
        "category": category,
        "must_ask_user": required,
        "compared_automatically": auto,
        "rules_glossary": schema.get("_rules", {}),
        "guidance": "Prompt the engineer for any 'must_ask_user' specs not yet provided before assessing candidates.",
    }


@tool
def score_substitution_fit(reference_part_id: str, candidate_part_id: str,
                           requirements_json: str = "") -> dict:
    """Deterministically compare a candidate part against a reference part
    (and the engineer's stated requirements) spec-by-spec, flagging every
    spec that is out of tolerance. Also surfaces lifecycle/supply-chain risk.

    This assembles EVIDENCE for an engineering decision. It does NOT recommend
    or approve a substitution.

    Args:
        reference_part_id: The part being replaced — either its catalog folder
            ID (e.g., 'rw_rl_0060') or its display name as shown in the
            catalog (e.g., 'RW3 0.06', 'AnyCompany RW3 0.06'). Both resolve.
        candidate_part_id: The proposed substitute — same format as above.
        requirements_json: Optional JSON string of the engineer's stated requirements,
            keyed by spec field (e.g., '{"momentum_storage_nms": 0.05, "voltage_v": "5.0",
            "interface": "RS-422", "operating_temp_c": "-20 to +60"}'). When provided,
            these take precedence over the reference values for the relevant rules.
    """
    ref = get_part_specs(reference_part_id)
    cand = get_part_specs(candidate_part_id)
    if "error" in ref or "error" in cand:
        return {"error": "One or both parts not found",
                "reference": ref, "candidate": cand}
    # Use the resolved catalog IDs (not whatever free-text name was passed
    # in) so downstream consumers — memos, audit log, frontend — get a
    # stable, real part_id rather than an arbitrary display-name string.
    reference_part_id = ref.get("part_id", reference_part_id)
    candidate_part_id = cand.get("part_id", candidate_part_id)

    category = ref.get("category", "")
    schema = _load_requirements_schema()
    cat_schema = schema.get("categories", {}).get(category)
    if not cat_schema:
        return {"error": f"No requirements schema for category '{category}'.",
                "available_categories": sorted(schema.get("categories", {}).keys())}

    # Parse the engineer's stated requirements, if any.
    requirements = {}
    if requirements_json:
        try:
            parsed = json.loads(requirements_json)
            if isinstance(parsed, dict):
                requirements = parsed
        except json.JSONDecodeError:
            pass

    # Warn about any required-from-user specs that were not supplied.
    missing_inputs = [
        {"field": s["field"], "label": s["label"]}
        for s in cat_schema["critical_specs"]
        if s.get("required_from_user") and s["field"] not in requirements
    ]

    results = []
    counts = {"pass": 0, "flag": 0, "review": 0, "unknown": 0}
    for spec in cat_schema["critical_specs"]:
        field = spec["field"]
        rule = spec["rule"]
        tol = spec.get("tolerance_pct")
        cand_val = cand.get(field)
        ref_val = ref.get(field)
        req_val = requirements.get(field)

        status, note = _evaluate_spec(rule, cand_val, ref_val, req_val, tol)
        counts[status] += 1
        results.append({
            "field": field,
            "label": spec["label"],
            "rule": rule,
            "reference_value": ref_val,
            "candidate_value": cand_val,
            "required_value": req_val,
            "status": status,
            "note": note,
        })

    # Lifecycle / supply-chain risk on the candidate (and note if the
    # reference is obsolete, which is often why we're here).
    cand_life = cand.get("lifecycle", {})
    ref_life = ref.get("lifecycle", {})
    lifecycle_flags = []
    cand_status = _norm(cand_life.get("lifecycle_status"))
    if cand_status in ("obsolete", "nrnd (not recommended for new designs)", "nrnd"):
        lifecycle_flags.append(
            f"Candidate lifecycle status is '{cand_life.get('lifecycle_status')}' — availability risk."
        )
    if _norm(cand_life.get("lead_time_risk")) in ("high", "critical", "medium to high"):
        lifecycle_flags.append(
            f"Candidate lead-time risk is '{cand_life.get('lead_time_risk')}'."
        )

    out_of_tolerance = [r for r in results if r["status"] in ("flag", "review", "unknown")]
    summary = (
        f"{counts['pass']} of {len(results)} critical specs pass. "
        f"{counts['flag']} flagged, {counts['review']} need review, {counts['unknown']} unknown."
    )
    if out_of_tolerance:
        summary += " Not a drop-in replacement; the flagged specs require engineering review."
    else:
        summary += " No spec flags, but qualification and engineering sign-off are still required."

    return {
        "reference_part": {"id": reference_part_id, "name": ref.get("name", reference_part_id)},
        "candidate_part": {"id": candidate_part_id, "name": cand.get("name", candidate_part_id)},
        "category": category,
        "requirements_used": requirements,
        "missing_user_inputs": missing_inputs,
        "spec_results": results,
        "counts": counts,
        "out_of_tolerance": out_of_tolerance,
        "lifecycle": {
            "reference_status": ref_life.get("lifecycle_status"),
            "candidate_status": cand_life.get("lifecycle_status"),
            "candidate_lead_time_weeks": cand_life.get("typical_lead_time_weeks"),
            "flags": lifecycle_flags,
        },
        "summary": summary,
        "disclaimer": "Evidence only. This tool does not recommend or approve a substitution; the engineer decides.",
    }


# ============================================================
# WEB SEARCH — Real-time EOL/market data (AgentCore Web Search)
# ============================================================
AGENTCORE_GATEWAY_ID = os.environ.get("AGENTCORE_GATEWAY_ID", "")


@tool
def web_search_eol(query: str) -> dict:
    """Search the web for current EOL notices, lifecycle status, vendor
    announcements, and lead-time data for aerospace components.

    Use this when the engineer asks about current market availability,
    recent obsolescence notices, or lead-time changes that may not be
    reflected in the static catalog.

    When AGENTCORE_GATEWAY_ID is set, this calls AgentCore Web Search
    (managed, within the AWS security boundary, zero data egress).
    Otherwise falls back to simulated results for demo purposes.

    Args:
        query: Natural language search query about component availability,
               EOL status, or market data. Be specific with part names/vendors.
    """
    # ---- PRODUCTION PATH: AgentCore Gateway Web Search ----
    gateway_id = os.environ.get("AGENTCORE_GATEWAY_ID", "")
    if gateway_id:
        try:
            import boto3
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            import requests as _requests

            session = boto3.Session()
            credentials = session.get_credentials().get_frozen_credentials()
            region = os.environ.get("BEDROCK_REGION", "us-east-1")

            # The Gateway MCP endpoint
            gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"

            # MCP JSON-RPC payload to call the WebSearch tool
            # The tool name is prefixed with the target name: <target-id>___WebSearch
            # Discover the actual tool name by listing tools (cached after the
            # first lookup — avoids a tools/list round trip on every call)
            cache_key = (gateway_id, "web_search")
            web_search_tool_name = _GATEWAY_TOOL_NAME_CACHE.get(cache_key, "WebSearch")
            if cache_key not in _GATEWAY_TOOL_NAME_CACHE:
                list_payload = {"jsonrpc": "2.0", "id": "list-tools", "method": "tools/list", "params": {}}
                list_request = AWSRequest(
                    method="POST", url=gateway_url,
                    data=json.dumps(list_payload),
                    headers={"Content-Type": "application/json"}
                )
                SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(list_request)
                list_resp = _requests.post(gateway_url, headers=dict(list_request.headers), data=list_request.body, timeout=15)

                # Find the WebSearch tool name (it's prefixed with the target ID)
                if list_resp.status_code == 200:
                    tools_list = list_resp.json().get("result", {}).get("tools", [])
                    for t in tools_list:
                        if "WebSearch" in t.get("name", ""):
                            web_search_tool_name = t["name"]
                            break
                _GATEWAY_TOOL_NAME_CACHE[cache_key] = web_search_tool_name

            payload = {
                "jsonrpc": "2.0",
                "id": "web-search-request",
                "method": "tools/call",
                "params": {
                    "name": web_search_tool_name,
                    "arguments": {"query": query}
                }
            }

            # Sign the request with SigV4
            request = AWSRequest(
                method="POST",
                url=gateway_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)

            # Make the HTTP call
            response = _requests.post(
                gateway_url,
                headers=dict(request.headers),
                data=request.body,
                timeout=30,
            )

            if response.status_code == 200:
                rpc_response = response.json()

                # Check for RPC-level errors
                if "error" in rpc_response:
                    return {
                        "results": [],
                        "count": 0,
                        "query": query,
                        "error": f"Gateway tool error: {rpc_response['error'].get('message', '')}",
                    }

                tool_result = rpc_response.get("result", {})
                content = tool_result.get("content", [])

                results = []
                for item in content if isinstance(content, list) else [content]:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        # The text may be a JSON string containing search results
                        try:
                            parsed = json.loads(text) if text.startswith("{") or text.startswith("[") else None
                        except (json.JSONDecodeError, TypeError):
                            parsed = None

                        if parsed and isinstance(parsed, dict) and "results" in parsed:
                            for sr in parsed["results"]:
                                results.append({
                                    "title": sr.get("title", ""),
                                    "url": sr.get("url", ""),
                                    "snippet": sr.get("snippet", sr.get("context", "")),
                                    "published": sr.get("publishedDate", ""),
                                    "source": "AgentCore Web Search (live)",
                                })
                        elif parsed and isinstance(parsed, list):
                            for sr in parsed:
                                if isinstance(sr, dict):
                                    results.append({
                                        "title": sr.get("title", ""),
                                        "url": sr.get("url", ""),
                                        "snippet": sr.get("snippet", sr.get("context", "")),
                                        "source": "AgentCore Web Search (live)",
                                    })
                        elif text:
                            results.append({
                                "title": text[:100],
                                "url": "",
                                "snippet": text,
                                "source": "AgentCore Web Search (live)",
                            })

                if results:
                    return {
                        "results": results,
                        "count": len(results),
                        "query": query,
                        "source": "AgentCore Web Search (live, managed, zero data egress)",
                    }
            else:
                return {
                    "results": [],
                    "count": 0,
                    "query": query,
                    "error": f"Gateway returned {response.status_code}: {response.text[:300]}",
                }

        except ImportError:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": "Missing 'requests' package. Install with: pip install requests",
            }
        except Exception as e:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": f"AgentCore Web Search failed: {type(e).__name__}: {e}",
                "note": "Check AGENTCORE_GATEWAY_ID, region, and IAM permissions (bedrock-agentcore:InvokeGateway).",
            }

    # ---- DEMO PATH: Simulated results ----
    query_lower = query.lower()
    results = []

    if "anycompany" in query_lower or "rw" in query_lower:
        results.append({
            "title": "AnyCompany Space Systems — Reaction Wheel Product Line",
            "url": "https://example.com/anycompany/reaction-wheels",
            "snippet": "AnyCompany offers reaction wheels from 0.003 to 5.0 Nms. All models are actively produced with no announced end-of-life. Lead times vary by model (10-16 weeks typical).",
            "source": "web_search (simulated for demo)",
        })
    if "obsolete" in query_lower or "eol" in query_lower or "end of life" in query_lower:
        results.append({
            "title": "DMSMS Alert: Component Lifecycle Monitoring",
            "url": "https://www.gidep.org/",
            "snippet": "No active DMSMS alerts found for the AnyCompany reaction wheel product line as of 2026. All models report Active lifecycle status per vendor.",
            "source": "web_search (simulated for demo)",
        })
    if "lead time" in query_lower or "availability" in query_lower:
        results.append({
            "title": "Aerospace Component Lead Time Tracker",
            "url": "https://example.com/lead-time-tracker",
            "snippet": "AnyCompany RW3 0.06: ~10 weeks. RW4 1.0: ~12 weeks. RW 5.0: ~16 weeks. Supply stable; no constraints reported Q3 2026.",
            "source": "web_search (simulated for demo)",
        })

    if not results:
        results.append({
            "title": f"Web search: {query[:80]}",
            "url": "https://www.satnow.com/",
            "snippet": "No specific results found for this query. Try searching with specific part names or vendor names.",
            "source": "web_search (simulated for demo)",
        })

    return {
        "results": results,
        "count": len(results),
        "query": query,
        "note": "AGENTCORE_GATEWAY_ID not set. Using simulated results. Set AGENTCORE_GATEWAY_ID to enable live AgentCore Web Search.",
    }


# ============================================================
# VISUAL SIMILARITY — Nova MME + S3 Vectors
# ============================================================
# Supplemental evaluation signal: compares part photos using
# multimodal embeddings to assess physical/form-factor similarity.
# This is SUPPORTING evidence alongside the spec-fit scoring,
# not the basis for a substitution decision.
# ============================================================

@tool
def visual_similarity_score(part_id_a: str, part_id_b: str) -> dict:
    """Compare two parts visually using Nova Multimodal Embeddings for a
    quantitative similarity score, plus Claude Vision for a detailed
    physical analysis of specific differences.

    Returns:
    - Nova MME cosine similarity (deterministic, reproducible)
    - Claude Vision analysis of specific physical differences (mounting,
      connectors, size, form factor)

    This is a SUPPLEMENTAL signal for the evaluation, not the decision basis.

    Args:
        part_id_a: First part — catalog folder ID or display name (both resolve),
            e.g. 'rw_rl_0060' or 'RW3 0.06'.
        part_id_b: Second part — catalog folder ID or display name (both resolve).
    """
    # Resolve display names (e.g. "RW 0.03") to catalog folder IDs before
    # building file paths — previously this built the path directly from
    # whatever string was passed in, so a display name silently matched no
    # folder and the function returned "photos not found" even though the
    # photos existed under the resolved ID.
    resolved_a = _resolve_part_id(part_id_a)
    resolved_b = _resolve_part_id(part_id_b)

    if resolved_a is None or resolved_b is None:
        return {
            "error": f"Part not found: {'part_a (' + part_id_a + ')' if resolved_a is None else ''}"
                     f"{' and ' if resolved_a is None and resolved_b is None else ''}"
                     f"{'part_b (' + part_id_b + ')' if resolved_b is None else ''}".strip(),
            "part_a_photo": False,
            "part_b_photo": False,
        }

    # Load photos
    photo_a_bytes = None
    photo_b_bytes = None
    photo_a_path = None
    photo_b_path = None
    for ext in ("png", "jpg", "jpeg"):
        path_a = PARTS_DATA_DIR / resolved_a / f"photo.{ext}"
        if path_a.exists() and path_a.stat().st_size > 0:
            photo_a_bytes = path_a.read_bytes()
            photo_a_path = str(path_a)
            break
    for ext in ("png", "jpg", "jpeg"):
        path_b = PARTS_DATA_DIR / resolved_b / f"photo.{ext}"
        if path_b.exists() and path_b.stat().st_size > 0:
            photo_b_bytes = path_b.read_bytes()
            photo_b_path = str(path_b)
            break

    if not photo_a_bytes or not photo_b_bytes:
        return {
            "error": "One or both part photos not found.",
            "part_a_photo": bool(photo_a_bytes),
            "part_b_photo": bool(photo_b_bytes),
        }

    try:
        import boto3
        import numpy as np

        bedrock_client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

        # --- STEP 1: Nova MME embedding similarity (quantitative) ---
        def _embed_image(image_bytes):
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            fmt = "png" if image_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "jpeg"
            body = {
                "taskType": "SINGLE_EMBEDDING",
                "singleEmbeddingParams": {
                    "embeddingPurpose": "IMAGE_RETRIEVAL",
                    "embeddingDimension": 1024,
                    "image": {
                        "detailLevel": "STANDARD_IMAGE",
                        "format": fmt,
                        "source": {"bytes": b64},
                    },
                },
            }
            resp = bedrock_client.invoke_model(
                modelId="amazon.nova-2-multimodal-embeddings-v1:0",
                body=json.dumps(body),
                accept="application/json",
                contentType="application/json",
            )
            result = json.loads(resp["body"].read())
            return np.array(result["embeddings"][0]["embedding"])

        emb_a = _embed_image(photo_a_bytes)
        emb_b = _embed_image(photo_b_bytes)
        similarity = float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))

        # --- STEP 2: Claude Vision physical analysis (qualitative) ---
        specs_a = get_part_specs(resolved_a)
        specs_b = get_part_specs(resolved_b)
        name_a = specs_a.get("name", resolved_a)
        name_b = specs_b.get("name", resolved_b)

        # Prepare images for Claude Vision
        b64_a = base64.b64encode(photo_a_bytes).decode("utf-8")
        b64_b = base64.b64encode(photo_b_bytes).decode("utf-8")
        fmt_a = "png" if photo_a_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "jpeg"
        fmt_b = "png" if photo_b_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "jpeg"

        vision_prompt = f"""You are comparing two aerospace reaction wheels for physical compatibility assessment.

Image 1: {name_a}
Image 2: {name_b}

Analyze SPECIFIC physical differences between these two reaction wheels. For each difference, state what you observe concretely. Focus on:

1. HOUSING SIZE AND SHAPE: Relative size difference, housing geometry (cylindrical, square, etc.)
2. MOUNTING INTERFACE: Visible mounting holes, bolt pattern, mounting plate design
3. CONNECTOR LOCATION AND TYPE: Where the electrical connector is positioned, its size/type
4. OVERALL FORM FACTOR: Whether one could physically replace the other in the same bracket/mounting

Be specific and factual about what you SEE. Do not guess about specs you cannot observe.
Format as a bulleted list of concrete observations. Keep it to 4-6 specific points."""

        # The Claude Vision call runs in the middle of a compound multi-specialist
        # turn, alongside the specialists' other Bedrock calls. That burst can trip
        # the account's Claude requests-per-minute quota (ThrottlingException),
        # which used to surface as a bare "Vision analysis unavailable". Retry a few
        # times with exponential backoff so transient throttles/timeouts recover
        # instead of degrading the whole visual comparison.
        _VISION_MODEL_ID = "us.anthropic.claude-sonnet-5-5"
        _RETRYABLE = ("ThrottlingException", "TooManyRequestsException",
                      "ModelTimeoutException", "ServiceUnavailableException",
                      "InternalServerException")
        vision_response = None
        _last_vision_err = None
        for _attempt in range(4):
            try:
                vision_response = bedrock_client.converse(
                    modelId=_VISION_MODEL_ID,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"image": {"format": fmt_a, "source": {"bytes": photo_a_bytes}}},
                            {"image": {"format": fmt_b, "source": {"bytes": photo_b_bytes}}},
                            {"text": vision_prompt},
                        ]
                    }],
                    inferenceConfig={"maxTokens": 768},
                )
                break
            except Exception as _ve:
                _last_vision_err = _ve
                if type(_ve).__name__ not in _RETRYABLE or _attempt == 3:
                    raise
                _backoff = 0.5 * (2 ** _attempt)  # 0.5s, 1s, 2s
                print(f"[visual_similarity_score] Claude Vision retryable error "
                      f"({type(_ve).__name__}), attempt {_attempt + 1}/4, "
                      f"backing off {_backoff}s: {_ve}")
                time.sleep(_backoff)
        # Claude Sonnet can emit a reasoning/thinking block before the text block,
        # so the answer is not always content[0]. Grabbing content[0]["text"]
        # blindly threw `KeyError: 'text'` intermittently (only when a non-text
        # block came first). Scan for the first block that actually has "text".
        _content_blocks = vision_response["output"]["message"].get("content", [])
        physical_analysis = next(
            (b["text"] for b in _content_blocks if isinstance(b, dict) and "text" in b),
            None,
        )
        if physical_analysis is None:
            _block_types = [
                (list(b.keys())[0] if isinstance(b, dict) and b else type(b).__name__)
                for b in _content_blocks
            ]
            raise ValueError(
                f"Claude Vision response had no text block; blocks={_block_types}"
            )

    except Exception as e:
        # If vision fails, still return the MME score. Surface the ACTUAL error
        # (class + message) instead of just the class name — the class alone made
        # it impossible to tell throttling from a config/validation error on the
        # deployed Runtime. Log loudly too (Runtime CloudWatch is OTel-verbose, so
        # a distinctive prefix is the only way to find this).
        print(f"[visual_similarity_score] Claude Vision analysis FAILED "
              f"model=us.anthropic.claude-sonnet-5-5 region={BEDROCK_REGION}: "
              f"{type(e).__name__}: {e}")
        try:
            return {
                "part_a": {"id": resolved_a, "name": name_a, "photo_path": photo_a_path},
                "part_b": {"id": resolved_b, "name": name_b, "photo_path": photo_b_path},
                "visual_similarity": round(similarity, 4),
                "interpretation": (
                    "Very similar form factor" if similarity > 0.85
                    else "Moderately similar" if similarity > 0.7
                    else "Visually different form factors"
                ),
                "physical_analysis": f"Vision analysis unavailable: {type(e).__name__}: {e}",
                "models_used": ["amazon.nova-2-multimodal-embeddings-v1:0"],
            }
        except Exception:
            return {"error": f"Visual comparison failed: {type(e).__name__}: {e}"}

    return {
        "part_a": {"id": resolved_a, "name": name_a, "photo_path": photo_a_path},
        "part_b": {"id": resolved_b, "name": name_b, "photo_path": photo_b_path},
        "visual_similarity": round(similarity, 4),
        "interpretation": (
            "Very similar form factor" if similarity > 0.85
            else "Moderately similar" if similarity > 0.7
            else "Visually different form factors"
        ),
        "physical_analysis": physical_analysis,
        "models_used": [
            "amazon.nova-2-multimodal-embeddings-v1:0 (quantitative similarity)",
            "claude-sonnet-5-5 (physical difference analysis)",
        ],
        "note": "Visual similarity is a supplemental signal. The physical analysis describes "
                "specific observable differences. It does not replace spec-driven evaluation.",
    }


# ============================================================
# CATALOG FILTER — Exhaustive spec-based filtering
# ============================================================

@tool
def filter_parts_by_spec(field: str, value: str, operator: str = "contains") -> dict:
    """Exhaustively scan ALL parts in the catalog and return those matching
    a specific spec criterion. Use this for filter-type questions like
    "which parts have 5V" or "which wheels use RS-422" where you need a
    complete, guaranteed answer rather than semantic best-effort.

    Unlike kb_search (which returns top-K by relevance), this checks
    every single part and never misses a match.

    Args:
        field: The spec field to filter on (e.g., 'voltage_v', 'interface', 'mass_g').
        value: The value to match against (e.g., '5', 'RS-422', '200').
        operator: How to match — 'contains' (value found in field), 'equals' (exact),
                  'gte' (numeric >=), 'lte' (numeric <=).
    """
    parts_dir = PARTS_DATA_DIR
    if not parts_dir.exists():
        return {"error": "Parts directory not found.", "matches": [], "count": 0}

    matches = []
    scanned = 0

    for part_dir in sorted(parts_dir.iterdir()):
        if not part_dir.is_dir():
            continue
        specs_file = part_dir / "specs.json"
        if not specs_file.exists():
            continue

        specs = json.loads(specs_file.read_text())
        scanned += 1

        # Check the field (support nested lifecycle fields too)
        if "." in field:
            # e.g., "lifecycle.lead_time_risk"
            parts = field.split(".", 1)
            field_value = specs.get(parts[0], {})
            if isinstance(field_value, dict):
                field_value = field_value.get(parts[1])
            else:
                field_value = None
        else:
            field_value = specs.get(field)

        if field_value is None:
            continue

        # Also check the voltage_range_v for voltage queries
        matched = False
        field_str = str(field_value).lower()
        value_lower = value.lower()

        if operator == "contains":
            matched = value_lower in field_str
            # For voltage, also check the range field
            if not matched and field == "voltage_v":
                range_val = str(specs.get("voltage_range_v", "")).lower()
                if range_val:
                    # Parse range and check if value falls within
                    nums = re.findall(r"[\d.]+", range_val)
                    try:
                        target = float(value)
                        if len(nums) >= 2:
                            low, high = float(nums[0]), float(nums[1])
                            matched = low <= target <= high
                    except (ValueError, IndexError):
                        pass
        elif operator == "equals":
            matched = field_str == value_lower
        elif operator == "gte":
            try:
                matched = float(re.search(r"[\d.]+", field_str).group()) >= float(value)
            except (ValueError, AttributeError):
                pass
        elif operator == "lte":
            try:
                matched = float(re.search(r"[\d.]+", field_str).group()) <= float(value)
            except (ValueError, AttributeError):
                pass

        if matched:
            matches.append({
                "part_id": part_dir.name,
                "name": specs.get("name", part_dir.name),
                "matched_field": field,
                "field_value": field_value,
                "voltage_range": specs.get("voltage_range_v", "N/A"),
            })

    return {
        "matches": matches,
        "count": len(matches),
        "total_scanned": scanned,
        "filter": {"field": field, "value": value, "operator": operator},
        "note": "Exhaustive scan of all parts. Every match is guaranteed; nothing is missed.",
    }


# ============================================================
# MULTIMODAL RETRIEVAL — Chart/diagram search via Nova MME KB
# ============================================================

# Multimodal retrieval uses the same knowledge base as kb_search — the managed
# KB supports Nova MME embeddings, so PARTS_KB_ID is the single source of truth
# for text/document retrieval. (Image-as-query does not use the KB at all; it
# queries the native S3 Vectors index below.)


def _retrieve_visual_via_gateway(gateway_id: str, query_text: str, part_id: str,
                                 resolved_part_id, top_k: int):
    """Retrieve visual/text KB content through the AgentCore Gateway (text only).

    Mirrors kb_search's gateway path: discover the KB Retrieve tool via
    tools/list (cached), SigV4-sign a tools/call with {retrievalQuery:{text}},
    and parse the nested retrievalResults. Applies the same client-side part
    filtering that the direct path uses.

    Returns a result payload dict on success, or None to signal the caller
    should fall through to the direct Bedrock retrieve (gateway unreachable,
    tool not found, HTTP error, or no parsable results).
    """
    try:
        import boto3 as _boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        import requests as _requests

        region = os.environ.get("BEDROCK_REGION", "us-east-1")
        session = _boto3.Session()
        credentials = session.get_credentials().get_frozen_credentials()
        gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"

        # Reuse the same cached KB Retrieve tool name kb_search discovers.
        cache_key = (gateway_id, "kb_retrieve")
        retrieve_tool_name = _GATEWAY_TOOL_NAME_CACHE.get(cache_key)
        if retrieve_tool_name is None:
            list_payload = {"jsonrpc": "2.0", "id": "list-tools", "method": "tools/list", "params": {}}
            list_req = AWSRequest(method="POST", url=gateway_url, data=json.dumps(list_payload), headers={"Content-Type": "application/json"})
            SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(list_req)
            list_resp = _requests.post(gateway_url, headers=dict(list_req.headers), data=list_req.body, timeout=15)
            if list_resp.status_code == 200:
                for t in list_resp.json().get("result", {}).get("tools", []):
                    if "Retrieve" in t.get("name", "") and "search" not in t.get("name", "").lower():
                        retrieve_tool_name = t["name"]
                        break
            if retrieve_tool_name:
                _GATEWAY_TOOL_NAME_CACHE[cache_key] = retrieve_tool_name

        if not retrieve_tool_name:
            return None

        # Over-fetch when filtering to a specific part, same as direct path.
        fetch_top_k = max(top_k, 10) if resolved_part_id else top_k
        payload = {
            "jsonrpc": "2.0",
            "id": "kb-retrieve",
            "method": "tools/call",
            "params": {
                "name": retrieve_tool_name,
                "arguments": {
                    "retrievalQuery": {"text": query_text},
                    "retrievalConfiguration": {
                        "managedSearchConfiguration": {"numberOfResults": fetch_top_k}
                    },
                },
            },
        }
        call_req = AWSRequest(method="POST", url=gateway_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
        SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(call_req)
        call_resp = _requests.post(gateway_url, headers=dict(call_req.headers), data=call_req.body, timeout=30)
        if call_resp.status_code != 200:
            return None

        rpc_result = call_resp.json().get("result", {})
        content = rpc_result.get("content", [])

        results = []
        for item in content if isinstance(content, list) else [content]:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            try:
                parsed = json.loads(text) if text.startswith("{") else None
            except (json.JSONDecodeError, TypeError):
                parsed = None
            if not (parsed and "retrievalResults" in parsed):
                continue
            for r in parsed["retrievalResults"]:
                r_content = r.get("content", {})
                r_location = r.get("location", {})
                score = r.get("score", 0.0)
                content_type = r_content.get("type", "TEXT")
                s3_uri = r_location.get("s3Location", {}).get("uri", "")
                item_id = _part_id_from_s3_uri(s3_uri)
                source_file = s3_uri.split("/")[-1] if s3_uri else ""

                result_entry = {
                    "content_type": content_type,
                    "score": score,
                    "source": s3_uri,
                    "source_file": source_file,
                    "part_id": item_id,
                    "retrieval_path": "AgentCore Gateway",
                }
                if content_type == "TEXT":
                    result_entry["text"] = r_content.get("text", "")[:500]
                else:
                    result_entry["description"] = f"Visual content from {source_file} (part: {item_id})"
                    result_entry["image_source"] = s3_uri
                    if item_id and source_file:
                        local_path = PARTS_DATA_DIR / item_id / source_file
                        if local_path.exists():
                            result_entry["local_path"] = str(local_path)
                results.append(result_entry)

        if not results:
            return None

        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Same client-side part filter as the direct path.
        filtered_note = None
        if resolved_part_id:
            filtered = [r for r in results if r["part_id"] == resolved_part_id][:top_k]
            if filtered:
                results = filtered
            else:
                results = results[:top_k]
                filtered_note = (
                    f"No indexed visual content found specifically for '{resolved_part_id}'. "
                    "Showing the closest unfiltered semantic matches instead — treat "
                    "these as possibly belonging to a DIFFERENT part."
                )
        else:
            results = results[:top_k]

        payload_out = {
            "results": results,
            "count": len(results),
            "query_type": "text",
            "kb_id": PARTS_KNOWLEDGE_BASE_ID,
            "retrieval_path": "AgentCore Gateway",
        }
        if part_id:
            payload_out["requested_part_id"] = part_id
            payload_out["resolved_part_id"] = resolved_part_id
            if resolved_part_id is None:
                payload_out["note"] = (
                    f"Could not resolve '{part_id}' to a catalog part — searched "
                    "without a part filter, so results may include other parts."
                )
            elif filtered_note:
                payload_out["note"] = filtered_note
        return payload_out

    except Exception:
        return None  # Fall through to direct path


# ------------------------------------------------------------
# S3 Vectors image-as-query path
# ------------------------------------------------------------
# The managed Bedrock KB rejects IMAGE-type retrieval queries ("Image input is
# not yet supported for MANAGED knowledge bases"). To support true image-as-
# query ("here's a chart, which wheel is it?") we maintain a native S3 Vectors
# index (native/index_parts.py) of Nova MME embeddings — including cropped
# chart regions so an uploaded chart matches chart-vs-chart. This helper embeds
# the uploaded image and queries that index directly.
S3_VECTOR_BUCKET = os.environ.get("S3_VECTOR_BUCKET", "skylab-mfg-vectors")
S3_VECTOR_INDEX = os.environ.get("S3_VECTOR_INDEX", "reaction-wheels")
_NOVA_MME_MODEL_ID = "amazon.nova-2-multimodal-embeddings-v1:0"
_NOVA_MME_DIM = 1024


def _embed_query_image_nova_mme(image_bytes: bytes) -> list:
    """Embed an uploaded image with Nova MME using IMAGE_RETRIEVAL purpose,
    matching how native/index_parts.py indexed the catalog (GENERIC_INDEX).
    Returns a 1024-d float embedding."""
    import boto3
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        fmt = "png"
    elif image_bytes[:2] == b'\xff\xd8':
        fmt = "jpeg"
    else:
        fmt = "png"
    body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": "IMAGE_RETRIEVAL",
            "embeddingDimension": _NOVA_MME_DIM,
            "image": {
                "detailLevel": "STANDARD_IMAGE",
                "format": fmt,
                "source": {"bytes": b64},
            },
        },
    }
    br = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    resp = br.invoke_model(
        modelId=_NOVA_MME_MODEL_ID, body=json.dumps(body),
        accept="application/json", contentType="application/json",
    )
    result = json.loads(resp["body"].read())
    return result["embeddings"][0]["embedding"]


def _retrieve_visual_via_s3_vectors(query_image_b64: str, part_id: str,
                                    resolved_part_id, top_k: int):
    """Image-as-query retrieval against the native S3 Vectors index.

    Returns a result payload dict in the same shape as retrieve_visual_content
    (results[] with content_type/score/source/source_file/part_id, plus count,
    query_type, image_search_supported), or None to signal "not available —
    fall through to the managed-KB path" (e.g. bucket/index unset or an AWS
    error). Dedupes by part_id keeping each part's best-scoring vector, so
    matching the whole chart band and the individual plots doesn't return the
    same part three times.
    """
    if not (S3_VECTOR_BUCKET and S3_VECTOR_INDEX):
        return None
    try:
        import boto3
        image_bytes = base64.b64decode(query_image_b64)
        embedding = _embed_query_image_nova_mme(image_bytes)

        s3v = boto3.client("s3vectors", region_name=BEDROCK_REGION)
        # Fetch more than top_k because a single part contributes several
        # vectors (photo, document, chart, chart_left, chart_right); we dedupe
        # to best-per-part below.
        fetch_k = max(top_k * 6, 12)
        resp = s3v.query_vectors(
            vectorBucketName=S3_VECTOR_BUCKET,
            indexName=S3_VECTOR_INDEX,
            queryVector={"float32": embedding},
            topK=fetch_k,
            returnDistance=True,
            returnMetadata=True,
        )

        # Collapse to best (highest-similarity) hit per part_id.
        best_by_part = {}
        for v in resp.get("vectors", []):
            meta = v.get("metadata", {}) or {}
            pid = meta.get("part_id", "")
            if not pid:
                continue
            similarity = 1.0 - v.get("distance", 1.0)  # cosine distance -> sim
            src_file = meta.get("source_file", "")
            prev = best_by_part.get(pid)
            if prev is None or similarity > prev["score"]:
                # content_type mirrors the managed-KB path's vocabulary so the
                # stream adapter's image extraction (which keys off an image
                # file extension in source_file) works unchanged. A chart or
                # photo hit points at an image file; report IMAGE.
                is_image = src_file.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".webp")
                )
                entry = {
                    "content_type": "IMAGE" if is_image else "TEXT",
                    "score": similarity,
                    "source": f"s3vectors://{S3_VECTOR_BUCKET}/{S3_VECTOR_INDEX}/{v.get('key','')}",
                    "source_file": src_file,
                    "part_id": pid,
                    "modality": meta.get("modality", ""),
                    "chart_region": meta.get("chart_region", ""),
                    "name": meta.get("name", ""),
                }
                if is_image:
                    entry["description"] = (
                        f"Visual content from {src_file} (part: {pid})"
                    )
                    # Provide a local path so the API can serve the full page.
                    if src_file:
                        local_path = PARTS_DATA_DIR / pid / src_file
                        if local_path.exists():
                            entry["local_path"] = str(local_path)
                    entry["image_source"] = entry["source"]
                best_by_part[pid] = entry

        ranked = sorted(
            best_by_part.values(), key=lambda r: r["score"], reverse=True
        )

        # Optional client-side part filter (discovery case omits part_id).
        filtered_note = None
        if resolved_part_id:
            only = [r for r in ranked if r["part_id"] == resolved_part_id]
            if only:
                ranked = only
            else:
                filtered_note = (
                    f"No indexed visual content found specifically for "
                    f"'{resolved_part_id}'. Showing the closest matches instead."
                )
        results = ranked[:top_k]

        payload = {
            "results": results,
            "count": len(results),
            "query_type": "image",
            "image_search_supported": True,
            "retrieval": "s3_vectors",
            "index": f"{S3_VECTOR_BUCKET}/{S3_VECTOR_INDEX}",
        }
        if part_id:
            payload["requested_part_id"] = part_id
            payload["resolved_part_id"] = resolved_part_id
            if filtered_note:
                payload["note"] = filtered_note
        return payload

    except Exception as e:
        # Any failure (bucket/index missing, perms, region, model access) ->
        # signal the caller to fall through to the managed-KB path.
        #
        # LOG IT LOUDLY. This used to fail silently, which is genuinely
        # dangerous: the caller degrades to a TEXT search over chart
        # descriptions and the model then confidently names the WRONG part,
        # with no indication that image-as-query never actually ran. The most
        # common cause is a missing s3vectors:QueryVectors permission on the
        # calling identity (on AgentCore Runtime, the runtime execution role) —
        # local runs work because a developer's own credentials are broader.
        print(
            "[retrieve_visual_content] S3 Vectors image query FAILED — falling "
            f"back to text search. Image-as-query is NOT active. "
            f"{type(e).__name__}: {e} "
            f"(bucket={S3_VECTOR_BUCKET}, index={S3_VECTOR_INDEX}, "
            f"region={BEDROCK_REGION}). If this is AccessDenied, grant "
            "s3vectors:QueryVectors to the calling identity."
        )
        return None


@tool
def retrieve_visual_content(query_text: str = "", query_image_b64: str = "",
                             part_id: str = "", top_k: int = 3) -> dict:
    """Search the multimodal knowledge base for visual content: torque curves,
    power charts, interface diagrams, and architecture drawings from datasheets and ICDs.

    Can be queried with text ("torque curve for 0.06 Nms wheel") or with an
    uploaded image (a chart from a requirements doc to find matching parts).

    Returns image chunks with source attribution (which document, which part).

    Args:
        query_text: Text description of the visual content to find.
        query_image_b64: Base64-encoded image to search with (e.g., a performance chart to match against).
        part_id: Optional. If you already know which part the engineer means
            (e.g. they named it directly, or you already resolved it via
            get_part_specs), pass its catalog folder ID here to restrict
            results to that part's own indexed content. Without this,
            search is a blind semantic match across every part's charts and
            diagrams — since a torque curve image doesn't visually "contain"
            a part name, cross-modal text-to-image similarity alone can
            easily surface the wrong part's chart. Only omit this when the
            engineer is asking you to identify an unknown part from an
            uploaded image/description (the discovery case).
        top_k: Number of results to return.
    """
    kb_id = PARTS_KNOWLEDGE_BASE_ID
    if not kb_id:
        return {"error": "No knowledge base configured. Set PARTS_KB_ID."}

    resolved_part_id = _resolve_part_id(part_id) if part_id else None
    # If the caller didn't pass a resolvable part_id, try to infer the part
    # from the query text itself (e.g. "show me the torque curve for the RW 0.4"
    # -> rw_rl_0400). This makes retrieval robust even when the specialist
    # forgets to pass part_id, so a blind KB text search can't surface a
    # wrong-part chart that merely matched on shared boilerplate text.
    if resolved_part_id is None and query_text:
        resolved_part_id = _resolve_part_from_text(query_text)

    # ---- IMAGE-AS-QUERY PATH: native S3 Vectors index ----
    # The managed KB can't accept IMAGE-type queries, so for an uploaded image
    # we query the native S3 Vectors index (Nova MME embeddings, incl. cropped
    # chart regions). This is the reliable "which wheel is this chart?" path.
    # Returns None only when S3 Vectors is unconfigured or errors, in which
    # case we fall through to the managed-KB path (which will degrade to the
    # image_search_supported: False signal).
    if query_image_b64:
        sv = _retrieve_visual_via_s3_vectors(
            query_image_b64, part_id, resolved_part_id, top_k
        )
        if sv is not None:
            return sv

    # ---- GATEWAY PATH: route TEXT retrieval through AgentCore Gateway ----
    # The Gateway's KB Retrieve tool is text-only ($.retrievalQuery.text) — it
    # cannot accept an IMAGE-type query — so only text queries route here.
    # Image queries (query_image_b64) skip this and use the direct Bedrock
    # call below. On any failure we also fall through to the direct path.
    gateway_id = os.environ.get("AGENTCORE_GATEWAY_ID", "")
    if gateway_id and query_text and not query_image_b64:
        gw = _retrieve_visual_via_gateway(
            gateway_id, query_text, part_id, resolved_part_id, top_k
        )
        if gw is not None:
            return gw
        # else: gateway unavailable / returned nothing usable -> direct path

    try:
        import boto3
        client = boto3.client("bedrock-agent-runtime", region_name=BEDROCK_REGION)

        # Build the query (text or image)
        if query_image_b64:
            image_bytes = base64.b64decode(query_image_b64)
            if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                img_format = "png"
            elif image_bytes[:2] == b'\xff\xd8':
                img_format = "jpeg"
            else:
                img_format = "png"
            retrieval_query = {
                "type": "IMAGE",
                "image": {
                    "format": img_format,
                    "inlineContent": image_bytes,
                }
            }
        else:
            retrieval_query = {"text": query_text}

        # Resolve a display name (e.g. "RW3 0.06") to its catalog folder ID.
        #
        # NOTE: this is NOT applied as a server-side vectorSearchConfiguration
        # filter. A metadata filter (e.g. equals on a "part_id" key) only
        # works if every indexed vector was tagged with that custom metadata
        # key at ingestion time — which requires either the S3 Vectors direct
        # API (native/index_parts.py, a REFERENCE script not wired into this
        # app) or a sidecar `<filename>.metadata.json` per source file when
        # using a standard Bedrock S3 data source (neither exists here). A
        # console-created Bedrock KB over the parts catalog has no such field, so a
        # filter on it matches zero vectors — not "no match for this part,"
        # but "this field doesn't exist on anything," silently returning
        # nothing instead of falling back to an honest error.
        #
        # Instead, retrieve broadly (same semantic search as before, more
        # candidates) and filter/rerank client-side by parsing the part
        # folder out of each result's S3 URI — the same technique kb_search
        # already uses just above this function, which relies only on the
        # data's S3 layout convention (s3://bucket/parts/<part_id>/<file>),
        # not on any custom metadata infrastructure that may not exist.
        # (resolved_part_id computed above, before the gateway path.)
        fetch_top_k = max(top_k, 10) if resolved_part_id else top_k

        # Managed Knowledge Bases require `managedSearchConfiguration`; classic
        # (vector) KBs require `vectorSearchConfiguration`. Try managed first
        # and fall back for classic KBs — same pattern as kb_search, so this
        # works whether the KB is MANAGED or a classic vector store.
        search_configs = [
            {"managedSearchConfiguration": {"numberOfResults": fetch_top_k}},
            {"vectorSearchConfiguration": {"numberOfResults": fetch_top_k}},
        ]
        response = None
        last_error = None
        for cfg in search_configs:
            try:
                response = client.retrieve(
                    knowledgeBaseId=kb_id,
                    retrievalQuery=retrieval_query,
                    retrievalConfiguration=cfg,
                )
                break
            except Exception as e:
                code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
                msg = str(e)
                # Managed KBs don't accept IMAGE-type retrieval queries yet
                # ("Image input is not yet supported for MANAGED knowledge
                # bases"). This is a platform limitation, not a bug — return a
                # clean, structured signal so the specialist can degrade
                # gracefully (analyze the uploaded image with vision + do a
                # text search) instead of surfacing a raw ValidationException.
                if query_image_b64 and code == "ValidationException" and "image" in msg.lower():
                    return {
                        "results": [],
                        "count": 0,
                        "query_type": "image",
                        "image_search_supported": False,
                        "note": (
                            "Image-as-query retrieval is not supported on this managed "
                            "knowledge base. Analyze the uploaded image directly (vision) "
                            "to read its values/shape, then use a TEXT query "
                            "(retrieve_visual_content or kb_search) or filter_parts_by_spec "
                            "to find the matching part — do not report this as an error to "
                            "the engineer."
                        ),
                    }
                # Only fall through on the "wrong config shape" validation
                # error; surface anything else (permissions, region, bad ID).
                if code == "ValidationException" and (
                    "managedSearchConfiguration" in msg or "vectorSearchConfiguration" in msg
                ):
                    last_error = e
                    continue
                raise
        if response is None:
            raise last_error or RuntimeError("Knowledge Base retrieve failed")

        results = []
        for r in response.get("retrievalResults", []):
            content = r.get("content", {})
            location = r.get("location", {})
            score = r.get("score", 0.0)
            content_type = content.get("type", "TEXT")
            s3_uri = location.get("s3Location", {}).get("uri", "")

            # Extract part ID from S3 path (matches real catalog folders,
            # so it works under any bucket prefix like synthetic-parts-data/).
            item_id = _part_id_from_s3_uri(s3_uri)

            # Get the file name from the URI
            source_file = s3_uri.split("/")[-1] if s3_uri else ""

            result_entry = {
                "content_type": content_type,
                "score": score,
                "source": s3_uri,
                "source_file": source_file,
                "part_id": item_id,
            }

            if content_type == "TEXT":
                result_entry["text"] = content.get("text", "")[:500]
            elif content_type == "IMAGE":
                # Image chunk: contains the visual content (chart, diagram, photo)
                result_entry["description"] = f"Visual content from {source_file} (part: {item_id})"
                # The image bytes are in content.byteContent but we'll reference the source
                result_entry["image_source"] = s3_uri
                # Load local copy if available for display
                if item_id and source_file:
                    local_path = PARTS_DATA_DIR / item_id / source_file
                    if local_path.exists():
                        result_entry["local_path"] = str(local_path)

            results.append(result_entry)

        # Client-side part filter (see note above on why this isn't a
        # server-side vectorSearchConfiguration filter). Only keep results
        # whose S3 path resolves to the requested part. If that leaves
        # nothing — e.g. this part genuinely has no indexed visual content —
        # fall back to the unfiltered top_k so the caller still gets
        # something useful rather than a bare empty list, and note the
        # fallback so the caller can be honest about it.
        filtered_note = None
        if resolved_part_id:
            filtered = [r for r in results if r["part_id"] == resolved_part_id][:top_k]
            if filtered:
                results = filtered
            else:
                results = results[:top_k]
                filtered_note = (
                    f"No indexed visual content found specifically for '{resolved_part_id}'. "
                    "Showing the closest unfiltered semantic matches instead — treat "
                    "these as possibly belonging to a DIFFERENT part."
                )

        result_payload = {
            "results": results,
            "count": len(results),
            "query_type": "image" if query_image_b64 else "text",
            "kb_id": kb_id,
        }
        if part_id:
            result_payload["requested_part_id"] = part_id
            result_payload["resolved_part_id"] = resolved_part_id
            if resolved_part_id is None:
                result_payload["note"] = (
                    f"Could not resolve '{part_id}' to a catalog part — searched "
                    "without a part filter, so results may include other parts."
                )
            elif filtered_note:
                result_payload["note"] = filtered_note
        return result_payload

    except Exception as e:
        return {"error": f"Multimodal retrieval failed: {type(e).__name__}: {e}"}
