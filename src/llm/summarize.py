"""Generador de briefings usando OpenAI API GPT-4/GPT-5.

Convierte los datos de relaciones de factores en un texto natural, profesional
y fácil de entender en 2-3 minutos de lectura.
"""

from __future__ import annotations

import json
import os
from typing import Optional
import pandas as pd
from openai import OpenAI, APIError


def get_openai_client() -> OpenAI:
    """Obtiene cliente OpenAI configurado con API key del entorno."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY no configurada. "
            "Define la variable de entorno antes de ejecutar."
        )
    return OpenAI(api_key=api_key)


def build_briefing_with_llm(
    date: str,
    relations_df: pd.DataFrame,
    news_items: list[dict],
    model: str = "gpt-4",
) -> str:
    """Genera un briefing profesional usando OpenAI API basado en relaciones.

    Args:
        date: Fecha del análisis (YYYY-MM-DD)
        relations_df: DataFrame con análisis de relaciones (debe incluir periodo)
        news_items: Lista de noticias del día
        model: Modelo OpenAI a usar (gpt-4, gpt-4-turbo, etc.)

    Returns:
        Texto del briefing profesional en español
    """
    try:
        client = get_openai_client()

        # Filtrar solo datos del período 5d para el briefing (más relevante)
        if "periodo" in relations_df.columns:
            df_5d = relations_df[relations_df["periodo"] == "5d"].copy()
        else:
            df_5d = relations_df.copy()

        # Preparar tabla en formato legible
        tabla_text = _format_tabla_for_prompt(df_5d)

        # Preparar contexto de noticias
        noticias_text = _format_noticias_for_prompt(news_items)

        # Construir prompt del sistema y usuario
        system_prompt = _get_system_prompt()
        user_prompt = f"""
Fecha del análisis: {date}

TABLA DE FACTORES (período 5d):
{tabla_text}

NOTICIAS DEL DÍA (contexto):
{noticias_text}

Genera un briefing claro, profesional y natural en español que cualquier persona 
entienda en 2-3 minutos. Sigue EXACTAMENTE las instrucciones del sistema.
"""

        # Llamar API OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=800,
        )

        briefing_text = response.choices[0].message.content
        return briefing_text

    except APIError as e:
        raise RuntimeError(f"Error llamando OpenAI API: {str(e)}")


def _get_system_prompt() -> str:
    """Retorna el prompt del sistema con instrucciones detalladas."""
    return """Eres un analista financiero que genera briefings diarios sobre el precio del dólar frente al peso colombiano.

INSTRUCCIONES PARA GENERAR EL BRIEFING:

1. APERTURA: Empieza diciendo cuánto se movió el dólar frente al peso hoy, en qué dirección, y expresa el cambio en porcentaje con un decimal (ej: "subió 0.5%").

2. FACTORES PRINCIPALES: Identifica los dos factores con mayor contribución absoluta (excluyendo residual). Nómbralos en orden de importancia.
   - Si contribución es positiva: "presionó al dólar al alza"
   - Si contribución es negativa: "favoreció al peso"

3. MAPEO DE NOMBRES:
   - DXY, DXY_L1 → "dólar global"
   - LA_USD → "monedas de Latinoamérica"
   - BZ=F, BZ_lag1 → "petróleo"
   - GXG, ICOL, CIB → "mercado local colombiano"
   - ^VIX → "aversión al riesgo global"
   - ^TNX → "tasas de bonos en EE.UU."
   - USDCLP=X → "peso chileno"
   - USDMXN=X → "peso mexicano"

4. PETRÓLEO: Si aparece en los dos principales, menciona explícitamente que se movió en la misma dirección y apoyo/limitó el movimiento.

5. MONEDAS REGIONALES: Si LA_USD, USDCLP=X o USDMXN=X son relevantes, di que "los pares de la región acompañaron el movimiento".

6. VOLATILIDAD GLOBAL: Si ^VIX está en los dos principales o tiene score alto, agrega una frase corta sobre apetito por riesgo acorde al signo de su contribución.

7. RESIDUAL: Si es > 30% del movimiento, añade que "una parte importante no fue explicada por activos observados, probablemente por factores locales".

8. MOVIMIENTO MIXTO: Si ningún factor explica ≥25% del movimiento, di "el movimiento fue mixto sin un catalizador dominante".

9. NÚMEROS: Muestra porcentajes con un decimal, redondea hacia el valor más cercano. Máximo dos cifras por número.

10. PROHIBICIONES: 
    - NO inventes noticias, nombres de personas, cifras específicas de indicadores, decisiones de bancos centrales ni eventos.
    - Si alude a catalizadores, sé genérico: "datos globales", "ajustes en tasas", "noticias locales".

11. ESTRUCTURA: 1-3 párrafos máximo, corridos, sin listas ni viñetas. Tono claro, directo, profesional, sin jerga técnica.

12. LENGUAJE PERMITIDO: "subió/cayó X%", "el principal impulso", "acompañaron el movimiento", "aportó en contra", "una fracción no se explicó", "sugiere efecto local", "parece", "probablemente", "en línea con".

13. NUNCA uses: guiones largos, tablas, código, títulos, viñetas.

14. ESTILO: Natural, como si lo escribiera un analista experimentado para un cliente que no es técnico.
"""


def _format_tabla_for_prompt(df: pd.DataFrame) -> str:
    """Formatea el DataFrame de relaciones para incluir en el prompt."""
    if df.empty:
        return "Sin datos disponibles."

    texto = ""
    for idx, row in df.iterrows():
        factor = row.get("factor", "Unknown")
        retorno = row.get("retorno_hoy", 0)
        contrib = row.get("contribucion", 0)
        score = row.get("score_factor", 0)

        # Formatear valores
        ret_fmt = f"{retorno:.3f}"
        contrib_fmt = f"{contrib:.3f}"
        score_fmt = f"{score:.3f}"

        texto += f"- {factor}: retorno={ret_fmt}%, contribución={contrib_fmt}%, score={score_fmt}\n"

    return texto


def _format_noticias_for_prompt(news_items: list[dict]) -> str:
    """Formatea noticias para incluir en el prompt."""
    if not news_items:
        return "No hay noticias disponibles del día."

    texto = ""
    for i, news in enumerate(news_items[:5], 1):  # Top 5 noticias
        titulo = news.get("title", "Sin título")
        source = news.get("source", "Fuente desconocida")
        texto += f"{i}. {titulo} (Fuente: {source})\n"

    return texto


def build_briefing_markdown(
    date: str,
    market_day: pd.DataFrame,
    news_items: list[dict],
) -> str:
    """Genera briefing en Markdown (compatible hacia atrás)."""
    lines = [
        f"# Briefing Diario - {date}",
        "",
        "## Resumen de Mercado",
        "",
        "| Ticker | Precio | Cambio |",
        "|--------|--------|--------|",
    ]

    if not market_day.empty:
        for _, row in market_day.iterrows():
            ticker = row.get("ticker", "N/A")
            close = row.get("close", 0)
            change = row.get("pct_change", 0)
            lines.append(
                f"| {ticker} | {close:.2f} | {change:+.2%} |"
            )

    lines.append("")
    lines.append("## Noticias Relevantes")
    lines.append("")

    if news_items:
        for news in news_items[:5]:
            titulo = news.get("title", "Sin título")
            url = news.get("link", "#")
            lines.append(f"- [{titulo}]({url})")
    else:
        lines.append("No hay noticias disponibles.")

    return "\n".join(lines)


def build_briefing_html(
    date: str,
    market_day: pd.DataFrame,
    news_items: list[dict],
) -> str:
    """Genera briefing en HTML (compatible hacia atrás)."""
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Briefing - {date}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; margin: 20px; max-width: 900px; margin-left: auto; margin-right: auto; line-height: 1.6; color: #333; }}
        h1 {{ color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        h2 {{ color: #0066cc; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #0066cc; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .meta {{ color: #666; font-size: 0.9em; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <h1>Briefing Diario - {date}</h1>
    
    <h2>Resumen de Mercado</h2>
    <table>
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Precio</th>
                <th>Cambio</th>
            </tr>
        </thead>
        <tbody>
"""
    if not market_day.empty:
        for _, row in market_day.iterrows():
            ticker = row.get("ticker", "N/A")
            close = row.get("close", 0)
            change = row.get("pct_change", 0)
            change_color = "green" if change > 0 else "red"
            html += f"""            <tr>
                <td><strong>{ticker}</strong></td>
                <td>{close:.2f}</td>
                <td style="color: {change_color};">{change:+.2%}</td>
            </tr>
"""

    html += """        </tbody>
    </table>
    
    <h2>Noticias Relevantes</h2>
    <ul>
"""
    if news_items:
        for news in news_items[:5]:
            titulo = news.get("title", "Sin título")
            url = news.get("link", "#")
            html += f'        <li><a href="{url}" target="_blank">{titulo}</a></li>\n'
    else:
        html += "        <li>No hay noticias disponibles.</li>\n"

    html += f"""    </ul>
    
    <div class="meta">
        <p>Generado automáticamente el {date}</p>
    </div>
</body>
</html>
"""
    return html
