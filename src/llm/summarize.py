"""Formatos de salida para el briefing diario (Markdown y HTML liviano).

Briefing rápido:
- `_fmt_pct` normaliza cambios porcentuales y maneja valores faltantes.
- `build_briefing_markdown` arma el cuerpo principal del briefing en Markdown.
- `build_briefing_html` reutiliza el Markdown y lo envuelve en HTML simple para
  enviarlo por email o incrustarlo en una web.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd


def _fmt_pct(x: float | None) -> str:
    """Convierte un número en porcentaje con dos decimales; maneja NaNs con un guion."""

    if x is None or pd.isna(x):
        return "—"
    return f"{x*100:.2f}%"


def build_briefing_markdown(date_str: str, market_day: pd.DataFrame, news: Sequence[dict]) -> str:
    """Construye el briefing principal en Markdown a partir de precios y titulares."""

    tickers = {row["ticker"]: row for _, row in market_day.iterrows()} if not market_day.empty else {}
    usdcop = tickers.get("COP=X")
    brent = tickers.get("BZ=F")
    dxy = tickers.get("^DXY") or tickers.get("DX-Y.NYB") or tickers.get("DX=F")
    vix = tickers.get("^VIX")

    lines: list[str] = []
    lines.append(f"# Briefing USD/COP — {date_str}")
    lines.append("")
    lines.append("## Resumen de mercado")
    lines.append("- USD/COP: " + (f"{usdcop['close']:.2f} (Δ {_fmt_pct(usdcop['pct_change'])})" if usdcop is not None else "sin dato"))
    if brent is not None:
        lines.append(f"- Brent (BZ=F): {brent['close']:.2f} USD/bbl (Δ {_fmt_pct(brent['pct_change'])})")
    if dxy is not None:
        lines.append(f"- DXY (^DXY): {dxy['close']:.2f} (Δ {_fmt_pct(dxy['pct_change'])})")
    if vix is not None:
        lines.append(f"- VIX (^VIX): {vix['close']:.2f} (Δ {_fmt_pct(vix['pct_change'])})")

    lines.append("")
    lines.append("## Titulares relevantes")
    for item in list(news)[:6]:
        title = item.get("title") or item.get("url")
        src = item.get("source", "")
        url = item.get("url", "")
        lines.append(f"- [{title}]({url}) — {src}")

    lines.append("")
    lines.append("## Comentario (borrador)")
    lines.append("- El USD/COP reflejó el impacto combinado de los movimientos en Brent y DXY. Complementariamente, la volatilidad implícita (VIX) aporta señales de apetito por riesgo.")
    lines.append("- Los titulares sugieren factores locales (política, inflación, tasas) y externos (commodities, dólar global) como potenciales drivers.")
    lines.append("- Validar eventos puntuales (anuncios gubernamentales, datos macro, FED/BanRep) que puedan explicar la dirección del día.")
    lines.append("")
    lines.append("_Nota: Este resumen es generado automáticamente como base; requiere revisión humana cuando se use en producción_.")

    return "\n".join(lines)


def build_briefing_html(date_str: str, market_day: pd.DataFrame, news: Sequence[dict]) -> str:
    """Envuelve el Markdown generado en un HTML mínimo apto para email o web."""

    md = build_briefing_markdown(date_str, market_day, news)
    return f"""
<!DOCTYPE html>
<html lang=\"es\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
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
