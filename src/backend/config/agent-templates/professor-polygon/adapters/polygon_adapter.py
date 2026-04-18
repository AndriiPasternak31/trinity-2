"""Polygon (Polymarket trader) adapter for praxis-professor-core."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from praxis_professor_core.adapters.base import ProfessorAdapter
from praxis_professor_core.schemas import (
    DecisionLogSchema,
    GradingResult,
    GroundTruthResolver,
    Rubric,
)


class PolymarketResolver(GroundTruthResolver):
    """Looks up market resolutions via Polymarket Data API.

    In Phase 1 we rely on polygon-vybe's existing redeem skill to write the
    `outcome` column — so resolve() just reads the resolved status from the
    brier-log. Live API lookup deferred to Phase 1.5 if needed.
    """

    def __init__(self, brier_log_path: Path) -> None:
        self._path = brier_log_path

    def resolve(self, decision_id: str) -> int | None:
        # Implementation is a simple CSV lookup; Phase 1.5 can swap in an
        # authoritative API fetch if the CSV is stale.
        import pandas as pd  # noqa: PLC0415  # deferred import per plan intention

        if not self._path.exists():
            return None
        df = pd.read_csv(self._path)
        row = df[df["decision_id"].astype(str) == decision_id]
        if row.empty:
            return None
        resolved_val = str(row.iloc[0]["resolved"]).strip().lower()
        if resolved_val not in ("1", "true", "yes", "resolved"):
            return None
        outcome_raw = str(row.iloc[0]["outcome"]).strip().upper()
        outcome_map = {"YES": 1, "Y": 1, "1": 1, "TRUE": 1, "NO": 0, "N": 0, "0": 0, "FALSE": 0}
        if outcome_raw not in outcome_map:
            return None
        return outcome_map[outcome_raw]


class PolygonAdapter(ProfessorAdapter):
    """Concrete Professor for polygon-vybe."""

    schema = DecisionLogSchema(
        probability_field="my_calibrated_prob",
        outcome_field="outcome",
        status_field="resolved",
        reasoning_field="rationale",
        domain_field="edge_type",
        timestamp_field="timestamp",
        id_field="decision_id",
        market_price_field="market_price",
        confidence_field="confidence",
        edge_type_field="edge_type",
        attribution_field="attribution",
        hypothesis_ids_field="hypothesis",
    )

    def __init__(self, rubric_path: Path, workspace_path: Path) -> None:
        self._rubric_cfg: dict[str, Any] = yaml.safe_load(rubric_path.read_text())
        self.rubric = Rubric(
            target_brier_delta=self._rubric_cfg["target_brier_delta"],
            surprise_threshold=self._rubric_cfg["surprise_threshold"],
            min_resolved_for_feedback=self._rubric_cfg["min_resolved_for_feedback"],
            noise_dominance_threshold=self._rubric_cfg["noise_dominance_threshold"],
            graduation_approvals_required=self._rubric_cfg["graduation_approvals_required"],
        )
        self.resolver = PolymarketResolver(workspace_path / "brier-log.csv")
        self._workspace = workspace_path

    def format_feedback(self, result: GradingResult) -> str:
        return (
            "# Calibration Notes — polygon-vybe\n\n"
            f"- **Rolling Brier (window=30):** {result.rolling_brier:.3f}\n"
            f"- **Calibration residual (ECE):** {result.calibration_residual:.3f}\n"
            f"- **Noise dominance:** {result.noise_dominance:.2f}\n"
            f"- **Resolved decisions graded:** {result.resolved_count}\n"
            f"- **Surprises detected:** {len(result.surprises)}\n"
            f"- **Directives issued:** {len(result.directives)}\n"
        )

    def route_surprise(self, surprise_id: str, payload: dict[str, Any]) -> None:
        """Surprises get routed to Cornelius via the backprop skill; no-op here."""
