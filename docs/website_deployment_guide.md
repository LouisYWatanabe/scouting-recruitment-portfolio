# Website-ready deployment guide

This repository is structured as a two-layer portfolio:

1. **Streamlit app**: the interactive recruitment decision-support demo.
2. **Static website page**: a polished project page for your personal website, with an embedded app frame.

## Recommended setup

```text
scouting_recruitment_portfolio/
├── app.py                    # Streamlit demo
├── requirements.txt          # Python dependencies
├── data/sample_players.csv   # bundled offline demo data
├── src/                      # scoring and data loading logic
├── docs/                     # methodology and deployment notes
└── website/                  # static website landing page
    ├── index.html
    ├── styles.css
    ├── config.js
    ├── script.js
    └── assets/app-preview.svg
```

## Local preview

### 1. Run the Streamlit app

```bash
cd scouting_recruitment_portfolio
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### 2. Preview the static website

In another terminal:

```bash
cd scouting_recruitment_portfolio/website
python -m http.server 8000
```

Open:

```text
http://localhost:8000
```

The website will show a placeholder until you deploy the Streamlit app and update `website/config.js`.

## Deploying the Streamlit app

### Option A: Streamlit Community Cloud

1. Push this folder to a public or private GitHub repository.
2. Go to Streamlit Community Cloud.
3. Create a new app from the repository.
4. Set the main file path to:

```text
app.py
```

5. Deploy the app.
6. Copy the deployed URL, for example:

```text
https://your-project.streamlit.app
```

7. In `website/config.js`, set:

```js
window.PORTFOLIO_DEMO_URL = "https://your-project.streamlit.app/?embed=true";
```

### Option B: Hugging Face Spaces

1. Create a new Space.
2. Select Streamlit as the SDK.
3. Upload/push this repository.
4. Make sure `app.py` is at the Space root and `requirements.txt` is present.
5. Copy the Space URL and paste it into `website/config.js`.

## Deploying the website

You can host the `website/` folder on:

- your own website
- GitHub Pages
- Netlify
- Vercel
- university/project hosting

For a personal portfolio, the simplest structure is:

```text
/projects/scouting-analytics/
```

Upload the contents of `website/` to that page path.

## Suggested public wording

Use this wording to avoid overclaiming:

> This project is a public-data recruitment decision-support demo. It structures squad-need hypotheses, role-based longlists, shortlist scoring and QA flags, but it does not replace internal scouting, medical, contractual, financial or coaching judgement.

## What to change before sharing with clubs

- Replace demo screenshots with real screenshots after you deploy the app.
- Update `website/config.js` with the real Streamlit or Hugging Face URL.
- Update the GitHub URL.
- Add your own name, contact link and CV link if needed.
- Use real player-level data only where you can explain source, licence and limitations.
- Keep the public-data limitation statement visible.
