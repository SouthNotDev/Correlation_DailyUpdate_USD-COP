"""CLI wrapper to generate factor relation metrics for USD/COP."""

from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

from src.analysis.relations import run_relations


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute factor relation metrics for USD/COP.")
    parser.add_argument("--prices", default="data/processed/market_daily.parquet", help="Path to processed price parquet")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path for CSV output. Defaults to reports/relations/relations_<date>.csv",
    )
    args = parser.parse_args()

    if args.output:
        out_path = Path(args.output)
    else:
        today = datetime.today().strftime("%Y-%m-%d")
        out_path = Path("reports/relations") / f"relations_{today}.csv"

    df = run_relations(args.prices, out_path)
    print(f"Saved relations metrics to {out_path.resolve()}")
    print(df.head())


if __name__ == "__main__":
    main()
