# Daily USD/COP Market Briefings

An automated pipeline that turns raw market data into a daily, ready-to-publish briefing about how the US dollar is moving against the Colombian peso. Built to showcase data engineering, LLM prompt design, and product polish in one project. The project uses various statistical techniques to analyze the data and give an already cured data by tables to the LLM on each of the context calls.

## Project At A Glance
- Focuses on the USD/COP exchange rate and why it moved each day.
- Packages the story in a short briefing that is easy to drop into a website or newsletter.
- Runs hands-free every morning through GitHub Actions; no servers to maintain.
- Enriches the narrative with supporting data: market drivers, correlations, and curated news headlines.
- Ships multiple formats (plain text, Markdown, HTML, JSON, CSV) so different audiences can consume the output.

## What The Daily Briefing Delivers
- A 3–4 paragraph narrative that explains the daily currency move in plain language.
- A bullet list of the biggest drivers (e.g., oil prices, regional FX moves, global dollar strength).
- Quick stats for context: percentage move, volatility, number of supporting factors.
- Links to the most relevant headlines pulled from curated RSS sources.
- Companion data files for anyone who wants to run deeper analysis.

## How It Runs (High-Level)
1. **Every morning** a GitHub Actions workflow triggers the pipeline.
2. **Market data ingestion** pulls five years of price history for USD/COP and key drivers, plus the latest day.
3. **LLM briefing generation** creates a human-readable summary using a structured prompt.
4. **Publishing** saves the results in `reports/briefings/` so they can be embedded or consumed via the GitHub raw URL.

## Sample Output
```
USD/COP closed 0.6% higher on lighter-than-normal volumes. The move tracked broad
U.S. dollar strength as the DXY index gained 0.4%, while regional currencies
like MXN and CLP also weakened. Softer Brent crude prices removed a traditional
support for COP, and local rates in Colombia inched up, suggesting some domestic
pressure. Today's news cycle focused on Colombia's fiscal outlook and the Fed's
messaging, reinforcing the cautious tone.
```

## Tech Highlights (Short List)
- Python orchestrated scripts for data ingestion, analysis, and prompt assembly.
- OpenAI GPT models to transform structured metrics into clean narrative copy.
- GitHub Actions for fully automated scheduling and delivery.
- Ready-made JSON and HTML assets that a website can display with one fetch call.

## Want To Run It Yourself?
All implementation details live in `DOCS_TECNICOS.md`. That guide covers:
- Local setup and environment variables (including OpenAI credentials).
- Adjusting tickers, data sources, and scheduling.
- Publishing the briefing on a static site or another channel.

## Maintainer
Juan Diego Mesa · Data & AI Engineer  
Always looking to build automated research experiences that feel editorial, not robotic.
