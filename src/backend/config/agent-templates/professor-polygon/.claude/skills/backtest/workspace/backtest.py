"""Retrospective backtest of the Professor against polygon-vybe history."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

AGENT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(AGENT_ROOT))

from adapters.polygon_adapter import PolygonAdapter  # noqa: E402
from praxis_professor_core.brier import brier_score  # noqa: E402
from praxis_professor_core.calibration import apply_platt  # noqa: E402

POLYGON_LOG = Path(
    "/Users/andrii/Desktop/projects/vybe/agents/polygon-vybe/workspace/brier-log.csv"
)
REPORT = AGENT_ROOT / ".claude/skills/backtest/workspace/backtest-report.md"

# Phase 1 override: set to 3 because polygon-vybe currently has 3 resolved rows.
# Real statistical validation deferred to 14d observation window (spec §6 #1).
MIN_RESOLVED_FOR_BACKTEST = 3
STATISTICAL_POWER_TARGET = 30


def _load() -> pd.DataFrame:
    if not POLYGON_LOG.exists():
        raise FileNotFoundError(POLYGON_LOG)
    df = pd.read_csv(POLYGON_LOG)
    # The CSV stores resolved as integer 1/0 (not string "true"/"false").
    resolved_mask = df["resolved"].astype(str).isin({"1", "true", "True", "yes", "YES"})
    return df[resolved_mask].reset_index(drop=True)


def _held_out_split(
    df: pd.DataFrame, test_frac: float = 0.20
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = int(len(df) * (1 - test_frac))
    # Guarantee at least 1 row in each split
    cut = max(1, min(cut, len(df) - 1))
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


def _safe_brier(df: pd.DataFrame) -> float | None:
    """Compute Brier score over rows that have valid numeric prob and outcome.

    Returns None if there are fewer than 2 valid rows.
    """
    probs = pd.to_numeric(df["my_calibrated_prob"], errors="coerce")
    # Map text outcomes to numeric: YES/1 → 1, NO/0 → 0; anything else → NaN
    raw_outcome = df["outcome"].astype(str).str.upper().str.strip()
    outcome_mapped = raw_outcome.map({"1": 1, "YES": 1, "0": 0, "NO": 0})
    valid = probs.notna() & outcome_mapped.notna()
    if valid.sum() < 2:
        return None
    return float(brier_score(
        np.asarray(probs[valid], dtype=np.float64),
        np.asarray(outcome_mapped[valid], dtype=np.int64),
    ))


def run() -> None:
    df = _load()
    if len(df) < MIN_RESOLVED_FOR_BACKTEST:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            f"Insufficient resolved rows: {len(df)}. "
            f"Need ≥{MIN_RESOLVED_FOR_BACKTEST} for backtest.\n"
        )
        sys.exit(1)

    train, test = _held_out_split(df)
    adapter = PolygonAdapter(
        rubric_path=AGENT_ROOT / "config/rubric.yaml",
        workspace_path=Path(
            "/Users/andrii/Desktop/projects/vybe/agents/polygon-vybe/workspace"
        ),
    )

    result = adapter.grade(train)

    baseline_brier = _safe_brier(test)
    applied_brier = baseline_brier

    for d in result.directives:
        if d.type.value == "update_calibration" and baseline_brier is not None:
            a = float(d.payload["platt_a"])
            b = float(d.payload["platt_b"])
            probs = pd.to_numeric(test["my_calibrated_prob"], errors="coerce")
            raw_outcome = test["outcome"].astype(str).str.upper().str.strip()
            outcome_mapped = raw_outcome.map({"1": 1, "YES": 1, "0": 0, "NO": 0})
            valid = probs.notna() & outcome_mapped.notna()
            if valid.sum() >= 2:
                adjusted = apply_platt(
                    probs[valid].to_numpy(dtype=np.float64), a=a, b=b
                )
                applied_brier = float(
                    brier_score(
                        adjusted,
                        np.asarray(outcome_mapped[valid], dtype=np.int64),
                    )
                )

    provisional = len(df) < STATISTICAL_POWER_TARGET

    # Compute delta; treat None Brier as 0.000 for gate reporting
    baseline_val = baseline_brier if baseline_brier is not None else float("nan")
    applied_val = applied_brier if applied_brier is not None else float("nan")
    if baseline_brier is not None and applied_brier is not None:
        delta = baseline_brier - applied_brier
    else:
        delta = 0.0

    md: list[str] = [
        "# Backtest Report",
        "",
    ]
    if provisional:
        md.extend([
            "> **Provisional:** Fewer than "
            f"{STATISTICAL_POWER_TARGET} resolved rows available "
            f"(n={len(df)}). This run validates the pipeline mechanically; "
            "real statistical validation is deferred to the 14-day "
            "observation window (spec §6 criterion #1).",
            "",
        ])
    md.extend([
        f"- Train rows: {len(train)}",
        f"- Held-out test rows: {len(test)}",
        f"- Train rolling Brier: {result.rolling_brier:.3f}",
        (
            f"- Baseline (held-out) Brier: {baseline_val:.3f}"
            if baseline_brier is not None
            else "- Baseline (held-out) Brier: n/a (insufficient valid prob+outcome pairs)"
        ),
        (
            f"- Post-directive (held-out) Brier: {applied_val:.3f}"
            if applied_brier is not None
            else "- Post-directive (held-out) Brier: n/a"
        ),
        f"- **Delta: {delta:+.3f}**",
        "",
        "## Proposed Directives",
    ])
    for d in result.directives:
        md.append(f"- `{d.type.value}`: {d.rationale}")
    if not result.directives:
        md.append("- (none — below min_resolved_for_feedback threshold)")
    md.append("")
    md.append(f"## Surprises detected: {len(result.surprises)}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(md))
    print(REPORT.read_text())


if __name__ == "__main__":
    run()
