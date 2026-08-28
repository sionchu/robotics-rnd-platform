"""Compare the frozen Experiment 018 policy with the Experiment 020 policy."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

PAIRED_PLAN_SHA256 = "ece1662c6b5de3016c77b67c667b75f37551b3de80eaf137897645576abd2f2c"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def records_by_id(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = document.get("paired_episode_records")
    if not isinstance(records, list) or len(records) != 256:
        raise ValueError(f"Expected 256 paired records, got {len(records) if records else 0}.")
    if document.get("reset_plan_sha256") != PAIRED_PLAN_SHA256:
        raise ValueError(f"Unexpected reset plan SHA-256: {document.get('reset_plan_sha256')}")
    result = {record["episode_id"]: record for record in records}
    expected = {f"env_{env_id:02d}_ep_{episode:02d}" for env_id in range(64) for episode in range(4)}
    if set(result) != expected:
        raise ValueError("Paired episode IDs do not match env_00_ep_00 through env_63_ep_03.")
    return result


def metric(records: list[dict[str, Any]], key: str) -> float | None:
    return statistics.mean(float(record[key]) for record in records) if records else None


def compact_metrics(records: list[dict[str, Any]]) -> dict[str, float | int | None]:
    return {
        "episodes": len(records),
        "successes": sum(bool(record["success"]) for record in records),
        "success_rate": (
            sum(bool(record["success"]) for record in records) / len(records) if records else 0.0
        ),
        "mean_final_xy_error_mm": metric(records, "final_xy_error_mm"),
        "mean_max_insertion_depth_mm": metric(records, "max_insertion_depth_mm"),
        "mean_episode_length": metric(records, "episode_length"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-50", type=Path, required=True)
    parser.add_argument("--old-46", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    old_50 = records_by_id(load(args.old_50))
    old_46 = records_by_id(load(args.old_46))
    new = records_by_id(load(args.new))
    ids = sorted(old_46)
    if set(old_50) != set(old_46) or set(old_46) != set(new):
        raise ValueError("The three paired result files do not contain the same episode IDs.")

    known_failures = [
        episode_id
        for episode_id in ids
        if old_50[episode_id]["success"] and not old_46[episode_id]["success"]
    ]
    recovered = [episode_id for episode_id in known_failures if new[episode_id]["success"]]
    rows = []
    for episode_id in ids:
        rows.append(
            {
                "episode_id": episode_id,
                "old_success_50mm": bool(old_50[episode_id]["success"]),
                "old_success_46mm": bool(old_46[episode_id]["success"]),
                "new_success_46mm": bool(new[episode_id]["success"]),
                "old_final_xy_error_mm": old_46[episode_id]["final_xy_error_mm"],
                "new_final_xy_error_mm": new[episode_id]["final_xy_error_mm"],
                "old_max_insertion_depth_mm": old_46[episode_id]["max_insertion_depth_mm"],
                "new_max_insertion_depth_mm": new[episode_id]["max_insertion_depth_mm"],
                "old_episode_length": old_46[episode_id]["episode_length"],
                "new_episode_length": new[episode_id]["episode_length"],
            }
        )

    known_rows_old = [old_46[episode_id] for episode_id in known_failures]
    known_rows_new = [new[episode_id] for episode_id in known_failures]
    output = {
        "experiment": "020",
        "paired_plan_sha256": PAIRED_PLAN_SHA256,
        "episode_count": len(ids),
        "old_46mm": compact_metrics([old_46[episode_id] for episode_id in ids]),
        "new_46mm": compact_metrics([new[episode_id] for episode_id in ids]),
        "known_34_subset": {
            "definition": "Experiment 018 50mm success and 46mm failure",
            "episodes": len(known_failures),
            "recovered": len(recovered),
            "still_failed": len(known_failures) - len(recovered),
            "old_46mm_metrics": compact_metrics(known_rows_old),
            "new_46mm_metrics": compact_metrics(known_rows_new),
            "recovered_episode_ids": recovered,
        },
        "episode_rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps({key: output[key] for key in ("old_46mm", "new_46mm", "known_34_subset")}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
