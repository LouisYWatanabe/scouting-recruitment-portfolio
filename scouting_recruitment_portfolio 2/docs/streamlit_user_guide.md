
# Streamlit MVP user guide

## Purpose

The app demonstrates a public-data recruitment decision-support workflow:

1. load player data
2. define a club scenario
3. select priority roles
4. apply age, minutes and value filters
5. change role-specific weights
6. inspect the need board, longlist, shortlist and QA cards
7. export CSV/Markdown outputs

## Recommended portfolio use

For a live demo, start with the bundled demo CSV. Then show the StatsBomb Open Data mode to demonstrate that the workflow can consume a real downloadable public dataset.

## Important limitation

StatsBomb Open Data is event data. It does not include age, wage, contract length, injury history or market value. In this MVP, the StatsBomb mode generates transparent demo proxies for age and market value so the interface can run end-to-end. Do not describe those proxy fields as real player information.

## Serious version

For a club-facing case study, use Upload CSV mode with a cleaned player-season dataset that includes:

- player, team, league, position
- age, minutes
- public market value proxy
- role-relevant per-90 metrics
- availability or injury-history flags, if legally and ethically available
- league strength proxy

## Suggested demo script

1. Open the app and explain that it is a decision-support tool, not an automated recruitment recommendation.
2. Select a club or squad.
3. Select 2–3 priority roles.
4. Show the Need Board and explain depth/performance/availability risk.
5. Move the role-weight sliders and show how the shortlist changes.
6. Open Player QA cards and explain what still needs scout/video/medical validation.
7. Export the shortlist CSV and player cards.
