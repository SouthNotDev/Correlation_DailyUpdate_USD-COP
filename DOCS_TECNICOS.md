# Technical Guide: Daily USD/COP Market Briefings

## Purpose
This document explains how to configure, run, and publish the automated USD/COP briefing pipeline. It complements the recruiter-friendly README by covering the technical steps required to operate the project.

## Repository Layout
```
.
├── config/                # Global settings and secrets templates
├── data/                  # Local caches created when you run the pipeline
├── reports/
│   ├── briefings/         # Daily briefing outputs (text, Markdown, HTML, JSON)
│   └── relations/         # Factor correlation analysis
├── src/                   # Source code for data, analysis, and LLM prompts
└── Scripts/               # Helper scripts and utilities
```

## 1. Requirements
- Python 3.11 or newer
- Pip and virtualenv (bundled with modern Python installs)
- Git
- OpenAI account with access to GPT-4 or later
- (Optional) GitHub repository with Actions enabled for automation

## 2. Local Setup
1. Clone the repository.
   ```bash
git clone https://github.com/<your-user>/<your-fork>.git
cd Correlation_DailyUpdate_USD-COP
```
2. Create and activate a virtual environment.
   ```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```
3. Install dependencies.
   ```bash
pip install -r requirements.txt
```
4. Create a `.env` file based on the template and add credentials.
   ```bash
copy .env.example .env  # use cp on macOS/Linux
```
   Required variables:
   - `OPENAI_API_KEY`
   - `NEWS_USER_AGENT` (optional but improves news scraping reliability)

## 3. Configure Project Settings
### 3.1 Market Data and Factors
Edit `config/settings.yaml` to adjust tickers, periods, and analysis window. Default coverage includes:
- USD/COP spot (`COP=X`)
- Commodities such as Brent (`BZ=F`)
- Regional FX peers (USD/MXN, USD/CLP)
- Global risk gauges (DXY, VIX)

You can add or remove entries by updating the `yfinance.tickers` list. Keep the YAML syntax (two spaces for indentation) intact.

### 3.2 News Sources
Maintain RSS sources in `info_sources.csv`. Each row contains a source name, URL, and category. Use UTF-8 encoded URLs and confirm that the sites allow automated fetching.

### 3.3 Prompt Customization
The template used to brief the LLM lives in `src/llm/prompt.md`. You can tailor tone, structure, or length without touching the Python code.

## 4. Running The Pipeline Locally
Activate your virtual environment and invoke one of the scripts below.

- Full daily run (data refresh, analysis, LLM briefing):
  ```bash
python src/scripts/daily_update.py --date today
```
- Skip the LLM step when you only need data and correlations:
  ```bash
python src/scripts/daily_update.py --date today --skip-llm
```
- Regenerate only the factor correlation tables:
  ```bash
python src/scripts/run_relations.py
```

Outputs are written to `reports/briefings/` and `reports/relations/`. The latest files follow the `*_YYYY-MM-DD.*` naming pattern.

## 5. Automating With GitHub Actions
1. Fork the project or push it to your own repository.
2. In GitHub, go to **Settings → Secrets and variables → Actions** and add:
   - `OPENAI_API_KEY`
   - `NEWS_USER_AGENT` (optional)
3. Review `.github/workflows/daily-briefing.yml`.
   - The pipeline runs daily at 07:00 UTC. Adjust the cron schedule if you need a different cadence.
   - You can trigger the workflow manually from the Actions tab ("Run workflow").
4. Outputs generated in the GitHub runner are committed back to the repo if the workflow permissions allow it. Alternatively, the workflow can publish to artifacts or cloud storage with minor modifications.

## 6. Publishing On A Website
You have several options to surface the daily briefing on a website or newsletter.

### 6.1 Embed The Plain-Text Briefing
Use the text file `reports/briefings/briefing_llm_YYYY-MM-DD.txt`. For a static site, fetch the raw file from GitHub:
```javascript
const today = new Date().toISOString().split("T")[0];
const url = `https://raw.githubusercontent.com/<your-user>/<your-repo>/main/reports/briefings/briefing_${today}.txt`;

fetch(url)
  .then(response => response.text())
  .then(text => {
    document.getElementById("daily-briefing").innerText = text;
  });
```

### 6.2 Work With Structured Data
If you prefer to render your own layout, use the JSON file:
```javascript
const today = new Date().toISOString().split("T")[0];
const url = `https://raw.githubusercontent.com/<your-user>/<your-repo>/main/reports/briefings/briefing_${today}.json`;

fetch(url)
  .then(response => response.json())
  .then(data => {
    renderBriefing(data.briefing, data.factors);
  });
```
Include basic error handling to fall back to the most recent available file when markets are closed.

### 6.3 Automate Content Updates
For CMS platforms (Webflow, Wordpress, Ghost):
- Use a webhook or scheduled integration (Zapier, Make, custom script) that pulls the JSON file daily and updates the CMS entry.
- Store the last published date to avoid duplicate posts.
- Optionally, attach the HTML version (`briefing_YYYY-MM-DD.html`) for rich formatting.

## 7. Maintenance Checklist
- Monitor GitHub Actions logs for failures, especially around API limits or missing credentials.
- Refresh API keys and RSS sources quarterly to avoid stale feeds.
- Keep dependencies up to date with `pip install -r requirements.txt --upgrade` after reviewing changelogs.
- Archive or prune old `data/raw` files if running locally to reclaim disk space (they are git-ignored).

## 8. Troubleshooting
- **OPENAI_API_KEY not found**: Confirm the key exists in `.env` locally or as a GitHub secret. Restart the terminal after editing `.env` to reload variables.
- **News scraping returns empty results**: Check network connectivity, verify RSS URLs, and adjust the user agent string.
- **Insufficient data for correlations**: Extend the `period_years` value or switch to a longer historical window.
- **Workflow cannot push changes**: Ensure the workflow has `write` permissions under `workflow_call` or use a personal access token stored as a secret.

Need help? Open an issue in the repository or reach out on LinkedIn.
