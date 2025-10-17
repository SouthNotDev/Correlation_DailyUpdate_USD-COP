"""Formatters for the daily briefing outputs (Markdown and lightweight HTML)."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

DELTA = "\u0394"


def _fmt_pct(value: float | None) -> str:
    """Format a change value as a percentage with two decimals."""

    if value is None or pd.isna(value):
        return "-"
    return f"{value * 100:.2f}%"


def _first_available(
    tickers: dict[str, pd.Series],
    candidates: Sequence[str],
) -> tuple[str | None, pd.Series | None]:
    """Return the first available ticker row for the provided candidate list."""

    for key in candidates:
        row = tickers.get(key)
        if row is not None:
            return key, row
    return None, None


def build_briefing_markdown(
    date_str: str,
    market_day: pd.DataFrame,
    news: Sequence[dict],
) -> str:
    """Compose the Markdown briefing given daily market data and news items."""

    tickers = {row["ticker"]: row for _, row in market_day.iterrows()} if not market_day.empty else {}
    usdcop = tickers.get("COP=X")
    brent = tickers.get("BZ=F")
    dxy_key, dxy = _first_available(tickers, ("DX-Y.NYB", "^DXY", "DX=F"))
    vix = tickers.get("^VIX")

    lines: list[str] = []
    lines.append(f"# Briefing USD/COP \u2014 {date_str}")
    lines.append("")
    lines.append("## Resumen de mercado")
    lines.append(
        "- USD/COP: "
        + (
            f"{usdcop['close']:.2f} ({DELTA} {_fmt_pct(usdcop['pct_change'])})"
            if usdcop is not None
            else "sin dato"
        )
    )
    if brent is not None:
        lines.append(f"- Brent (BZ=F): {brent['close']:.2f} USD/bbl ({DELTA} {_fmt_pct(brent['pct_change'])})")
    if dxy is not None and dxy_key is not None:
        lines.append(f"- DXY ({dxy_key}): {dxy['close']:.2f} ({DELTA} {_fmt_pct(dxy['pct_change'])})")
    if vix is not None:
        lines.append(f"- VIX (^VIX): {vix['close']:.2f} ({DELTA} {_fmt_pct(vix['pct_change'])})")

    lines.append("")
    lines.append("## Titulares relevantes")
    for item in list(news)[:6]:
        title = item.get("title") or item.get("url") or "Sin título"
        source = item.get("source", "")
        url = item.get("url", "")
        suffix = f" — {source}" if source else ""
        lines.append(f"- [{title}]({url}){suffix}")

    lines.append("")
    lines.append("## Comentario (borrador)")
    lines.append(
        "- El USD/COP refleja el impacto combinado de los movimientos en Brent y DXY. "
        "Complementariamente, la volatilidad implícita (VIX) aporta señales de apetito por riesgo."
    )
    lines.append(
        "- Los titulares sugieren factores locales (política, inflación, tasas) y externos "
        "(commodities, dólar global) como potenciales drivers."
    )
    lines.append(
        "- Validar eventos puntuales (anuncios gubernamentales, datos macro, FED/BanRep) "
        "que puedan explicar la dirección del día."
    )
    lines.append("")
    lines.append(
        "_Nota: Este resumen se genera automáticamente como base; requiere revisión humana antes de usarse en producción._"
    )

    return "\n".join(lines)


def build_briefing_html(
    date_str: str,
    market_day: pd.DataFrame,
    news: Sequence[dict],
) -> str:
    """Wrap the Markdown output in a minimal HTML template."""

    md = build_briefing_markdown(date_str, market_day, news)
    return f"""<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Briefing USD/COP — {date_str}</title>
    <style>
      body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.45; padding: 24px; }}
      pre {{ white-space: pre-wrap; }}
      a {{ color: #0366d6; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
    </style>
  </head>
  <body>
    <pre>{md}</pre>
  </body>
</html>
"""
