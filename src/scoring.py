from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score


ROLE_MAP = {
    "CB": "CB", "LCB": "CB", "RCB": "CB",
    "RB": "RWB", "RFB": "RWB", "RWB": "RWB",
    "LB": "LWB", "LFB": "LWB", "LWB": "LWB",
    "ST": "ST", "CF": "ST",
    "LW": "W", "RW": "W", "LM": "W", "RM": "W",
    "CM": "CM", "CMF": "CM", "DM": "DM", "DMF": "DM", "AM": "AM", "AMF": "AM",
}

ROLE_METRICS: Dict[str, Dict[str, float]] = {
    "RWB": {
        "progressive_carries_p90": 0.20,
        "progressive_passes_p90": 0.15,
        "crosses_p90": 0.15,
        "xA_p90": 0.15,
        "touches_att_3rd_p90": 0.10,
        "tackles_interceptions_p90": 0.15,
        "miscontrols_p90": -0.10,
    },
    "LWB": {
        "progressive_carries_p90": 0.20,
        "progressive_passes_p90": 0.15,
        "crosses_p90": 0.15,
        "xA_p90": 0.15,
        "touches_att_3rd_p90": 0.10,
        "tackles_interceptions_p90": 0.15,
        "miscontrols_p90": -0.10,
    },
    "CB": {
        "aerial_win_pct": 0.20,
        "tackles_interceptions_p90": 0.15,
        "clearances_p90": 0.10,
        "progressive_passes_p90": 0.20,
        "progressive_carries_p90": 0.10,
        "pass_completion_pct": 0.15,
        "errors_p90": -0.10,
    },
    "ST": {
        "npxG_p90": 0.25,
        "shots_p90": 0.15,
        "touches_box_p90": 0.15,
        "goals_p90": 0.15,
        "pressures_p90": 0.15,
        "xA_p90": 0.05,
        "miscontrols_p90": -0.10,
    },
    "W": {
        "npxG_p90": 0.15,
        "xA_p90": 0.15,
        "progressive_carries_p90": 0.20,
        "progressive_passes_p90": 0.10,
        "touches_box_p90": 0.10,
        "crosses_p90": 0.10,
        "pressures_p90": 0.10,
        "miscontrols_p90": -0.10,
    },
    "CM": {
        "progressive_passes_p90": 0.20,
        "progressive_carries_p90": 0.15,
        "pass_completion_pct": 0.15,
        "tackles_interceptions_p90": 0.15,
        "xA_p90": 0.10,
        "pressures_p90": 0.15,
        "miscontrols_p90": -0.10,
    },
    "DM": {
        "tackles_interceptions_p90": 0.25,
        "progressive_passes_p90": 0.20,
        "pass_completion_pct": 0.15,
        "pressures_p90": 0.15,
        "errors_p90": -0.10,
        "aerial_win_pct": 0.15,
    },
    "AM": {
        "xA_p90": 0.25,
        "progressive_passes_p90": 0.15,
        "progressive_carries_p90": 0.15,
        "touches_att_3rd_p90": 0.15,
        "npxG_p90": 0.15,
        "pressures_p90": 0.05,
        "miscontrols_p90": -0.10,
    },
}

DEFAULT_ROLE_WEIGHTS = {
    "role_performance": 0.40,
    "squad_complementarity": 0.15,
    "value_intelligence": 0.25,
    "reliability": 0.15,
    "league_risk": -0.05,
}


def load_config(path: str | Path) -> dict:
    if yaml is None:
        raise ImportError("pyyaml is required to load YAML config files")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def minmax(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def robust_z_within_group(df: pd.DataFrame, group_col: str, cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            continue
        zcol = f"z_{col}"
        def _z(x: pd.Series) -> pd.Series:
            med = x.median()
            mad = (x - med).abs().median()
            if pd.isna(mad) or mad == 0:
                std = x.std(ddof=0)
                if pd.isna(std) or std == 0:
                    return pd.Series(0.0, index=x.index)
                return (x - x.mean()) / std
            return 0.6745 * (x - med) / mad
        out[zcol] = out.groupby(group_col, group_keys=False)[col].apply(_z).clip(-3, 3)
    return out


def prepare_players(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["role_family"] = out["position"].map(ROLE_MAP).fillna(out["position"])
    if "tackles_interceptions_p90" not in out.columns:
        out["tackles_interceptions_p90"] = out.get("tackles_p90", 0) + out.get("interceptions_p90", 0)
    if "availability_ratio" not in out.columns:
        out["availability_ratio"] = 1 - minmax(out.get("injury_days_last_2y", pd.Series(0, index=out.index))) * 0.5
    if "league_strength" not in out.columns:
        out["league_strength"] = 0.5
    return out


def add_role_performance(df: pd.DataFrame) -> pd.DataFrame:
    all_metrics = sorted({m for metric_weights in ROLE_METRICS.values() for m in metric_weights})
    out = robust_z_within_group(df, "role_family", all_metrics)
    out["role_performance_raw"] = 0.0
    out["role_metric_coverage"] = 0.0
    for role, weights in ROLE_METRICS.items():
        idx = out["role_family"].eq(role)
        if idx.sum() == 0:
            continue
        total_abs = sum(abs(w) for m, w in weights.items() if f"z_{m}" in out.columns)
        score = pd.Series(0.0, index=out.index)
        coverage = pd.Series(0.0, index=out.index)
        for m, w in weights.items():
            z = f"z_{m}"
            if z in out.columns:
                score.loc[idx] += out.loc[idx, z].fillna(0) * w
                coverage.loc[idx] += abs(w) * out.loc[idx, m].notna().astype(float)
        if total_abs > 0:
            out.loc[idx, "role_performance_raw"] = score.loc[idx] / total_abs
            out.loc[idx, "role_metric_coverage"] = coverage.loc[idx] / total_abs
    out["role_performance"] = minmax(out["role_performance_raw"])
    return out


def add_reliability(df: pd.DataFrame, minutes_anchor: int = 1800) -> pd.DataFrame:
    out = df.copy()
    minutes = pd.to_numeric(out["minutes"], errors="coerce").fillna(0)
    minutes_weight = np.sqrt(np.minimum(minutes / minutes_anchor, 1.0))
    availability = pd.to_numeric(out.get("availability_ratio", 1.0), errors="coerce").fillna(1.0).clip(0, 1)
    out["minutes_reliability"] = minutes_weight
    out["reliability"] = (0.7 * minutes_weight + 0.3 * availability).clip(0, 1)
    # shrink role score towards 0.5 when sample size is weak
    out["role_performance_reliable"] = 0.5 + (out["role_performance"] - 0.5) * out["minutes_reliability"]
    return out


def add_value_model(df: pd.DataFrame, min_rows: int = 80) -> Tuple[pd.DataFrame, dict]:
    out = df.copy()
    metrics = [c for c in df.columns if c.endswith("_p90") or c.endswith("_pct")]
    numeric = ["age", "minutes", "league_strength", "role_performance_reliable", "reliability"] + metrics
    numeric = [c for c in numeric if c in out.columns]
    categorical = [c for c in ["role_family", "league"] if c in out.columns]
    valid = out["market_value_eur"].notna() & (out["market_value_eur"] > 0)
    model_info = {"used_model": False, "r2": None, "mae_log": None, "note": "Fallback VFM used."}

    if valid.sum() >= min_rows:
        X = out.loc[valid, numeric + categorical]
        y = np.log1p(out.loc[valid, "market_value_eur"])
        pre = ColumnTransformer([
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
        ])
        model = GradientBoostingRegressor(random_state=42, n_estimators=180, learning_rate=0.045, max_depth=3)
        pipe = Pipeline([("pre", pre), ("model", model)])
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        pred = cross_val_predict(pipe, X, y, cv=cv)
        out.loc[valid, "market_value_pred_log_oof"] = pred
        out.loc[valid, "market_value_pred_eur_oof"] = np.expm1(pred)
        out.loc[valid, "value_residual_log"] = pred - y
        model_info = {
            "used_model": True,
            "r2": float(r2_score(y, pred)),
            "mae_log": float(mean_absolute_error(y, pred)),
            "note": "OOF GradientBoostingRegressor predicts log market value; residual>0 means public-value proxy appears lower than modelled value.",
        }
    else:
        out["market_value_pred_log_oof"] = np.nan
        out["market_value_pred_eur_oof"] = np.nan
        out["value_residual_log"] = np.nan

    # Robust fallback/value score: high role performance at lower market cost.
    out["cost_pressure"] = minmax(np.log1p(out["market_value_eur"].fillna(out["market_value_eur"].median())))
    residual_score = minmax(out["value_residual_log"])
    fallback_score = minmax(out["role_performance_reliable"] - out["cost_pressure"])
    out["value_intelligence"] = residual_score.where(out["value_residual_log"].notna(), fallback_score)
    return out, model_info


def squad_need_board(df: pd.DataFrame, club_name: str, priority_roles: Optional[List[str]] = None) -> pd.DataFrame:
    out = df.copy()
    club = out[out["team"].eq(club_name)].copy()
    if club.empty:
        raise ValueError(f"No players found for club: {club_name}")
    if priority_roles is None:
        priority_roles = sorted(club["role_family"].dropna().unique())
    rows = []
    for role in priority_roles:
        c = club[club["role_family"].eq(role)]
        peers = out[out["role_family"].eq(role)]
        depth = len(c)
        reliable_depth = int((c["minutes"] >= 900).sum()) if not c.empty else 0
        minutes_total = c["minutes"].sum()
        dependency = 1.0 if minutes_total <= 0 else float(((c["minutes"] / minutes_total) ** 2).sum())
        avg_age = c["age"].mean() if not c.empty else np.nan
        age_risk = 0.0 if pd.isna(avg_age) else float(np.clip((avg_age - 27) / 5, 0, 1))
        perf_gap = 0.5
        if not c.empty and not peers.empty:
            club_perf = c["role_performance_reliable"].mean()
            peer_median = peers["role_performance_reliable"].median()
            perf_gap = float(np.clip(0.5 + (peer_median - club_perf), 0, 1))
        availability_risk = float(1 - c["availability_ratio"].mean()) if not c.empty else 0.5
        depth_risk = float(np.clip((2 - reliable_depth) / 2, 0, 1))
        gap_score = 0.30 * depth_risk + 0.20 * dependency + 0.20 * perf_gap + 0.15 * age_risk + 0.15 * availability_risk
        rows.append({
            "role_family": role,
            "depth": depth,
            "reliable_depth_900m": reliable_depth,
            "minutes_dependency_hhi": round(dependency, 3),
            "average_age": round(avg_age, 1) if not pd.isna(avg_age) else np.nan,
            "depth_risk": round(depth_risk, 3),
            "performance_gap": round(perf_gap, 3),
            "age_risk": round(age_risk, 3),
            "availability_risk": round(availability_risk, 3),
            "gap_score": round(gap_score, 3),
            "need_label": "High" if gap_score >= 0.62 else "Medium" if gap_score >= 0.42 else "Low",
        })
    return pd.DataFrame(rows).sort_values("gap_score", ascending=False)


def build_longlist(df: pd.DataFrame, config: Mapping) -> pd.DataFrame:
    club = config["club"]
    roles = list(config.get("priority_roles", {}).keys())
    out = df.copy()
    mask = out["role_family"].isin(roles)
    mask &= out["age"].between(club.get("age_min", 18), club.get("age_max", 30), inclusive="both")
    mask &= out["minutes"] >= club.get("min_minutes", 900)
    mask &= out["market_value_eur"] <= club.get("budget_eur_max", np.inf)
    if club.get("exclude_current_club", True):
        mask &= ~out["team"].eq(club["name"])
    return out[mask].copy()


def add_squad_complementarity(df: pd.DataFrame, club_df: pd.DataFrame, roles: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    out["squad_complementarity"] = 0.5
    for role in roles:
        idx = out["role_family"].eq(role)
        club_role = club_df[club_df["role_family"].eq(role)]
        if club_role.empty:
            out.loc[idx, "squad_complementarity"] = out.loc[idx, "role_performance_reliable"]
        else:
            benchmark = club_role["role_performance_reliable"].max()
            out.loc[idx, "squad_complementarity"] = minmax(out.loc[idx, "role_performance_reliable"] - benchmark)
    return out


def rank_shortlist(df: pd.DataFrame, full_df: pd.DataFrame, config: Mapping) -> pd.DataFrame:
    club_name = config["club"]["name"]
    roles = list(config.get("priority_roles", {}).keys())
    club_df = full_df[full_df["team"].eq(club_name)]
    market = add_squad_complementarity(df, club_df, roles)
    if "league_translation_risk" not in market.columns:
        market["league_translation_risk"] = 1 - minmax(market["league_strength"])
    scores = []
    for i, row in market.iterrows():
        role_cfg = config.get("priority_roles", {}).get(row["role_family"], {})
        weights = {**DEFAULT_ROLE_WEIGHTS, **role_cfg.get("weights", {})}
        score = (
            weights["role_performance"] * row["role_performance_reliable"]
            + weights["squad_complementarity"] * row["squad_complementarity"]
            + weights["value_intelligence"] * row["value_intelligence"]
            + weights["reliability"] * row["reliability"]
            + weights["league_risk"] * row["league_translation_risk"]
        )
        scores.append(score)
    market["final_score"] = scores
    market["rank_in_role"] = market.groupby("role_family")["final_score"].rank(ascending=False, method="first")
    return market.sort_values(["final_score"], ascending=False)


def qa_flags(row: pd.Series) -> str:
    flags = []
    if row.get("minutes", 0) < 1200:
        flags.append("Amber: limited minutes")
    if row.get("availability_ratio", 1) < 0.75:
        flags.append("Amber: availability history")
    if row.get("league_translation_risk", 0.5) > 0.7:
        flags.append("Amber: league step-up risk")
    if row.get("role_metric_coverage", 1) < 0.75:
        flags.append("Amber: metric coverage")
    if row.get("market_value_eur", 0) > 0.9 * row.get("budget_cap", np.inf):
        flags.append("Amber: near budget ceiling")
    return "; ".join(flags) if flags else "Green: no major public-data flag"


def make_player_cards(shortlist: pd.DataFrame, n: int = 12) -> str:
    lines = ["# Shortlist Player Cards", "", "Generated from public-data MVP pipeline. These are screening outputs, not final recruitment recommendations.", ""]
    cols = ["player", "team", "league", "age", "position", "role_family", "minutes", "market_value_eur", "final_score", "role_performance_reliable", "value_intelligence", "reliability"]
    for _, r in shortlist.head(n).iterrows():
        lines.append(f"## {r['player']} — {r['role_family']}")
        lines.append(f"Club/league: {r['team']} / {r['league']}  ")
        lines.append(f"Age/minutes/value: {int(r['age'])}, {int(r['minutes'])} minutes, €{r['market_value_eur']/1_000_000:.1f}m  ")
        lines.append(f"Final score: {r['final_score']:.3f}; role score: {r['role_performance_reliable']:.3f}; value score: {r['value_intelligence']:.3f}; reliability: {r['reliability']:.3f}.  ")
        lines.append(f"QA: {qa_flags(r)}")
        lines.append("")
    return "\n".join(lines)


def run_pipeline(data_path: str | Path, config_path: str | Path, output_dir: str | Path) -> dict:
    config = load_config(config_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(data_path)
    df = prepare_players(df)
    df = add_role_performance(df)
    df = add_reliability(df)
    df, model_info = add_value_model(df)
    roles = list(config.get("priority_roles", {}).keys())
    need = squad_need_board(df, config["club"]["name"], roles)
    longlist = build_longlist(df, config)
    ranked = rank_shortlist(longlist, df, config)
    final_n = int(config.get("outputs", {}).get("final_shortlist_n", 12))
    shortlist = ranked.head(final_n).copy()
    shortlist["qa_flags"] = shortlist.apply(qa_flags, axis=1)

    need.to_csv(output_dir / "need_board.csv", index=False)
    longlist.to_csv(output_dir / "longlist.csv", index=False)
    ranked.to_csv(output_dir / "ranked_candidates.csv", index=False)
    shortlist.to_csv(output_dir / "shortlist.csv", index=False)
    (output_dir / "player_cards.md").write_text(make_player_cards(shortlist, final_n), encoding="utf-8")
    pd.DataFrame([model_info]).to_csv(output_dir / "model_info.csv", index=False)
    return {"need_board": need, "longlist": longlist, "ranked": ranked, "shortlist": shortlist, "model_info": model_info}
