"""One-line JSON logs to stdout (prd §18, tech §12)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


def log_line(event: dict[str, Any]) -> None:
    """Emit a single JSON object on stdout (no secrets)."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    line = json.dumps(payload, ensure_ascii=False, default=str)
    print(line, file=sys.stdout, flush=True)
