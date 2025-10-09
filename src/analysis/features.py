"""Pequeñas utilidades para construir el contexto diario del briefing.

Briefing rápido:
- `daily_context` filtra el último día disponible y devuelve los valores por
  ticker con su variación porcentual.

El módulo se mantiene intencionalmente mínimo; los análisis más complejos se
ejecutan en la fase de research fuera del pipeline.
"""

from __future__ import annotations

import pandas as pd


def daily_context(df_long: pd.DataFrame) -> pd.DataFrame:
    """Devuelve un DataFrame con el snapshot más reciente por ticker."""

    if df_long.empty:
        return df_long
    last_date = df_long["date"].max()
    day = df_long[df_long["date"] == last_date].copy()
    return day.sort_values("ticker").reset_index(drop=True)
