# Manifest

Website-ready package for the role-based scouting analytics portfolio.

## Core app

- `app.py` — Streamlit app redesigned for website/demo use
- `requirements.txt` — Python dependencies
- `.streamlit/config.toml` — Streamlit config

## Website layer

- `website/index.html` — static landing page
- `website/styles.css` — responsive styling
- `website/config.js` — Streamlit/GitHub URL config
- `website/script.js` — iframe and CTA logic
- `website/assets/app-preview.svg` — preview graphic

## Analytics pipeline

- `src/scoring.py` — squad need, longlist, shortlist and QA scoring
- `src/statsbomb_loader.py` — optional StatsBomb Open Data loader
- `configs/celtic_style_scenario.yaml` — scenario config
- `data/sample_players.csv` — bundled demo data

## Docs and reports

- `docs/methodology.md`
- `docs/data_schema.md`
- `docs/streamlit_user_guide.md`
- `docs/website_deployment_guide.md`
- `docs/project_page_copy.md`
- `reports/club_facing_one_pager.md`
- `reports/validation_checklist.md`
- `reports/website_readme_for_clubs.md`

## Optional deployment

- `.github/workflows/deploy_website.yml` — deploys `website/` to GitHub Pages
