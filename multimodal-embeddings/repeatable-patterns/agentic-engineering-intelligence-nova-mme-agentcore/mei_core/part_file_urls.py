# ============================================================
# VENDORED COPY — do not edit here.
# This is a copy of api/services/part_file_urls.py from the parent SkyLab Manufacturing
# Intelligence app, vendored into notebooks/mei_core/ so the notebooks run
# standalone (e.g. when this folder is moved to another repo). The app
# still runs on its own agent/ + api/ modules; this is an independent copy.
# Intra-package imports were rewritten to be package-relative.
# To refresh: re-run the vendoring step (see notebooks/README.md).
# ============================================================

"""Dataset-versioned URLs for locally served part assets.

Appends a ``dataset`` query key to each asset URL so browser caches stay
partitioned per dataset. The serving route ignores this key when choosing the
file; the process selects its actual data directory via PARTS_DATA_DIR. The
notebooks use a single (synthetic) catalog, so this is effectively a constant
tag here.
"""

from urllib.parse import quote

from .dataset_profiles import active_dataset


def build_part_file_url(part_id: str, filename: str) -> str:
    """Return a cache-partitioned relative URL for a part asset.

    ``part_id`` and ``filename`` are validated by the serving route before the
    file is opened. Quote them here so a future filename with whitespace or
    other URL-significant characters remains safe and renderable.
    """
    dataset = quote(active_dataset(), safe="")
    part = quote(part_id, safe="")
    file_name = quote(filename, safe="")
    return f"/api/parts/{part}/files/{file_name}?dataset={dataset}"
