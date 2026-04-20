"""Dump the FastAPI app's OpenAPI schema to disk without running a server.

Output is deterministic (sorted keys, stable indent) so git diffs are minimal.
Usage:
    uv run python scripts/export_openapi.py           # writes backend/openapi.json
    uv run python scripts/export_openapi.py --stdout  # prints to stdout (for drift check)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Import here instead of top-level so that a bad import doesn't break the stdout path.
from app.main import app


def main() -> int:
    schema = app.openapi()
    text = json.dumps(schema, sort_keys=True, indent=2) + "\n"

    if "--stdout" in sys.argv:
        sys.stdout.write(text)
        return 0

    out = Path(__file__).resolve().parent.parent / "openapi.json"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
