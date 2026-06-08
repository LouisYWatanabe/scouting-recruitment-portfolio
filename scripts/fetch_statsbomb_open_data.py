"""Optional helper to fetch small pieces of StatsBomb Open Data.

This script is intentionally separate from the MVP pipeline because the core MVP
uses a local CSV. Run only where internet access is available and ensure your use
matches the StatsBomb Open Data terms and attribution requirements.
"""
from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


def fetch_json(url: str):
    with urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    out_dir = ROOT / "data" / "statsbomb_open_sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    competitions = fetch_json(f"{BASE}/competitions.json")
    (out_dir / "competitions.json").write_text(json.dumps(competitions, indent=2), encoding="utf-8")
    print(f"Saved competitions metadata to {out_dir / 'competitions.json'}")
    print("Next step: choose a competition_id and season_id, then fetch matches/events for your demo case.")

if __name__ == "__main__":
    main()
