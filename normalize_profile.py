import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    changes = []
    for preference in data.get("task_preferences", []):
        if preference["preference_level"] == "untested" and preference["confidence"] != "low":
            changes.append({
                "type": "normalize_untested_preference_confidence",
                "task_name": preference["task_name"],
                "from": preference["confidence"],
                "to": "low",
            })
            preference["confidence"] = "low"

    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.log).write_text(json.dumps({"input": args.input, "output": args.output, "changes": changes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changes": len(changes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
