"""Compare Experiment 018, 020, and 021 on the fixed paired reset plan."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

PLAN_SHA256 = "ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def by_id(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = document.get("paired_episode_records")
    if not isinstance(records, list) or len(records) != 256:
        raise ValueError(f"Expected 256 paired records, got {len(records) if records else 0}.")
    if document.get("reset_plan_sha256") != PLAN_SHA256:
        raise ValueError(f"Unexpected paired plan SHA-256: {document.get('reset_plan_sha256')}")
    result = {record["episode_id"]: record for record in records}
    expected = {f"env_{env:02d}_ep_{episode:02d}" for env in range(64) for episode in range(4)}
    if set(result) != expected:
        raise ValueError("Paired episode IDs do not match the fixed 64x4 plan.")
    return result


def metrics(records: list[dict[str, Any]]) -> dict[str, float | int]:
    return {
        "episodes": len(records),
        "successes": sum(bool(record["success"]) for record in records),
        "success_rate": sum(bool(record["success"]) for record in records) / len(records),
        "mean_final_xy_error_mm": statistics.mean(record["final_xy_error_mm"] for record in records),
        "median_final_xy_error_mm": statistics.median(record["final_xy_error_mm"] for record in records),
        "mean_max_insertion_depth_mm": statistics.mean(
            record["max_insertion_depth_mm"] for record in records
        ),
        "median_max_insertion_depth_mm": statistics.median(
            record["max_insertion_depth_mm"] for record in records
        ),
        "mean_episode_length": statistics.mean(record["episode_length"] for record in records),
        "mean_episodic_reward": statistics.mean(record["episodic_reward"] for record in records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-50", type=Path, required=True)
    parser.add_argument("--old-46", type=Path, required=True)
    parser.add_argument("--exp020", type=Path, required=True)
    parser.add_argument("--exp021", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    old_50 = by_id(load(args.old_50))
    old_46 = by_id(load(args.old_46))
    exp020 = by_id(load(args.exp020))
    exp021 = by_id(load(args.exp021))
    ids = sorted(old_46)
    if not (set(old_50) == set(old_46) == set(exp020) == set(exp021)):
        raise ValueError("The four paired result files do not contain the same IDs.")

    known_34 = [
        episode_id
        for episode_id in ids
        if old_50[episode_id]["success"] and not old_46[episode_id]["success"]
    ]
    rows = []
    for episode_id in ids:
        rows.append(
            {
                "episode_id": episode_id,
                "exp018_success": bool(old_46[episode_id]["success"]),
                "exp020_success": bool(exp020[episode_id]["success"]),
                "exp021_success": bool(exp021[episode_id]["success"]),
                "exp018_final_xy_error_mm": old_46[episode_id]["final_xy_error_mm"],
                "exp020_final_xy_error_mm": exp020[episode_id]["final_xy_error_mm"],
                "exp021_final_xy_error_mm": exp021[episode_id]["final_xy_error_mm"],
                "exp018_max_insertion_depth_mm": old_46[episode_id]["max_insertion_depth_mm"],
                "exp020_max_insertion_depth_mm": exp020[episode_id]["max_insertion_depth_mm"],
                "exp021_max_insertion_depth_mm": exp021[episode_id]["max_insertion_depth_mm"],
                "exp018_episode_length": old_46[episode_id]["episode_length"],
                "exp020_episode_length": exp020[episode_id]["episode_length"],
                "exp021_episode_length": exp021[episode_id]["episode_length"],
            }
        )

    def subset(mapping: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [mapping[episode_id] for episode_id in known_34]

    output = {
        "experiment": "021",
        "paired_plan_sha256": PLAN_SHA256,
        "policies": {
            "exp018_46mm": metrics([old_46[episode_id] for episode_id in ids]),
            "exp020_46mm": metrics([exp020[episode_id] for episode_id in ids]),
            "exp021_46mm": metrics([exp021[episode_id] for episode_id in ids]),
        },
        "known_34_subset": {
            "definition": "Experiment 018 50mm success and 46mm failure",
            "episodes": len(known_34),
            "exp018_46mm": metrics(subset(old_46)),
            "exp020_46mm": metrics(subset(exp020)),
            "exp021_46mm": metrics(subset(exp021)),
            "exp021_recovered": sum(bool(exp021[episode_id]["success"]) for episode_id in known_34),
        },
        "episode_rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"policies": output["policies"], "known_34_subset": output["known_34_subset"]}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
