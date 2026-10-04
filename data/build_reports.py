"""Builds data/reports.json: 30 synthetic CT reports with hand-written gold labels.

All reports are fictional and written for this project. Gold labels describe what a careful
reader would extract; `expected_category` is the guideline category the author expects.
"""
import json
from pathlib import Path

K, A = "kidney", "adrenal"
NF, SURV, CHAR, REF, HORM = (
    "NO_FOLLOWUP", "IMAGING_SURVEILLANCE", "CHARACTERIZATION_IMAGING", "SPECIALIST_REFERRAL", "HORMONAL_WORKUP")


def f(organ, side, size, expected, stated=(), **kw):
    d = {"organ": organ, "side": side, "size_cm": size, "stated_actions": list(stated)}
    d.update(kw)
    return {"gold": d, "expected_category": expected}


REPORTS = [
    ("R01", """EXAM: CT abdomen and pelvis with IV contrast (portal venous phase).
INDICATION: Right lower quadrant pain.
FINDINGS:
Kidneys: 2.1 cm homogeneous lesion in the right kidney interpolar region measuring 8 HU, with an imperceptible wall and no septa or calcification. Left kidney unremarkable.
Adrenals: Normal.
Appendix: Normal.
IMPRESSION:
1. No acute abnormality.
2. Simple right renal cyst (Bosniak I). No follow-up needed.""",
     [f(K, "right", 2.1, "Bosniak I", [NF], composition="cystic", enhanced_hu=8, homogeneous=True, reported_category="Bosniak I")]),

    ("R02", """EXAM: CT abdomen with IV contrast, portal venous phase.
INDICATION: Weight loss.
FINDINGS:
Kidneys: Left kidney lower pole cystic lesion measuring 3.4 cm with two thin (1 mm) septa and thin peripheral calcification. No enhancing soft tissue. Right kidney normal.
Adrenals: Normal.
IMPRESSION:
Left renal cyst, Bosniak II. No follow-up imaging required.""",
     [f(K, "left", 3.4, "Bosniak II", [NF], composition="cystic", septa_count=2, septa_mm=1, reported_category="Bosniak II")]),

    ("R03", """EXAM: CT chest, abdomen and pelvis with contrast.
INDICATION: Lymphoma staging, follow-up.
FINDINGS:
Abdomen: Right kidney upper pole cystic lesion measuring 4.2 cm with a smooth, minimally thickened 3 mm enhancing wall. No septa or nodularity. Left kidney normal. Adrenal glands normal.
IMPRESSION:
1. No evidence of lymphoma recurrence.
2. Right renal complex cyst, likely benign.""",
     [f(K, "right", 4.2, "Bosniak IIF", [], composition="cystic", wall_mm=3)]),

    ("R04", """EXAM: CT abdomen/pelvis with IV contrast.
INDICATION: Diverticulitis.
FINDINGS:
Kidneys: 2.8 cm cystic lesion in the left kidney containing multiple (5) thin, smooth enhancing septa, each less than 2 mm. No thickened wall or nodule.
Adrenals: Unremarkable.
IMPRESSION:
1. Uncomplicated sigmoid diverticulitis.
2. Left renal cystic lesion, Bosniak IIF. Recommend follow-up CT or MRI in 6 months.""",
     [f(K, "left", 2.8, "Bosniak IIF", [SURV], composition="cystic", septa_count=5, septa_mm=2, reported_category="Bosniak IIF")]),

    ("R05", """EXAM: CT abdomen with and without contrast (renal mass protocol).
INDICATION: Hematuria.
FINDINGS:
Right kidney: 3.0 cm cystic lesion with an irregular, thick 5 mm enhancing septum. Left kidney normal.
Adrenals: Normal.
IMPRESSION:
Right renal cystic mass, Bosniak III. Urology referral recommended.""",
     [f(K, "right", 3.0, "Bosniak III", [REF], composition="cystic", septa_count=1, septa_mm=5,
        irregular_wall_or_septa=True, reported_category="Bosniak III")]),

    ("R06", """EXAM: CT abdomen and pelvis with IV contrast.
INDICATION: Abdominal pain.
FINDINGS:
Kidneys: Left kidney interpolar cystic lesion measuring 3.6 cm with an enhancing 7 mm mural nodule along the posterior wall. Right kidney normal.
Adrenals: Normal.
IMPRESSION:
Left renal cystic lesion. Recommend follow-up ultrasound in 12 months.""",
     [f(K, "left", 3.6, "Bosniak IV", [SURV], composition="cystic", enhancing_nodule=True)]),

    ("R07", """EXAM: CT abdomen, multiphase renal protocol.
INDICATION: Microscopic hematuria.
FINDINGS:
Right kidney: 2.4 cm solid mass in the lower pole measuring 35 HU on unenhanced images and 120 HU in the nephrographic phase. No macroscopic fat.
Left kidney and adrenals: Normal.
IMPRESSION:
Enhancing solid right renal mass, suspicious for renal cell carcinoma. Urology referral.""",
     [f(K, "right", 2.4, "Solid enhancing mass (suspicious for RCC)", [REF], composition="solid", unenhanced_hu=35, enhanced_hu=120)]),

    ("R08", """EXAM: CT abdomen with and without IV contrast.
INDICATION: Right upper quadrant pain.
FINDINGS:
Gallbladder: Multiple gallstones without wall thickening.
Kidneys: 1.9 cm exophytic solid lesion from the left upper pole measuring 28 HU pre-contrast and 95 HU post-contrast. Right kidney normal.
Adrenals: Normal.
IMPRESSION:
1. Cholelithiasis without cholecystitis.
2. Small left renal lesion, likely cyst.""",
     [f(K, "left", 1.9, "Solid enhancing mass (suspicious for RCC)", [], composition="solid", unenhanced_hu=28, enhanced_hu=95)]),

    ("R09", """EXAM: CT abdomen without contrast.
INDICATION: Flank pain, rule out stone.
FINDINGS:
Kidneys: No hydronephrosis or calculi. 1.6 cm lesion in the right kidney containing macroscopic fat (-45 HU), consistent with angiomyolipoma.
Adrenals: Normal.
IMPRESSION:
1. No urolithiasis.
2. Small right renal angiomyolipoma. No follow-up needed.""",
     [f(K, "right", 1.6, "Angiomyolipoma", [NF], macroscopic_fat=True, unenhanced_hu=-45)]),

    ("R10", """EXAM: CT abdomen and pelvis with contrast.
INDICATION: Trauma, motor vehicle collision.
FINDINGS:
No solid organ injury. Left kidney: 5.2 cm fat-containing lesion (-60 HU) in the lower pole without hemorrhage. Right kidney normal.
Adrenals: Normal.
IMPRESSION:
1. No traumatic injury.
2. Left renal angiomyolipoma. No further imaging.""",
     [f(K, "left", 5.2, "Angiomyolipoma ≥4 cm", [NF], macroscopic_fat=True, enhanced_hu=-60)]),

    ("R11", """EXAM: CT chest/abdomen with contrast.
INDICATION: Pulmonary nodule follow-up.
FINDINGS:
Upper abdomen: 0.6 cm hypodense lesion in the right kidney, too small to characterize. Adrenals normal.
IMPRESSION:
Stable 4 mm pulmonary nodule. Tiny right renal hypodensity, too small to characterize, likely cyst; no follow-up.""",
     [f(K, "right", 0.6, "Bosniak II (too small to characterize)", [NF], too_small_to_characterize=True)]),

    ("R12", """EXAM: CT abdomen with contrast.
INDICATION: Pancreatitis.
FINDINGS:
Pancreas: Mild peripancreatic stranding.
Kidneys: 0.7 cm hypodense left renal lesion too small to characterize.
Adrenals: Normal.
IMPRESSION:
1. Mild acute interstitial pancreatitis.
2. Subcentimeter left renal lesion. Recommend renal ultrasound to further evaluate.""",
     [f(K, "left", 0.7, "Bosniak II (too small to characterize)", [CHAR], too_small_to_characterize=True)]),

    ("R13", """EXAM: CT abdomen and pelvis with contrast, portal venous phase only.
INDICATION: Crohn disease flare.
FINDINGS:
Kidneys: 2.2 cm homogeneous lesion in the right kidney measuring 45 HU. No unenhanced images available.
Adrenals: Normal.
IMPRESSION:
1. Active terminal ileitis.
2. Indeterminate right renal lesion. Recommend renal mass protocol CT or MRI.""",
     [f(K, "right", 2.2, "Indeterminate renal mass", [CHAR], enhanced_hu=45, homogeneous=True)]),

    ("R14", """EXAM: CT abdomen with IV contrast (portal venous phase).
INDICATION: Nausea and vomiting.
FINDINGS:
Kidneys: 1.8 cm homogeneous left renal lesion measuring 52 HU.
Adrenals: Normal.
IMPRESSION:
1. No bowel obstruction.
2. Left renal lesion, likely hyperdense cyst.""",
     [f(K, "left", 1.8, "Indeterminate renal mass", [], enhanced_hu=52, homogeneous=True)]),

    ("R15", """EXAM: CT abdomen and pelvis without contrast (stone protocol).
INDICATION: Left flank pain.
FINDINGS:
Kidneys: 3 mm non-obstructing left lower pole calculus. 1.5 cm homogeneous right renal lesion measuring 78 HU.
Adrenals: Normal.
IMPRESSION:
1. Non-obstructing left nephrolithiasis.
2. Hyperdense right renal cyst, Bosniak II. No follow-up.""",
     [f(K, "right", 1.5, "Bosniak II (hyperattenuating)", [NF], composition="cystic", unenhanced_hu=78, homogeneous=True, reported_category="Bosniak II")]),

    ("R16", """EXAM: CT abdomen with contrast, portal venous phase.
INDICATION: Elevated liver enzymes.
FINDINGS:
Kidneys: 2.5 cm homogeneous right renal lesion measuring 26 HU, likely cyst.
Adrenals: Normal.
IMPRESSION:
1. Hepatic steatosis.
2. Right renal lesion, likely cyst. Recommend follow-up ultrasound in 6 months.""",
     [f(K, "right", 2.5, "Bosniak II", [SURV], composition="cystic", enhanced_hu=26, homogeneous=True)]),

    ("R17", """EXAM: CT abdomen without contrast.
INDICATION: Hematuria, stone protocol.
FINDINGS:
Kidneys: No calculi.
Adrenals: 2.1 cm homogeneous left adrenal nodule measuring 4 HU.
IMPRESSION:
Left adrenal nodule consistent with lipid-rich adenoma. No further imaging. Recommend biochemical evaluation for autonomous cortisol secretion (1 mg dexamethasone suppression test).""",
     [f(A, "left", 2.1, "Lipid-rich adenoma (benign imaging)", [NF, HORM], unenhanced_hu=4, homogeneous=True)]),

    ("R18", """EXAM: CT abdomen and pelvis without contrast.
INDICATION: Renal colic.
FINDINGS:
Kidneys: 4 mm obstructing right UVJ stone with mild hydronephrosis.
Adrenals: 1.8 cm right adrenal nodule measuring -2 HU.
IMPRESSION:
1. Obstructing right UVJ calculus.
2. Right adrenal adenoma, no follow-up.""",
     [f(A, "right", 1.8, "Lipid-rich adenoma (benign imaging)", [NF], unenhanced_hu=-2)]),

    ("R19", """EXAM: CT abdomen with contrast, portal venous phase.
INDICATION: Abdominal pain.
FINDINGS:
Adrenals: 2.6 cm homogeneous left adrenal nodule measuring 60 HU.
Kidneys: Normal.
IMPRESSION:
Indeterminate left adrenal nodule. Recommend dedicated adrenal protocol CT and endocrine evaluation.""",
     [f(A, "left", 2.6, "Indeterminate adrenal mass", [CHAR, HORM], enhanced_hu=60, homogeneous=True)]),

    ("R20", """EXAM: CT abdomen without and with contrast.
INDICATION: Back pain.
FINDINGS:
Adrenals: 4.8 cm heterogeneous right adrenal mass measuring 38 HU on unenhanced images.
Kidneys: Normal.
IMPRESSION:
Right adrenal mass. Recommend follow-up CT in 12 months.""",
     [f(A, "right", 4.8, "Indeterminate adrenal mass, ≥4 cm or heterogeneous", [SURV], unenhanced_hu=38, homogeneous=False)]),

    ("R21", """EXAM: CT abdomen with contrast.
INDICATION: Colitis.
FINDINGS:
Adrenals: 0.8 cm left adrenal nodule.
Kidneys: Normal.
IMPRESSION:
1. Mild colitis.
2. Subcentimeter left adrenal nodule, no follow-up.""",
     [f(A, "left", 0.8, "Sub-centimetre adrenal nodule", [NF])]),

    ("R22", """EXAM: CT abdomen with contrast.
INDICATION: Abdominal distension.
FINDINGS:
Adrenals: 3.2 cm right adrenal mass containing macroscopic fat (-80 HU), consistent with myelolipoma.
Kidneys: Normal.
IMPRESSION:
Right adrenal myelolipoma. No follow-up.""",
     [f(A, "right", 3.2, "Myelolipoma", [NF], macroscopic_fat=True, enhanced_hu=-80)]),

    ("R23", """EXAM: CT abdomen without contrast.
INDICATION: Constipation.
FINDINGS:
Adrenals: 1.4 cm homogeneous left adrenal nodule measuring 18 HU.
Kidneys: Normal.
IMPRESSION:
1. Moderate stool burden.
2. Left adrenal nodule.""",
     [f(A, "left", 1.4, "Indeterminate adrenal mass", [], unenhanced_hu=18, homogeneous=True)]),

    ("R24", """EXAM: CT abdomen without contrast.
INDICATION: Flank pain.
FINDINGS:
Adrenals: 1.2 cm left adrenal nodule measuring 6 HU.
Kidneys: No calculi.
IMPRESSION:
Left adrenal adenoma. Recommend follow-up CT in 12 months and hormonal workup.""",
     [f(A, "left", 1.2, "Lipid-rich adenoma (benign imaging)", [SURV, HORM], unenhanced_hu=6)]),

    ("R25", """EXAM: CT abdomen without contrast.
INDICATION: Flank pain.
FINDINGS:
Kidneys: 3.1 cm simple right renal cyst measuring 5 HU with no septa.
Adrenals: 2.4 cm homogeneous left adrenal nodule measuring 8 HU.
IMPRESSION:
1. Bosniak I right renal cyst, no follow-up.
2. Left adrenal adenoma; recommend 1 mg dexamethasone suppression test.""",
     [f(K, "right", 3.1, "Bosniak I", [NF], composition="cystic", unenhanced_hu=5, reported_category="Bosniak I"),
      f(A, "left", 2.4, "Lipid-rich adenoma (benign imaging)", [HORM], unenhanced_hu=8, homogeneous=True)]),

    ("R26", """EXAM: CT abdomen with and without contrast.
INDICATION: Anemia.
FINDINGS:
Kidneys: 2.0 cm solid left renal mass measuring 40 HU unenhanced and 130 HU after contrast.
Adrenals: 1.6 cm right adrenal nodule measuring 25 HU on unenhanced images.
IMPRESSION:
1. Left renal mass suspicious for renal cell carcinoma; urology referral.
2. Right adrenal nodule, likely adenoma.""",
     [f(K, "left", 2.0, "Solid enhancing mass (suspicious for RCC)", [REF], composition="solid", unenhanced_hu=40, enhanced_hu=130),
      f(A, "right", 1.6, "Indeterminate adrenal mass", [], unenhanced_hu=25)]),

    ("R27", """EXAM: CT abdomen and pelvis with contrast.
INDICATION: Pelvic pain.
FINDINGS:
Kidneys: 1.2 cm simple cyst in the right kidney measuring 3 HU. 3.8 cm cyst in the left kidney with a 3 mm thickened enhancing septum.
Adrenals: Normal.
IMPRESSION:
Bilateral renal cysts, benign. No follow-up.""",
     [f(K, "right", 1.2, "Bosniak I", [NF], composition="cystic", enhanced_hu=3),
      f(K, "left", 3.8, "Bosniak IIF", [NF], composition="cystic", septa_count=1, septa_mm=3)]),

    ("R28", """EXAM: CT abdomen and pelvis with contrast.
INDICATION: Abdominal pain.
FINDINGS:
Kidneys: Normal in size and enhancement. No masses or hydronephrosis.
Adrenals: Normal.
IMPRESSION:
No acute abnormality.""",
     []),

    ("R29", """EXAM: CT abdomen with contrast.
INDICATION: Gastroenteritis.
FINDINGS:
Kidneys: 2.7 cm right renal cystic lesion with a thin 2 mm wall and two thin septa.
Adrenals: Normal.
IMPRESSION:
Right renal cystic lesion, Bosniak IIF. Recommend follow-up imaging in 6 months.""",
     [f(K, "right", 2.7, "Bosniak II", [SURV], composition="cystic", wall_mm=2, septa_count=2, reported_category="Bosniak IIF")]),

    ("R30", """CT A/P w/wo contrast for hematuria.
Incidental 2.3cm enhancing solid lesion arising from the lower pole of the R kidney (32 HU pre / 110 HU post). L kidney and both adrenals unremarkable.
IMP: R renal lesion. Recommend dedicated renal MRI.""",
     [f(K, "right", 2.3, "Solid enhancing mass (suspicious for RCC)", [CHAR], composition="solid", unenhanced_hu=32, enhanced_hu=110)]),
]


def main():
    out = [{"id": rid, "text": text, "findings": findings} for rid, text, findings in REPORTS]
    path = Path(__file__).with_name("reports.json")
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {len(out)} reports, {sum(len(r['findings']) for r in out)} findings -> {path}")


if __name__ == "__main__":
    main()
