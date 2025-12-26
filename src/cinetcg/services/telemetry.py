from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class TelemetryService:
    path: Path

    def log(self, event_type: str, payload: Mapping[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "type": event_type,
            "payload": dict(payload),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
