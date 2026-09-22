import argparse
import json
from pathlib import Path


def normalized_text(value):
    return "".join(str(value or "").lower().split()).replace("；", "").replace("，", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    changes = []
    conditions = data["basic_conditions"]["other_application_conditions"]
    degree_text = normalized_text(data["basic_conditions"]["degree_requirements"]["minimum_degree"])
    kept = []
    for condition in conditions:
        value = normalized_text(condition["normalized_value"])
        if value and degree_text and (value in degree_text or degree_text in value):
            changes.append({
                "type": "remove_duplicate_condition",
                "condition_name": condition["condition_name"],
                "normalized_value": condition["normalized_value"],
                "reason": "Already represented in degree_requirements",
            })
        else:
            kept.append(condition)
    data["basic_conditions"]["other_application_conditions"] = kept

    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.log).write_text(json.dumps({"input": args.input, "output": args.output, "changes": changes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changes": len(changes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
