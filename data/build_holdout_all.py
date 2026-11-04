"""Builds data/reports_holdout_all.json: 27 hand-written held-out reports for the seven organs added
after the first version (lung, liver, pancreas, thyroid, pituitary, brain, bone).

Written by hand, in my own wording, BEFORE the regex reader was extended to these organs, and never
used to tune the regex, the generator or the model. All reports are fictional. Gold labels describe
what a careful reader would extract; `expected_category` and `expected_status` are what I expect the
guideline engine to return, written before running it.

Usage:  python data/build_holdout_all.py
"""
import json
from pathlib import Path

NF, SURV, CHAR, REF, HORM = (
    "NO_FOLLOWUP", "IMAGING_SURVEILLANCE", "CHARACTERIZATION_IMAGING", "SPECIALIST_REFERRAL", "HORMONAL_WORKUP")


def f(organ, side, size, modality, expected, status, stated=(), **kw):
    d = {"organ": organ, "side": side, "size_cm": size, "modality": modality, "stated_actions": list(stated)}
    d.update(kw)
    return {"gold": d, "expected_category": expected, "expected_status": status}


REPORTS = [
    # ---------------- lung (Fleischner 2017)
    ("A01", """EXAM: CT chest with contrast.
INDICATION: 58-year-old man, 30 pack-year smoker, persistent cough.
FINDINGS:
Lungs: There is a 7 x 5 mm solid nodule in the right middle lobe. No consolidation or effusion.
Mediastinum: No lymphadenopathy.
IMPRESSION:
6 mm right middle lobe nodule. No follow-up required.""",
     [f("lung", "right", 0.7, "CT", "Solid nodule 6-8 mm (single)", "under-call", [NF], short_axis_cm=0.5,
        patient_risk="high")]),
    ("A02", """EXAM: CT abdomen and pelvis with contrast.
INDICATION: Never smoker. Right lower quadrant pain.
FINDINGS:
Lung bases: 4 mm solid nodule in the left lower lobe.
Appendix: Normal.
IMPRESSION:
1. No acute abdominal process.
2. Tiny left basal lung nodule; recommend chest CT in 12 months.""",
     [f("lung", "left", 0.4, "CT", "Solid nodule <6 mm (single)", "over-call", [SURV], patient_risk="low")]),
    ("A03", """EXAM: CT chest without contrast.
INDICATION: Dyspnoea.
FINDINGS:
Lungs: 16 mm part-solid nodule in the left upper lobe with an 8 mm solid component.
IMPRESSION:
Part-solid left upper lobe nodule. Short-interval CT in 3 months.""",
     [f("lung", "left", 1.6, "CT", "Part-solid nodule ≥6 mm, solid part ≥6 mm", "concordant", [SURV],
        nodule_type="part-solid", solid_component_mm=8)]),
    ("A04", """EXAM: CT chest with contrast.
INDICATION: Chest pain.
FINDINGS:
Lungs: Scattered ground-glass nodules in both upper lobes, the largest 9 mm on the right.
Heart: Normal size.
IMPRESSION:
Multiple ground-glass nodules, likely inflammatory. No follow-up.""",
     [f("lung", "right", 0.9, "CT", "Multiple subsolid nodules, one or more ≥6 mm", "under-call", [NF],
        nodule_type="ground-glass", multiple=True)]),
    # ---------------- liver (ACR 2017)
    ("A05", """EXAM: CT chest, abdomen and pelvis with contrast.
INDICATION: Staging, known colon cancer.
FINDINGS:
Liver: 7 mm hypoattenuating lesion in segment 8, too small to characterise.
Lungs: Clear.
IMPRESSION:
Subcentimetre liver lesion, likely a cyst. No further imaging.""",
     [f("liver", "unknown", 0.7, "CT", "Liver lesion <1 cm", "under-call", [NF], patient_risk="high",
        appearance="indeterminate")]),
    ("A06", """EXAM: CT abdomen with contrast.
INDICATION: Right upper quadrant pain.
FINDINGS:
Liver: 2.4 cm lesion in segment 6 with peripheral nodular enhancement and progressive centripetal fill-in, consistent with a haemangioma.
Gallbladder: Normal.
IMPRESSION:
Hepatic haemangioma. No follow-up.""",
     [f("liver", "unknown", 2.4, "CT", "Liver lesion with benign features", "concordant", [NF],
        appearance="benign")]),
    ("A07", """EXAM: CT abdomen with contrast.
INDICATION: Hepatitis C, abdominal discomfort.
FINDINGS:
Liver: 1.8 cm ill-defined, heterogeneously enhancing lesion in segment 4.
Spleen: Normal.
IMPRESSION:
Hepatic lesion, likely benign.""",
     [f("liver", "unknown", 1.8, "CT", "Liver lesion >1.5 cm with suspicious features", "under-call", [],
        patient_risk="high", appearance="suspicious")]),
    ("A08", """EXAM: MRI abdomen with gadolinium.
INDICATION: No history of malignancy or liver disease. Back pain.
FINDINGS:
Liver: 1.2 cm lesion in segment 7 showing uniform arterial hyperenhancement and isointensity on portal venous and delayed phases (flash-filling).
IMPRESSION:
Flash-filling liver lesion, likely benign. Recommend MRI liver in 6 months.""",
     [f("liver", "unknown", 1.2, "MRI", "Flash-filling liver lesion 1-1.5 cm", "over-call", [SURV],
        patient_risk="low", appearance="flash-filling")]),
    # ---------------- pancreas (ACR 2017)
    ("A09", """EXAM: CT abdomen with contrast.
INDICATION: 71-year-old woman. Abdominal pain.
FINDINGS:
Pancreas: 9 mm simple-appearing cyst in the pancreatic body. Main duct is not dilated (2 mm).
IMPRESSION:
Small pancreatic cyst, likely side-branch IPMN. Follow-up MRI in 2 years.""",
     [f("pancreas", "unknown", 0.9, "CT", "Pancreatic cyst <1.5 cm", "concordant", [SURV], patient_age=71,
        duct_mm=2, composition="cystic")]),
    ("A10", """EXAM: CT abdomen with contrast.
INDICATION: 64-year-old man. Weight loss.
FINDINGS:
Pancreas: 2.8 cm cystic lesion in the pancreatic head with a 5 mm enhancing mural nodule. Main pancreatic duct 4 mm.
IMPRESSION:
Pancreatic head cyst. Follow-up MRI in 12 months.""",
     [f("pancreas", "unknown", 2.8, "CT", "Pancreatic cyst with high-risk stigmata", "under-call", [SURV],
        patient_age=64, duct_mm=4, enhancing_nodule=True, composition="cystic")]),
    ("A11", """EXAM: MRI abdomen with and without contrast.
INDICATION: 55-year-old woman. Incidental finding on ultrasound.
FINDINGS:
Pancreas: 3.4 cm unilocular cyst in the tail. No mural nodule; the main duct measures 3 mm.
IMPRESSION:
Pancreatic tail cyst. Recommend EUS with fine-needle aspiration.""",
     [f("pancreas", "unknown", 3.4, "MRI", "Pancreatic cyst ≥3 cm", "concordant", [REF], patient_age=55,
        duct_mm=3, composition="cystic")]),
    ("A12", """EXAM: CT abdomen with contrast.
INDICATION: 84-year-old man. Fall.
FINDINGS:
Pancreas: 1.6 cm cyst in the uncinate process.
Bones: No fracture.
IMPRESSION:
Pancreatic cyst; given the patient's age, no further imaging is recommended.""",
     [f("pancreas", "unknown", 1.6, "CT", "Pancreatic cyst, patient ≥80", "concordant", [NF], patient_age=84,
        composition="cystic")]),
    # ---------------- thyroid (ACR 2015)
    ("A13", """EXAM: CT neck with contrast.
INDICATION: 29-year-old woman. Neck pain after a fall.
FINDINGS:
Thyroid: 1.2 cm hypodense nodule in the left lobe.
Airway: Patent.
IMPRESSION:
Left thyroid nodule. No further evaluation needed.""",
     [f("thyroid", "left", 1.2, "CT", "Thyroid nodule ≥1 cm, age <35", "under-call", [NF], patient_age=29)]),
    ("A14", """EXAM: CT chest with contrast.
INDICATION: 62-year-old man. Cough.
FINDINGS:
Thyroid: 1.1 cm nodule in the right lobe.
Lungs: Clear.
IMPRESSION:
Incidental right thyroid nodule; recommend thyroid ultrasound.""",
     [f("thyroid", "right", 1.1, "CT", "Thyroid nodule <1.5 cm, age ≥35", "over-call", [CHAR], patient_age=62)]),
    ("A15", """EXAM: FDG PET-CT skull base to mid-thigh.
INDICATION: 67-year-old woman. Lymphoma staging.
FINDINGS:
Thyroid: 1.4 cm nodule in the right lobe with intense focal FDG uptake (SUVmax 9.2).
IMPRESSION:
FDG-avid right thyroid nodule. Recommend thyroid ultrasound and FNA.""",
     [f("thyroid", "right", 1.4, "PET-CT", "FDG-avid thyroid nodule", "concordant", [CHAR, REF], patient_age=67,
        fdg_avid=True)]),
    ("A16", """EXAM: CT neck with contrast.
INDICATION: 45-year-old man. Hoarseness.
FINDINGS:
Thyroid: 2.6 cm left thyroid nodule with extrathyroidal extension and enlarged level IV lymph nodes.
IMPRESSION:
Left thyroid mass with suspicious nodes. Recommend thyroid ultrasound with FNA.""",
     [f("thyroid", "left", 2.6, "CT", "Thyroid nodule with suspicious features", "concordant", [CHAR, REF],
        patient_age=45, appearance="suspicious")]),
    # ---------------- pituitary (Endocrine Society 2011)
    ("A17", """EXAM: MRI pituitary with and without gadolinium.
INDICATION: Headache.
FINDINGS:
Sella: 6 mm hypoenhancing lesion in the left side of the adenohypophysis, consistent with a microadenoma. The stalk is midline.
IMPRESSION:
Pituitary microadenoma. Repeat MRI in 12 months.""",
     [f("pituitary", "unknown", 0.6, "MRI", "Pituitary microincidentaloma (<1 cm)", "under-call", [SURV])]),
    ("A18", """EXAM: MRI brain with contrast.
INDICATION: Dizziness.
FINDINGS:
Sella: 1.8 cm sellar and suprasellar mass elevating and compressing the optic chiasm.
Brain: No infarct.
IMPRESSION:
Pituitary macroadenoma compressing the chiasm. Recommend neurosurgical referral, visual field testing and pituitary hormone evaluation.""",
     [f("pituitary", "unknown", 1.8, "MRI", "Pituitary lesion abutting/compressing the chiasm", "concordant",
        [REF, HORM], chiasm_contact=True)]),
    ("A19", """EXAM: CT head without contrast.
INDICATION: Minor head injury.
FINDINGS:
Sella: Incidental 1.3 cm sellar mass, likely a pituitary macroadenoma; no suprasellar extension.
IMPRESSION:
Probable pituitary macroadenoma. Recommend dedicated pituitary MRI and endocrine evaluation.""",
     [f("pituitary", "unknown", 1.3, "CT", "Pituitary macroincidentaloma (≥1 cm)", "concordant", [CHAR, HORM])]),
    # ---------------- brain / meningioma (EANO 2021)
    ("A20", """EXAM: MRI brain with gadolinium.
INDICATION: Migraine.
FINDINGS:
Brain: 1.4 cm extra-axial, dural-based enhancing lesion along the right frontal convexity with a dural tail, in keeping with a meningioma. No oedema.
IMPRESSION:
Small right frontal meningioma. No follow-up required.""",
     [f("brain", "right", 1.4, "MRI", "Incidental asymptomatic meningioma", "under-call", [NF])]),
    ("A21", """EXAM: MRI brain with gadolinium.
INDICATION: Follow-up of known meningioma.
COMPARISON: MRI 2 years ago.
FINDINGS:
Brain: The left parasagittal meningioma now measures 3.1 cm, previously 2.4 cm.
IMPRESSION:
Interval growth of left parasagittal meningioma. Follow-up MRI in 12 months.""",
     [f("brain", "left", 3.1, "MRI", "Growing or symptomatic meningioma", "under-call", [SURV], growth=True)]),
    ("A22", """EXAM: CT head without contrast.
INDICATION: Fall.
FINDINGS:
Brain: 2.0 cm calcified extra-axial mass along the falx, likely a meningioma. No haemorrhage.
IMPRESSION:
Probable falcine meningioma. Recommend MRI with contrast.""",
     [f("brain", "unknown", 2.0, "CT", "Incidental asymptomatic meningioma", "concordant", [CHAR])]),
    # ---------------- bone (Bone-RADS 2022)
    ("A23", """EXAM: CT abdomen and pelvis without contrast.
INDICATION: Flank pain.
FINDINGS:
Bones: 1.1 cm sclerotic focus in the left iliac bone measuring 1050 HU, consistent with a bone island.
Kidneys: No stones.
IMPRESSION:
Bone island. No follow-up.""",
     [f("bone", "left", 1.1, "CT", "Bone-RADS 1", "concordant", [NF], bone_density="sclerotic",
        unenhanced_hu=1050)]),
    ("A24", """EXAM: CT chest with contrast.
INDICATION: Known breast cancer, staging.
FINDINGS:
Bones: 1.5 cm lytic lesion in the T8 vertebral body without cortical breach.
IMPRESSION:
Indeterminate lytic T8 lesion. No follow-up.""",
     [f("bone", "unknown", 1.5, "CT", "Bone-RADS 2/3 (known cancer)", "under-call", [NF], bone_density="lucent",
        patient_risk="high")]),
    ("A25", """EXAM: CT pelvis without contrast.
INDICATION: Hip pain.
FINDINGS:
Bones: 3.2 cm lytic lesion in the right proximal femur with endosteal scalloping and cortical breakthrough.
IMPRESSION:
Lytic femoral lesion. Follow-up CT in 6 months.""",
     [f("bone", "right", 3.2, "CT", "Bone-RADS 4", "under-call", [SURV], bone_density="lucent",
        appearance="suspicious")]),
    ("A26", """EXAM: MRI lumbar spine without contrast.
INDICATION: Back pain.
FINDINGS:
Bones: 1.2 cm lesion in the L2 vertebral body, hyperintense on T1 and T2 and following fat signal on all sequences, consistent with a typical haemangioma.
Discs: Mild degeneration at L4-5.
IMPRESSION:
Vertebral haemangioma; no further imaging required.""",
     [f("bone", "unknown", 1.2, "MRI", "Bone-RADS 1", "concordant", [NF], appearance="benign")]),
    # ---------------- two organs in one report
    ("A27", """EXAM: CT chest with contrast.
INDICATION: 52-year-old woman. Shortness of breath.
FINDINGS:
Lungs: 3 mm solid nodule in the right upper lobe.
Thyroid: 0.8 cm nodule in the left lobe.
IMPRESSION:
1. Tiny right upper lobe nodule, no follow-up needed.
2. Subcentimetre left thyroid nodule, no further workup.""",
     [f("lung", "right", 0.3, "CT", "Solid nodule <6 mm (single)", "concordant", [NF]),
      f("thyroid", "left", 0.8, "CT", "Thyroid nodule <1.5 cm, age ≥35", "concordant", [NF], patient_age=52)]),
]


def main():
    out = [{"id": rid, "text": text, "findings": finds} for rid, text, finds in REPORTS]
    path = Path(__file__).resolve().parent / "reports_holdout_all.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(out)} reports, {sum(len(r['findings']) for r in out)} lesions -> {path.name}")


if __name__ == "__main__":
    main()
