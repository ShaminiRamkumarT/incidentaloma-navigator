"""Rule-based (regex) baseline extractor. Transparent and offline, but brittle by design:
it reads features only from FINDINGS and recommendations only from IMPRESSION.

The kidney and adrenal rules come from the first version of the project. Rules for the other seven
organs were added later, written from guideline vocabulary and checked against the synthetic
training reports only (never against the held-out reports)."""
import re
from typing import List, Optional

from .schema import Action, Finding, ReportExtraction

NUM = r"-?\d+(?:\.\d+)?"
SIZE_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*cm\b", re.I)
HU_RE = re.compile(rf"({NUM})\s*HU\b")
LESION_RE = re.compile(r"\b(lesion|cyst|mass|nodule|hypodensity|angiomyolipoma|myelolipoma)", re.I)
UNENH_RE = re.compile(r"unenhanced|non-?contrast|pre-?contrast|\bpre\b|without contrast", re.I)
ENH_RE = re.compile(r"nephrographic|portal|post-?contrast|\bpost\b|after contrast|enhanced phase|arterial", re.I)
SPLIT_IMPRESSION = re.compile(r"\n\s*(?:IMPRESSION|IMP)\s*:", re.I)

COUNT_WORDS = {"a": 1, "an": 1, "one": 1, "single": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
               "few": 2, "several": 4, "multiple": 4, "many": 4}
SEPTA_COUNT_RE = re.compile(
    r"\b(a|an|one|single|two|three|four|five|six|few|several|multiple|many)\b(\s*\((\d+)\))?"
    r"((?:[\s,]+(?:thin|thick|thickened|smooth|irregular|enhancing|minimally|\(?\d+(?:\.\d+)?\s*mm\)?))*)[\s,]+sept",
    re.I)

ACTION_PATTERNS = [
    (Action.SPECIALIST_REFERRAL, re.compile(r"urolog|referr|\brefer\b|surgical (consult|evaluation)|multidisciplinary|\bMDT\b"
                                            r"|neurosurg|\bEUS\b|\bFNA\b|fine[- ]needle|biopsy|oncolog|pulmonolog", re.I)),
    (Action.HORMONAL_WORKUP, re.compile(r"dexamethasone|\bDST\b|biochemical|hormon|metanephrine|aldosterone|endocrin", re.I)),
    (Action.IMAGING_SURVEILLANCE, re.compile(r"follow[- ]?up (CT|MRI|ultrasound|imaging|US)\b|in \d+ (months|years)|surveillance"
                                             r"|repeat (CT|MRI|imaging)|short[- ]interval", re.I)),
    (Action.CHARACTERIZATION_IMAGING, re.compile(r"protocol (CT|MRI)|mass protocol|adrenal protocol|dedicated|further evaluat|\bMRI\b"
                                                 r"|characteri[sz]ation|thyroid ultrasound|\bPET\b", re.I)),
]
EXPLICIT_CHAR = re.compile(r"protocol|dedicated", re.I)
NO_FU_RE = re.compile(r"no (further )?(follow[- ]?up|imaging)|no further (imaging|evaluation|work)", re.I)


def _sentences(text: str) -> List[str]:
    out = []
    for line in text.splitlines():
        out.extend(s.strip() for s in re.split(r"(?<=[.;])\s+", line) if s.strip())
    return out


ORGAN_PATTERNS = [  # checked in this order
    ("adrenal", r"adrenal"),
    ("kidney", r"kidney|renal"),
    ("pituitary", r"pituitar|\bsella|adenohypophysis|macroadenoma|microadenoma"),
    ("thyroid", r"thyroid"),
    ("pancrea", r"pancrea"),
    ("liver", r"liver|hepatic|\bsegment \d"),
    ("lung", r"\blungs?\b|pulmonary|\blobe\b|lingula"),
    ("brain", r"meningioma|extra-?axial|dural"),
    ("bone", r"\bbones?\b|osseous|vertebra|femur|femoral|humer|iliac|\bribs?\b|sacrum|calvari|\blytic\b|sclerotic"),
]
NEW_ORGANS = {"lung", "liver", "pancreas", "thyroid", "pituitary", "brain", "bone"}


def _organ(s: str) -> Optional[str]:
    for organ, rx in ORGAN_PATTERNS:
        if re.search(rx, s, re.I):
            return "pancreas" if organ == "pancrea" else organ
    return None


def _side(s: str) -> str:
    m = re.search(r"\b(left|right)\b", s, re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"\b([LR])\b", s)
    if m:
        return "left" if m.group(1) == "L" else "right"
    return "unknown"


def _exam_phase(header: str) -> Optional[str]:
    if re.search(r"with and without|without and with|w/wo|multiphase|renal (mass )?protocol", header, re.I):
        return None
    if re.search(r"without (iv )?contrast|non-?contrast|stone protocol", header, re.I):
        return "unenhanced"
    if re.search(r"contrast|portal venous", header, re.I):
        return "enhanced"
    return None


def _mm_features(s: str, f: Finding):
    """Assign each 'N mm' to the nearest following structure (wall / septum / nodule)."""
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*mm\b", s):
        val = float(m.group(1))
        after = s[m.end(): m.end() + 35].lower()
        before = s[max(0, m.start() - 30): m.start()].lower()
        hits = [(after.find(k), k) for k in ("wall", "sept", "nodul") if after.find(k) >= 0]
        if not hits:
            hits = [(len(before) - before.rfind(k), k) for k in ("wall", "sept", "nodul") if before.rfind(k) >= 0]
        if not hits:
            continue
        _, kind = min(hits)
        if kind == "wall":
            f.wall_mm = val
        elif kind == "sept":
            f.septa_mm = max(val, f.septa_mm or 0)


def _features(s: str, f: Finding, phase: Optional[str]):
    low = s.lower()
    if re.search(r"\bcyst", low):
        f.composition = "cystic"
    elif re.search(r"\bsolid\b", low):
        f.composition = "solid"
    if "heterogeneous" in low:
        f.homogeneous = False
    elif "homogeneous" in low:
        f.homogeneous = True
    if "irregular" in low:
        f.irregular_wall_or_septa = True
    if "too small to characterize" in low:
        f.too_small_to_characterize = True
    if re.search(r"macroscopic fat|fat[- ]containing|containing fat", low):
        f.macroscopic_fat = True
    if f.organ == "kidney" and re.search(r"(enhancing|mural|soft[- ]tissue)\s+(\d+\s*mm\s+)?(mural\s+)?nodul", low):
        f.enhancing_nodule = True
    m = SEPTA_COUNT_RE.search(s)
    if m:
        f.septa_count = int(m.group(3)) if m.group(3) else COUNT_WORDS[m.group(1).lower()]
    _mm_features(s, f)

    hus = list(HU_RE.finditer(s))
    for i, h in enumerate(hus):
        end = hus[i + 1].start() if i + 1 < len(hus) else len(s)
        after = s[h.end(): min(end, h.end() + 40)]
        if UNENH_RE.search(after):
            kind = "unenhanced"
        elif ENH_RE.search(after):
            kind = "enhanced"
        else:
            kind = phase or "enhanced"
        setattr(f, f"{kind}_hu", float(h.group(1)))


SIZE_ANY_RE = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(?:x|×|by)\s*(\d+(?:\.\d+)?))?\s*(cm|mm)\b", re.I)
LESION_NEW_RE = re.compile(r"\b(lesion|cyst|mass|nodule|focus|adenoma|macroadenoma|microadenoma|meningioma|haemangioma"
                           r"|hemangioma|island)", re.I)


def _negated(s: str, start: int) -> bool:
    return bool(re.search(r"\b(no|without|not)\b[^.;,]{0,25}$", s[:start], re.I))


def _has(s: str, rx: str) -> bool:
    m = re.search(rx, s, re.I)
    return bool(m) and not _negated(s, m.start())


def _size_new(s: str):
    for m in SIZE_ANY_RE.finditer(s):
        after = s[m.end(): m.end() + 30].lower()
        if re.match(r"\s*(solid component|wall|duct|septum)", after) or "duct" in s[max(0, m.start() - 25): m.start()].lower():
            continue
        k = 0.1 if m.group(3).lower() == "mm" else 1.0
        a, b = float(m.group(1)) * k, (float(m.group(2)) * k if m.group(2) else None)
        return round(max(a, b or 0), 2), (round(min(a, b), 2) if b else None)
    return None, None


def _context(header: str) -> dict:
    """Patient facts from the exam line and indication."""
    ctx = {"modality": "PET-CT" if re.search(r"\bPET", header) else "MRI" if re.search(r"\bMRI?\b", header) else "CT"}
    m = re.search(r"(\d{1,3})[- ]year[- ]old|aged (\d{1,3})", header, re.I)
    if m:
        ctx["age"] = int(m.group(1) or m.group(2))
    if re.search(r"never[- ]smoker|non-?smoker|no smoking", header, re.I):
        ctx["lung_risk"] = "low"
    elif re.search(r"smoker|pack[- ]year|smoking", header, re.I):
        ctx["lung_risk"] = "high"
    if re.search(r"cancer|carcinoma|malignan|melanoma|lymphoma|metasta", header, re.I) and \
            not re.search(r"no (known |history of )?(cancer|malignan)", header, re.I):
        ctx["cancer"] = True
    if re.search(r"cirrhosis|hepatitis|NASH|alcohol", header, re.I):
        ctx["liver_disease"] = True
    if re.search(r"no (history of |known )?(malignancy|cancer) or liver disease", header, re.I):
        ctx["liver_low"] = True
    if re.search(r"limited life expectancy|palliative", header, re.I):
        ctx["limited"] = True
    if re.search(r"seizure|weakness|deficit", header, re.I):
        ctx["neuro"] = True
    return ctx


def _features_new(s: str, f: Finding, phase: Optional[str], ctx: dict):
    low = s.lower()
    o = f.organ
    if o == "lung":
        if _has(s, r"ground[- ]glass|non-?solid"):
            f.nodule_type = "ground-glass"
        elif _has(s, r"part[- ]solid|semi-?solid"):
            f.nodule_type = "part-solid"
        if re.search(r"\b(multiple|several|scattered|numerous)\b", low):
            f.multiple = True
        m = re.search(r"(\d+(?:\.\d+)?)\s*mm solid component", low)
        if m:
            f.solid_component_mm = float(m.group(1))
    elif o == "liver":
        if _has(s, r"haemangioma|hemangioma|focal fat|\bFNH\b|peripheral nodular|simple cyst"):
            f.appearance = "benign"
        elif _has(s, r"ill-defined|heterogeneous|poorly marginated"):
            f.appearance = "suspicious"
        elif _has(s, r"flash[- ]filling|arterial hyperenhancement"):
            f.appearance = "flash-filling"
        elif _has(s, r"too small to characteri|indeterminate|incompletely characteri"):
            f.appearance = "indeterminate"
    elif o == "pancreas":
        if re.search(r"\bcyst", low):
            f.composition = "cystic"
        m = re.search(r"duct[^.;]{0,30}?(\d+(?:\.\d+)?)\s*mm", low)
        if m:
            f.duct_mm = float(m.group(1))
        if _has(s, r"non-?enhancing (mural )?nodule"):
            f.mural_nodule = True
        elif _has(s, r"enhancing (mural nodule|nodule|solid)"):
            f.enhancing_nodule = True
        if _has(s, r"thick(ened)?[^.;]{0,20}wall"):
            f.irregular_wall_or_septa = True
    elif o == "thyroid":
        if _has(s, r"FDG (uptake|avid)|FDG-avid|focal uptake"):
            f.fdg_avid = True
        elif re.search(r"(no|without) (focal )?FDG", s, re.I):
            f.fdg_avid = False
        if _has(s, r"extrathyroidal|invasion|lymph node"):
            f.appearance = "suspicious"
    elif o == "pituitary":
        if re.search(r"(abut|compress|contact|elevat|displac)\w*[^.;]{0,25}chiasm", low):
            f.chiasm_contact = True
    elif o == "brain":
        if re.search(r"\b(increased|grown|growth|enlarg)|previously \d", low):
            f.growth = True
    elif o == "bone":
        if _has(s, r"\blytic|lucent"):
            f.bone_density = "lucent"
        elif _has(s, r"sclerotic|blastic"):
            f.bone_density = "sclerotic"
        if _has(s, r"cortical (destruction|breach|breakthrough)|periosteal reaction|soft[- ]tissue (extension|mass)"
                   r"|pathologic(al)? fracture|endosteal scalloping"):
            f.appearance = "suspicious"
        elif _has(s, r"bone island|enostosis|haemangioma|hemangioma|non-?ossifying|macroscopic fat"):
            f.appearance = "benign"
        hus = [float(h.group(1)) for h in HU_RE.finditer(s)]
        if hus:
            f.unenhanced_hu = hus[0]


def _apply_context(f: Finding, ctx: dict):
    f.modality = ctx["modality"]
    if f.organ == "lung" and "lung_risk" in ctx:
        f.patient_risk = ctx["lung_risk"]
    if f.organ == "liver":
        if ctx.get("cancer") or ctx.get("liver_disease"):
            f.patient_risk = "high"
        elif ctx.get("liver_low"):
            f.patient_risk = "low"
    if f.organ == "bone" and ctx.get("cancer"):
        f.patient_risk = "high"
    if f.organ in ("pancreas", "thyroid") and "age" in ctx:
        f.patient_age = ctx["age"]
    if f.organ == "thyroid" and ctx.get("limited"):
        f.limited_life_expectancy = True
    if f.organ == "brain" and ctx.get("neuro"):
        f.symptomatic = True


def extract(text: str) -> ReportExtraction:
    parts = SPLIT_IMPRESSION.split(text, maxsplit=1)
    body, impression = parts[0], (parts[1] if len(parts) > 1 else "")
    header = body.split("FINDINGS")[0] if "FINDINGS" in body else body.splitlines()[0]
    phase = _exam_phase(header)
    ctx = _context(header)

    findings: List[Finding] = []
    started = "FINDINGS" not in body
    for line in body.splitlines():
        if "FINDINGS" in line:
            started = True
            continue
        if not started:
            continue
        header_organ = _organ(line.split(":")[0]) if ":" in line else None
        current: Optional[Finding] = None
        for s in _sentences(line):
            organ = _organ(s) or header_organ
            if organ in NEW_ORGANS:
                size, short = _size_new(s)
                if size is not None and LESION_NEW_RE.search(s):
                    current = Finding(organ=organ, side=_side(s), size_cm=size)
                    if organ == "lung" and short:
                        current.short_axis_cm = short
                    findings.append(current)
                    _features_new(s, current, phase, ctx)
                    _apply_context(current, ctx)
                elif current is not None and current.organ in NEW_ORGANS and not re.match(r"no\b", s, re.I):
                    _features_new(s, current, phase, ctx)
                continue
            if organ and SIZE_RE.search(s) and LESION_RE.search(s):
                current = Finding(organ=organ, side=_side(s), size_cm=float(SIZE_RE.search(s).group(1)))
                findings.append(current)
                _features(s, current, phase)
            elif current is not None and not re.match(r"no\b", s, re.I) and _organ(s) is None:
                _features(s, current, phase)

    m = re.search(r"Bosniak\s+(IIF|IV|III|II|I)\b", impression)
    if m:
        for f in findings:
            if f.organ == "kidney":
                f.reported_category = f"Bosniak {m.group(1)}"

    _assign_actions(impression, findings)
    return ReportExtraction(findings=findings)


def _assign_actions(impression: str, findings: List[Finding]):
    items = re.split(r"\n\s*\d+[.)]\s*", "\n" + impression)
    for item in items:
        ctx_organ, ctx_side = None, "unknown"
        for s in _sentences(item):
            organ = _organ(s)
            if organ:
                ctx_organ = organ
                ctx_side = "unknown" if re.search(r"bilateral", s, re.I) else _side(s)
            actions = [a for a, rx in ACTION_PATTERNS if rx.search(s)]
            if Action.IMAGING_SURVEILLANCE in actions and Action.CHARACTERIZATION_IMAGING in actions \
                    and not EXPLICIT_CHAR.search(s):
                actions.remove(Action.CHARACTERIZATION_IMAGING)
            if NO_FU_RE.search(s):
                actions = [a for a in actions if a not in (Action.IMAGING_SURVEILLANCE, Action.CHARACTERIZATION_IMAGING)]
                actions.insert(0, Action.NO_FOLLOWUP)
            if not actions:
                continue
            targets = [f for f in findings if ctx_organ is None or f.organ == ctx_organ]
            sided = [f for f in targets if ctx_side != "unknown" and f.side == ctx_side]
            for f in (sided or targets):
                for a in actions:
                    if a not in f.stated_actions:
                        f.stated_actions.append(a)
