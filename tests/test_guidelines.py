"""Every gold lesion must land in the category its author expected, and key edge cases hold."""
import json
from pathlib import Path

import pytest

from navigator.guidelines import classify, concordance
from navigator.schema import Action, Finding

DATA = Path(__file__).resolve().parent.parent / "data"
CASES = [(r["id"], x) for name in ("reports.json", "reports_holdout.json")
         for r in json.loads((DATA / name).read_text()) for x in r["findings"]]


@pytest.mark.parametrize("rid,case", CASES, ids=[c[0] for c in CASES])
def test_expected_category(rid, case):
    assert classify(Finding(**case["gold"])).category == case["expected_category"]


def test_bosniak_thresholds():
    cyst = dict(organ="kidney", composition="cystic")
    assert classify(Finding(**cyst, septa_mm=2, septa_count=3)).category == "Bosniak II"
    assert classify(Finding(**cyst, septa_mm=3, septa_count=1)).category == "Bosniak IIF"
    assert classify(Finding(**cyst, septa_count=4)).category == "Bosniak IIF"
    assert classify(Finding(**cyst, wall_mm=4)).category == "Bosniak III"
    assert classify(Finding(**cyst, enhancing_nodule=True)).category == "Bosniak IV"


def test_adrenal_10_hu_cutoff():
    assert Action.CHARACTERIZATION_IMAGING not in classify(Finding(organ="adrenal", size_cm=2, unenhanced_hu=10)).actions
    assert Action.CHARACTERIZATION_IMAGING in classify(Finding(organ="adrenal", size_cm=2, unenhanced_hu=11)).actions


def test_missing_referral_is_high_severity():
    f = Finding(organ="kidney", composition="cystic", enhancing_nodule=True, stated_actions=[Action.IMAGING_SURVEILLANCE])
    c = concordance(f, classify(f))
    assert (c.status, c.severity) == ("under-call", "high")


def test_any_imaging_satisfies_imaging():
    f = Finding(organ="kidney", composition="cystic", wall_mm=3, stated_actions=[Action.CHARACTERIZATION_IMAGING])
    assert concordance(f, classify(f)).status == "concordant"
