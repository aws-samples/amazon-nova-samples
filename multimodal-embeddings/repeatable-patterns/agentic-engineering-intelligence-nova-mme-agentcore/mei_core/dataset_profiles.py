# ============================================================
# VENDORED COPY — do not edit here.
# A synthetic-only, trimmed copy of the parent app's dataset_profiles.py,
# vendored into notebooks/mei_core/ so the notebooks run standalone. The app's
# own dataset_profiles.py (repo root) is unchanged and still supports multiple
# datasets; this notebook copy is deliberately synthetic-only.
# ============================================================

"""Synthetic-dataset config for the notebooks.

The notebooks only ever use the synthetic AnyCompany reaction-wheel catalog
bundled in this folder (notebooks/data/synthetic-parts-data). This module keeps
the same two entry points the vendored tools call — ``active_dataset()`` and
``resolve()`` — but hardcodes the synthetic dataset: no dataset switching, no
alternate catalogs.

``resolve()`` only seeds PARTS_DATA_DIR (the bundled synthetic catalog, which
ships with these notebooks). The AWS-backed resources — the parts knowledge
base and the S3 Vectors bucket/index — have NO default: you must export
PARTS_KB_ID, S3_VECTOR_BUCKET, and S3_VECTOR_INDEX to point at resources in
your own account. ``resolve()`` raises a clear error listing any that are
missing so the sample never silently targets someone else's resources.
"""

import os
from pathlib import Path

DATASET_NAME = "synthetic"

# Locate the bundled synthetic catalog. In this vendored layout the data dir is
# the PARENT of this package (notebooks/data/); fall back to a couple of other
# plausible locations so the default is correct whether run standalone or in
# place. An explicitly exported PARTS_DATA_DIR always overrides this.
_PKG_DIR = Path(__file__).resolve().parent          # notebooks/mei_core/
_candidates = [
    _PKG_DIR.parent,                                 # notebooks/  (bundled data lives here)
    _PKG_DIR,                                         # notebooks/mei_core/
    _PKG_DIR.parent.parent,                           # one level up (running in place)
]
_DATA_ROOT = next(
    (c for c in _candidates if (c / "data" / "synthetic-parts-data").exists()),
    _PKG_DIR.parent,
)

# The one default we CAN ship: the bundled synthetic catalog that lives
# alongside these notebooks. Seeded with setdefault so an explicit export wins.
_DEFAULTS = {
    "PARTS_DATA_DIR": str(_DATA_ROOT / "data" / "synthetic-parts-data"),
}

# AWS-backed resources with NO default — the reader must point these at
# resources in their own account. resolve() raises if any are unset.
_REQUIRED_AWS_VARS = (
    "PARTS_KB_ID",       # Bedrock knowledge base id, e.g. "<your-kb-id>"
    "S3_VECTOR_BUCKET",  # S3 vector bucket, e.g. "amzn-s3-demo-vectors"
    "S3_VECTOR_INDEX",   # S3 vector index name, e.g. "<your-vector-index>"
)


def active_dataset() -> str:
    """Always 'synthetic' — the notebooks use a single catalog."""
    return DATASET_NAME


def resolve() -> dict:
    """Seed the bundled-catalog default into os.environ (setdefault — never
    clobbers an explicit export) and require the AWS-backed vars to be set.

    Raises RuntimeError listing any of PARTS_KB_ID / S3_VECTOR_BUCKET /
    S3_VECTOR_INDEX that are missing, so the sample never silently targets
    resources it does not own. Returns the effective values for logging."""
    for key, value in _DEFAULTS.items():
        os.environ.setdefault(key, value)

    missing = [v for v in _REQUIRED_AWS_VARS if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". These point at AWS resources in YOUR account and have no "
            "default. Set them before running the notebooks, e.g.:\n"
            '    os.environ["PARTS_KB_ID"] = "<your-kb-id>"\n'
            '    os.environ["S3_VECTOR_BUCKET"] = "amzn-s3-demo-vectors"\n'
            '    os.environ["S3_VECTOR_INDEX"] = "<your-vector-index>"'
        )

    return {
        "DATASET": DATASET_NAME,
        "PARTS_DATA_DIR": os.environ.get("PARTS_DATA_DIR", ""),
        "PARTS_KB_ID": os.environ.get("PARTS_KB_ID", ""),
        "S3_VECTOR_BUCKET": os.environ.get("S3_VECTOR_BUCKET", ""),
        "S3_VECTOR_INDEX": os.environ.get("S3_VECTOR_INDEX", ""),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(resolve(), indent=2))
