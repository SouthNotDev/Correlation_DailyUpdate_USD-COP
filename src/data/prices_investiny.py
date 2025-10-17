"""Funciones para obtener datos historicos desde Investing.com usando investiny.

Briefing rapido:
- `download_investiny_prices` prepara un diccionario {alias: DataFrame OHLC}
  para cada instrumento configurado.
- `save_investiny_csv_per_instrument` persiste los datos crudos por instrumento.
- `investiny_to_long` convierte el diccionario anterior a formato largo estandar.

El objetivo es que este modulo se encargue de la integracion con Investing.com
de forma analoga al flujo existente con yfinance.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, Mapping

import pandas as pd
from investiny.historical import historical_data

from src.utils.io import date_folder

InstrumentConfig = Mapping[str, Any]
InstrumentFrames = Dict[str, pd.DataFrame]


def _normalize_instrument_entry(key: str, entry: Any) -> tuple[str, int] | None:
    """Devuelve (alias, investing_id) si la entrada es valida; caso contrario `None`."""

    if entry is None:
        return None
    if isinstance(entry, int):
        return key, entry
    if isinstance(entry, str):
        try:
            return key, int(entry)
        except ValueError:
            return None
    if isinstance(entry, Mapping):
        investing_id = entry.get("id")
        if investing_id is None:
            return None
        alias = entry.get("alias") or key
        try:
            return alias, int(investing_id)
        except (TypeError, ValueError):
            return None
    return None


def _fetch_investiny_frame(investing_id: int, lookback_days: int, interval: str) -> pd.DataFrame:
    """Obtiene el DataFrame OHLC para el `investing_id` indicado."""

    today = dt.date.today()
    start = today - dt.timedelta(days=lookback_days)
    # Investiny espera fechas en formato m/d/Y.
    to_date = today.strftime("%m/%d/%Y")
    from_date = start.strftime("%m/%d/%Y")

    raw = historical_data(
        investing_id=investing_id,
        from_date=from_date,
        to_date=to_date,
        interval=interval,
    )
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = {"open", "high", "low", "close", "volume"}
    for col in numeric_cols & set(df.columns):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    return df.sort_values("date").reset_index(drop=True)


def download_investiny_prices(
    instruments: InstrumentConfig,
    lookback_days: int = 365,
    interval: str = "D",
) -> InstrumentFrames:
    """Descarga datos OHLC desde Investing.com para los instrumentos configurados."""

    frames: InstrumentFrames = {}
    if not instruments:
        return frames
    for key, entry in instruments.items():
        alias_and_id = _normalize_instrument_entry(key, entry)
        if alias_and_id is None:
            continue
        alias, investing_id = alias_and_id
        try:
            df = _fetch_investiny_frame(investing_id, lookback_days=lookback_days, interval=interval)
        except ConnectionError as exc:
            logging.warning("Investiny fetch failed for %s (%s): %s", alias, investing_id, exc)
            continue
        if df.empty:
            continue
        frames[alias] = df
    return frames


def save_investiny_csv_per_instrument(
    frames: InstrumentFrames,
    base_dir: str,
    date_str: str,
) -> None:
    """Guarda cada DataFrame en CSV dentro de `raw/investiny/<fecha>`."""

    if not frames:
        return
    out_dir = date_folder(base_dir, "investiny", date_str)
    for alias, df in frames.items():
        df.to_csv(out_dir / f"{alias}.csv", index=False)


def investiny_to_long(frames: InstrumentFrames) -> pd.DataFrame:
    """Convierte los datos OHLC descargados a formato largo (date, ticker, close)."""

    if not frames:
        return pd.DataFrame(columns=["date", "ticker", "close"])
    stacked: list[pd.DataFrame] = []
    for alias, df in frames.items():
        subset = df[["date", "close"]].copy()
        subset["ticker"] = alias
        stacked.append(subset)
    combined = pd.concat(stacked, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.dropna(subset=["close"])
    combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)
    return combined[["date", "ticker", "close"]]
