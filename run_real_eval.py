"""Scores the readers on real published sentences (data/real_snippets.json, CC BY case reports).

Each sentence is wrapped as a one-line FINDINGS section, the way it would sit in a report.
Scored: did the reader find the lesion in the right organ, read the side (where the sentence states
it) and the largest size; and how many false alarms it raised.

Usage:  python run_real_eval.py
"""
import json
from pathlib import Path

import pandas as pd

from navigator import extract_ml, extract_rules

ROOT = Path(__file__).resolve().parent


def score(extract, name):
    rows = []
    for s in json.loads((ROOT / "data" / "real_snippets.json").read_text()):
        found = extract("FINDINGS:\n" + s["text"]).findings
        g = s["gold"]
        row = {"id": s["id"], "pmcid": s["source"]["pmcid"], "gold_organ": g and g["organ"],
               "gold_side": g and g["side"], "gold_size_cm": g and g["size_cm"],
               "pred": "; ".join(f"{f.organ} {f.side} {f.size_cm}" for f in found)}
        if g:
            hit = [f for f in found if f.organ == g["organ"]]
            f = hit[0] if hit else None
            row.update(detected=bool(f),
                       side_ok=None if g["side"] == "unknown" or not f else f.side == g["side"],
                       size_ok=bool(f) and f.size_cm is not None and abs(f.size_cm - g["size_cm"]) < 0.05,
                       false_alarms=len(found) - len(hit[:1]))
        else:
            row.update(detected=None, side_ok=None, size_ok=None, false_alarms=len(found))
        rows.append(row)
    df = pd.DataFrame(rows)
    pos, neg = df[df.gold_organ.notna()], df[df.gold_organ.isna()]
    summary = {
        "extractor": name, "sentences": len(df), "with_target_lesion": len(pos),
        "lesions_found": round(pos.detected.mean(), 3),
        "side_correct_where_stated": round(pos.side_ok.dropna().astype(bool).mean(), 3),
        "size_correct": round(pos.size_ok.mean(), 3),
        "found_by_organ": {o: round(v, 2) for o, v in pos.groupby("gold_organ").detected.mean().items()},
        "false_alarms_on_negatives": f"{int((neg.false_alarms > 0).sum())}/{len(neg)}",
        "extra_findings_on_positives": int(pos.false_alarms.sum()),
    }
    tag = name.split()[0]
    df.to_csv(ROOT / "results" / f"eval_{tag}_real.csv", index=False)
    (ROOT / "results" / f"summary_{tag}_real.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    for fn, name in ((extract_ml.extract, "ml (trained token model)"), (extract_rules.extract, "rules (regex baseline)")):
        print(json.dumps(score(fn, name), indent=1))
