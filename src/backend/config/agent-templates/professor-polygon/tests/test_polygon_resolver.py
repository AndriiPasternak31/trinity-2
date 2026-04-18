"""PolymarketResolver maps polygon's resolved=1 + outcome=YES/NO correctly."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from adapters.polygon_adapter import PolymarketResolver


def test_resolver_yes_mapping(tmp_path: Path) -> None:
    path = tmp_path / "brier-log.csv"
    df = pd.DataFrame({
        "decision_id": ["r1", "r2", "d99"],
        "resolved": ["1", "1", "0"],
        "outcome": ["NO", "YES", ""],
    })
    df.to_csv(path, index=False)
    resolver = PolymarketResolver(path)
    assert resolver.resolve("r1") == 0  # NO
    assert resolver.resolve("r2") == 1  # YES
    assert resolver.resolve("d99") is None  # unresolved
