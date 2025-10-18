"""Script principal que orquesta el pipeline diario completo.

Ejecuta en secuencia:
1. Descarga precios de últimos 200 días
2. Genera análisis de relaciones
3. Scrappe noticias
4. Genera briefing con LLM
5. Guarda resultados

Este script corre diariamente a través de GitHub Actions a las 7am.
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
from src.analysis.relations import run_relations
from src.data.combine import add_basic_features
from src.data.prices_yf import download_yf_prices, save_prices_csv_per_symbol, to_long
from src.llm.summarize import build_briefing_with_llm, build_briefing_markdown, build_briefing_html
from src.news.scrape import scrape_sources
from src.utils.io import ensure_dir


def load_settings(path: str | os.PathLike) -> dict:
    """Abre el archivo YAML indicado y devuelve la configuración como dict."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    """Ejecuta el pipeline diario: precios → relaciones → noticias → briefing LLM."""

    parser = argparse.ArgumentParser(description="Run complete daily update pipeline.")
    parser.add_argument("--date", default="today", help="Date YYYY-MM-DD or 'today'")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to settings.yaml")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM briefing generation")
    args = parser.parse_args()

    settings = load_settings(args.config)
    tz = settings.get("locale", {}).get("timezone", "UTC")

    # Resolver fecha
    if args.date == "today":
        date = dt.date.today().strftime("%Y-%m-%d")
    else:
        date = args.date

    base_dir = settings.get("storage", {}).get("base_dir", "data")
    reports_dir = settings.get("reports", {}).get("dir", "reports/briefings")

    print(f"[{date}] Iniciando pipeline diario...")

    # 1) Descargar precios (últimos 200 días)
    print(f"[{date}] Descargando precios...")
    tickers = settings["yfinance"]["tickers"]
    period_years = int(settings["yfinance"].get("period_years", 5))
    interval = settings["yfinance"].get("interval", "1d")

    prices_wide = download_yf_prices(tickers, period_years=period_years, interval=interval)
    if not prices_wide.empty:
        save_prices_csv_per_symbol(prices_wide, base_dir=base_dir, date_str=date)
        long = to_long(prices_wide)
        long = add_basic_features(long)
        long = long.sort_values(["date", "ticker"]).reset_index(drop=True)
    else:
        long = pd.DataFrame(columns=["date", "ticker", "close", "pct_change"])

    ensure_dir(Path(base_dir) / "processed")
    long.to_parquet(Path(base_dir) / "processed" / "market_daily.parquet", index=False)
    print(f"[{date}] ✓ Precios guardados ({len(long)} registros)")

    market_day = daily_context(long)

    # 2) Generar análisis de relaciones
    print(f"[{date}] Generando análisis de relaciones...")
    relations_output = Path(reports_dir) / f"relations_{date}.json"
    ensure_dir(relations_output.parent)
    
    try:
        relations_df = run_relations(
            str(Path(base_dir) / "processed" / "market_daily.parquet"),
            str(relations_output)
        )
        print(f"[{date}] ✓ Análisis de relaciones generado")
    except Exception as e:
        print(f"[{date}] ⚠ Error en análisis de relaciones: {e}")
        relations_df = pd.DataFrame()

    # 3) Scrappear noticias
    print(f"[{date}] Scrapeando noticias...")
    news_cfg = settings.get("news", {})
    news_items: list[dict] = []
    if news_cfg.get("enabled", True):
        out_dir = Path(base_dir) / "raw" / "news" / date
        sources_csv = news_cfg.get("sources_csv", "info_sources.csv")
        keywords = news_cfg.get("keywords", ["peso", "dólar", "USDCOP"])
        try:
            news_items = scrape_sources(sources_csv, keywords, out_dir=out_dir)
            print(f"[{date}] ✓ Noticias obtenidas ({len(news_items)} items)")
        except Exception as e:
            print(f"[{date}] ⚠ Error en scraping: {e}")
            news_items = []

    # 4) Generar briefing con LLM
    print(f"[{date}] Generando briefing con LLM...")
    ensure_dir(reports_dir)
    
    if not args.skip_llm and not relations_df.empty:
        try:
            briefing_llm = build_briefing_with_llm(
                date,
                relations_df,
                news_items,
                model="gpt-4"  # Cambiar a "gpt-5" cuando esté disponible
            )
            
            # Guardar briefing LLM
            briefing_llm_path = Path(reports_dir) / f"briefing_llm_{date}.txt"
            with open(briefing_llm_path, "w", encoding="utf-8") as f:
                f.write(briefing_llm)
            
            print(f"[{date}] ✓ Briefing LLM generado")
            
            # Guardar resumen en JSON para facilitar acceso programático
            summary_json = {
                "date": date,
                "briefing": briefing_llm,
                "factors_count": len(relations_df),
                "news_count": len(news_items)
            }
            
            summary_path = Path(reports_dir) / f"briefing_{date}.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary_json, f, ensure_ascii=False, indent=2)
            
            print(f"[{date}] ✓ Resumen JSON guardado")
            
        except Exception as e:
            print(f"[{date}] ⚠ Error generando briefing LLM: {e}")

    # 5) Generar briefings Markdown y HTML (compatibilidad hacia atrás)
    print(f"[{date}] Generando briefings Markdown y HTML...")
    md_path = Path(reports_dir) / f"briefing_{date}.md"
    html_path = Path(reports_dir) / f"briefing_{date}.html"

    md = build_briefing_markdown(date, market_day, news_items)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    html = build_briefing_html(date, market_day, news_items)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[{date}] ✓ Briefings Markdown y HTML generados")

    # 6) Output final en JSON
    output = {
        "date": date,
        "timezone": tz,
        "prices_rows": int(len(long)),
        "relations_rows": int(len(relations_df)),
        "news_count": int(len(news_items)),
        "report_llm": str(Path(reports_dir) / f"briefing_llm_{date}.txt"),
        "report_md": str(md_path),
        "report_html": str(html_path),
        "report_json": str(Path(reports_dir) / f"briefing_{date}.json"),
        "relations_csv": str(relations_output),
    }

    print(f"[{date}] ✓ Pipeline completado")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
