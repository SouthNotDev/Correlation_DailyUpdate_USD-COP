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

## Sample Output
```
USD/COP closed 0.6% higher on lighter-than-normal volumes. The move tracked broad
U.S. dollar strength as the DXY index gained 0.4%, while regional currencies
like MXN and CLP also weakened. Softer Brent crude prices removed a traditional
support for COP, and local rates in Colombia inched up, suggesting some domestic
pressure. Today's news cycle focused on Colombia's fiscal outlook and the Fed's
messaging, reinforcing the cautious tone.
```

## Tech Highlights
- Python scripts orchestrate data ingestion, analysis, and prompt assembly.
- OpenAI GPT models transform structured metrics into clean narrative copy.
- GitHub Actions handles automated scheduling and delivery.
- Produces clean Markdown that can be fetched directly from GitHub for web or newsletter publishing.

## Want To Run It Yourself?
Open `QUICK_START.md` for a concise setup checklist. It covers how to add your OpenAI key, run the pipeline locally or on schedule, and embed the daily briefing on a website or newsletter.

## Maintainer
Juan Diego Mesa - Data and AI Engineer
Always looking to build automated research experiences that feel editorial, not robotic.
