"""Daily Professor run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

AGENT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(AGENT_ROOT))

from adapters.polygon_adapter import PolygonAdapter  # noqa: E402

POLYGON_WORKSPACE = Path("/Users/andrii/Desktop/projects/vybe/agents/polygon-vybe/workspace")
PROF_WORKSPACE = AGENT_ROOT / "workspace"


def run() -> None:
    log_path = POLYGON_WORKSPACE / "brier-log.csv"
    if not log_path.exists():
        print(f"[grade] Missing {log_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(log_path)
    adapter = PolygonAdapter(
        rubric_path=AGENT_ROOT / "config/rubric.yaml",
        workspace_path=POLYGON_WORKSPACE,
    )
    result = adapter.grade(df)

    (POLYGON_WORKSPACE / "calibration-notes.md").write_text(adapter.format_feedback(result))

    surprise_md = ["# Surprise Log", ""]
    for s in result.surprises:
        surprise_md.append(f"- `{s.decision_id}` |p−o|={s.magnitude:.2f} ({s.domain})")
    (POLYGON_WORKSPACE / "surprise-log.md").write_text("\n".join(surprise_md))

    PROF_WORKSPACE.mkdir(parents=True, exist_ok=True)
    directives_payload = [
        {"type": d.type.value, "payload": d.payload, "rationale": d.rationale}
        for d in result.directives
    ]
    (PROF_WORKSPACE / "directives.json").write_text(json.dumps(directives_payload, indent=2))

    print(f"[grade] {result.resolved_count} resolved; {len(result.directives)} directives")


if __name__ == "__main__":
    run()
