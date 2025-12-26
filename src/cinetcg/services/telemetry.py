from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


@dataclass
class TelemetryService:
    path: Path

    def log(self, event_type: str, payload: Mapping[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "type": event_type,
            "payload": dict(payload),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
