"""Route resolved outcomes to Cornelius Q-value update."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

POLYGON_WORKSPACE = Path("/Users/andrii/Desktop/projects/vybe/agents/polygon-vybe/workspace")
NOTE_ID_PATTERN = re.compile(r"cornelius:([a-zA-Z0-9_-]+)")
_OUTCOME_MAP = {
    "YES": 1, "Y": 1, "1": 1, "TRUE": 1,
    "NO": 0, "N": 0, "0": 0, "FALSE": 0,
}


def _call_cornelius(note_id: str, outcome: int, attribution: str) -> None:
    """Invoke cornelius /record-outcome via Trinity MCP bridge."""
    payload = {
        "agent": "cornelius",
        "skill": "record-outcome",
        "args": {"note_id": note_id, "outcome": outcome, "attribution": attribution},
    }
    subprocess.run(  # noqa: S603,S607 — static args; payload goes via stdin JSON
        ["trinity-chat", "send", "--json"],
        input=json.dumps(payload),
        text=True,
        check=True,
    )


def backprop_row(row: dict[str, Any]) -> int:
    reasoning = str(row.get("rationale", ""))
    note_ids = set(NOTE_ID_PATTERN.findall(reasoning))
    if not note_ids:
        return 0
    outcome_raw = str(row.get("outcome", "")).strip().upper()
    if outcome_raw not in _OUTCOME_MAP:
        return 0
    outcome = _OUTCOME_MAP[outcome_raw]
    attribution = str(row.get("attribution", ""))
    for nid in note_ids:
        _call_cornelius(nid, outcome, attribution)
    return len(note_ids)


def run() -> None:
    log = POLYGON_WORKSPACE / "brier-log.csv"
    last_seen = POLYGON_WORKSPACE / ".backprop-cursor"
    if not log.exists():
        sys.exit(0)
    df = pd.read_csv(log)
    resolved_mask = df["resolved"].astype(str).str.strip().str.lower().isin(
        ["1", "true", "yes", "resolved"]
    )
    resolved = df[resolved_mask]
    if last_seen.exists():
        cursor = int(last_seen.read_text())
        resolved = resolved.iloc[cursor:]
    total = 0
    for _, row in resolved.iterrows():
        total += backprop_row({str(k): v for k, v in row.to_dict().items()})
    last_seen.write_text(str(int(resolved_mask.sum())))
    print(f"[backprop] forwarded {total} note-outcome pairs to cornelius")


if __name__ == "__main__":
    run()
