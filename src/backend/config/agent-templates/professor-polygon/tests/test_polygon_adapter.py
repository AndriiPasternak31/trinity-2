from pathlib import Path

import pandas as pd
import pytest

from adapters.polygon_adapter import PolygonAdapter


@pytest.fixture()
def adapter(tmp_path: Path) -> PolygonAdapter:
    rubric_path = Path(__file__).parent.parent / "config/rubric.yaml"
    return PolygonAdapter(
        rubric_path=rubric_path,
        workspace_path=tmp_path,
    )


def test_adapter_schema_matches_polygon_vybe_columns(adapter: PolygonAdapter) -> None:
    s = adapter.schema
    assert s.probability_field == "my_calibrated_prob"
    assert s.outcome_field == "outcome"
    assert s.id_field == "decision_id"


def test_adapter_grades_empty_log(adapter: PolygonAdapter) -> None:
    df = pd.DataFrame(columns=[
        "decision_id", "timestamp", "my_calibrated_prob", "outcome",
        "resolved", "rationale", "market", "edge_type",
    ])
    result = adapter.grade(df)
    assert result.resolved_count == 0


def test_feedback_rendering(adapter: PolygonAdapter) -> None:
    from praxis_professor_core.schemas import GradingResult
    result = GradingResult(
        rolling_brier=0.22,
        calibration_residual=0.04,
        noise_dominance=0.85,
        resolved_count=40,
        surprises=[],
        directives=[],
    )
    md = adapter.format_feedback(result)
    assert "Rolling Brier" in md
    assert "0.220" in md
