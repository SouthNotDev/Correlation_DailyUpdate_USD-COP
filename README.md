# Daily USD-COP Market Briefings

An automated pipeline that turns raw market data into a daily, ready-to-publish briefing about how the US dollar moves against the Colombian peso. It demonstrates data engineering, LLM prompt design, and product polish working together to deliver a repeatable insight product. The workflow applies several statistical checks before handing clean tables to the language model on each run.

## Project At A Glance
- Focuses on the USD-COP exchange rate and why it changed each day.
- Packages the story in a short briefing that is ready for a website or newsletter.
- Runs hands-free every morning through GitHub Actions with no servers to manage.
- Enriches the narrative with supporting data: market drivers, correlations, and curated news headlines.
- Ships a single Markdown briefing each day, making it easy to embed or share without extra processing.

## What The Daily Briefing Delivers
- A 3-4 paragraph narrative that explains the daily currency move in plain language.
- A bullet list of the biggest drivers (for example oil prices, regional FX moves, global dollar strength).
- Quick stats for context: percentage move, volatility, number of supporting factors.
- Links to the most relevant headlines pulled from curated RSS sources.
- Companion data files for anyone who wants to run deeper analysis.

## How It Runs (High-Level)
1. Every morning a GitHub Actions workflow triggers the pipeline.
2. Market data ingestion pulls five years of history for USD-COP and key drivers, plus the latest day.
3. The LLM briefing step turns structured metrics into a human-readable summary.
4. Publishing saves the results in `reports/briefings/` so they can be embedded or consumed via the GitHub raw URL.
5. A Buttondown step queues the newsletter so subscribers receive it right after the workflow finishes.

## Sample Output - In spanish
```
# Briefing USD-COP - 19 de octubre de 2025

Ayer, viernes 17 de octubre de 2025, el cierre del tipo de cambio USD-COP fue de 3.860,75 COP por USD, lo que representa una disminución de 28,95 COP (-0,74%) en comparación con el cierre anterior de 3.889,70 COP por USD. Este movimiento a la baja se vio influenciado por varios factores en el mercado cambiario.

En términos cuantitativos, los activos financieros colombianos tuvieron una contribución negativa al tipo de cambio, lo que indica un mayor apetito por riesgo en el contexto local, mientras que los factores locales no modelados también aportaron a la presión a la baja. En contraste, las monedas latinoamericanas frente al dólar mostraron un ligero debilitamiento, lo que restó soporte al peso colombiano. El petróleo Brent y el índice dólar global no tuvieron un impacto significativo en el movimiento del día, lo que sugiere que el mercado estuvo más influenciado por factores internos y la dinámica de riesgo local.

En el contexto noticioso, se reportaron rumores sobre un decreto que podría cambiar la inversión de las administradoras de fondos de pensiones, lo que generó incertidumbre en el mercado y contribuyó a la caída del dólar. Además, la situación política en Ecuador, con el fin de las protestas tras un acuerdo entre el presidente y los indígenas, podría tener un efecto indirecto en la región, aunque no se observaron impactos inmediatos en el tipo de cambio. En conclusión, el driver principal del movimiento fue el aumento del apetito por riesgo en el mercado colombiano, mientras que el riesgo secundario a seguir es la evolución de las noticias relacionadas con las políticas económicas locales.

```

## Tech Highlights
- Python scripts orchestrate data ingestion, analysis, and prompt assembly.
- OpenAI GPT models transform structured metrics into clean narrative copy.
- GitHub Actions handles automated scheduling and delivery.
- Produces clean Markdown that can be fetched directly from GitHub for web or newsletter publishing.

## Want To Run It Yourself?
Open `QUICK_START.md` for a concise setup checklist. It covers how to add your OpenAI key, run the pipeline locally or on schedule, and embed the daily briefing on a website or newsletter.

## Newsletter Delivery
- Subscribe to the daily email at [buttondown.com/juandavidsanchezlatorre](https://buttondown.com/juandavidsanchezlatorre).
- Emails ship with the subject `USD/COP - Briefing 2 minutos | YYYY-MM-DD` as soon as the 07:00 UTC job completes.
- The Buttondown integration lives in `src/scripts/send_newsletter.py` and expects `BUTTONDOWN_API_KEY` (and optionally `BUTTONDOWN_NEWSLETTER`) to be present as GitHub Action secrets.

## Maintainer
Juan Diego Mesa - Data and AI Engineer
Always looking to build automated research experiences that feel editorial, not robotic.
