"""Rule-based (regex) baseline extractor. Transparent and offline, but brittle by design:
it reads features only from FINDINGS and recommendations only from IMPRESSION."""
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
    (Action.SPECIALIST_REFERRAL, re.compile(r"urolog|referr|\brefer\b|surgical (consult|evaluation)|multidisciplinary|\bMDT\b", re.I)),
    (Action.HORMONAL_WORKUP, re.compile(r"dexamethasone|\bDST\b|biochemical|hormonal|metanephrine|aldosterone|endocrin", re.I)),
    (Action.IMAGING_SURVEILLANCE, re.compile(r"follow[- ]?up (CT|MRI|ultrasound|imaging|US)\b|in \d+ months|surveillance|repeat (CT|MRI|imaging)", re.I)),
    (Action.CHARACTERIZATION_IMAGING, re.compile(r"protocol (CT|MRI)|mass protocol|adrenal protocol|dedicated|further evaluat|\bMRI\b|characteri[sz]ation", re.I)),
]
EXPLICIT_CHAR = re.compile(r"protocol|dedicated", re.I)
NO_FU_RE = re.compile(r"no (further )?(follow[- ]?up|imaging)|no further (imaging|evaluation|work)", re.I)


def _sentences(text: str) -> List[str]:
    out = []
    for line in text.splitlines():
        out.extend(s.strip() for s in re.split(r"(?<=[.;])\s+", line) if s.strip())
    return out


def _organ(s: str) -> Optional[str]:
    if re.search(r"adrenal", s, re.I):
        return "adrenal"
    if re.search(r"kidney|renal", s, re.I):
        return "kidney"
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


def extract(text: str) -> ReportExtraction:
    parts = SPLIT_IMPRESSION.split(text, maxsplit=1)
    body, impression = parts[0], (parts[1] if len(parts) > 1 else "")
    header = body.split("FINDINGS")[0] if "FINDINGS" in body else body.splitlines()[0]
    phase = _exam_phase(header)

    findings: List[Finding] = []
    for line in body.splitlines():
        header_organ = _organ(line.split(":")[0]) if ":" in line else None
        current: Optional[Finding] = None
        for s in _sentences(line):
            organ = _organ(s) or header_organ
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
