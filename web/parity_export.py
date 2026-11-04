"""Writes what the Python regex reader and rules engine produce for every report, so that
web/parity_check.js can confirm the browser engine gives identical results.

Usage:  python web/parity_export.py > /tmp/py_out.json && node web/parity_check.js /tmp/py_out.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from navigator.extract_rules import extract  # noqa: E402
from navigator.guidelines import classify, concordance  # noqa: E402

FILES = ["reports.json", "reports_holdout.json", "reports_holdout_all.json", "synthetic_test.json"]

out = []
for name in FILES:
    for r in json.loads((ROOT / "data" / name).read_text()):
        py = []
        for f in extract(r["text"]).findings:
            g = classify(f)
            c = concordance(f, g)
            d = f.model_dump(mode="json")
            d.update(category=g.category, actions=[a.value for a in g.actions], status=c.status, severity=c.severity,
                     message=c.message, rationale=g.rationale, notes=g.notes)
            py.append(d)
        out.append({"id": r["id"], "text": r["text"], "py": py})
print(json.dumps(out))
