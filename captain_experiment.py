import argparse
import json
from tactical_checks import analyze_tactics, check_recommendation
from datetime import datetime, timezone
from pathlib import Path

from council_experiment import (
    BOARD_RULES,
    CAPTAIN_INSTRUCTIONS,
    MODEL,
    RESPONSE_FORMAT,
    client,
)


def load_case(path):
    with path.open("r", encoding="utf-8") as file:
        case = json.load(file)

    board = case["board"]
    expected_column = case["expected_column"]

    if (
        not isinstance(board, list)
        or len(board) != 6
        or any(not isinstance(row, list) or len(row) != 7 for row in board)
        or any(
            type(cell) is not int or cell not in (0, 1, 2)
            for row in board
            for cell in row
        )
    ):
        raise ValueError("Saved case must contain a 6×7 integer board.")

    if type(expected_column) is not int or not 0 <= expected_column <= 6:
        raise ValueError("Saved case has an invalid expected column.")

    payload = {
        "board": board,
        "current_player": case["current_player"],
        "attacker_proposal": case["reports"]["attacker"],
        "defender_review": case["reports"]["defender"],
    }

    return case, payload


def run_captain(messages, board, expected_column, effort, max_tokens):
    result = {
        "reasoning_effort": effort,
        "max_completion_tokens": max_tokens,
        "finish_reason": None,
        "usage": None,
        "raw_content": None,
        "recommendation": None,
        "format_passed": False,
        "legal_move_passed": False,
        "move_passed": False,
        "explanation_review": "not_reviewed",
        "error": None,
    }

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            reasoning_effort=effort,
            max_completion_tokens=max_tokens,
            response_format=RESPONSE_FORMAT,
            messages=messages,
        )

        choice = completion.choices[0]
        result["finish_reason"] = choice.finish_reason
        result["raw_content"] = choice.message.content

        if completion.usage is not None:
            result["usage"] = completion.usage.model_dump(mode="json")

        if choice.finish_reason != "stop":
            raise ValueError(
                f"Generation did not finish normally: {choice.finish_reason}"
            )

        content = choice.message.content
        if not content or not content.strip():
            raise ValueError("Captain returned empty content.")

        recommendation = json.loads(content)
        result["recommendation"] = recommendation

        if not isinstance(recommendation, dict):
            raise ValueError("Response must be a JSON object.")

        if set(recommendation) != {"recommended_column", "explanation"}:
            raise ValueError("Response has missing or unexpected fields.")

        column = recommendation["recommended_column"]
        explanation = recommendation["explanation"]

        if type(column) is not int or not 0 <= column <= 6:
            raise ValueError("recommended_column must be an integer from 0–6.")

        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError("explanation must be a nonempty string.")

        result["format_passed"] = True

        if all(row[column] != 0 for row in board):
            raise ValueError(f"Recommended column {column} is full.")

        result["legal_move_passed"] = True
        result["move_passed"] = column == expected_column

    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"

    return result


def summarize(results, effort):
    trials = [result for result in results if result["reasoning_effort"] == effort]

    return {
        "trials": len(trials),
        "normal_completions": sum(
            result["finish_reason"] == "stop" for result in trials
        ),
        "format_passes": sum(result["format_passed"] for result in trials),
        "legal_move_passes": sum(result["legal_move_passed"] for result in trials),
        "move_passes": sum(result["move_passed"] for result in trials),
        "errors": sum(result["error"] is not None for result in trials),
        "explanations_reviewed": 0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare captain settings using fixed advisor reports."
    )
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument(
        "--efforts",
        nargs="+",
        choices=["low", "medium", "high"],
        default=["low", "medium"],
    )
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()

    if args.runs < 1 or args.max_tokens < 1:
        parser.error("--runs and --max-tokens must be positive.")

    if len(set(args.efforts)) != len(args.efforts):
        parser.error("--efforts must not contain duplicates.")

    case, payload = load_case(args.case)

    tactical_analysis = analyze_tactics(
        payload["board"],
        payload["current_player"],
    )

    print("\n--- DETERMINISTIC BOARD ANALYSIS ---")
    print(json.dumps(tactical_analysis, indent=2))

    system_prompt = BOARD_RULES + "\n\n" + CAPTAIN_INSTRUCTIONS
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload)},
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output_directory = Path("captain_results")
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"captain_comparison_{timestamp}.json"

    experiment = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_case": str(args.case),
        "test_case": case.get("test_case"),
        "tactical_analysis": tactical_analysis,
        "model": MODEL,
        "expected_column": case["expected_column"],
        "settings": {
            "efforts": args.efforts,
            "runs_per_effort": args.runs,
            "max_completion_tokens": args.max_tokens,
        },
        "messages": messages,
        "response_format": RESPONSE_FORMAT,
        "results": [],
        "summary": {},
    }

    def save_progress():
        experiment["summary"] = {
            effort: summarize(experiment["results"], effort) for effort in args.efforts
        }
        output_path.write_text(
            json.dumps(experiment, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    total_calls = args.runs * len(args.efforts)
    print("Saved case:", args.case)
    print("Expected column:", case["expected_column"])
    print("Captain API calls planned:", total_calls)
    print("Advisor calls planned: 0")

    save_progress()

    for trial in range(1, args.runs + 1):
        for effort in args.efforts:
            print(f"\n--- Trial {trial}: {effort} ---")

            result = run_captain(
                messages=messages,
                board=payload["board"],
                expected_column=case["expected_column"],
                effort=effort,
                max_tokens=args.max_tokens,
            )
            recommendation = result["recommendation"]

            if result["format_passed"] and isinstance(recommendation, dict):
                result["tactical_check"] = check_recommendation(
                    tactical_analysis,
                    recommendation["recommended_column"],
                )
            else:
                result["tactical_check"] = {
                    "tactical_passed": False,
                    "reason": "No valid completed recommendation was available.",
                }

            print(
                "Deterministic tactical check:",
                json.dumps(result["tactical_check"], indent=2),
            )
            result["trial"] = trial
            experiment["results"].append(result)
            save_progress()

            print("Finish reason:", result["finish_reason"])
            print("Move:", "PASS" if result["move_passed"] else "FAIL")

            if result["recommendation"] is not None:
                print(
                    json.dumps(
                        result["recommendation"],
                        indent=2,
                        ensure_ascii=False,
                    )
                )

            if result["error"]:
                print("Error:", result["error"])

    print("\n--- SUMMARY ---")
    for effort, summary in experiment["summary"].items():
        print(
            f"{effort}: "
            f"{summary['move_passes']}/{summary['trials']} move passes, "
            f"{summary['errors']} errors"
        )

    print("Explanation accuracy: not automatically evaluated.")
    print("Saved experiment:", output_path)


if __name__ == "__main__":
    main()
