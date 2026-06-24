"""Compare two batch summary JSONs side-by-side.

Usage:
    python tests/compare_runs.py tests/runs/summary_A.json tests/runs/summary_B.json
"""
import json
import sys
from pathlib import Path


def load_summary(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt_resilience(metrics: dict | None) -> str:
    if not metrics:
        return "n/a"
    verdict = metrics.get("verdict", "?")
    stability = metrics.get("stability", "?")
    drift = metrics.get("mean_utility_drift", "?")
    return f"{verdict} (stab={stability}, drift={drift})"


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__.strip())
        sys.exit(1)

    a = load_summary(sys.argv[1])
    b = load_summary(sys.argv[2])

    print(f"{'Scenario':<30} {'Run A':<30} {'Run B':<30}")
    print("─" * 90)

    a_map = {r["scenario"]: r for r in a["results"]}
    b_map = {r["scenario"]: r for r in b["results"]}
    all_scenarios = sorted(set(list(a_map.keys()) + list(b_map.keys())))

    for scenario in all_scenarios:
        ra = a_map.get(scenario)
        rb = b_map.get(scenario)
        col_a = fmt_resilience(ra["resilience_metrics"]) if ra else "—"
        col_b = fmt_resilience(rb["resilience_metrics"]) if rb else "—"
        print(f"{scenario:<30} {col_a:<30} {col_b:<30}")

    print("─" * 90)
    print(f"{'Total time':<30} {a.get('total_elapsed_s', '?')}s{'':<24} {b.get('total_elapsed_s', '?')}s")
    print(f"{'Pass/Fail':<30} {a.get('passed', '?')}/{a.get('failed', '?')}{'':<24} {b.get('passed', '?')}/{b.get('failed', '?')}")


if __name__ == "__main__":
    main()
