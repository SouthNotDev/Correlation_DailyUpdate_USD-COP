"""Utilities to build the USD-COP daily briefing with OpenAI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence, Tuple

import pandas as pd

try:  # pragma: no cover - optional dependency in local dev
    from openai import OpenAI, APIError
except ModuleNotFoundError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

    class APIError(Exception):
        """Fallback API error when OpenAI SDK is unavailable."""


PROMPT_FILE = Path(__file__).with_name("prompt.md")

FACTOR_INFO: dict[str, dict[str, str]] = {
    "DXY_L1": {
        "label": "Índice dólar global (DXY)",
        "description": (
            "Refleja la fortaleza del dólar frente a una cesta de monedas. "
            "Contribuciones positivas suelen empujar al USD-COP al alza; "
            "contribuciones negativas indican un dólar global más débil."
        ),
    },
    "LA_USD": {
        "label": "Monedas latinoamericanas frente al USD",
        "description": (
            "Agrupa movimientos de pares regionales (MXN, CLP, etc.). "
            "Un aporte positivo implica que la región se depreció frente al dólar, "
            "restando soporte al peso colombiano."
        ),
    },
    "BZ_lag1": {
        "label": "Petróleo Brent (cierre previo)",
        "description": (
            "Precio del crudo Brent en la sesión previa. Subidas suelen fortalecer "
            "los ingresos petroleros de Colombia y presionan a la baja al USD-COP."
        ),
    },
    "Local5d": {
        "label": "Activos financieros colombianos",
        "description": (
            "Resume acciones, bonos y tasas locales. Aportes negativos indican apetito "
            "por riesgo en Colombia que fortalece al peso; positivos reflejan estrés local."
        ),
    },
    "residual": {
        "label": "Factores locales no modelados",
        "description": (
            "Parte del movimiento que no explican los factores cuantitativos. "
            "Puede asociarse a noticias o flujos específicos del mercado colombiano."
        ),
    },
}

DEFAULT_FACTOR_INFO = {
    "label": "Factor sin nombre",
    "description": (
        "Variable sin descripción específica. Traduce el impacto según su contribución "
        "y el contexto de noticias."
    ),
}


def get_openai_client() -> OpenAI:
    """Return an authenticated OpenAI client using the environment API key."""
    if OpenAI is None:
        raise ModuleNotFoundError(
            "The 'openai' package is not installed. Install it or run with --skip-llm."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing OPENAI_API_KEY. Set it in the environment before running the pipeline."
        )
    return OpenAI(api_key=api_key)


def build_briefing_with_llm(
    date: str,
    price_context: str,
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

        factors_summary, factor_notes = _format_factors_for_prompt(df_window)
        news_text = _format_noticias_for_prompt(list(news_items))

        system_prompt = _get_system_prompt()
        user_prompt = (
            f"Fecha analizada: {date}\n\n"
            "Cierres y variación reciente (usa estos valores literalmente en la primera frase):\n"
            f"{price_context}\n\n"
            "Factores cuantitativos relevantes para el movimiento del USD-COP:\n"
            f"{factors_summary}\n\n"
            "Cómo interpretar cada factor (emplea estos nombres en la redacción, nunca los códigos técnicos):\n"
            f"{factor_notes}\n\n"
            "Temas económicos del día (parafrásealos sin citar titulares textuales):\n"
            f"{news_text}\n\n"
            "Sigue las instrucciones del sistema y produce un briefing profesional en español."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.55,
            max_tokens=750,
        )

        return (response.choices[0].message.content or "").strip()

    except APIError as exc:  # pragma: no cover - network side effect
        raise RuntimeError(f"OpenAI API error: {exc}") from exc


def _get_system_prompt() -> str:
    """Read the system prompt instructions from prompt.md."""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt file not found at {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


def _format_factors_for_prompt(df: pd.DataFrame) -> Tuple[str, str]:
    """Return a summary string and a description string for factor data."""
    if df.empty:
        return (
            "No hay datos de relaciones disponibles para el último cierre.",
            "Sin definiciones de factores disponibles.",
        )

    df_sorted = df.copy()
    df_sorted["abs_contrib"] = df_sorted["contribucion"].abs()
    df_sorted = df_sorted.sort_values("abs_contrib", ascending=False)

    summary_lines: list[str] = []
    description_lines: list[str] = []
    seen_labels: set[str] = set()

    for _, row in df_sorted.iterrows():
        factor_code = str(row.get("factor", "N/A"))
        info = FACTOR_INFO.get(factor_code, DEFAULT_FACTOR_INFO)
        label = info["label"]

        contrib = float(row.get("contribucion", 0.0))
        retorno = float(row.get("retorno_hoy", 0.0))
        score = float(row.get("score_factor", 0.0))

        summary_lines.append(
            f"- {label}: contribución estimada {contrib:+.2f} puntos, "
            f"variación del factor {retorno:+.2f}, score {score:.2f}."
        )

        if label not in seen_labels:
            description_lines.append(f"- {label}: {info['description']}")
            seen_labels.add(label)

    return "\n".join(summary_lines), "\n".join(description_lines)


def _format_noticias_for_prompt(news_items: Sequence[dict]) -> str:
    """Return the news list formatted as bullet points."""
    if not news_items:
        return "No hay titulares para este día. Indícalo si afecta la conclusión."

    lines = []
    for item in news_items[:5]:
        title = item.get("title") or "Sin titulo"
        source = item.get("source") or "Fuente desconocida"
        lines.append(f"- {title} (Fuente: {source})")
    return "\n".join(lines)
