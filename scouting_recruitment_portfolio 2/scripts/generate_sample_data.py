from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

TEAMS = ["Celtic", "Aberdeen", "Hearts", "Hibernian", "St Mirren", "Dundee", "Rapid Wien", "Sturm Graz", "Midtjylland", "Brondby", "AIK", "Molde", "AZ Alkmaar", "Utrecht", "Genk", "Standard Liege"]
LEAGUES = {
    "Celtic": ("Scottish Premiership", 0.68), "Aberdeen": ("Scottish Premiership", 0.62), "Hearts": ("Scottish Premiership", 0.61), "Hibernian": ("Scottish Premiership", 0.59), "St Mirren": ("Scottish Premiership", 0.55), "Dundee": ("Scottish Premiership", 0.52),
    "Rapid Wien": ("Austria Bundesliga", 0.63), "Sturm Graz": ("Austria Bundesliga", 0.66), "Midtjylland": ("Danish Superliga", 0.64), "Brondby": ("Danish Superliga", 0.60), "AIK": ("Allsvenskan", 0.55), "Molde": ("Eliteserien", 0.57), "AZ Alkmaar": ("Eredivisie", 0.72), "Utrecht": ("Eredivisie", 0.66), "Genk": ("Belgian Pro League", 0.68), "Standard Liege": ("Belgian Pro League", 0.61)
}
POSITIONS = ["CB", "RB", "RWB", "LB", "CM", "DM", "AM", "LW", "RW", "ST"]

def clip(a, lo, hi):
    return np.clip(a, lo, hi)


def role_base(pos):
    if pos in ["RB", "RWB", "LB"]:
        return dict(progressive_carries_p90=2.8, progressive_passes_p90=4.5, crosses_p90=2.5, xA_p90=0.10, touches_att_3rd_p90=18, tackles_p90=1.7, interceptions_p90=1.2, miscontrols_p90=1.4, aerial_win_pct=45, clearances_p90=2.0, pass_completion_pct=78, errors_p90=0.03, npxG_p90=0.03, shots_p90=0.4, touches_box_p90=1.5, goals_p90=0.02, pressures_p90=13)
    if pos == "CB":
        return dict(progressive_carries_p90=0.9, progressive_passes_p90=4.0, crosses_p90=0.1, xA_p90=0.02, touches_att_3rd_p90=4, tackles_p90=1.2, interceptions_p90=1.7, miscontrols_p90=0.3, aerial_win_pct=62, clearances_p90=4.5, pass_completion_pct=84, errors_p90=0.05, npxG_p90=0.04, shots_p90=0.5, touches_box_p90=1.1, goals_p90=0.03, pressures_p90=5)
    if pos == "ST":
        return dict(progressive_carries_p90=1.4, progressive_passes_p90=1.7, crosses_p90=0.4, xA_p90=0.09, touches_att_3rd_p90=22, tackles_p90=0.5, interceptions_p90=0.3, miscontrols_p90=2.4, aerial_win_pct=48, clearances_p90=0.6, pass_completion_pct=72, errors_p90=0.02, npxG_p90=0.38, shots_p90=2.8, touches_box_p90=5.7, goals_p90=0.32, pressures_p90=14)
    if pos in ["LW", "RW"]:
        return dict(progressive_carries_p90=4.1, progressive_passes_p90=2.8, crosses_p90=2.0, xA_p90=0.16, touches_att_3rd_p90=30, tackles_p90=0.8, interceptions_p90=0.6, miscontrols_p90=2.2, aerial_win_pct=35, clearances_p90=0.5, pass_completion_pct=75, errors_p90=0.03, npxG_p90=0.22, shots_p90=2.1, touches_box_p90=4.4, goals_p90=0.16, pressures_p90=16)
    if pos in ["CM", "DM", "AM"]:
        attacking = 1.3 if pos == "AM" else 1.0
        defensive = 1.2 if pos == "DM" else 1.0
        return dict(progressive_carries_p90=2.0*attacking, progressive_passes_p90=5.2, crosses_p90=0.6, xA_p90=0.10*attacking, touches_att_3rd_p90=18*attacking, tackles_p90=1.8*defensive, interceptions_p90=1.4*defensive, miscontrols_p90=1.3, aerial_win_pct=48, clearances_p90=1.2*defensive, pass_completion_pct=83, errors_p90=0.04, npxG_p90=0.10*attacking, shots_p90=1.1*attacking, touches_box_p90=2.0*attacking, goals_p90=0.07*attacking, pressures_p90=19)
    return role_base("CM")


def make_player(i, team, pos):
    league, strength = LEAGUES[team]
    age = int(clip(rng.normal(24.5, 4), 17, 35))
    minutes = int(clip(rng.normal(1550, 650), 120, 3300))
    talent = rng.normal(0, 1)
    base = role_base(pos)
    row = {"player": f"{team[:3].upper()} Player {i:03d}", "team": team, "league": league, "position": pos, "age": age, "minutes": minutes, "league_strength": strength}
    for k, v in base.items():
        noise = rng.normal(0, max(abs(v)*0.20, 0.04))
        role_signal = talent * max(abs(v)*0.12, 0.03)
        val = v + noise + role_signal
        if k.endswith("_pct") or k == "aerial_win_pct" or k == "pass_completion_pct":
            val = clip(val, 20, 95)
        elif k == "errors_p90":
            val = clip(v + rng.normal(0, 0.02) - talent*0.01, 0, 0.18)
        else:
            val = max(0, val)
        row[k] = round(float(val), 3)
    row["tackles_interceptions_p90"] = round(row["tackles_p90"] + row["interceptions_p90"], 3)
    age_pen = max(age - 26, 0) * -0.07
    value = np.exp(14.2 + 0.55*talent + 0.7*strength + 0.00018*minutes + age_pen + rng.normal(0, 0.35))
    row["market_value_eur"] = int(clip(value, 150_000, 25_000_000))
    # Celtic sample intentionally has some gaps for RWB/CB/ST to make need board meaningful.
    if team == "Celtic" and pos in ["RWB", "RB", "CB", "ST"]:
        row["minutes"] = int(clip(row["minutes"] + rng.normal(-250, 450), 200, 2400))
    row["injury_days_last_2y"] = int(max(0, rng.gamma(1.4, 22) - talent*4))
    return row


def main():
    rows = []
    i = 1
    for team in TEAMS:
        n = 16 if team == "Celtic" else 18
        for _ in range(n):
            # Slightly reduce Celtic specialised RWB/ST depth.
            if team == "Celtic":
                pos = rng.choice(POSITIONS, p=[0.16,0.04,0.03,0.08,0.18,0.11,0.10,0.12,0.12,0.06])
            else:
                pos = rng.choice(POSITIONS, p=[0.16,0.08,0.06,0.08,0.16,0.10,0.10,0.10,0.10,0.06])
            rows.append(make_player(i, team, pos))
            i += 1
    df = pd.DataFrame(rows)
    out = Path(__file__).resolve().parents[1] / "data" / "sample_players.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {out} with {len(df)} rows")

if __name__ == "__main__":
    main()
