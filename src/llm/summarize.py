"""Utilities to build the USD-COP daily briefing with OpenAI."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
import os

import pandas as pd
from openai import OpenAI, APIError


PROMPT_FILE = Path(__file__).with_name("prompt.md")


def get_openai_client() -> OpenAI:
    """Return an authenticated OpenAI client using the environment API key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing OPENAI_API_KEY. Set it in the environment before running the pipeline."
        )
    return OpenAI(api_key=api_key)


def build_briefing_with_llm(
    date: str,
    relations_df: pd.DataFrame,
    news_items: Sequence[dict],
    model: str = "gpt-4o-mini",
) -> str:
    """Generate a Markdown briefing for the given date using the LLM."""
    try:
        client = get_openai_client()

        if "periodo" in relations_df.columns:
            df_window = relations_df[relations_df["periodo"] == "5d"].copy()
        else:
            df_window = relations_df.copy()

        table_text = _format_tabla_for_prompt(df_window)
        news_text = _format_noticias_for_prompt(list(news_items))

        system_prompt = _get_system_prompt()
        user_prompt = (
            f"Fecha analizada: {date}\n\n"
            "Relaciones cuantitativas (ventana 5d). Cada fila describe un factor, "
            "su contribucion porcentual estimada al movimiento diario del USD-COP y "
            "una medida de relevancia estadistica.\n"
            f"{table_text}\n\n"
            "Titulares verificados del dia (usa solo los que aporten contexto, no inventes detalles):\n"
            f"{news_text}\n\n"
            "Con esa informacion, explica en espanol por que el USD-COP se movio respecto al cierre anterior. "
            "Apoya tus conclusiones en los factores cuantitativos y refuerza con los titulares cuando sea oportuno. "
            "Si faltan datos, reconocelo antes de concluir."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=700,
        )

        return (response.choices[0].message.content or "").strip()

    except APIError as exc:
        raise RuntimeError(f"OpenAI API error: {exc}") from exc


def _get_system_prompt() -> str:
    """Read the system prompt instructions from prompt.md."""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt file not found at {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


def _format_tabla_for_prompt(df: pd.DataFrame) -> str:
    """Format the relations dataframe into a readable Markdown table."""
    if df.empty:
        return "No hay datos de relaciones disponibles."

    table_lines = ["| Factor | Contribucion % | Score |", "|--------|----------------|-------|"]
    for _, row in df.iterrows():
        factor = str(row.get("factor", "N/A"))
        contrib = float(row.get("contribucion", 0.0))
        score = float(row.get("score_factor", 0.0))
        table_lines.append(f"| {factor} | {contrib:+.2f} | {score:.2f} |")
    return "\n".join(table_lines)


def _format_noticias_for_prompt(news_items: Sequence[dict]) -> str:
    """Return the news list formatted as bullet points."""
    if not news_items:
        return "No hay titulares para este dia."

    lines = []
    for item in news_items[:5]:
        title = item.get("title") or "Sin titulo"
        source = item.get("source") or "Fuente desconocida"
        lines.append(f"- {title} (Fuente: {source})")
    return "\n".join(lines)
