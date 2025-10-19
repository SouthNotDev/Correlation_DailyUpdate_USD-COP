"""Daily pipeline to generate the USD-COP briefing."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import yaml

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
        try:
            if item.is_file():
                item.unlink()
            else:
                shutil.rmtree(item)
        except PermissionError:
            print(f"[cleanup] Permission denied removing {item}. Skipping.")


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


SPANISH_WEEKDAYS = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def format_spanish_date(value: dt.date) -> str:
    """Return a human-readable Spanish date string."""
    return (
        f"{SPANISH_WEEKDAYS[value.weekday()]} "
        f"{value.day} de {SPANISH_MONTHS[value.month]} de {value.year}"
    )


def format_currency(value: float) -> str:
    """Format COP values using Spanish-style separators."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float) -> str:
    """Format percentage changes with sign and Spanish decimal separator."""
    return f"{value:+.2%}".replace(".", ",")


def build_price_context(long_prices: pd.DataFrame, report_date: dt.date) -> Tuple[str, Dict[str, float]]:
    """Create a textual summary of the latest USD/COP closes."""
    usd = long_prices[long_prices["ticker"] == "COP=X"].copy()
    if usd.empty:
        return (
            "No hay precios recientes para USD/COP; indícalo si impacta la explicación.",
            {},
        )

    usd["date"] = pd.to_datetime(usd["date"])
    usd = usd.sort_values("date").reset_index(drop=True)

    latest = usd.iloc[-1]
    last_date = latest["date"].date()
    last_close = float(latest["close"])
    days_since = (report_date - last_date).days

    price_meta = {
        "last_date": last_date.isoformat(),
        "last_close": last_close,
        "report_date": report_date.isoformat(),
        "days_since": days_since,
    }

    lines = [
        f"- Último cierre disponible ({format_spanish_date(last_date)}): "
        f"{format_currency(last_close)} COP por USD",
    ]

    if len(usd) > 1:
        previous = usd.iloc[-2]
        prev_date = previous["date"].date()
        prev_close = float(previous["close"])
        abs_change = last_close - prev_close
        pct_change = (abs_change / prev_close) if prev_close else 0.0
        direction = (
            "al alza" if abs_change > 0 else "a la baja" if abs_change < 0 else "sin cambios"
        )

        price_meta.update(
            {
                "prev_date": prev_date.isoformat(),
                "prev_close": prev_close,
                "abs_change": abs_change,
                "pct_change": pct_change,
            }
        )

        lines.append(
            f"- Cierre previo ({format_spanish_date(prev_date)}): "
            f"{format_currency(prev_close)} COP por USD"
        )
        lines.append(
            f"- Variación vs. cierre previo: {format_currency(abs_change)} COP "
            f"({format_percent(pct_change)}) - dirección {direction}"
        )
    else:
        lines.append(
            "- No hay un cierre anterior disponible para comparar (primera observación registrada)."
        )

    if days_since != 0:
        if days_since == 1:
            lines.append(
                f"- Nota: el informe se genera el {format_spanish_date(report_date)} (1 día después del último cierre)."
            )
        elif days_since > 1:
            lines.append(
                f"- Nota: el informe se genera el {format_spanish_date(report_date)}, "
                f"{days_since} días después del último cierre negociado."
            )
        elif days_since < 0:
            lines.append(
                f"- Nota: la fecha del informe ({format_spanish_date(report_date)}) es anterior al último cierre registrado."
            )

    return "\n".join(lines), price_meta


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

    report_date = dt.date.fromisoformat(date)
    price_context, price_meta = build_price_context(long_prices, report_date)

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
            briefing_md = build_briefing_with_llm(
                date,
                price_context,
                price_meta,
                relations_df,
                news_items,
            )
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
        "price_text": price_context,
        "price_meta": price_meta,
        "briefing_path": str(briefing_path),
        "relations_path": str(relations_output),
        "market_data_path": str(processed_path),
    }

    print(f"[{date}] Pipeline finished.")
    print(json.dumps(output_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
