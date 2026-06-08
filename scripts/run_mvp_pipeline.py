from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scoring import run_pipeline

if __name__ == "__main__":
    data_path = ROOT / "data" / "sample_players.csv"
    config_path = ROOT / "configs" / "celtic_style_scenario.yaml"
    output_dir = ROOT / "outputs"
    results = run_pipeline(data_path, config_path, output_dir)
    print("Need board")
    print(results["need_board"].to_string(index=False))
    print("\nTop shortlist")
    print(results["shortlist"][["player", "team", "role_family", "age", "minutes", "market_value_eur", "final_score", "qa_flags"]].head(12).to_string(index=False))
    print(f"\nOutputs written to: {output_dir}")
