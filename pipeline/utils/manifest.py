import json
from pathlib import Path
from datetime import datetime

MANIFEST = Path("docs/manifest.json")


def _load() -> dict:
    if not MANIFEST.exists():
        return {"entries": []}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def add_entry(entry: dict) -> None:
    data = _load()
    entry["created_at"] = datetime.utcnow().isoformat() + "Z"
    data["entries"].insert(0, entry)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2), encoding="utf-8")
