"""mei_core — a self-contained copy of the SkyLab Manufacturing Intelligence
agent + tools, vendored so the notebooks run standalone.

This is a COPY of the app's agent/ and api/services/ modules (see each file's
header). The running application still uses its own modules; editing these does
not affect the app. Import from here in the notebooks:

    from mei_core import run_multi_agent, run_agent_with_events
    from mei_core.tools import get_part_specs, score_substitution_fit, ...
    from mei_core.agents import create_catalog_specialist, ...
"""

from . import dataset_profiles  # noqa: F401

# Agent graph + orchestration
from .agents import (  # noqa: F401
    run_multi_agent,
    create_planner,
    create_supervisor,
    create_catalog_specialist,
    create_evaluation_specialist,
    create_knowledge_specialist,
    _parse_specialist_plan,
    _auto_log_evaluations,
    MODEL_ID,
    SPECIALIST_MODEL_ID,
    PLANNER_MODEL_ID,
)

# Tools (deterministic evidence layer)
from .tools import (  # noqa: F401
    PARTS_DATA_DIR,
    AUDIT_LOG_PATH,
    kb_search,
    get_part_specs,
    compare_parts,
    filter_parts_by_spec,
    score_substitution_fit,
    get_substitution_requirements,
    generate_substitution_memo,
    visual_similarity_score,
    web_search_eol,
    retrieve_visual_content,
    check_qualification_status,
    _resolve_part_id,
    _resolve_part_from_text,
    _extract_momentum_value,
    _write_audit_entry,
)

# Streaming + fixed-chain IIA
from .stream_adapter import run_agent_with_events  # noqa: F401
from .impact_assessment import run_integration_impact_assessment  # noqa: F401
