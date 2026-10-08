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

``resolve()`` only ever calls ``os.environ.setdefault(...)``, so an explicitly
exported env var (PARTS_DATA_DIR, PARTS_KB_ID, S3_VECTOR_INDEX,
S3_VECTOR_BUCKET) always wins. The notebook setup cells export PARTS_DATA_DIR
to the bundled catalog before importing, so this mainly provides the KB /
S3 Vectors defaults used by the AWS-backed cells.
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

# Defaults for the AWS-backed resources the synthetic notebooks use.
_DEFAULTS = {
    "PARTS_DATA_DIR": str(_DATA_ROOT / "data" / "synthetic-parts-data"),
    "PARTS_KB_ID": "KBJSEK4HDV",
    "S3_VECTOR_INDEX": "reaction-wheels-synthetic",
    "S3_VECTOR_BUCKET": "skylab-mfg-vectors",
}


def active_dataset() -> str:
    """Always 'synthetic' — the notebooks use a single catalog."""
    return DATASET_NAME


def resolve() -> dict:
    """Seed the synthetic defaults into os.environ (setdefault — never clobbers
    an explicitly-exported value). Returns the effective values for logging."""
    for key, value in _DEFAULTS.items():
        os.environ.setdefault(key, value)
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
