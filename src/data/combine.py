"""Transformaciones livianas sobre los precios ya en formato largo.

Briefing rápido:
- `add_basic_features` normaliza la columna `close` a valores numéricos y
  calcula el cambio porcentual diario por ticker.

La idea es mantener este módulo enfocado en características sencillas; los
estudios profundos viven en la capa de research externa.
"""

from __future__ import annotations

import pandas as pd


def add_basic_features(long_prices: pd.DataFrame) -> pd.DataFrame:
    """Normaliza precios y agrega `pct_change` agrupado por ticker."""

    df = long_prices.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])  # Mantener solo series numéricas limpias.
    df["pct_change"] = df.groupby("ticker")["close"].pct_change()
    return df
