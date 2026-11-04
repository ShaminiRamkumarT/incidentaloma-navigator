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


# --- lung (Fleischner 2017) ---
def _lung(**kw):
    return Finding(organ="lung", **kw)


def _status(f):
    return concordance(f, classify(f)).status


def test_fleischner_solid_size_bands():
    assert classify(_lung(size_cm=0.5)).category == "Solid nodule <6 mm (single)"
    assert classify(_lung(size_cm=0.6)).category == "Solid nodule 6-8 mm (single)"
    assert classify(_lung(size_cm=0.8)).category == "Solid nodule 6-8 mm (single)"
    assert classify(_lung(size_cm=0.9)).category == "Solid nodule >8 mm (single)"


def test_fleischner_uses_mean_diameter():
    # 9 x 5 mm -> mean 7 mm -> 6-8 mm band, not >8 mm
    assert classify(_lung(size_cm=0.9, short_axis_cm=0.5)).category == "Solid nodule 6-8 mm (single)"


def test_small_solid_nodule_depends_on_risk():
    img = [Action.IMAGING_SURVEILLANCE]
    assert _status(_lung(size_cm=0.4, patient_risk="unknown", stated_actions=img)) == "concordant"
    assert _status(_lung(size_cm=0.4, patient_risk="unknown")) == "concordant"
    assert _status(_lung(size_cm=0.4, patient_risk="high", stated_actions=[Action.NO_FOLLOWUP])) == "concordant"
    assert _status(_lung(size_cm=0.4, patient_risk="low", stated_actions=img)) == "over-call"


def test_large_solid_nodule_without_followup_is_under_call():
    f = _lung(size_cm=1.2, stated_actions=[Action.NO_FOLLOWUP])
    assert _status(f) == "under-call"
    assert _status(_lung(size_cm=1.2, stated_actions=[Action.SPECIALIST_REFERRAL])) == "concordant"
    assert _status(_lung(size_cm=1.2, stated_actions=[Action.CHARACTERIZATION_IMAGING])) == "concordant"  # PET-CT


def test_subsolid_rules():
    assert classify(_lung(size_cm=0.5, nodule_type="ground-glass")).actions == [Action.NO_FOLLOWUP]
    assert classify(_lung(size_cm=0.7, nodule_type="ground-glass")).actions == [Action.IMAGING_SURVEILLANCE]
    assert classify(_lung(size_cm=0.4, nodule_type="ground-glass", multiple=True)).actions == [Action.IMAGING_SURVEILLANCE]
    f = _lung(size_cm=1.4, nodule_type="part-solid", solid_component_mm=7, stated_actions=[Action.SPECIALIST_REFERRAL])
    assert _status(f) == "concordant"
    f = _lung(size_cm=1.4, nodule_type="part-solid", solid_component_mm=3, stated_actions=[Action.NO_FOLLOWUP])
    assert _status(f) == "under-call"


def test_modality_defaults_to_ct():
    assert Finding(organ="lung").modality == "CT"


# --- liver (ACR 2017) ---
def _liver(**kw):
    return Finding(organ="liver", **kw)


def test_liver_benign_needs_no_workup_any_risk():
    for risk in ("low", "high", "unknown"):
        assert classify(_liver(size_cm=2.5, appearance="benign", patient_risk=risk)).actions == [Action.NO_FOLLOWUP]


def test_liver_small_lesion_depends_on_risk():
    assert classify(_liver(size_cm=0.7, patient_risk="low")).actions == [Action.NO_FOLLOWUP]
    assert classify(_liver(size_cm=0.7, patient_risk="high")).actions == [Action.IMAGING_SURVEILLANCE]
    f = _liver(size_cm=0.7, patient_risk="high", stated_actions=[Action.NO_FOLLOWUP])
    assert _status(f) == "under-call"
    f = _liver(size_cm=0.7, patient_risk="high", appearance="benign", stated_actions=[Action.NO_FOLLOWUP])
    assert _status(f) == "concordant"
    assert _status(_liver(size_cm=0.7, stated_actions=[Action.IMAGING_SURVEILLANCE])) == "concordant"


def test_liver_flash_filling():
    assert classify(_liver(size_cm=1.2, appearance="flash-filling", patient_risk="low")).actions == [Action.NO_FOLLOWUP]
    assert classify(_liver(size_cm=1.2, appearance="flash-filling", patient_risk="high")).actions == [Action.CHARACTERIZATION_IMAGING]
    assert classify(_liver(size_cm=2.0, appearance="flash-filling", patient_risk="low")).actions == [Action.CHARACTERIZATION_IMAGING]


def test_liver_suspicious_and_hu_derivation():
    assert classify(_liver(size_cm=1.3, appearance="suspicious", patient_risk="low")).actions == [Action.CHARACTERIZATION_IMAGING]
    assert classify(_liver(size_cm=2.0, enhanced_hu=45)).category == "Liver lesion >1.5 cm with suspicious features"
    assert classify(_liver(size_cm=2.0, enhanced_hu=12, homogeneous=True)).category == "Liver lesion with benign features"
    f = _liver(size_cm=3.0, appearance="suspicious", patient_risk="high", stated_actions=[Action.SPECIALIST_REFERRAL])
    assert _status(f) == "concordant"
    f = _liver(size_cm=3.0, appearance="suspicious", patient_risk="low", stated_actions=[Action.NO_FOLLOWUP])
    c = concordance(f, classify(f))
    assert c.status == "under-call"


def test_liver_pet_uptake_is_suspicious():
    g = classify(_liver(size_cm=1.8, modality="PET-CT", fdg_avid=True, appearance="benign"))
    assert g.actions == [Action.CHARACTERIZATION_IMAGING] and g.notes


# --- pancreas (ACR 2017) ---
def test_pancreas_rules():
    P = lambda **kw: Finding(organ="pancreas", **kw)
    assert classify(P(size_cm=1.0, patient_age=55)).actions == [Action.IMAGING_SURVEILLANCE]
    assert classify(P(size_cm=1.0, enhancing_nodule=True)).category == "Pancreatic cyst with high-risk stigmata"
    assert classify(P(size_cm=1.0, duct_mm=8)).category == "Pancreatic cyst with worrisome features"
    assert _status(P(size_cm=3.2, stated_actions=[Action.IMAGING_SURVEILLANCE])) == "concordant"
    assert _status(P(size_cm=2.0, stated_actions=[Action.SPECIALIST_REFERRAL])) == "concordant"
    assert _status(P(size_cm=1.2, patient_age=85, stated_actions=[Action.NO_FOLLOWUP])) == "concordant"
    c = concordance(P(size_cm=2.0, mural_nodule=True, stated_actions=[Action.IMAGING_SURVEILLANCE]),
                    classify(P(size_cm=2.0, mural_nodule=True)))
    assert (c.status, c.severity) == ("under-call", "high")


# --- thyroid (ACR 2015) ---
def test_thyroid_age_size_thresholds():
    T = lambda **kw: Finding(organ="thyroid", **kw)
    assert classify(T(size_cm=1.2, patient_age=30)).actions == [Action.CHARACTERIZATION_IMAGING]
    assert classify(T(size_cm=1.2, patient_age=50)).actions == [Action.NO_FOLLOWUP]
    assert classify(T(size_cm=1.5, patient_age=50)).actions == [Action.CHARACTERIZATION_IMAGING]
    assert classify(T(size_cm=0.8, modality="PET-CT", fdg_avid=True)).actions == [Action.CHARACTERIZATION_IMAGING]
    assert classify(T(size_cm=2.5, patient_age=88, limited_life_expectancy=True)).actions == [Action.NO_FOLLOWUP]
    assert classify(T(size_cm=0.8, appearance="suspicious", limited_life_expectancy=True)).actions == [Action.CHARACTERIZATION_IMAGING]
    assert _status(T(size_cm=1.2, stated_actions=[Action.CHARACTERIZATION_IMAGING])) == "concordant"


# --- pituitary (Endocrine Society 2011) and brain (EANO 2021) ---
def test_pituitary_needs_hormones():
    f = Finding(organ="pituitary", modality="MRI", size_cm=0.6, stated_actions=[Action.IMAGING_SURVEILLANCE])
    c = concordance(f, classify(f))
    assert (c.status, c.severity, c.missing) == ("under-call", "medium", [Action.HORMONAL_WORKUP])
    f = Finding(organ="pituitary", modality="MRI", size_cm=1.6, chiasm_contact=True)
    assert Action.SPECIALIST_REFERRAL in classify(f).actions


def test_meningioma():
    assert classify(Finding(organ="brain", modality="MRI", size_cm=1.5)).actions == [Action.IMAGING_SURVEILLANCE]
    assert classify(Finding(organ="brain", size_cm=3, growth=True)).actions == [Action.SPECIALIST_REFERRAL]


# --- bone (Bone-RADS) ---
def test_bone_rads():
    B = lambda **kw: Finding(organ="bone", **kw)
    assert classify(B(bone_density="sclerotic", unenhanced_hu=1100)).category == "Bone-RADS 1"
    assert classify(B(bone_density="lucent", unenhanced_hu=-40)).category == "Bone-RADS 1"
    assert classify(B(appearance="suspicious")).category == "Bone-RADS 4"
    assert classify(B(bone_density="sclerotic", unenhanced_hu=1100, patient_risk="high")).category == "Bone-RADS 2/3 (known cancer)"
    assert classify(B(bone_density="lucent", unenhanced_hu=40)).category == "Bone-RADS 3"
    assert _status(B(appearance="suspicious", stated_actions=[Action.IMAGING_SURVEILLANCE])) == "under-call"
