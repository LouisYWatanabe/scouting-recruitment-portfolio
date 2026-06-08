# Data schema for real player data

To replace the sample data, prepare a CSV with one row per player-season or player-current-season record.

## Required columns

| Column | Type | Example | Notes |
|---|---|---|---|
| `player` | string | Player Name | Unique display name |
| `team` | string | Celtic | Current club/team |
| `league` | string | Scottish Premiership | Current league |
| `position` | string | RB | Raw position; mapped to role family |
| `age` | number | 23 | Age at season/reference date |
| `minutes` | number | 1820 | League minutes preferred |
| `market_value_eur` | number | 4500000 | Public market proxy, not actual fee |
| `league_strength` | number 0-1 | 0.68 | Heuristic or external league-strength score |

## Recommended performance columns

All performance metrics should be per 90 unless stated otherwise.

| Column | Used for |
|---|---|
| `npxG_p90` | striker / winger goal threat |
| `shots_p90` | shooting volume |
| `goals_p90` | finishing output, descriptive only |
| `touches_box_p90` | box presence |
| `xA_p90` | chance creation |
| `progressive_passes_p90` | progression by passing |
| `progressive_carries_p90` | progression by carrying |
| `crosses_p90` | wide creation |
| `touches_att_3rd_p90` | advanced involvement |
| `pressures_p90` | pressing proxy |
| `tackles_p90` | defending |
| `interceptions_p90` | defending |
| `tackles_interceptions_p90` | combined defensive activity; auto-created if missing |
| `aerial_win_pct` | aerial strength |
| `clearances_p90` | box defending / defensive volume |
| `pass_completion_pct` | ball security |
| `miscontrols_p90` | lower is better |
| `errors_p90` | lower is better |
| `injury_days_last_2y` | descriptive availability flag only |

## Optional columns for future versions

| Column | Use |
|---|---|
| `contract_months_remaining` | contract-risk and value context |
| `wage_estimate_eur` | affordability, if legally/ethically sourced |
| `national_team_caps` | work permit / reputation context |
| `event_player_id` | join key to event data |
| `video_url` | video validation workflow |

## Data ethics note

Only use data that you are allowed to use. Avoid unauthorised scraping where site terms do not permit it. Keep the portfolio reproducible and transparent about data provenance.
