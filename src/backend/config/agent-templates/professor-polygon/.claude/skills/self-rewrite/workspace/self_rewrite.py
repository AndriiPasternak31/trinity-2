"""Apply pending Directives to polygon-vybe via git commits."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

AGENT_ROOT = Path(__file__).resolve().parents[4]
POLYGON_ROOT = Path("/Users/andrii/Desktop/projects/vybe/agents/polygon-vybe")
POLYGON_WORKSPACE = POLYGON_ROOT / "workspace"
CALIB_PARAMS = POLYGON_WORKSPACE / "calibration-params.json"
DIRECTIVES = AGENT_ROOT / "workspace/directives.json"
REFUSED = AGENT_ROOT / "workspace/refused-directives.md"


def _safe_platt(payload: dict[str, Any]) -> bool:
    a = float(payload.get("platt_a", 1.0))
    return 0.3 <= a <= 3.0


def _git_commit(path: Path, msg: str) -> None:
    rel = path.relative_to(POLYGON_ROOT)
    subprocess.run(  # noqa: S603 — static arg list; path components are validated before reaching here
        [
            "git", "-C", str(POLYGON_ROOT),
            "-c", "user.name=professor-polygon",
            "-c", "user.email=professor-polygon@praxis.local",
            "add", str(rel),
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603 — static arg list; commit message is from internal logic only
        [
            "git", "-C", str(POLYGON_ROOT),
            "-c", "user.name=professor-polygon",
            "-c", "user.email=professor-polygon@praxis.local",
            "commit", "-m", msg,
        ],
        check=True,
    )


def _refuse(directive: dict[str, Any], reason: str) -> None:
    REFUSED.parent.mkdir(parents=True, exist_ok=True)
    with REFUSED.open("a") as f:
        f.write(
            f"- `{directive.get('type')}` — {reason}\n"
            f"  Payload: `{json.dumps(directive.get('payload', {}))}`\n"
        )


def apply_update_calibration(payload: dict[str, Any]) -> None:
    if not _safe_platt(payload):
        _refuse({"type": "update_calibration", "payload": payload}, "Platt A out of [0.3, 3.0]")
        return
    current = json.loads(CALIB_PARAMS.read_text()) if CALIB_PARAMS.exists() else {}
    current["platt_a"] = float(payload["platt_a"])
    current["platt_b"] = float(payload["platt_b"])
    CALIB_PARAMS.write_text(json.dumps(current, indent=2))
    _git_commit(
        CALIB_PARAMS,
        f"chore(calibration): professor-polygon Platt A={payload['platt_a']:.3f} B={payload['platt_b']:.3f}",
    )


def apply_new_correction_skill(payload: dict[str, Any]) -> None:
    correction_id = str(payload.get("id", "")).strip()
    if not correction_id or not correction_id.replace("-", "").isalnum():
        _refuse({"type": "new_correction_skill", "payload": payload}, "invalid id")
        return
    skill_dir = POLYGON_ROOT / ".claude/skills" / f"correction-{correction_id}"
    if skill_dir.exists():
        _refuse({"type": "new_correction_skill", "payload": payload}, "skill already exists")
        return
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(payload.get("content", ""))
    _git_commit(skill_dir / "SKILL.md", f"feat(skill): professor-polygon correction-{correction_id}")


def run() -> None:
    if not DIRECTIVES.exists():
        print("[self-rewrite] no directives pending")
        return
    directives = json.loads(DIRECTIVES.read_text())
    if not directives:
        print("[self-rewrite] no directives pending")
        return
    for d in directives:
        if d["type"] == "update_calibration":
            apply_update_calibration(d["payload"])
        elif d["type"] == "new_correction_skill":
            apply_new_correction_skill(d["payload"])
        else:
            _refuse(d, f"unknown directive type {d['type']}")
    DIRECTIVES.write_text("[]")
    print(f"[self-rewrite] processed {len(directives)} directives")


if __name__ == "__main__":
    run()
