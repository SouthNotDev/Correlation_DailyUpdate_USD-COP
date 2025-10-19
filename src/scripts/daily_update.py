"""Daily pipeline to generate the USD-COP briefing."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path

import pandas as pd
import yaml

from src.analysis.features import daily_context
from src.analysis.relations import run_relations
from src.data.combine import add_basic_features
from src.data.prices_yf import (
    download_yf_prices,
    save_prices_csv_per_symbol,
    to_long,
)
from src.llm.summarize import build_briefing_with_llm
from src.news.scrape import scrape_sources
from src.utils.io import ensure_dir


def load_settings(path: str | Path) -> dict:
    """Read the YAML settings file."""
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def clean_directory(path: Path) -> None:
    """Remove every file and folder inside the provided directory."""
    if not path.exists():
        return
    for item in path.iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_file():
            item.unlink()
        else:
            shutil.rmtree(item)


def prepare_storage(base_dir: Path, reports_dir: Path, relations_dir: Path) -> None:
    """Ensure working folders exist and clear previous outputs."""
    raw_dir = base_dir / "raw"
    processed_dir = base_dir / "processed"

    for target in [raw_dir, processed_dir, reports_dir, relations_dir]:
        target.mkdir(parents=True, exist_ok=True)
        clean_directory(target)


def resolve_date(date_arg: str) -> str:
    if date_arg == "today":
        return dt.date.today().strftime("%Y-%m-%d")
    return date_arg


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete daily update pipeline.")
    parser.add_argument("--date", default="today", help="Date in YYYY-MM-DD format or 'today'")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to the settings file")
    parser.add_argument("--skip-llm", action="store_true", help="Skip briefing generation")
    args = parser.parse_args()

    settings = load_settings(args.config)
    date = resolve_date(args.date)

    base_dir = Path(settings.get("storage", {}).get("base_dir", "data"))
    reports_dir = Path(settings.get("reports", {}).get("dir", "reports/briefings"))
    relations_dir = Path(settings.get("reports", {}).get("relations_dir", "reports/relations"))
    prepare_storage(base_dir, reports_dir, relations_dir)

    print(f"[{date}] Starting daily pipeline...")

    # 1) Download price history
    tickers = settings["yfinance"]["tickers"]
    period_years = int(settings["yfinance"].get("period_years", 5))
    interval = settings["yfinance"].get("interval", "1d")

    print(f"[{date}] Downloading prices...")
    prices_wide = download_yf_prices(tickers, period_years=period_years, interval=interval)
    if prices_wide.empty:
        long_prices = pd.DataFrame(columns=["date", "ticker", "close", "pct_change"])
    else:
        save_prices_csv_per_symbol(prices_wide, base_dir=str(base_dir), date_str=date)
        long_prices = to_long(prices_wide)
        long_prices = add_basic_features(long_prices)
        long_prices = long_prices.sort_values(["date", "ticker"]).reset_index(drop=True)

    processed_path = base_dir / "processed" / "market_daily.parquet"
    ensure_dir(processed_path.parent)
    long_prices.to_parquet(processed_path, index=False)
    print(f"[{date}] Stored {len(long_prices)} price rows.")

    market_day = daily_context(long_prices)

    # 2) Relations analysis
    print(f"[{date}] Building factor relations...")
    relations_output = relations_dir / f"relations_{date}.json"
    ensure_dir(relations_output.parent)

    try:
        relations_df = run_relations(str(processed_path), str(relations_output))
        print(f"[{date}] Relations analysis completed.")
    except Exception as exc:  # noqa: BLE001
        print(f"[{date}] Relations analysis failed: {exc}")
        relations_df = pd.DataFrame()

    # 3) News scraping
    print(f"[{date}] Scraping news...")
    news_settings = settings.get("news", {})
    news_items: list[dict] = []
    if news_settings.get("enabled", True):
        sources_csv = news_settings.get("sources_csv", "info_sources.csv")
        keywords = news_settings.get("keywords", ["peso", "dolar", "USDCOP"])
        out_dir = base_dir / "raw" / "news" / date
        ensure_dir(out_dir)
        try:
            news_items = scrape_sources(sources_csv, keywords, out_dir=str(out_dir))
            print(f"[{date}] Retrieved {len(news_items)} headlines.")
        except Exception as exc:  # noqa: BLE001
            print(f"[{date}] News scraping failed: {exc}")

    # 4) LLM briefing
    briefing_path = reports_dir / f"briefing_{date}.md"
    if args.skip_llm:
        print(f"[{date}] Skipping LLM step by request.")
        briefing_path.write_text("# Briefing no generado\n", encoding="utf-8")
        print(f"[{date}] Briefing placeholder saved to {briefing_path}.")
    elif relations_df.empty:
        print(f"[{date}] Skipping LLM step due to missing relations data.")
        briefing_path.write_text("# Briefing no disponible\n", encoding="utf-8")
        print(f"[{date}] Briefing placeholder saved to {briefing_path}.")
    else:
        print(f"[{date}] Generating briefing with LLM...")
        try:
            briefing_md = build_briefing_with_llm(date, relations_df, news_items)
            briefing_path.write_text(briefing_md + "\n", encoding="utf-8")
            print(f"[{date}] Briefing saved to {briefing_path}.")
        except Exception as exc:  # noqa: BLE001
            print(f"[{date}] LLM generation failed: {exc}")
            briefing_path.write_text("# Briefing no disponible\n", encoding="utf-8")
            print(f"[{date}] Briefing placeholder saved to {briefing_path}.")

    output_summary = {
        "date": date,
        "prices_rows": int(len(long_prices)),
        "relations_rows": int(len(relations_df)),
        "news_count": int(len(news_items)),
        "briefing_path": str(briefing_path),
        "relations_path": str(relations_output),
        "market_data_path": str(processed_path),
    }

    print(f"[{date}] Pipeline finished.")
    print(json.dumps(output_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
