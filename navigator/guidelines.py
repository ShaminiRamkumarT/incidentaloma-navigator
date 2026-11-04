"""Deterministic guideline engine for incidental findings on CT, MRI and PET-CT.

Simplified, educational encodings of:
  * Bosniak classification v2019 [1]
  * ACR Incidental Findings Committee white paper on renal masses [2]
  * ESE/ENSAT guideline on adrenal incidentalomas [3]
  * Fleischner Society 2017 guideline on incidental pulmonary nodules [4]
  * ACR Incidental Findings Committee white paper on liver lesions [5]
  * ACR Incidental Findings Committee white paper on pancreatic cysts [6]
  * ACR Incidental Thyroid Findings Committee white paper [7]
  * Endocrine Society guideline on pituitary incidentaloma [8]
  * EANO guideline on meningiomas [9]
  * Society of Skeletal Radiology Bone-RADS white paper [10]

Sources:
  1. Silverman SG, Pedrosa I, Ellis JH, et al. Bosniak Classification of Cystic
     Renal Masses, Version 2019: An Update Proposal and Needs Assessment.
     Radiology. 2019;292(2):475-488. doi:10.1148/radiol.2019182646
  2. Herts BR, Silverman SG, Hindman NM, et al. Management of the Incidental
     Renal Mass on CT: A White Paper of the ACR Incidental Findings Committee.
     J Am Coll Radiol. 2018;15(2):264-273. doi:10.1016/j.jacr.2017.04.028
  3. Fassnacht M, Tsagarakis S, Terzolo M, et al. European Society of
     Endocrinology clinical practice guidelines on the management of adrenal
     incidentalomas, in collaboration with the European Network for the Study
     of Adrenal Tumors. Eur J Endocrinol. 2023;189(1):G1-G42.
     doi:10.1093/ejendo/lvad066
  4. MacMahon H, Naidich DP, Goo JM, et al. Guidelines for Management of
     Incidental Pulmonary Nodules Detected on CT Images: From the Fleischner
     Society 2017. Radiology. 2017;284(1):228-243. doi:10.1148/radiol.2017161659
  5. Gore RM, Pickhardt PJ, Mortele KJ, et al. Management of Incidental Liver
     Lesions on CT: A White Paper of the ACR Incidental Findings Committee.
     J Am Coll Radiol. 2017;14(11):1429-1437. doi:10.1016/j.jacr.2017.07.018
  6. Megibow AJ, Baker ME, Morgan DE, et al. Management of Incidental
     Pancreatic Cysts: A White Paper of the ACR Incidental Findings Committee.
     J Am Coll Radiol. 2017;14(7):911-923. doi:10.1016/j.jacr.2017.03.010
  7. Hoang JK, Langer JE, Middleton WD, et al. Managing Incidental Thyroid
     Nodules Detected on Imaging: White Paper of the ACR Incidental Thyroid
     Findings Committee. J Am Coll Radiol. 2015;12(2):143-150.
     doi:10.1016/j.jacr.2014.09.038
  8. Freda PU, Beckers AM, Katznelson L, et al. Pituitary Incidentaloma: An
     Endocrine Society Clinical Practice Guideline. J Clin Endocrinol Metab.
     2011;96(4):894-904. doi:10.1210/jc.2010-1048
  9. Goldbrunner R, Stavrinou P, Jenkinson MD, et al. EANO guideline on the
     diagnosis and management of meningiomas. Neuro Oncol. 2021;23(11):1821-1834.
     doi:10.1093/neuonc/noab150
  10. Chang CY, Garner HW, Ahlawat S, et al. Society of Skeletal Radiology -
     white paper. Guidelines for the diagnostic management of incidental solitary
     bone lesions on CT and MRI in adults: bone reporting and data system
     (Bone-RADS). Skeletal Radiol. 2022;51(9):1743-1764.
     doi:10.1007/s00256-022-04022-8

NOT a medical device and not for clinical use. Thresholds are simplified; see README.
"""
from dataclasses import dataclass, field
from typing import List

from .schema import Action, Finding

BOSNIAK = "Bosniak v2019 (Radiology 2019)"
ACR_RENAL = "ACR renal mass white paper (JACR 2018)"
ESE = "ESE/ENSAT adrenal incidentaloma guideline (EJE 2023)"
FLEISCHNER = "Fleischner Society 2017 (Radiology 2017)"
ACR_LIVER = "ACR liver lesion white paper (JACR 2017)"
ACR_PANCREAS = "ACR pancreatic cyst white paper (JACR 2017)"
ACR_THYROID = "ACR incidental thyroid nodule white paper (JACR 2015)"
ES_PITUITARY = "Endocrine Society pituitary incidentaloma guideline (JCEM 2011)"
EANO = "EANO meningioma guideline (Neuro-Oncology 2021)"
BONE_RADS = "Bone-RADS, Society of Skeletal Radiology (Skeletal Radiol 2022)"

NONE_, FU, CHAR, REF, HORM = ([Action.NO_FOLLOWUP], [Action.IMAGING_SURVEILLANCE], [Action.CHARACTERIZATION_IMAGING],
                              [Action.SPECIALIST_REFERRAL], [Action.HORMONAL_WORKUP])


@dataclass
class GuidelineResult:
    category: str
    actions: List[Action]
    rationale: str
    source: str
    notes: List[str] = field(default_factory=list)
    # Other recommendations the guideline also accepts (e.g. "optional CT at 12 months",
    # or risk-dependent advice when the report does not state the patient's risk).
    alternatives: List[List[Action]] = field(default_factory=list)


def _fluid(hu):
    return hu is not None and -9 <= hu <= 20


def classify_renal(f: Finding) -> GuidelineResult:
    enh = f.enhancement_hu
    size = f.size_cm

    if f.macroscopic_fat:
        if size is not None and size >= 4:
            return GuidelineResult(
                "Angiomyolipoma ≥4 cm", [Action.SPECIALIST_REFERRAL],
                "Macroscopic fat indicates angiomyolipoma; ≥4 cm carries haemorrhage risk, so urology review is advised.",
                ACR_RENAL)
        return GuidelineResult(
            "Angiomyolipoma", [Action.NO_FOLLOWUP],
            "Macroscopic fat without calcification indicates a benign angiomyolipoma.", ACR_RENAL)

    if f.composition == "cystic":
        if f.enhancing_nodule:
            return GuidelineResult(
                "Bosniak IV", [Action.SPECIALIST_REFERRAL],
                "Enhancing nodule in a cystic mass (~90% malignant): urology referral.", BOSNIAK)
        thick = max([x for x in (f.wall_mm, f.septa_mm) if x is not None], default=None)
        if f.irregular_wall_or_septa or (thick is not None and thick >= 4):
            return GuidelineResult(
                "Bosniak III", [Action.SPECIALIST_REFERRAL],
                "Thick (≥4 mm) or irregular enhancing wall/septa (~50% malignant): urology referral.", BOSNIAK)
        if (thick is not None and thick >= 3) or (f.septa_count or 0) >= 4:
            return GuidelineResult(
                "Bosniak IIF", [Action.IMAGING_SURVEILLANCE],
                "Minimally thickened (3 mm) wall/septa or ≥4 thin septa: imaging at 6 and 12 months, then yearly to 5 years.",
                BOSNIAK)
        if 1 <= (f.septa_count or 0) <= 3:
            return GuidelineResult(
                "Bosniak II", [Action.NO_FOLLOWUP], "Few (1-3) thin septa: benign, no follow-up.", BOSNIAK)
        hu = f.enhanced_hu if f.enhanced_hu is not None else f.unenhanced_hu
        if hu is None or _fluid(hu):
            return GuidelineResult(
                "Bosniak I", [Action.NO_FOLLOWUP],
                "Thin smooth wall, no septa, simple fluid attenuation: benign, no follow-up.", BOSNIAK)
        # cyst described but attenuation not simple fluid: fall through to homogeneous-mass rules

    if f.too_small_to_characterize:
        return GuidelineResult(
            "Bosniak II (too small to characterize)", [Action.NO_FOLLOWUP],
            "Homogeneous low-attenuation lesion too small to characterize: presumed benign.", BOSNIAK)

    solid_enhancing = enh is not None and enh >= 20
    if f.composition == "solid" or solid_enhancing:
        if solid_enhancing:
            if size is not None and size < 1:
                return GuidelineResult(
                    "Solid enhancing mass <1 cm", [Action.IMAGING_SURVEILLANCE],
                    "Very small enhancing solid mass: follow-up imaging is a reasonable option.", ACR_RENAL,
                    ["Simplified from the ACR flowchart; urology referral is also acceptable."])
            return GuidelineResult(
                "Solid enhancing mass (suspicious for RCC)", [Action.SPECIALIST_REFERRAL],
                "Enhancement ≥20 HU without macroscopic fat: suspicious for renal cell carcinoma, urology referral.",
                ACR_RENAL)
        if enh is None:
            return GuidelineResult(
                "Solid mass, enhancement not assessed", [Action.CHARACTERIZATION_IMAGING],
                "Solid-appearing mass without pre- and post-contrast measurements: renal mass protocol CT or MRI.",
                ACR_RENAL)

    if f.homogeneous is not False:
        if f.unenhanced_hu is not None and f.unenhanced_hu >= 70:
            return GuidelineResult("Bosniak II (hyperattenuating)", [Action.NO_FOLLOWUP],
                                   "Homogeneous ≥70 HU on non-contrast CT: benign hyperdense cyst.", BOSNIAK)
        if enh is not None and enh < 10 and (f.unenhanced_hu or 0) > 20:
            return GuidelineResult("Bosniak II (non-enhancing)", [Action.NO_FOLLOWUP],
                                   "Homogeneous, >20 HU and non-enhancing on renal mass protocol CT.", BOSNIAK)
        if f.enhanced_hu is None and _fluid(f.unenhanced_hu):
            return GuidelineResult("Bosniak II", [Action.NO_FOLLOWUP],
                                   "Homogeneous -9 to 20 HU on non-contrast CT: benign.", BOSNIAK)
        if f.unenhanced_hu is None and f.enhanced_hu is not None:
            if _fluid(f.enhanced_hu):
                return GuidelineResult("Bosniak I/II (fluid attenuation)", [Action.NO_FOLLOWUP],
                                       "Homogeneous fluid attenuation on post-contrast CT: benign.", BOSNIAK)
            if 21 <= f.enhanced_hu <= 30:
                return GuidelineResult("Bosniak II", [Action.NO_FOLLOWUP],
                                       "Homogeneous 21-30 HU on portal venous phase: benign.", BOSNIAK)

    return GuidelineResult(
        "Indeterminate renal mass", [Action.CHARACTERIZATION_IMAGING],
        "Cannot be classified from available phases: renal mass protocol CT or MRI.", BOSNIAK)


def classify_adrenal(f: Finding) -> GuidelineResult:
    size = f.size_cm
    if size is not None and size < 1:
        return GuidelineResult("Sub-centimetre adrenal nodule", [Action.NO_FOLLOWUP],
                               "Guideline applies to masses ≥1 cm; no work-up needed.", ESE)
    if f.macroscopic_fat:
        return GuidelineResult("Myelolipoma", [Action.NO_FOLLOWUP],
                               "Macroscopic fat indicates a benign myelolipoma.", ESE)
    if f.unenhanced_hu is not None and f.unenhanced_hu <= 10 and f.homogeneous is not False:
        return GuidelineResult(
            "Lipid-rich adenoma (benign imaging)", [Action.HORMONAL_WORKUP],
            "Homogeneous ≤10 HU on non-contrast CT: benign, no further imaging; every patient still needs a "
            "1 mg dexamethasone suppression test (plus aldosterone/renin if hypertensive or hypokalaemic).", ESE)
    large_or_heterogeneous = (size is not None and size >= 4) or f.homogeneous is False
    if large_or_heterogeneous:
        return GuidelineResult(
            "Indeterminate adrenal mass, ≥4 cm or heterogeneous", [Action.SPECIALIST_REFERRAL, Action.HORMONAL_WORKUP],
            "Indeterminate mass that is large or heterogeneous: discuss in an expert multidisciplinary team "
            "(surgery usually considered) and complete hormonal work-up including metanephrines.", ESE)
    why = ("No non-contrast attenuation available" if f.unenhanced_hu is None
           else f"{f.unenhanced_hu:g} HU on non-contrast CT (>10 HU)")
    return GuidelineResult(
        "Indeterminate adrenal mass", [Action.CHARACTERIZATION_IMAGING, Action.HORMONAL_WORKUP],
        f"{why}: further imaging (non-contrast/washout CT or chemical-shift MRI) or repeat imaging in 6-12 months, "
        "plus hormonal work-up including metanephrines.", ESE)


def _nodule_mm(f: Finding):
    """Fleischner size: mean of long and short axis, rounded to the nearest mm."""
    if f.size_cm is None:
        return None
    if f.short_axis_cm is not None:
        return round((f.size_cm + f.short_axis_cm) / 2 * 10)
    return round(f.size_cm * 10)


def classify_lung(f: Finding) -> GuidelineResult:
    """Fleischner 2017, adults >=35 with an incidental nodule (not screening, known cancer or immunosuppression)."""
    mm = _nodule_mm(f)
    none_, img, ref = [Action.NO_FOLLOWUP], [Action.IMAGING_SURVEILLANCE], [Action.SPECIALIST_REFERRAL]
    n = "multiple" if f.multiple else "single"
    notes = ["Size = mean of long and short axis, rounded to the nearest mm."] if f.short_axis_cm else []
    if f.modality == "MRI":
        notes.append("Fleischner applies to CT; MRI-reported nodule handled as if on CT.")

    if mm is None:
        return GuidelineResult("Lung nodule, size not stated", img,
                               "Size is needed to apply Fleischner; follow-up CT is the safe default.", FLEISCHNER, notes)

    kind = f.nodule_type or "solid"
    if kind == "solid":
        if mm < 6:
            cat = f"Solid nodule <6 mm ({n})"
            if f.patient_risk == "low":
                return GuidelineResult(cat, none_, "Low-risk patient: no routine follow-up.", FLEISCHNER, notes)
            if f.patient_risk == "high":
                return GuidelineResult(cat, img, "High-risk patient: optional CT at 12 months.", FLEISCHNER, notes,
                                       alternatives=[none_])
            return GuidelineResult(cat, none_,
                                   "Risk not stated: no follow-up (low risk) or optional CT at 12 months (high risk) "
                                   "are both acceptable.", FLEISCHNER, notes, alternatives=[img])
        if mm <= 8:
            when = "3-6 months" if f.multiple else "6-12 months"
            return GuidelineResult(f"Solid nodule 6-8 mm ({n})", img,
                                   f"CT at {when}, then consider (low risk) or perform (high risk) CT at 18-24 months.",
                                   FLEISCHNER, notes)
        if f.multiple:
            return GuidelineResult("Solid nodules >8 mm (multiple)", img,
                                   "CT at 3-6 months, then consider CT at 18-24 months.", FLEISCHNER, notes)
        return GuidelineResult("Solid nodule >8 mm (single)", img,
                               "Consider CT at 3 months, PET-CT or tissue sampling.", FLEISCHNER, notes,
                               alternatives=[ref])

    # subsolid
    if f.multiple:
        if mm < 6:
            return GuidelineResult("Multiple subsolid nodules <6 mm", img,
                                   "CT at 3-6 months; if stable, consider CT at 2 and 4 years.", FLEISCHNER, notes)
        return GuidelineResult("Multiple subsolid nodules, one or more ≥6 mm", img,
                               "CT at 3-6 months; further management based on the most suspicious nodule.",
                               FLEISCHNER, notes)
    if kind == "ground-glass":
        if mm < 6:
            return GuidelineResult("Ground-glass nodule <6 mm", none_, "No routine follow-up.", FLEISCHNER, notes)
        return GuidelineResult("Ground-glass nodule ≥6 mm", img,
                               "CT at 6-12 months to confirm persistence, then every 2 years until 5 years.",
                               FLEISCHNER, notes)
    if mm < 6:
        return GuidelineResult("Part-solid nodule <6 mm", none_, "No routine follow-up.", FLEISCHNER, notes)
    if (f.solid_component_mm or 0) >= 6:
        return GuidelineResult("Part-solid nodule ≥6 mm, solid part ≥6 mm", img,
                               "CT at 3-6 months to confirm persistence; a persistent solid part ≥6 mm is highly "
                               "suspicious, so referral or biopsy is also acceptable.", FLEISCHNER, notes,
                               alternatives=[ref])
    return GuidelineResult("Part-solid nodule ≥6 mm", img,
                           "CT at 3-6 months to confirm persistence; if unchanged and solid part <6 mm, yearly CT for "
                           "5 years.", FLEISCHNER, notes)


def _liver_appearance(f: Finding, notes: List[str]) -> str:
    if f.modality == "PET-CT" and f.fdg_avid:
        notes.append("FDG uptake above normal liver treated as a suspicious feature (IncidentaLens rule, not part of "
                     "the ACR CT white paper).")
        return "suspicious"
    if f.appearance:
        return f.appearance
    enh = f.enhancement_hu
    if (enh is not None and enh > 20) or f.homogeneous is False:
        return "suspicious"
    hu = f.enhanced_hu if f.enhanced_hu is not None else f.unenhanced_hu
    if hu is not None and f.homogeneous is not False and hu <= 20:
        return "benign"
    if f.enhanced_hu is not None and f.enhanced_hu > 20:
        return "suspicious"
    return "indeterminate"


def classify_liver(f: Finding) -> GuidelineResult:
    """ACR 2017 white paper on incidental liver lesions (rebuilt from the paper's text and figure footnotes)."""
    notes: List[str] = []
    if f.modality == "MRI":
        notes.append("ACR white paper covers CT; the same feature rules are applied to this MRI finding.")
    look = _liver_appearance(f, notes)
    size, risk = f.size_cm, f.patient_risk
    none_, fu, mri, ref = ([Action.NO_FOLLOWUP], [Action.IMAGING_SURVEILLANCE],
                           [Action.CHARACTERIZATION_IMAGING], [Action.SPECIALIST_REFERRAL])

    if look == "benign" and (size is None or size >= 1):
        return GuidelineResult("Liver lesion with benign features", none_,
                               "Distinctly benign features: no further work-up, regardless of patient risk.",
                               ACR_LIVER, notes)
    if size is None:
        return GuidelineResult("Liver lesion, size not stated", mri,
                               "Size is needed to apply the ACR algorithm; MRI is the safe default.", ACR_LIVER, notes)

    if size < 1:
        cat = "Liver lesion <1 cm"
        if risk == "high":
            alts = [none_] if look == "benign" else []
            return GuidelineResult(cat, fu, "High-risk patient: MRI in 3-6 months to characterise and check for "
                                   "growth" + (" (benign features: no work-up also acceptable)." if alts else "."),
                                   ACR_LIVER, notes, alternatives=alts)
        if risk == "low":
            return GuidelineResult(cat, none_, "Low-risk patient: can be considered benign, no work-up"
                                   + ("; MRI may be considered as features are suspicious." if look == "suspicious" else "."),
                                   ACR_LIVER, notes, alternatives=[mri] if look == "suspicious" else [])
        return GuidelineResult(cat, none_, "Risk not stated: no work-up (low risk) or MRI in 3-6 months (high risk) "
                               "are both acceptable.", ACR_LIVER, notes, alternatives=[fu])

    band = "1-1.5 cm" if size <= 1.5 else ">1.5 cm"
    if look == "flash-filling":
        cat = f"Flash-filling liver lesion {band}"
        if size > 1.5 or risk == "high":
            return GuidelineResult(cat, mri, "Prompt MRI is advised.", ACR_LIVER, notes)
        if risk == "low":
            return GuidelineResult(cat, none_, "Low-risk patient, ≤1.5 cm: no further work-up.", ACR_LIVER, notes)
        return GuidelineResult(cat, none_, "Risk not stated: no work-up (low risk) or prompt MRI (high risk) are both "
                               "acceptable.", ACR_LIVER, notes, alternatives=[mri])
    if look == "suspicious":
        biopsy_ok = size > 1.5 and risk != "low"
        return GuidelineResult(f"Liver lesion {band} with suspicious features", mri,
                               "Prompt MRI is advised" + ("; direct biopsy may be considered for a large, highly "
                               "suspicious lesion in a high-risk patient." if biopsy_ok else "."),
                               ACR_LIVER, notes, alternatives=[ref] if biopsy_ok else [])
    return GuidelineResult(f"Indeterminate liver lesion {band}", mri,
                           "Features cannot be assessed on this scan: MRI is advised.", ACR_LIVER, notes)


def classify_pancreas(f: Finding) -> GuidelineResult:
    """ACR 2017 pancreatic cyst white paper (simplified to the type of action)."""
    size, age = f.size_cm, f.patient_age
    if f.enhancing_nodule or (f.duct_mm is not None and f.duct_mm >= 10):
        return GuidelineResult("Pancreatic cyst with high-risk stigmata", REF,
                               "Enhancing solid component or main duct ≥10 mm: EUS-FNA and surgical consultation.",
                               ACR_PANCREAS)
    worrisome = [w for w, hit in (("thickened/enhancing wall", f.irregular_wall_or_septa),
                                  ("non-enhancing mural nodule", f.mural_nodule),
                                  ("main duct ≥7 mm", f.duct_mm is not None and f.duct_mm >= 7)) if hit]
    if worrisome:
        return GuidelineResult("Pancreatic cyst with worrisome features", REF,
                               f"Worrisome feature ({', '.join(worrisome)}): EUS-FNA and surgical consultation.",
                               ACR_PANCREAS)
    if age is not None and age >= 80:
        return GuidelineResult("Pancreatic cyst, patient ≥80", NONE_,
                               "Age ≥80: surveillance is generally not advised; a single follow-up may be chosen "
                               "depending on health and patient preference.", ACR_PANCREAS, alternatives=[FU])
    if size is None:
        return GuidelineResult("Pancreatic cyst, size not stated", FU,
                               "Size is needed to set the schedule; imaging follow-up is the safe default.", ACR_PANCREAS)
    if size >= 3:
        return GuidelineResult("Pancreatic cyst ≥3 cm", REF,
                               "Size ≥3 cm is a worrisome feature: EUS-FNA and surgical consultation; a cyst with no "
                               "other feature can alternatively be followed.", ACR_PANCREAS, alternatives=[FU])
    if size >= 1.5:
        return GuidelineResult(f"Pancreatic cyst {'1.5-2.5' if size <= 2.5 else '2.5-3'} cm", FU,
                               "Imaging follow-up (6-12 monthly at first, depending on size and duct communication); "
                               "EUS-FNA is an accepted alternative.", ACR_PANCREAS, alternatives=[REF])
    when = "every 2 years" if (age or 0) >= 65 else "yearly"
    return GuidelineResult("Pancreatic cyst <1.5 cm", FU,
                           f"Imaging follow-up {when if age is not None else 'yearly (<65) or every 2 years (65-79)'}, "
                           "stopping after 9-10 years or at age 80.", ACR_PANCREAS)


def classify_thyroid(f: Finding) -> GuidelineResult:
    """ACR 2015 three-tier system for thyroid nodules seen on CT, MRI or PET-CT."""
    size, age = f.size_cm, f.patient_age
    if f.appearance == "suspicious":
        return GuidelineResult("Thyroid nodule with suspicious features", CHAR,
                               "Local invasion or abnormal lymph nodes: dedicated thyroid ultrasound.", ACR_THYROID)
    if f.limited_life_expectancy:
        return GuidelineResult("Thyroid nodule, limited life expectancy", NONE_,
                               "Limited life expectancy or serious comorbidity: no further evaluation.", ACR_THYROID)
    if f.fdg_avid:
        return GuidelineResult("FDG-avid thyroid nodule", CHAR,
                               "Focal FDG uptake is highly suspicious: thyroid ultrasound and FNA.", ACR_THYROID,
                               alternatives=[REF])
    if size is None:
        return GuidelineResult("Thyroid nodule, size not stated", CHAR,
                               "Size is needed; thyroid ultrasound is the safe default.", ACR_THYROID)
    if age is None:
        if size < 1:
            return GuidelineResult("Thyroid nodule <1 cm", NONE_, "Below the size threshold at any age.", ACR_THYROID)
        if size < 1.5:
            return GuidelineResult("Thyroid nodule 1-1.5 cm, age not stated", NONE_,
                                   "Ultrasound if age <35, none if ≥35; age not stated, so both are accepted.",
                                   ACR_THYROID, alternatives=[CHAR])
        return GuidelineResult("Thyroid nodule ≥1.5 cm", CHAR, "Dedicated thyroid ultrasound.", ACR_THYROID)
    limit = 1.0 if age < 35 else 1.5
    band = f"age {'<35' if age < 35 else '≥35'}"
    if size >= limit:
        return GuidelineResult(f"Thyroid nodule ≥{limit:g} cm, {band}", CHAR, "Dedicated thyroid ultrasound.",
                               ACR_THYROID)
    return GuidelineResult(f"Thyroid nodule <{limit:g} cm, {band}", NONE_, "Below the size threshold: no work-up.",
                           ACR_THYROID)


def classify_pituitary(f: Finding) -> GuidelineResult:
    """Endocrine Society 2011 pituitary incidentaloma guideline."""
    notes = []
    if f.chiasm_contact or f.symptomatic:
        return GuidelineResult("Pituitary lesion abutting/compressing the chiasm", REF + HORM,
                               "Formal visual field testing and surgical referral, plus hormonal evaluation.",
                               ES_PITUITARY)
    imaging = FU
    if f.modality != "MRI":
        imaging = CHAR
        notes.append("Found on CT/PET-CT: dedicated pituitary MRI first.")
    if f.size_cm is not None and f.size_cm < 1:
        return GuidelineResult("Pituitary microincidentaloma (<1 cm)", imaging + HORM,
                               "Hormonal evaluation for hypersecretion and hypopituitarism; repeat MRI at 1 year, then "
                               "every 1-2 years.", ES_PITUITARY, notes)
    if f.size_cm is None:
        notes.append("Size not stated; handled as a macroincidentaloma.")
    return GuidelineResult("Pituitary macroincidentaloma (≥1 cm)", imaging + HORM,
                           "Hormonal evaluation for hypersecretion and hypopituitarism; repeat MRI at 6 months, then "
                           "yearly for 3 years.", ES_PITUITARY, notes)


def classify_brain(f: Finding) -> GuidelineResult:
    """EANO 2021: incidental suspected meningioma."""
    if f.growth or f.symptomatic:
        return GuidelineResult("Growing or symptomatic meningioma", REF,
                               "Surgical resection is the first option for growing or symptomatic tumours: "
                               "neurosurgical referral.", EANO)
    notes = [] if f.modality == "MRI" else ["Seen on CT/PET-CT: MRI is the follow-up modality."]
    return GuidelineResult("Incidental asymptomatic meningioma", FU,
                           "Observation: MRI yearly for 5 years, then every 2 years.", EANO, notes)


def classify_bone(f: Finding) -> GuidelineResult:
    """Bone-RADS (CT/MRI), simplified from the paper's text."""
    look = f.appearance
    hu = f.unenhanced_hu if f.unenhanced_hu is not None else f.enhanced_hu
    if look is None and f.macroscopic_fat:
        look = "benign"
    if look is None and hu is not None:
        if f.bone_density == "sclerotic" and hu > 885:
            look = "benign"
        elif f.bone_density == "lucent" and hu < -10:
            look = "benign"
    if look == "suspicious":
        return GuidelineResult("Bone-RADS 4", REF,
                               "Suspicious for malignancy or needs treatment: biopsy and/or orthopaedic oncology "
                               "referral.", BONE_RADS)
    if f.patient_risk == "high":
        return GuidelineResult("Bone-RADS 2/3 (known cancer)", CHAR,
                               "Known cancer that spreads to bone: PET, bone scan or MRI, or follow-up imaging.",
                               BONE_RADS, alternatives=[FU])
    if look == "benign":
        return GuidelineResult("Bone-RADS 1", NONE_, "Likely benign: leave alone.", BONE_RADS)
    return GuidelineResult("Bone-RADS 3", FU,
                           "Indeterminate: follow-up imaging at 6, 6 and 12 months (or a different modality, "
                           "Bone-RADS 2).", BONE_RADS, alternatives=[CHAR])


CLASSIFIERS = {"pancreas": classify_pancreas, "thyroid": classify_thyroid, "pituitary": classify_pituitary,
               "brain": classify_brain, "bone": classify_bone}


def classify(f: Finding) -> GuidelineResult:
    if f.organ in CLASSIFIERS:
        return CLASSIFIERS[f.organ](f)
    if f.organ == "liver":
        return classify_liver(f)
    if f.organ == "lung":
        return classify_lung(f)
    return classify_renal(f) if f.organ == "kidney" else classify_adrenal(f)


# ---------------------------------------------------------------------------
# Concordance between the report's recommendation and the guideline
# ---------------------------------------------------------------------------
IMAGING = {Action.IMAGING_SURVEILLANCE, Action.CHARACTERIZATION_IMAGING}


@dataclass
class Concordance:
    status: str            # concordant | under-call | over-call
    severity: str          # none | low | medium | high
    missing: List[Action]
    extra: List[Action]
    no_recommendation: bool
    message: str


def concordance(f: Finding, g: GuidelineResult) -> Concordance:
    """Compare the report with the guideline; if any accepted alternative matches, it is concordant."""
    first = _concordance(f, g.actions)
    if first.status == "concordant":
        return first
    for alt in g.alternatives:
        c = _concordance(f, alt)
        if c.status == "concordant":
            c.message = "Recommendation matches an option the guideline accepts."
            return c
    return first


def _concordance(f: Finding, actions: List[Action]) -> Concordance:
    required = {a for a in actions if a != Action.NO_FOLLOWUP}
    stated = {a for a in f.stated_actions if a != Action.NO_FOLLOWUP}
    no_rec = not f.stated_actions

    missing = set(required - stated)
    extra = set(stated - required)
    # Either kind of imaging satisfies an imaging requirement.
    if missing & IMAGING and stated & IMAGING:
        missing -= IMAGING
        extra -= IMAGING
    # A specialist referral escalates past an imaging requirement (counted as an over-call).
    if missing & IMAGING and Action.SPECIALIST_REFERRAL in stated:
        missing -= IMAGING

    order = list(Action)
    missing_l = sorted(missing, key=order.index)
    extra_l = sorted(extra, key=order.index)

    if missing_l:
        severity = "high" if Action.SPECIALIST_REFERRAL in missing else "medium"
        what = ", ".join(a.value.replace("_", " ").lower() for a in missing_l)
        lead = "No recommendation given" if no_rec else "Recommendation falls short"
        return Concordance("under-call", severity, missing_l, extra_l, no_rec, f"{lead}: guideline calls for {what}.")
    if extra_l:
        what = ", ".join(a.value.replace("_", " ").lower() for a in extra_l)
        return Concordance("over-call", "low", missing_l, extra_l, no_rec,
                           f"Guideline does not call for {what} (possible unnecessary follow-up).")
    return Concordance("concordant", "none", [], [], no_rec, "Recommendation matches the guideline.")
