
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import hashlib
import math

import numpy as np
import pandas as pd
import requests

RAW_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def _get_json(url: str, timeout: int = 30):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def load_competitions() -> pd.DataFrame:
    """Load the public StatsBomb competition index from GitHub."""
    data = _get_json(f"{RAW_BASE}/competitions.json")
    df = pd.DataFrame(data)
    keep = [
        "competition_id", "season_id", "country_name", "competition_name",
        "competition_gender", "season_name", "match_updated", "match_available_360",
    ]
    return df[[c for c in keep if c in df.columns]].sort_values(
        ["competition_name", "season_name"], kind="stable"
    )


def load_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    data = _get_json(f"{RAW_BASE}/matches/{competition_id}/{season_id}.json")
    rows = []
    for m in data:
        rows.append({
            "match_id": m.get("match_id"),
            "match_date": m.get("match_date"),
            "kick_off": m.get("kick_off"),
            "home_team": (m.get("home_team") or {}).get("home_team_name"),
            "away_team": (m.get("away_team") or {}).get("away_team_name"),
            "competition_stage": (m.get("competition_stage") or {}).get("name"),
        })
    return pd.DataFrame(rows).sort_values(["match_date", "match_id"], kind="stable")


def load_events(match_id: int) -> List[dict]:
    return _get_json(f"{RAW_BASE}/events/{match_id}.json")


def load_lineups(match_id: int) -> List[dict]:
    return _get_json(f"{RAW_BASE}/lineups/{match_id}.json")


def _safe_name(obj, key="name"):
    if isinstance(obj, dict):
        return obj.get(key)
    return None


def _event_minute(e: dict) -> float:
    return float(e.get("minute", 0)) + float(e.get("second", 0)) / 60.0


def _position_to_role(pos_name: Optional[str]) -> str:
    if not pos_name:
        return "CM"
    p = pos_name.lower()
    if "goalkeeper" in p:
        return "GK"
    if "center back" in p or "centre back" in p or "left center back" in p or "right center back" in p:
        return "CB"
    if "right back" in p or "right wing back" in p:
        return "RWB"
    if "left back" in p or "left wing back" in p:
        return "LWB"
    if "center forward" in p or "striker" in p:
        return "ST"
    if "right wing" in p or "left wing" in p or "right midfield" in p or "left midfield" in p:
        return "W"
    if "defensive midfield" in p:
        return "DM"
    if "attacking midfield" in p:
        return "AM"
    if "center midfield" in p or "centre midfield" in p:
        return "CM"
    return "CM"


def _role_to_position(role: str) -> str:
    return {
        "CB": "CB", "RWB": "RWB", "LWB": "LWB", "ST": "ST", "W": "RW", "DM": "DM", "AM": "AM", "CM": "CM", "GK": "GK",
    }.get(role, "CM")


def _stable_demo_number(name: str, lo: float, hi: float) -> float:
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    x = int(h[:8], 16) / 0xFFFFFFFF
    return lo + x * (hi - lo)


def _lineup_table(lineups: List[dict], match_id: int) -> pd.DataFrame:
    rows = []
    for team_block in lineups:
        team_name = team_block.get("team_name") or _safe_name(team_block.get("team"))
        for p in team_block.get("lineup", []):
            player_name = p.get("player_name") or _safe_name(p.get("player"))
            player_id = p.get("player_id") or (p.get("player") or {}).get("id")
            positions = p.get("positions") or []
            # Prefer the first listed tactical position, but keep fallback.
            pos_name = None
            if positions:
                pos_name = _safe_name(positions[0].get("position")) or positions[0].get("position_name")
            rows.append({
                "match_id": match_id,
                "player_id": player_id,
                "player": player_name,
                "team": team_name,
                "position_name": pos_name,
                "role_family": _position_to_role(pos_name),
            })
    return pd.DataFrame(rows)


def _minutes_from_lineups_and_subs(lineups: List[dict], events: List[dict], match_id: int) -> pd.DataFrame:
    players = _lineup_table(lineups, match_id)
    if players.empty:
        return players.assign(minutes_match=0.0)
    match_end = max([_event_minute(e) for e in events], default=90.0)
    match_end = max(match_end, 90.0)
    players["start_min"] = 0.0
    players["end_min"] = match_end
    # If a player has no event and appears as late substitute, lineups positions may include from/to fields,
    # but those fields are not always reliable. Substitution events give a usable approximation.
    player_names = set(players["player"].dropna())
    add_rows = []
    for e in events:
        if _safe_name(e.get("type")) != "Substitution":
            continue
        t = _event_minute(e)
        off_name = _safe_name(e.get("player"))
        team = _safe_name(e.get("team"))
        sub = e.get("substitution") or {}
        on_name = _safe_name(sub.get("replacement"))
        if off_name in player_names:
            players.loc[players["player"].eq(off_name) & players["match_id"].eq(match_id), "end_min"] = t
        if on_name and on_name not in player_names:
            add_rows.append({
                "match_id": match_id,
                "player_id": None,
                "player": on_name,
                "team": team,
                "position_name": None,
                "role_family": "CM",
                "start_min": t,
                "end_min": match_end,
            })
            player_names.add(on_name)
    if add_rows:
        players = pd.concat([players, pd.DataFrame(add_rows)], ignore_index=True)
    players["minutes_match"] = (players["end_min"] - players["start_min"]).clip(lower=0)
    return players


def _progressive(start: Optional[List[float]], end: Optional[List[float]], threshold: float = 10.0) -> bool:
    if not start or not end or len(start) < 2 or len(end) < 2:
        return False
    # Simple public-data approximation: positive x gain on StatsBomb's 120x80 grid.
    return (float(end[0]) - float(start[0])) >= threshold


def aggregate_match(match_id: int) -> pd.DataFrame:
    events = load_events(match_id)
    lineups = load_lineups(match_id)
    minutes = _minutes_from_lineups_and_subs(lineups, events, match_id)
    rows: Dict[Tuple[str, str], dict] = {}

    for _, r in minutes.iterrows():
        key = (r["player"], r["team"])
        rows[key] = {
            "player": r["player"],
            "team": r["team"],
            "league": "StatsBomb Open Data",
            "position": _role_to_position(r["role_family"]),
            "role_family": r["role_family"],
            "minutes": float(r.get("minutes_match", 0.0)),
            "shots": 0, "goals": 0, "npxG": 0.0, "passes": 0, "pass_completed": 0,
            "progressive_passes": 0, "carries": 0, "progressive_carries": 0,
            "crosses": 0, "key_passes": 0, "pressures": 0, "tackles_interceptions": 0,
            "clearances": 0, "miscontrols": 0, "errors": 0, "touches_att_3rd": 0, "touches_box": 0,
        }

    for e in events:
        player = _safe_name(e.get("player"))
        team = _safe_name(e.get("team"))
        if not player or not team:
            continue
        key = (player, team)
        if key not in rows:
            rows[key] = {
                "player": player, "team": team, "league": "StatsBomb Open Data", "position": "CM", "role_family": "CM",
                "minutes": 0.0, "shots": 0, "goals": 0, "npxG": 0.0, "passes": 0, "pass_completed": 0,
                "progressive_passes": 0, "carries": 0, "progressive_carries": 0, "crosses": 0, "key_passes": 0,
                "pressures": 0, "tackles_interceptions": 0, "clearances": 0, "miscontrols": 0, "errors": 0,
                "touches_att_3rd": 0, "touches_box": 0,
            }
        rec = rows[key]
        typ = _safe_name(e.get("type"))
        loc = e.get("location")
        if loc and len(loc) >= 2:
            if loc[0] >= 80:
                rec["touches_att_3rd"] += 1
            if loc[0] >= 102 and 18 <= loc[1] <= 62:
                rec["touches_box"] += 1
        if typ == "Shot":
            rec["shots"] += 1
            shot = e.get("shot") or {}
            rec["npxG"] += float(shot.get("statsbomb_xg") or 0.0)
            if _safe_name(shot.get("outcome")) == "Goal":
                rec["goals"] += 1
        elif typ == "Pass":
            rec["passes"] += 1
            p = e.get("pass") or {}
            if p.get("outcome") is None:
                rec["pass_completed"] += 1
            if _progressive(e.get("location"), p.get("end_location")):
                rec["progressive_passes"] += 1
            if p.get("cross"):
                rec["crosses"] += 1
            if p.get("shot_assist") or p.get("goal_assist"):
                rec["key_passes"] += 1
        elif typ == "Carry":
            rec["carries"] += 1
            c = e.get("carry") or {}
            if _progressive(e.get("location"), c.get("end_location")):
                rec["progressive_carries"] += 1
        elif typ == "Pressure":
            rec["pressures"] += 1
        elif typ in {"Interception", "Ball Recovery", "Duel", "Block"}:
            rec["tackles_interceptions"] += 1
        elif typ == "Clearance":
            rec["clearances"] += 1
        elif typ == "Miscontrol":
            rec["miscontrols"] += 1
        elif typ == "Error":
            rec["errors"] += 1

    return pd.DataFrame(rows.values())


def aggregate_competition(competition_id: int, season_id: int, max_matches: int = 12) -> pd.DataFrame:
    matches = load_matches(competition_id, season_id)
    match_ids = matches["match_id"].dropna().astype(int).head(max_matches).tolist()
    frames = []
    for mid in match_ids:
        frames.append(aggregate_match(mid))
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)
    agg_cols = {
        "minutes": "sum", "shots": "sum", "goals": "sum", "npxG": "sum", "passes": "sum", "pass_completed": "sum",
        "progressive_passes": "sum", "carries": "sum", "progressive_carries": "sum", "crosses": "sum", "key_passes": "sum",
        "pressures": "sum", "tackles_interceptions": "sum", "clearances": "sum", "miscontrols": "sum", "errors": "sum",
        "touches_att_3rd": "sum", "touches_box": "sum",
    }
    meta = raw.groupby(["player", "team"], as_index=False).agg({
        "league": "first", "position": "first", "role_family": "first", **agg_cols
    })
    # Build a scoring-compatible player table.
    minutes = meta["minutes"].replace(0, np.nan)
    factor = 90 / minutes
    meta["npxG_p90"] = meta["npxG"] * factor
    meta["goals_p90"] = meta["goals"] * factor
    meta["shots_p90"] = meta["shots"] * factor
    meta["progressive_passes_p90"] = meta["progressive_passes"] * factor
    meta["progressive_carries_p90"] = meta["progressive_carries"] * factor
    meta["crosses_p90"] = meta["crosses"] * factor
    meta["xA_p90"] = meta["key_passes"] * factor * 0.05  # explicit proxy: not true xA
    meta["pressures_p90"] = meta["pressures"] * factor
    meta["tackles_interceptions_p90"] = meta["tackles_interceptions"] * factor
    meta["clearances_p90"] = meta["clearances"] * factor
    meta["miscontrols_p90"] = meta["miscontrols"] * factor
    meta["errors_p90"] = meta["errors"] * factor
    meta["touches_att_3rd_p90"] = meta["touches_att_3rd"] * factor
    meta["touches_box_p90"] = meta["touches_box"] * factor
    meta["pass_completion_pct"] = np.where(meta["passes"] > 0, 100 * meta["pass_completed"] / meta["passes"], np.nan)
    meta["aerial_win_pct"] = 50.0
    # Fields not available in StatsBomb Open Data. Keep as transparent demo proxies so the app can run.
    # Users can upload/merge real age, market value, contract, wage and injury data later.
    meta["age"] = meta["player"].apply(lambda x: round(_stable_demo_number(str(x), 19, 31), 1))
    meta["market_value_eur"] = meta.apply(lambda r: round(_stable_demo_number(str(r["player"])+str(r["team"]), 200_000, 7_500_000), -4), axis=1)
    meta["injury_days_last_2y"] = 0
    meta["availability_ratio"] = 1.0
    meta["league_strength"] = 0.65
    meta["data_source"] = "StatsBomb Open Data aggregation; age/value are demo proxies"
    return meta
