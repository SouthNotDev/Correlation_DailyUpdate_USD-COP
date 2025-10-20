# Quick Start

Follow these steps to generate the USD-COP daily briefing in minutes.

## 1. Create Your OpenAI API Key
1. Visit https://platform.openai.com/api-keys
2. Select **Create new secret key**
3. Name it something memorable (for example `usd-cop-briefing`)
4. Copy the key because it is shown only once

## 2. Store The Key In GitHub
1. Open your repository on GitHub.com
2. Navigate to **Settings > Secrets and variables > Actions**
3. Choose **New repository secret**
4. Set **Name** to `OPENAI_API_KEY` and paste the value you copied
5. Save the secret

## 3. Run The Pipeline
- **Automatic**: The workflow runs every day at 07:00 UTC. Fresh briefings appear in `reports/briefings/`
- **Manual**: Go to the **Actions** tab, select **Daily Briefing**, click **Run workflow**, and wait roughly three minutes
- The run automatically removes previous daily data and keeps only the freshly generated files

The primary file for your website or newsletter is `reports/briefings/briefing_YYYY-MM-DD.md`.

## 4. Connect Buttondown (Optional)
1. Log into [Buttondown](https://buttondown.com/) and open **Settings → API**.
2. Create a personal API token and copy it.
3. Back in GitHub, add a new repository secret named `BUTTONDOWN_API_KEY` with that token.
4. (Optional) Add `BUTTONDOWN_NEWSLETTER` if you use a non-default newsletter slug. This project defaults to `juandavidsanchezlatorre`.
5. Share the public subscribe link: `https://buttondown.com/juandavidsanchezlatorre`. New subscribers will receive the daily email automatically once the secrets are in place.

## Optional: Local Execution
```bash
python -m venv .venv
.venv\\Scripts\\activate  # use source .venv/bin/activate on macOS or Linux
pip install -r requirements.txt
set OPENAI_API_KEY=sk-your-key  # macOS/Linux: export OPENAI_API_KEY=sk-your-key
python src/scripts/daily_update.py --date today
```

## Optional: Website Embed
```javascript
const today = new Date().toISOString().split("T")[0];
const url = `https://raw.githubusercontent.com/<your-user>/<your-repo>/main/reports/briefings/briefing_${today}.md`;

fetch(url)
  .then(response => response.text())
  .then(markdown => {
    document.querySelector("#briefing").textContent = markdown;
  })
  .catch(() => console.log("Briefing not available yet."));
```

## Troubleshooting
- **Missing key**: Confirm `OPENAI_API_KEY` exists in GitHub secrets or your local `.env`
- **Empty news section**: Add a `NEWS_USER_AGENT` secret so news sources accept the scraper
- **Newsletter skipped**: Ensure `BUTTONDOWN_API_KEY` is defined and the GitHub Action log shows the Buttondown step running
- **No new files**: Check the Action logs for errors and confirm the schedule is set to your desired time
