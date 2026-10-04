"""Builds data/reports_holdout.json: 16 synthetic reports written AFTER the regex extractor was
frozen, deliberately using phrasing it was not tuned on (mm sizes, 'Hounsfield units', unicode
minus signs, bilateral lesions in one sentence, reversed word order). Fictional data."""
import json
from pathlib import Path

from build_reports import A, CHAR, HORM, K, NF, REF, SURV, f

HOLDOUT = [
    ("H01", """EXAM: CT abdomen/pelvis with IV contrast.
INDICATION: Left lower quadrant pain.
FINDINGS:
There is a 31 mm cystic lesion in the left kidney with numerous thin septations. Adrenal glands unremarkable.
IMPRESSION:
Bosniak IIF left renal cyst. Recommend surveillance imaging at 6 and 12 months.""",
     [f(K, "left", 3.1, "Bosniak IIF", [SURV], composition="cystic", septa_count=4, reported_category="Bosniak IIF")]),

    ("H02", """EXAM: CT urogram (unenhanced, nephrographic and excretory phases).
INDICATION: Gross hematuria.
FINDINGS:
Right renal mass: 2.9 x 2.5 cm, heterogeneously enhancing, HU 30 (precontrast) and 105 (nephrographic).
IMPRESSION:
Concerning for renal cell carcinoma. Refer to urology.""",
     [f(K, "right", 2.9, "Solid enhancing mass (suspicious for RCC)", [REF], unenhanced_hu=30, enhanced_hu=105, homogeneous=False)]),

    ("H03", """EXAM: CT abdomen without contrast.
INDICATION: Hypertension, flank pain.
FINDINGS:
No renal masses or stones. Left adrenal: 2.3 cm nodule with attenuation of 7 Hounsfield units on noncontrast images.
IMPRESSION:
Left adrenal adenoma. Clinical correlation for hormonal hypersecretion recommended.""",
     [f(A, "left", 2.3, "Lipid-rich adenoma (benign imaging)", [HORM], unenhanced_hu=7)]),

    ("H04", """EXAM: CT abdomen with contrast.
INDICATION: Fever.
FINDINGS:
Exophytic 1.4 cm hyperdense lesion off the right kidney, 58 HU on venous phase only; cannot exclude solid lesion.
IMPRESSION:
Indeterminate right renal lesion; consider renal MRI for characterization.""",
     [f(K, "right", 1.4, "Indeterminate renal mass", [CHAR], enhanced_hu=58)]),

    ("H05", """EXAM: CT abdomen without and with contrast.
INDICATION: Abdominal fullness.
FINDINGS:
The left adrenal gland demonstrates a 4.4 cm homogeneous mass measuring 32 HU unenhanced.
IMPRESSION:
Large indeterminate left adrenal mass. Recommend endocrine surgery referral and biochemical work-up including plasma metanephrines.""",
     [f(A, "left", 4.4, "Indeterminate adrenal mass, ≥4 cm or heterogeneous", [REF, HORM], unenhanced_hu=32, homogeneous=True)]),

    ("H06", """EXAM: CT abdomen with contrast.
INDICATION: Epigastric pain.
FINDINGS:
Simple-appearing 5.5 cm cyst, upper pole left kidney, fluid attenuation, no septations.
IMPRESSION:
Benign left renal cyst. Recommend follow-up ultrasound in one year.""",
     [f(K, "left", 5.5, "Bosniak I", [SURV], composition="cystic")]),

    ("H07", """EXAM: CT abdomen without contrast.
INDICATION: Back pain.
FINDINGS:
Kidneys: 2.2 cm right interpolar lesion with internal macroscopic fat consistent with AML.
Adrenals: 1.1 cm left adrenal nodule, 22 HU.
IMPRESSION:
1. Right renal AML.
2. Indeterminate 1.1 cm left adrenal nodule; adrenal washout CT recommended.""",
     [f(K, "right", 2.2, "Angiomyolipoma", [], macroscopic_fat=True),
      f(A, "left", 1.1, "Indeterminate adrenal mass", [CHAR], unenhanced_hu=22)]),

    ("H08", """EXAM: CT abdomen, renal mass protocol.
INDICATION: Follow-up of complex cyst.
FINDINGS:
4.0 cm right renal cystic mass with a nodular enhancing soft tissue component measuring 9 mm.
IMPRESSION:
Right renal cystic mass with enhancing nodular component, Bosniak IV. Urologic consultation advised.""",
     [f(K, "right", 4.0, "Bosniak IV", [REF], composition="cystic", enhancing_nodule=True, reported_category="Bosniak IV")]),

    ("H09", """EXAM: CT chest with contrast.
INDICATION: Cough.
FINDINGS:
Lungs clear. Upper abdomen: partially imaged 1.7 cm hypoattenuating right adrenal nodule (Hounsfield units 41, contrast-enhanced).
IMPRESSION:
No acute cardiopulmonary process.""",
     [f(A, "right", 1.7, "Indeterminate adrenal mass", [], enhanced_hu=41)]),

    ("H10", """EXAM: CT abdomen and pelvis with contrast.
INDICATION: Urinary tract infection.
FINDINGS:
Kidneys: 3.3 cm left renal cyst with a 4 mm irregular enhancing wall.
IMPRESSION:
Complex left renal cyst; recommend follow-up CT in 6 months.""",
     [f(K, "left", 3.3, "Bosniak III", [SURV], composition="cystic", wall_mm=4, irregular_wall_or_septa=True)]),

    ("H11", """EXAM: CT abdomen with contrast.
INDICATION: Abdominal pain.
FINDINGS:
Several subcentimeter hypodensities in both kidneys, too small to characterize.
IMPRESSION:
No follow-up needed for tiny renal hypodensities.""",
     [f(K, "unknown", None, "Bosniak II (too small to characterize)", [NF], too_small_to_characterize=True)]),

    ("H12", """EXAM: CT abdomen with contrast, portal venous phase.
INDICATION: Weight loss.
FINDINGS:
Adrenals: 3.0 cm right adrenal mass with heterogeneous enhancement, 85 HU. No unenhanced images.
IMPRESSION:
Right adrenal mass, likely adenoma. No further follow up.""",
     [f(A, "right", 3.0, "Indeterminate adrenal mass, ≥4 cm or heterogeneous", [NF], enhanced_hu=85, homogeneous=False)]),

    ("H13", """EXAM: CT abdomen without and with contrast.
INDICATION: Hematuria.
FINDINGS:
8 mm enhancing solid nodule in the left kidney (25 HU unenhanced, 90 HU nephrographic).
IMPRESSION:
Tiny enhancing left renal nodule; recommend follow-up renal mass protocol CT in 6-12 months.""",
     [f(K, "left", 0.8, "Solid enhancing mass <1 cm", [SURV], composition="solid", unenhanced_hu=25, enhanced_hu=90)]),

    ("H14", """EXAM: CT abdomen without contrast.
INDICATION: Flank pain.
FINDINGS:
Bilateral adrenal nodules: right 1.5 cm (−5 HU), left 2.0 cm (3 HU).
IMPRESSION:
Bilateral adrenal adenomas. Recommend 1 mg overnight dexamethasone suppression test.""",
     [f(A, "right", 1.5, "Lipid-rich adenoma (benign imaging)", [HORM], unenhanced_hu=-5),
      f(A, "left", 2.0, "Lipid-rich adenoma (benign imaging)", [HORM], unenhanced_hu=3)]),

    ("H15", """EXAM: CT abdomen with contrast.
INDICATION: Surveillance after left nephrectomy.
FINDINGS:
Kidneys: Status post left nephrectomy. Right kidney normal without masses.
Adrenals: No nodules.
IMPRESSION:
No evidence of recurrence.""",
     []),

    ("H16", """EXAM: CT abdomen with contrast.
INDICATION: Pain.
FINDINGS:
2.0 cm left renal cyst with one thin septum and a fleck of calcification.
IMPRESSION:
Minimally complex left renal cyst (Bosniak IIF). Follow-up CT in 6 months recommended.""",
     [f(K, "left", 2.0, "Bosniak II", [SURV], composition="cystic", septa_count=1, reported_category="Bosniak IIF")]),
]


def main():
    out = [{"id": rid, "text": text, "findings": fs} for rid, text, fs in HOLDOUT]
    path = Path(__file__).with_name("reports_holdout.json")
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {len(out)} reports, {sum(len(r['findings']) for r in out)} findings -> {path}")


if __name__ == "__main__":
    main()
