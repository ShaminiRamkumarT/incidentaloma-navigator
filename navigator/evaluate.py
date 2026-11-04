"""Scores an extractor against the gold labels in data/reports.json.

Three levels:
  1. Detection   - did it find each lesion (matched on organ + side + nearest size)?
  2. Fields      - per-field accuracy on matched lesions.
  3. End to end  - does the guideline category and the concordance flag computed from the
                   extracted fields match the one computed from the gold fields?
"""
import json
from pathlib import Path
from typing import Callable, Dict, List

import pandas as pd

from .guidelines import classify, concordance
from .schema import Finding, ReportExtraction

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["size_cm", "composition", "unenhanced_hu", "enhanced_hu", "homogeneous", "wall_mm", "septa_count",
          "septa_mm", "irregular_wall_or_septa", "enhancing_nodule", "macroscopic_fat",
          "too_small_to_characterize", "stated_actions"]


# Fields scored per organ (a lung nodule is not scored on septa, etc.)
COMMON = ["size_cm", "side", "stated_actions"]
ORGAN_FIELDS = {
    "kidney": FIELDS,
    "adrenal": FIELDS,
    "lung": COMMON + ["short_axis_cm", "nodule_type", "solid_component_mm", "multiple", "patient_risk"],
    "liver": COMMON + ["appearance", "enhanced_hu", "homogeneous", "patient_risk", "fdg_avid"],
    "pancreas": COMMON + ["patient_age", "duct_mm", "mural_nodule", "enhancing_nodule", "irregular_wall_or_septa"],
    "thyroid": COMMON + ["patient_age", "appearance", "fdg_avid", "limited_life_expectancy"],
    "pituitary": COMMON + ["chiasm_contact"],
    "brain": COMMON + ["growth", "symptomatic"],
    "bone": COMMON + ["bone_density", "appearance", "unenhanced_hu", "patient_risk"],
}
ALL_FIELDS = list(dict.fromkeys(f for v in ORGAN_FIELDS.values() for f in v))

SPLITS = {"dev": "reports.json", "holdout": "reports_holdout.json", "holdout_all": "reports_holdout_all.json",
          "synth_test": "synthetic_test.json"}


def load_reports(split: str = "dev") -> List[dict]:
    return json.loads((ROOT / "data" / SPLITS[split]).read_text())


def _match(gold: List[Finding], pred: List[Finding]):
    pairs, used = [], set()
    for gi, g in enumerate(gold):
        cands = [(abs((p.size_cm or 0) - (g.size_cm or 0)), pi) for pi, p in enumerate(pred)
                 if pi not in used and p.organ == g.organ and (g.side == "unknown" or p.side in (g.side, "unknown"))]
        if cands:
            _, pi = min(cands)
            used.add(pi)
            pairs.append((gi, pi))
        else:
            pairs.append((gi, None))
    unmatched_pred = [pi for pi in range(len(pred)) if pi not in used]
    return pairs, unmatched_pred


def _same(field, a, b):
    if field == "stated_actions":
        return sorted(x.value for x in a) == sorted(x.value for x in b)
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) < 0.05
    return a == b


def evaluate(extractor: Callable[[str], ReportExtraction], name: str, split: str = "dev") -> Dict:
    rows, field_hits, false_pos = [], {k: [] for k in ALL_FIELDS}, 0
    reports = load_reports(split)
    for r in reports:
        gold = [Finding(**x["gold"]) for x in r["findings"]]
        try:
            pred = extractor(r["text"]).findings
            error = ""
        except Exception as e:  # keep scoring the rest
            pred, error = [], f"{type(e).__name__}: {e}"
        pairs, extra = _match(gold, pred)
        false_pos += len(extra)
        for gi, pi in pairs:
            g = gold[gi]
            gg = classify(g)
            gc = concordance(g, gg)
            row = {"report": r["id"], "organ": g.organ, "side": g.side, "size_cm": g.size_cm,
                   "gold_category": gg.category, "gold_status": gc.status, "gold_severity": gc.severity,
                   "detected": pi is not None, "error": error}
            if pi is not None:
                p = pred[pi]
                pg = classify(p)
                pc = concordance(p, pg)
                row.update(pred_category=pg.category, pred_status=pc.status, pred_severity=pc.severity,
                           category_match=pg.category == gg.category, status_match=pc.status == gc.status)
                wrong = []
                for k in ORGAN_FIELDS[g.organ]:
                    ok = _same(k, getattr(g, k), getattr(p, k))
                    field_hits[k].append(ok)
                    if not ok:
                        wrong.append(f"{k}: gold={_fmt(getattr(g, k))} pred={_fmt(getattr(p, k))}")
                row["field_errors"] = "; ".join(wrong)
            else:
                row.update(pred_category=None, pred_status=None, pred_severity=None,
                           category_match=False, status_match=False, field_errors="not detected")
            rows.append(row)
        for pi in extra:
            p = pred[pi]
            rows.append({"report": r["id"], "organ": p.organ, "side": p.side, "size_cm": p.size_cm,
                         "gold_category": None, "gold_status": None, "detected": False,
                         "pred_category": classify(p).category, "field_errors": "false positive"})

    df = pd.DataFrame(rows)
    gold_rows = df[df["gold_category"].notna()]
    n_gold = len(gold_rows)
    discordant = gold_rows[gold_rows["gold_status"] != "concordant"]
    flagged = gold_rows[gold_rows["pred_status"].fillna("concordant") != "concordant"]
    tp = len(gold_rows[(gold_rows["gold_status"] != "concordant") & (gold_rows["pred_status"].fillna("concordant") != "concordant")])
    summary = {
        "extractor": name,
        "split": split,
        "reports": len(reports),
        "gold_findings": n_gold,
        "detection_recall": round(gold_rows["detected"].mean(), 3),
        "false_positive_findings": int(false_pos),
        "field_accuracy": {k: round(sum(v) / len(v), 3) for k, v in field_hits.items() if v},
        "category_agreement": round(gold_rows["category_match"].mean(), 3),
        "status_agreement": round(gold_rows["status_match"].mean(), 3),
        "discordance_sensitivity": round(tp / len(discordant), 3) if len(discordant) else None,
        "discordance_ppv": round(tp / len(flagged), 3) if len(flagged) else None,
        "category_agreement_by_organ": {o: round(v, 3) for o, v in
                                        gold_rows.groupby("organ")["category_match"].mean().items()},
        "high_severity_caught": f"{len(gold_rows[(gold_rows.gold_severity == 'high') & (gold_rows.pred_severity == 'high')])}"
                                f"/{len(gold_rows[gold_rows.gold_severity == 'high'])}",
    }
    return {"summary": summary, "rows": df}


def _fmt(v):
    if isinstance(v, list):
        return "[" + ",".join(x.value for x in v) + "]"
    return v


def save(result: Dict, tag: str):
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    result["rows"].to_csv(out / f"eval_{tag}.csv", index=False)
    (out / f"summary_{tag}.json").write_text(json.dumps(result["summary"], indent=2))
