# Role-Based Scouting Analytics Portfolio

A website-ready football analytics portfolio package for a **public-data recruitment decision-support demo**.

The project is designed to be shown on your personal website, while the interactive workflow runs as a Streamlit app. It demonstrates how a club scenario can be turned into squad-need hypotheses, role-based longlists, explainable shortlists and QA flags for further scout/video/medical/financial validation.

## Live-demo structure

```text
Personal website page  ->  embedded Streamlit app  ->  GitHub methodology/code
website/index.html        app.py                      docs/ + src/
```

## What this portfolio demonstrates

1. **Squad-need hypothesis** from public/player-level data.
2. **Role-based longlist** using age, minutes, market-value proxy and role filters.
3. **Configurable shortlist scoring** using editable role weights.
4. **Player QA cards** with reliability and public-data risk flags.
5. **Exportable outputs** for further analyst/scout discussion.
6. **Website-ready project page** for your personal site.

## What it deliberately does not claim

This is not a final recruitment recommendation system. It does not replace internal scouting, medical information, contract/wage data, agent context, tactical meetings or coach/technical director judgement.

## Repository contents

| Path | Purpose |
|---|---|
| `app.py` | Website-ready Streamlit app |
| `website/index.html` | Static project landing page for your own website |
| `website/config.js` | Set deployed Streamlit URL and GitHub URL |
| `website/styles.css` | Website styling |
| `website/assets/app-preview.svg` | Portfolio preview graphic |
| `src/scoring.py` | Core scoring pipeline |
| `src/statsbomb_loader.py` | Optional StatsBomb Open Data loader |
| `data/sample_players.csv` | Bundled offline demo data |
| `configs/celtic_style_scenario.yaml` | Editable scenario config |
| `docs/methodology.md` | Methodological explanation |
| `docs/data_schema.md` | Required schema for real data |
| `docs/website_deployment_guide.md` | Step-by-step website deployment guide |
| `docs/project_page_copy.md` | Copy text for personal website |
| `reports/website_readme_for_clubs.md` | Club-facing explanation |
| `.github/workflows/deploy_website.yml` | Optional GitHub Pages workflow for the static page |

## Run the Streamlit app locally

```bash
cd scouting_recruitment_portfolio
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Preview the website locally

In a second terminal:

```bash
cd scouting_recruitment_portfolio/website
python -m http.server 8000
```

Open:

```text
http://localhost:8000
```

The website will show an embedded-demo placeholder until you deploy the Streamlit app and update `website/config.js`.

## Deploy path

1. Push the repository to GitHub.
2. Deploy `app.py` to Streamlit Community Cloud or Hugging Face Spaces.
3. Copy the deployed demo URL.
4. Edit `website/config.js`:

```js
window.PORTFOLIO_DEMO_URL = "https://your-project.streamlit.app/?embed=true";
window.GITHUB_REPO_URL = "https://github.com/your-username/scouting-recruitment-portfolio";
```

5. Host the `website/` folder on your personal website, GitHub Pages, Netlify or Vercel.

## Data modes

The app supports three modes:

1. **Bundled website demo**: runs immediately with synthetic player-season data.
2. **Download StatsBomb Open Data**: downloads public event data and aggregates it to player-level features. Age and market value are demo proxies unless merged with real metadata.
3. **Upload my own CSV**: upload a player-level CSV following `docs/data_schema.md`.

## Recommended public wording

> This project is a public-data recruitment decision-support demo. It structures squad-need hypotheses, role-based longlists, shortlist scoring and QA flags, but it does not replace internal scouting, medical, contractual, financial or coaching judgement.

## Next improvements

- Replace synthetic sample data with a reproducible real public dataset.
- Add screenshots from the deployed app to the website page.
- Add sensitivity analysis and backtesting outputs.
- Add event-data role validation using StatsBomb Open Data / socceraction.
- Add a lightweight PDF methodology brief for direct club outreach.
