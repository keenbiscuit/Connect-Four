import argparse
import json
import sys

from datetime import datetime, timezone
from pathlib import Path
from tactical_checks import analyze_tactics
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.app.services.council_service import (
    ATTACKER_INSTRUCTIONS,
    CAPTAIN_INSTRUCTIONS,
    DEFENDER_INSTRUCTIONS,
    MODEL,
    RESPONSE_FORMAT,
    build_board_rules,
    run_guarded_council,
)


def load_council_case(path):
    with path.open("r", encoding="utf-8") as file:
        case = json.load(file)

    board = case["board"]
    current_player = case["current_player"]

    build_board_rules(current_player)

    analysis = analyze_tactics(board, current_player)
    expected_column = case["expected_column"]

    if (
        type(expected_column) is not int
        or expected_column not in analysis["acceptable_columns"]
    ):
        raise ValueError(
            "The saved expected column does not satisfy the tactical policy."
        )

    return case, analysis


def write_run_record(path, record):
    temporary_path = path.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    temporary_path.replace(path)


def main():
    parser = argparse.ArgumentParser(
        description="Run the council with a deterministic tactical guard."
    )
    parser.add_argument(
        "--case",
        type=Path,
        required=True,
        help="Saved JSON case containing the board and expected column.",
    )
    args = parser.parse_args()

    case, analysis = load_council_case(args.case)
    board = case["board"]

    directory = Path("council_results")
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    result_path = directory / f"guarded_council_{timestamp}.json"

    record = {
        "test_case": case.get("test_case", args.case.stem),
        "source_case": str(args.case),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "model": MODEL,
        "reasoning_effort": "low",
        "max_completion_tokens": 4096,
        "board": board,
        "current_player": case["current_player"],
        "expected_column": case["expected_column"],
        "tactical_analysis": analysis,
        "prompts": {
            "board_rules": build_board_rules(case["current_player"]),
            "attacker": ATTACKER_INSTRUCTIONS,
            "defender": DEFENDER_INSTRUCTIONS,
            "captain": CAPTAIN_INSTRUCTIONS,
        },
        "response_format": RESPONSE_FORMAT,
    }

    write_run_record(result_path, record)

    print("\n--- GUARDED COUNCIL ---")
    print("Case:", record["test_case"])
    player_name = {1: "Red", 2: "Yellow"}[case["current_player"]]
    print("Current player:", player_name)
    print("Acceptable columns:", analysis["acceptable_columns"])
    print("Run record:", result_path)

    outcome = run_guarded_council(
        board=board,
        current_player=case["current_player"],
    )
    for stage, report in outcome["reports"].items():
        print(f"\n--- {stage.upper()} ---")
        print(json.dumps(report, indent=2, ensure_ascii=False))

    record.update(outcome)

    final = outcome["final_recommendation"]

    record["status"] = "completed"
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    record["checks"] = {
        "final_matches_expected_column": (
            final["recommended_column"] == case["expected_column"]
        ),
        "raw_captain_explanation_review": "not_reviewed",
    }

    write_run_record(result_path, record)

    print("\n--- FINAL RECOMMENDATION ---")
    print("Column:", final["recommended_column"])
    print("Explanation:", final["explanation"])
    print("Source:", final["source"])
    print("Tactical outcome:", final["tactical_outcome"])

    if final["fallback_reason"] is not None:
        print("Fallback reason:", final["fallback_reason"])

    print("\nCouncil execution:", outcome["council_status"])

    if outcome["failed_stage"] is not None:
        print("Failed advisor:", outcome["failed_stage"])
        print("Error:", outcome["error"]["message"])

    print(
        "Final matches saved expected column:",
        record["checks"]["final_matches_expected_column"],
    )
    print("Saved result:", result_path)
    print("No game move was applied.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
