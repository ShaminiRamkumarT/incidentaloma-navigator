"""Usage: python run_eval.py [rules|llm|both] [dev|holdout|all]   (llm needs ANTHROPIC_API_KEY)"""
import json
import sys

from navigator import extract_rules
from navigator.evaluate import evaluate, save


def main(which: str, split: str):
    splits = ["dev", "holdout"] if split == "all" else [split]
    extractors = []
    if which in ("rules", "both"):
        extractors.append(("rules", "rules (regex baseline)", extract_rules.extract))
    if which in ("llm", "both"):
        from navigator import extract_llm
        extractors.append(("llm", f"llm ({extract_llm.MODEL})", extract_llm.extract))
    for tag, name, fn in extractors:
        for sp in splits:
            res = evaluate(fn, name, sp)
            save(res, f"{tag}_{sp}")
            print(json.dumps(res["summary"], indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "rules", sys.argv[2] if len(sys.argv) > 2 else "all")
