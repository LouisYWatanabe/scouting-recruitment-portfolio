from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
import streamlit as st
import yaml

from src.scoring import (
    prepare_players,
    add_role_performance,
    add_reliability,
    add_value_model,
    squad_need_board,
    build_longlist,
    rank_shortlist,
    qa_flags,
)

try:
    from src.statsbomb_loader import load_competitions, load_matches, aggregate_competition
except Exception:  # pragma: no cover - optional live data mode
    load_competitions = None
    load_matches = None
    aggregate_competition = None

ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = ROOT / "configs" / "celtic_style_scenario.yaml"
DEFAULT_SAMPLE_PATH = ROOT / "data" / "sample_players.csv"

st.set_page_config(
    page_title="Scouting Analytics Portfolio",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

WEBSITE_CSS = """
<style>
:root {
  --bg-card: rgba(255,255,255,0.04);
  --border-card: rgba(255,255,255,0.12);
}
.block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1280px;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(125,125,125,.15);}
.hero {
  border: 1px solid var(--border-card);
  background: linear-gradient(135deg, rgba(39,99,255,.16), rgba(28,166,112,.10));
  border-radius: 24px;
  padding: 2rem 2.2rem;
  margin-bottom: 1.2rem;
}
.hero h1 {font-size: 2.6rem; line-height: 1.05; margin-bottom: .6rem;}
.hero p {font-size: 1.05rem; color: rgba(240,240,240,.84); max-width: 920px;}
.pill {display:inline-block; border:1px solid rgba(255,255,255,.22); border-radius:999px; padding:.25rem .7rem; margin:.15rem; font-size:.82rem; color:rgba(255,255,255,.82)}
.card {border: 1px solid var(--border-card); border-radius: 18px; padding: 1rem 1.1rem; background: var(--bg-card); height: 100%;}
.card h3 {margin-top: 0; font-size: 1.1rem;}
.small-muted {font-size:.85rem; color:rgba(190,190,190,.86)}
.metric-note {font-size:.8rem; color:rgba(170,170,170,.8)}
.flag-green {color:#45d483; font-weight:700}
.flag-amber {color:#f7b955; font-weight:700}
.flag-red {color:#ff6b6b; font-weight:700}
hr {margin: 1.5rem 0;}
</style>
"""
st.markdown(WEBSITE_CSS, unsafe_allow_html=True)


# ---------- Utilities ----------

def load_default_config() -> dict:
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def csv_download(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def normalise_weights(w: dict) -> dict:
    pos_keys = ["role_performance", "squad_complementarity", "value_intelligence", "reliability"]
    s = sum(max(float(w.get(k, 0)), 0) for k in pos_keys)
    if s <= 0:
        for k in pos_keys:
            w[k] = 0.25
    else:
        for k in pos_keys:
            w[k] = max(float(w.get(k, 0)), 0) / s
    w["league_risk"] = -abs(float(w.get("league_risk", -0.05)))
    return w


@st.cache_data(show_spinner=False)
def load_sample_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=True)
def cached_competitions() -> pd.DataFrame:
    if load_competitions is None:
        raise ImportError("StatsBomb loader is unavailable. Install requirements.txt first.")
    return load_competitions()


@st.cache_data(show_spinner=True)
def cached_statsbomb_agg(competition_id: int, season_id: int, max_matches: int) -> pd.DataFrame:
    if aggregate_competition is None:
        raise ImportError("StatsBomb loader is unavailable. Install requirements.txt first.")
    return aggregate_competition(competition_id, season_id, max_matches=max_matches)


def build_config_from_ui(
    base: dict,
    roles: list[str],
    club_name: str,
    budget: float,
    age_min: int,
    age_max: int,
    min_minutes: int,
    exclude_current: bool,
    role_weight_ui: dict,
    final_shortlist_n: int,
) -> dict:
    cfg = json.loads(json.dumps(base))
    cfg["club"]["name"] = club_name
    cfg["club"]["budget_eur_max"] = float(budget)
    cfg["club"]["age_min"] = int(age_min)
    cfg["club"]["age_max"] = int(age_max)
    cfg["club"]["min_minutes"] = int(min_minutes)
    cfg["club"]["exclude_current_club"] = bool(exclude_current)
    cfg["priority_roles"] = {}
    default_labels = {
        "CB": "Centre-back / wide centre-back",
        "RWB": "Right full-back / wing-back",
        "LWB": "Left full-back / wing-back",
        "ST": "Forward / striker",
        "W": "Winger / wide forward",
        "CM": "Central midfielder",
        "DM": "Defensive midfielder",
        "AM": "Attacking midfielder",
    }
    for role in roles:
        cfg["priority_roles"][role] = {
            "label": default_labels.get(role, role),
            "need_description": "User-selected role in the public-data portfolio demo.",
            "weights": normalise_weights(role_weight_ui.get(role, {})),
        }
    cfg.setdefault("outputs", {})["final_shortlist_n"] = int(final_shortlist_n)
    return cfg


def run_pipeline_in_memory(df: pd.DataFrame, cfg: dict) -> dict:
    df = prepare_players(df)
    df = add_role_performance(df)
    df = add_reliability(df)
    df, model_info = add_value_model(df)
    roles = list(cfg.get("priority_roles", {}).keys())
    need = squad_need_board(df, cfg["club"]["name"], roles)
    longlist = build_longlist(df, cfg)
    ranked = rank_shortlist(longlist, df, cfg)
    shortlist = ranked.head(int(cfg.get("outputs", {}).get("final_shortlist_n", 12))).copy()
    if not shortlist.empty:
        shortlist["qa_flags"] = shortlist.apply(qa_flags, axis=1)
    return {
        "prepared": df,
        "need_board": need,
        "longlist": longlist,
        "ranked": ranked,
        "shortlist": shortlist,
        "model_info": model_info,
    }


def format_money(x: float | int | None) -> str:
    if pd.isna(x):
        return "—"
    x = float(x)
    if x >= 1_000_000:
        return f"€{x/1_000_000:.1f}m"
    if x >= 1_000:
        return f"€{x/1_000:.0f}k"
    return f"€{x:.0f}"


def flag_class(flags: str) -> str:
    if not flags or str(flags).strip() in {"", "[]"}:
        return "flag-green"
    flags_lower = str(flags).lower()
    if "low minutes" in flags_lower or "budget" in flags_lower or "injury" in flags_lower:
        return "flag-amber"
    return "flag-green"


def render_player_card(row: pd.Series, rank: int) -> None:
    flags = row.get("qa_flags", "")
    flag_label = "Green: no major public-data flag" if not str(flags).strip() else str(flags)
    st.markdown(
        f"""
        <div class="card">
          <div class="small-muted">Rank {rank} • {row.get('role_family', '—')} • {row.get('league', '—')}</div>
          <h3>{row.get('player', 'Unknown player')}</h3>
          <p><b>{row.get('team', '—')}</b> · Age {row.get('age', '—')} · {int(row.get('minutes', 0)):,} mins · {format_money(row.get('market_value_eur', np.nan))}</p>
          <p>Final score: <b>{row.get('final_score', np.nan):.3f}</b> · Role performance: {row.get('role_performance_reliable', np.nan):.3f} · Value IQ: {row.get('value_intelligence', np.nan):.3f}</p>
          <p class="{flag_class(flags)}">{flag_label}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- Header ----------
st.markdown(
    """
    <section class="hero">
      <span class="pill">Football analytics portfolio</span>
      <span class="pill">Public-data demo</span>
      <span class="pill">Website-ready</span>
      <h1>Role-Based Recruitment Decision Support</h1>
      <p>A compact, interactive scouting analytics portfolio: define a club scenario, generate a squad-need hypothesis, filter a role-based longlist, rank candidates with transparent assumptions, and export QA-ready player outputs.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.expander("Important scope note", expanded=False):
    st.markdown(
        """
        This is a **public-data decision-support demonstration**. It is designed for a portfolio website and interviews.

        It does **not** replace internal scouting, medical checks, contract/wage information, agent context, tactical briefings, or live recruitment meetings. StatsBomb Open Data mode uses real public event data, but age and market value are demo proxies unless you upload or merge real metadata.
        """
    )

base_cfg = load_default_config()

# ---------- Sidebar ----------
st.sidebar.title("Demo controls")
st.sidebar.caption("Default settings are optimised for website visitors: the bundled demo works immediately, while public-data mode can be used for a live data demo.")

st.sidebar.header("1. Data source")
source = st.sidebar.radio(
    "Choose data mode",
    ["Bundled website demo", "Download StatsBomb Open Data", "Upload my own CSV"],
    help="The bundled demo runs instantly. StatsBomb mode downloads public event data and aggregates it to player-level features.",
)

raw_df: pd.DataFrame | None = None
source_note = ""
if source == "Bundled website demo":
    raw_df = load_sample_data(str(DEFAULT_SAMPLE_PATH))
    source_note = "Bundled demo CSV. This is synthetic player-season data created to demonstrate the workflow without requiring private club data."
elif source == "Upload my own CSV":
    uploaded = st.sidebar.file_uploader("Upload player-level CSV", type=["csv"])
    if uploaded is None:
        st.info("Upload a CSV to continue, or switch to the bundled demo.")
        st.stop()
    raw_df = pd.read_csv(uploaded)
    source_note = "User-uploaded player-level CSV."
else:
    if load_competitions is None:
        st.error("StatsBomb loader dependencies are unavailable. Please install requirements.txt.")
        st.stop()
    try:
        comps = cached_competitions()
        comp_labels = comps.apply(
            lambda r: f"{r.get('competition_name')} — {r.get('season_name')} ({r.get('competition_gender', '')}) | comp={r.get('competition_id')}, season={r.get('season_id')}",
            axis=1,
        )
        selected_idx = st.sidebar.selectbox("Competition / season", range(len(comps)), format_func=lambda i: comp_labels.iloc[i], index=0)
        selected = comps.iloc[selected_idx]
        max_matches = st.sidebar.slider("Max matches to download", 1, 30, 8, help="Keep this small for a fast website demo.")
        if st.sidebar.button("Download and aggregate", type="primary"):
            raw_df = cached_statsbomb_agg(int(selected["competition_id"]), int(selected["season_id"]), int(max_matches))
            st.session_state["statsbomb_df"] = raw_df
            st.session_state["statsbomb_label"] = comp_labels.iloc[selected_idx]
        elif "statsbomb_df" in st.session_state:
            raw_df = st.session_state["statsbomb_df"]
        else:
            st.info("Choose a competition and click 'Download and aggregate'.")
            st.stop()
        source_note = f"StatsBomb Open Data aggregation: {st.session_state.get('statsbomb_label', '')}. Age/market value are demo proxies unless merged with real metadata."
    except Exception as e:  # pragma: no cover
        st.error(f"Could not download StatsBomb Open Data: {e}")
        st.stop()

if raw_df is None or raw_df.empty:
    st.error("No data loaded.")
    st.stop()

try:
    preview_df = prepare_players(raw_df.copy())
except Exception as e:
    st.error(f"Could not prepare data. Check docs/data_schema.md. Error: {e}")
    st.stop()

available_clubs = sorted(preview_df["team"].dropna().unique().tolist())
if base_cfg["club"].get("name") in available_clubs:
    default_club_index = available_clubs.index(base_cfg["club"].get("name"))
else:
    default_club_index = 0

st.sidebar.header("2. Club scenario")
club_name = st.sidebar.selectbox("Current squad / club to diagnose", available_clubs, index=default_club_index)
available_roles = sorted([r for r in preview_df["role_family"].dropna().unique() if r != "GK"])
default_roles = [r for r in ["CB", "RWB", "ST"] if r in available_roles] or available_roles[:3]
roles = st.sidebar.multiselect("Priority roles", available_roles, default=default_roles)

st.sidebar.header("3. Filters")
value_series = pd.to_numeric(preview_df.get("market_value_eur", pd.Series([8_000_000])), errors="coerce")
max_value_default = float(np.nanpercentile(value_series.dropna(), 85)) if len(value_series.dropna()) else 8_000_000
budget = st.sidebar.number_input("Budget ceiling / market proxy (€)", min_value=0, value=int(max(1_000_000, max_value_default)), step=500_000)
age_min, age_max = st.sidebar.slider("Age band", 16, 40, (18, 27))
max_minutes = int(preview_df["minutes"].max()) if "minutes" in preview_df.columns else 3000
min_minutes = st.sidebar.slider("Minimum minutes", 0, max(3000, max_minutes), min(900, max_minutes), step=100)
exclude_current = st.sidebar.checkbox("Exclude current club from candidates", value=True)
final_shortlist_n = st.sidebar.slider("Final shortlist size", 3, 30, 12)

st.sidebar.header("4. Scoring weights")
role_weight_ui: dict[str, dict] = {}
for role in roles:
    with st.sidebar.expander(f"{role} weights", expanded=False):
        role_weight_ui[role] = {
            "role_performance": st.slider(f"{role} role performance", 0.0, 1.0, 0.40, 0.05, key=f"{role}_perf"),
            "squad_complementarity": st.slider(f"{role} squad complementarity", 0.0, 1.0, 0.15, 0.05, key=f"{role}_squad"),
            "value_intelligence": st.slider(f"{role} value intelligence", 0.0, 1.0, 0.25, 0.05, key=f"{role}_value"),
            "reliability": st.slider(f"{role} reliability", 0.0, 1.0, 0.15, 0.05, key=f"{role}_rel"),
            "league_risk": st.slider(f"{role} league risk penalty", 0.0, 0.20, 0.05, 0.01, key=f"{role}_league"),
        }

if not roles:
    st.warning("Select at least one priority role.")
    st.stop()

cfg = build_config_from_ui(
    base_cfg,
    roles,
    club_name,
    budget,
    age_min,
    age_max,
    min_minutes,
    exclude_current,
    role_weight_ui,
    final_shortlist_n,
)

results = run_pipeline_in_memory(raw_df, cfg)
need = results["need_board"]
longlist = results["longlist"]
ranked = results["ranked"]
shortlist = results["shortlist"]
prepared = results["prepared"]
model_info = results["model_info"]

# ---------- KPI strip ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Players loaded", f"{len(prepared):,}")
k2.metric("Longlist", f"{len(longlist):,}")
k3.metric("Shortlist", f"{len(shortlist):,}")
k4.metric("Priority roles", f"{len(roles)}")
st.caption(source_note)

# ---------- Tabs ----------
tab_overview, tab_workflow, tab_players, tab_method, tab_export = st.tabs([
    "Overview",
    "Workflow demo",
    "Player cards",
    "Methodology",
    "Export",
])

with tab_overview:
    st.subheader("What this portfolio demonstrates")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="card"><h3>1. Squad need</h3><p>Creates public-data hypotheses for priority roles using depth, minutes and role benchmarks.</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><h3>2. Longlist</h3><p>Filters the market by role, age, minutes, value proxy and current-club exclusion.</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><h3>3. Shortlist</h3><p>Ranks candidates with transparent, adjustable role and club assumptions.</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="card"><h3>4. QA flags</h3><p>Highlights data limitations before scout, video, medical and financial validation.</p></div>', unsafe_allow_html=True)

    st.subheader("Current scenario")
    scen = pd.DataFrame([
        {"Item": "Current squad", "Value": club_name},
        {"Item": "Priority roles", "Value": ", ".join(roles)},
        {"Item": "Age band", "Value": f"{age_min}-{age_max}"},
        {"Item": "Minimum minutes", "Value": f"{min_minutes:,}"},
        {"Item": "Budget proxy", "Value": format_money(budget)},
        {"Item": "Data mode", "Value": source},
    ])
    st.dataframe(scen, hide_index=True, use_container_width=True)

with tab_workflow:
    st.subheader("Squad need hypothesis")
    if need.empty:
        st.warning("Need board is empty for this scenario.")
    else:
        need_cols = [c for c in ["role_family", "gap_score", "depth_score", "performance_gap", "availability_gap", "age_risk"] if c in need.columns]
        st.dataframe(need[need_cols].sort_values("gap_score", ascending=False), hide_index=True, use_container_width=True)
        if "gap_score" in need.columns:
            st.bar_chart(need.set_index("role_family")["gap_score"])

    st.subheader("Longlist")
    if longlist.empty:
        st.warning("No players passed the filters. Relax the age, minutes or budget settings.")
    else:
        cols = ["player", "team", "league", "role_family", "age", "minutes", "market_value_eur", "role_performance_reliable", "reliability"]
        st.dataframe(longlist[[c for c in cols if c in longlist.columns]].head(100), hide_index=True, use_container_width=True)

    st.subheader("Ranked shortlist")
    if ranked.empty:
        st.warning("No ranked candidates for this configuration.")
    else:
        cols = ["player", "team", "league", "role_family", "age", "minutes", "market_value_eur", "final_score", "role_performance_reliable", "value_intelligence", "reliability"]
        st.dataframe(ranked[[c for c in cols if c in ranked.columns]].head(50), hide_index=True, use_container_width=True)

with tab_players:
    st.subheader("Player QA cards")
    if shortlist.empty:
        st.warning("No shortlist available.")
    else:
        for start in range(0, min(len(shortlist), 12), 3):
            cols = st.columns(3)
            for idx, (_, row) in enumerate(shortlist.iloc[start:start+3].iterrows()):
                with cols[idx]:
                    render_player_card(row, start + idx + 1)

with tab_method:
    st.subheader("Methodology summary")
    st.markdown(
        """
        This app is deliberately framed as a **decision-support workflow**, not an automated recommendation engine.

        The current MVP uses broad role families, role-based peer comparison, minutes-based reliability adjustment, value intelligence, configurable weighting and QA flags. Fine-grained tactical labels such as inverted full-back versus overlapping full-back should only be claimed when event or tracking data supports the spatial distinction.
        """
    )
    method_table = pd.DataFrame([
        {"Layer": "Role performance", "MVP method": "Role-family metrics standardised against role peers", "What to validate next": "Event-data role validation"},
        {"Layer": "Reliability", "MVP method": "Minutes and availability shrinkage", "What to validate next": "Multi-season stability"},
        {"Layer": "Value", "MVP method": "Market value residual or fallback VFM", "What to validate next": "Real fee, wage and contract data"},
        {"Layer": "Video", "MVP method": "QA checklist", "What to validate next": "Data-directed clips and tracking prototype"},
    ])
    st.dataframe(method_table, hide_index=True, use_container_width=True)

    st.info("For a club-facing version, merge reliable market, contract, injury and scouting/video data before making any player-specific claim.")

with tab_export:
    st.subheader("Export for portfolio, GitHub or club-facing follow-up")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Download need board CSV", csv_download(need), "need_board.csv", "text/csv", disabled=need.empty)
    with c2:
        st.download_button("Download ranked candidates CSV", csv_download(ranked), "ranked_candidates.csv", "text/csv", disabled=ranked.empty)
    with c3:
        st.download_button("Download shortlist CSV", csv_download(shortlist), "shortlist.csv", "text/csv", disabled=shortlist.empty)

    brief = f"""# Recruitment Decision Support Demo Brief

## Scenario
Current squad: {club_name}
Priority roles: {', '.join(roles)}
Age band: {age_min}-{age_max}
Minimum minutes: {min_minutes:,}
Budget proxy: {format_money(budget)}

## Output
Loaded players: {len(prepared):,}
Longlist size: {len(longlist):,}
Shortlist size: {len(shortlist):,}

## Scope note
This is a public-data decision-support demonstration. It creates recruitment hypotheses and QA flags; it does not replace scouting, medical, tactical, contractual or financial judgement.
"""
    st.download_button("Download markdown brief", brief.encode("utf-8"), "portfolio_demo_brief.md", "text/markdown")

st.caption("Built as a website-ready football analytics portfolio demo. Public data, transparent assumptions, human-in-the-loop validation.")
