from __future__ import annotations

import os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
CODEXDASH_DIR = Path(os.path.expanduser(os.environ.get("CODEXDASH_DIR", str(HOME / ".codexdash"))))
EVENTS_PATH = Path(os.path.expanduser(os.environ.get("CODEXDASH_EVENTS", str(CODEXDASH_DIR / "events.ndjson"))))
DB_PATH = Path(os.path.expanduser(os.environ.get("CODEXDASH_DB", str(CODEXDASH_DIR / "codexdash.db"))))
DEFAULT_SESSION = os.environ.get("CODEX_TMUX_SESSION", "codexctl")
POLL_INTERVAL_MS = int(os.environ.get("CODEXDASH_POLL_MS", "500"))
TAIL_INTERVAL_MS = int(os.environ.get("CODEXDASH_TAIL_MS", "200"))
MAX_EVENT_LINE = int(os.environ.get("CODEXDASH_MAX_EVENT_LINE", "200000"))
