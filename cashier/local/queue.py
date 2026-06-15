"""Offline sale queue — stub. Full SQLite implementation in Step 6."""
import json
from pathlib import Path

QUEUE_FILE = Path.home() / ".griltek" / "offline_queue.jsonl"


def enqueue(sale_payload: dict) -> None:
    """Persist a sale for later sync when API is available."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(sale_payload) + "\n")


def pending_count() -> int:
    if not QUEUE_FILE.exists():
        return 0
    with open(QUEUE_FILE) as f:
        return sum(1 for _ in f)
