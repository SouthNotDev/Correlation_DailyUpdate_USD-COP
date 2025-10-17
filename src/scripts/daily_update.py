"""Script principal que orquesta el pipeline diario.

Briefing rápido:
- `load_settings` lee la configuración YAML.
- `main` es el entrypoint: descarga precios, extrae noticias y genera los
  briefings en Markdown y HTML.

El flujo se mantiene lineal para facilitar su ejecución manual o vía
automatizaciones como GitHub Actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd
import yaml

from src.analysis.features import daily_context
from src.data.combine import add_basic_features
from src.data.prices_investiny import (
    download_investiny_prices,
    investiny_to_long,
    save_investiny_csv_per_instrument,
)
from src.data.prices_yf import download_yf_prices, save_prices_csv_per_symbol, to_long
from src.llm.summarize import build_briefing_html, build_briefing_markdown
from src.news.scrape import scrape_sources
from src.utils.io import ensure_dir


def load_settings(path: str | os.PathLike) -> dict:
    """Abre el archivo YAML indicado y devuelve la configuración como dict."""

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    """Ejecuta el pipeline diario: precios → noticias → briefing."""

    parser = argparse.ArgumentParser(description="Run daily update pipeline.")
    parser.add_argument("--date", default="today", help="Date YYYY-MM-DD or 'today'")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to settings.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)
    tz = settings.get("locale", {}).get("timezone", "UTC")  # Reservado para futuros usos.

    # Resolver la fecha objetivo (por defecto, hoy).
    if args.date == "today":
        date = dt.date.today().strftime("%Y-%m-%d")
    else:
        date = args.date

    base_dir = settings.get("storage", {}).get("base_dir", "data")
    reports_dir = settings.get("reports", {}).get("dir", "reports/briefings")

    # 1) Precios vía yfinance
    tickers = settings["yfinance"]["tickers"]
    period_years = int(settings["yfinance"].get("period_years", 5))
    interval = settings["yfinance"].get("interval", "1d")

    prices_wide = download_yf_prices(tickers, period_years=period_years, interval=interval)
    long_frames: list[pd.DataFrame] = []
    if not prices_wide.empty:
        save_prices_csv_per_symbol(prices_wide, base_dir=base_dir, date_str=date)
        yf_long = to_long(prices_wide)
        yf_long = add_basic_features(yf_long)
        long_frames.append(yf_long)

    # 1.b) Precios via Investing.com (investiny)
    invest_cfg = settings.get("investiny", {})
    investiny_frames = {}
    if invest_cfg.get("enabled", False):
        instruments = invest_cfg.get("instruments", {})
        lookback_days = int(invest_cfg.get("lookback_days", 365))
        invest_interval = invest_cfg.get("interval", "D")
        investiny_frames = download_investiny_prices(
            instruments,
            lookback_days=lookback_days,
            interval=invest_interval,
        )
        if investiny_frames:
            save_investiny_csv_per_instrument(investiny_frames, base_dir=base_dir, date_str=date)
            investiny_long = investiny_to_long(investiny_frames)
            if not investiny_long.empty:
                investiny_long = add_basic_features(investiny_long)
                long_frames.append(investiny_long)

    if long_frames:
        long = pd.concat(long_frames, ignore_index=True)
        long = long.sort_values(["date", "ticker"]).reset_index(drop=True)
    else:
        long = pd.DataFrame(columns=["date", "ticker", "close", "pct_change"])  # Fallback vacío.

    ensure_dir(Path(base_dir) / "processed")
    long.to_parquet(Path(base_dir) / "processed" / "market_daily.parquet", index=False)

    market_day = daily_context(long)

    # 2) Noticias (scraping liviano)
    news_cfg = settings.get("news", {})
    news_items: list[dict] = []
    if news_cfg.get("enabled", True):
        out_dir = Path(base_dir) / "raw" / "news" / date
        sources_csv = news_cfg.get("sources_csv", "info_sources.csv")
        keywords = news_cfg.get("keywords", ["peso", "dólar", "USDCOP"]) 
        news_items = scrape_sources(sources_csv, keywords, out_dir=out_dir)

    # 3) Briefing (Markdown + HTML)
    ensure_dir(reports_dir)
    md_path = Path(reports_dir) / f"briefing_{date}.md"
    html_path = Path(reports_dir) / f"briefing_{date}.html"

    md = build_briefing_markdown(date, market_day, news_items)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    html = build_briefing_html(date, market_day, news_items)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Log de salida en JSON para integraciones (GitHub Actions, etc.).
    print(json.dumps({
        "date": date,
        "timezone": tz,
        "prices_rows": int(len(long)),
        "news_count": int(len(news_items)),
        "report_md": str(md_path),
        "report_html": str(html_path),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
