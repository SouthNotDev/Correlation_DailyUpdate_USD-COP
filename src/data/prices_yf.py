"""Funciones para obtener y preparar precios históricos desde yfinance.

Briefing rápido:
- `download_yf_prices` descarga cierres diarios para una lista de tickers y
  devuelve un DataFrame ancho (columnas por ticker).
- `save_prices_csv_per_symbol` persiste cada serie en CSV dentro de la carpeta
  diaria correspondiente.
- `to_long` transforma el DataFrame ancho en formato largo listo para análisis
  posteriores.

Este módulo es la puerta de entrada para la capa de datos de mercado del
pipeline diario.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

import pandas as pd
import yfinance as yf

from src.utils.io import ensure_dir, date_folder


def download_yf_prices(
    tickers: Iterable[str],
    period_years: int = 5,
    interval: str = "1d",
) -> pd.DataFrame:
    """Descarga cierres desde yfinance y devuelve un DataFrame indexado por fecha."""

    end = dt.date.today()
    start = end - dt.timedelta(days=365 * period_years + 7)

    frames: list[pd.Series] = []
    for t in tickers:
        # Descarga los precios históricos del ticker solicitado.
        df = yf.download(t, start=start.isoformat(), end=end.isoformat(), interval=interval, auto_adjust=False)
        if df.empty:
            continue
        s = df["Close"].copy()
        s.name = t
        s.index.name = "date"
        frames.append(s)
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, axis=1).sort_index()
    merged.index.name = "date"
    return merged


def save_prices_csv_per_symbol(df: pd.DataFrame, base_dir: str, date_str: str) -> None:
    """Guarda cada columna del DataFrame en un CSV individual dentro del día actual."""

    out_dir = date_folder(base_dir, "prices", date_str)
    for col in df.columns:
        path = out_dir / f"{col}.csv"
        df[[col]].rename(columns={col: "close"}).to_csv(path)


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el DataFrame ancho (columnas=tickers) a formato largo estándar."""

    long = df.reset_index().melt(id_vars=["date"], var_name="ticker", value_name="close")
    long = long.dropna().sort_values(["date", "ticker"]).reset_index(drop=True)
    return long
