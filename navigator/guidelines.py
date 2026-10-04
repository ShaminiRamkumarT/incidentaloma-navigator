"""Deterministic guideline engine for incidental renal and adrenal masses on CT.

Simplified, educational encodings of:
  * Bosniak classification v2019 (Silverman SG et al., Radiology 2019;292:475-488)
  * ACR Incidental Findings Committee white paper on renal masses
    (Herts BR et al., J Am Coll Radiol 2018;15:264-273)
  * ESE/ENSAT guideline on adrenal incidentalomas
    (Fassnacht M et al., Eur J Endocrinol 2023;189:G1-G42)

NOT a medical device and not for clinical use. Thresholds are simplified; see README.
"""
from dataclasses import dataclass, field
from typing import List

from .schema import Action, Finding

BOSNIAK = "Bosniak v2019 (Radiology 2019)"
ACR_RENAL = "ACR renal mass white paper (JACR 2018)"
ESE = "ESE/ENSAT adrenal incidentaloma guideline (EJE 2023)"


@dataclass
class GuidelineResult:
    category: str
    actions: List[Action]
    rationale: str
    source: str
    notes: List[str] = field(default_factory=list)


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


def classify(f: Finding) -> GuidelineResult:
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
    required = {a for a in g.actions if a != Action.NO_FOLLOWUP}
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
