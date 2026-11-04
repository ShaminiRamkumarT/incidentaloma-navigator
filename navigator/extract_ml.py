"""Trained extractor: a token-labelling model learned from the synthetic reports.

How it works
  1. Tokenise the report and describe every token by its word, shape, neighbours, report
     section and the exam's contrast phase.
  2. A logistic-regression model (scikit-learn, trained from scratch, no pretrained weights and
     no downloads) labels each token, e.g. SIZE, HU_PRE, ORG_LUNG, APPEAR_SUSP, ACT_SPECIALIST_REFERRAL.
  3. Small deterministic steps turn labelled spans into Finding fields (unit conversion, numbers,
     linking each recommendation in the impression to its lesion).

The guideline decision still happens in guidelines.py, so every flag stays traceable.
Train with:  python train_model.py
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .schema import Action, Finding, ReportExtraction

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "extractor.joblib"

TOKEN_RE = re.compile(r"\d+(?:\.\d+)?|[A-Za-z]+|[^\sA-Za-z\d]")
SECTION_RE = re.compile(r"^\s*(EXAM|INDICATION|CLINICAL HISTORY|HISTORY|COMPARISON|TECHNIQUE|FINDINGS|IMPRESSION|"
                        r"CONCLUSION|RECOMMENDATIONS?)\s*:", re.I)


# --------------------------------------------------------------------------- tokens and features
def tokenize(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def _sections(text: str) -> List[Tuple[int, int, str, str]]:
    """(start, end, section, line header) for every line."""
    out, sec, pos = [], "header", 0
    for line in text.split("\n"):
        m = SECTION_RE.match(line)
        if m:
            sec = m.group(1).upper()
            sec = {"CLINICAL HISTORY": "INDICATION", "HISTORY": "INDICATION", "CONCLUSION": "IMPRESSION",
                   "RECOMMENDATION": "IMPRESSION", "RECOMMENDATIONS": "IMPRESSION"}.get(sec, sec)
        hm = re.match(r"^\s*([A-Za-z ]{2,30}):", line)
        out.append((pos, pos + len(line), sec, hm.group(1).strip().lower() if hm else ""))
        pos += len(line) + 1
    return out


def exam_contrast(text: str) -> str:
    exam = text.split("\n", 1)[0].lower()
    if re.search(r"with and without|unenhanced and|multiphase|renal mass protocol|pre- and post", exam):
        return "both"
    if re.search(r"without|non-?contrast|unenhanced", exam):
        return "without"
    if re.search(r"with|contrast|enhanced|venous", exam):
        return "with"
    return "unknown"


def exam_modality(text: str) -> str:
    exam = text.split("\n", 1)[0]
    if re.search(r"PET", exam):
        return "PET-CT"
    if re.search(r"\bMRI?\b|magnetic", exam, re.I):
        return "MRI"
    if re.search(r"\bCT\b|computed", exam, re.I):
        return "CT"
    return "unknown"


def _shape(w: str) -> str:
    s = re.sub(r"[A-Z]", "A", w)
    s = re.sub(r"[a-z]", "a", s)
    s = re.sub(r"\d", "9", s)
    return re.sub(r"(.)\1+", r"\1\1", s)


ORGAN_WORDS = {"kidney": "kidney", "kidneys": "kidney", "renal": "kidney", "adrenal": "adrenal", "adrenals": "adrenal",
               "lung": "lung", "lungs": "lung", "lobe": "lung", "pulmonary": "lung", "lingula": "lung",
               "liver": "liver", "hepatic": "liver", "segment": "liver", "pancreas": "pancreas",
               "pancreatic": "pancreas", "thyroid": "thyroid", "pituitary": "pituitary", "sella": "pituitary",
               "meningioma": "brain", "brain": "brain", "dural": "brain", "bone": "bone", "bones": "bone",
               "vertebral": "bone", "femur": "bone", "rib": "bone", "sacrum": "bone", "humerus": "bone"}


def _line_organs(text: str):
    """For each line, the organ words it contains (a small dictionary, used as context features)."""
    out = []
    for line in text.split("\n"):
        out.append(sorted({ORGAN_WORDS[w] for w in re.findall(r"[a-z]+", line.lower()) if w in ORGAN_WORDS}))
    return out


def featurize(text: str):
    toks = tokenize(text)
    secs = _sections(text)
    lorg = _line_organs(text)
    contrast, modality = exam_contrast(text), exam_modality(text)
    feats = []
    si = 0
    for i, (w, a, b) in enumerate(toks):
        while si < len(secs) - 1 and a > secs[si][1]:
            si += 1
        sec, head = secs[si][2], secs[si][3]
        lw = w.lower()
        f = {"w=" + lw: 1, "shape=" + _shape(w): 1, "suf3=" + lw[-3:]: 1, "pre3=" + lw[:3]: 1,
             "sec=" + sec: 1, "head=" + head: 1, "contrast=" + contrast: 1, "mod=" + modality: 1,
             "isnum": float(w[0].isdigit()), "cap": float(w[0].isupper()), "bias": 1}
        for d in (-4, -3, -2, -1, 1, 2, 3, 4):
            j = i + d
            ww = toks[j][0].lower() if 0 <= j < len(toks) else ("<s>" if j < 0 else "</s>")
            f[f"w{d}={ww}"] = 1
            if abs(d) <= 2:
                f[f"shape{d}=" + (_shape(toks[j][0]) if 0 <= j < len(toks) else "-")] = 1
        prev = toks[i - 1][0].lower() if i else "<s>"
        nxt = toks[i + 1][0].lower() if i + 1 < len(toks) else "</s>"
        f[f"bi-={prev}|{lw}"] = 1
        f[f"bi+={lw}|{nxt}"] = 1
        f[f"sec_w={sec}|{lw}"] = 1
        for o in lorg[si]:
            f["lineorg=" + o] = 1
            f[f"lineorg_w={o}|{lw}"] = 1
        feats.append(f)
    return toks, feats


def token_labels(text: str, spans) -> List[str]:
    toks = tokenize(text)
    labels = ["O"] * len(toks)
    for a, b, lab in spans:
        for i, (_, ta, tb) in enumerate(toks):
            if ta >= a and tb <= b:
                labels[i] = lab
    return labels


# --------------------------------------------------------------------------- model
_model = None


def train(reports: List[dict], C: float = 2.0):
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression

    X, y = [], []
    for r in reports:
        _, feats = featurize(r["text"])
        X += feats
        y += token_labels(r["text"], r["spans"])
    vec = DictVectorizer(sparse=True)
    Xv = vec.fit_transform(X)
    clf = LogisticRegression(C=C, max_iter=2000)
    clf.fit(Xv, y)
    return {"vec": vec, "clf": clf}


def save(model, path: Path = MODEL_PATH):
    import joblib
    path.parent.mkdir(exist_ok=True)
    joblib.dump(model, path, compress=3)


def load(path: Path = MODEL_PATH):
    global _model
    if _model is None:
        import joblib
        if not path.exists():   # first run: train from the synthetic reports (about 10 seconds)
            import json
            save(train(json.loads((ROOT / "data" / "synthetic_train.json").read_text())), path)
        _model = joblib.load(path)
    return _model


def tag(text: str, model=None) -> List[Tuple[str, int, int]]:
    """Returns labelled spans (label, start, end)."""
    model = model or load()
    toks, feats = featurize(text)
    if not toks:
        return []
    labels = model["clf"].predict(model["vec"].transform(feats))
    spans, cur = [], None
    for (w, a, b), lab in zip(toks, labels):
        gap = cur is not None and text[cur[2]:a].strip() not in ("", "-", ",", "/", "(", ")", "x", "×", "'")
        if lab != "O" and cur and cur[0] == lab and not gap and not (lab.startswith("ACT_") and text[cur[2]-1:cur[2]] == "."):
            cur[2] = b
        else:
            if cur:
                spans.append(tuple(cur))
            cur = [lab, a, b] if lab != "O" else None
    if cur:
        spans.append(tuple(cur))
    return spans


# --------------------------------------------------------------------------- spans -> findings
ORG = {"ORG_KIDNEY": "kidney", "ORG_ADRENAL": "adrenal", "ORG_LUNG": "lung", "ORG_LIVER": "liver",
       "ORG_PANCREAS": "pancreas", "ORG_THYROID": "thyroid", "ORG_PITUITARY": "pituitary", "ORG_BRAIN": "brain",
       "ORG_BONE": "bone"}
ACT = {"ACT_" + a.value: a for a in Action}
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "few": 2, "several": 4,
           "multiple": 4, "many": 4, "numerous": 4}
CLAUSE_SPLIT = re.compile(r"\.\s+(?=[A-Z0-9])|;\s*|,?\s+and an?\s+|,\s*plus an?\s+")
RISK_FIELDS = {"lung", "liver", "bone"}


def _nums(s: str) -> List[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]


def _mm(s: str) -> Optional[float]:
    n = _nums(s)
    return n[0] if n else None


def _apply(f: Dict, lab: str, s: str):
    if lab == "SIZE":
        n = [x for x in _nums(s) if x > 0]
        if n:
            k = 0.1 if re.search(r"mm|millimet", s, re.I) else 1.0
            f["size_cm"] = round(max(n) * k, 2)
            if len(n) > 1:
                f["short_axis_cm"] = round(min(n) * k, 2)
    elif lab in ("HU_PRE", "HU_POST"):
        n = _nums(s)
        if n:
            f["unenhanced_hu" if lab == "HU_PRE" else "enhanced_hu"] = n[0]
    elif lab == "HOMOG":
        f["homogeneous"] = True
    elif lab == "HETEROG":
        f["homogeneous"] = False
    elif lab == "CYSTIC":
        f["composition"] = "cystic"
    elif lab == "SOLID":
        f.setdefault("composition", "solid")
    elif lab == "SEPTA_N":
        n = _nums(s)
        f["septa_count"] = int(n[0]) if n else WORDNUM.get(s.lower().strip(), 4)
    elif lab == "SEPTA_MM":
        f["septa_mm"] = _mm(s)
    elif lab == "WALL_MM":
        f["wall_mm"] = _mm(s)
    elif lab == "IRREG":
        f["irregular_wall_or_septa"] = True
    elif lab == "ENH_NODULE":
        f["enhancing_nodule"] = True
    elif lab == "FAT":
        f["macroscopic_fat"] = True
    elif lab == "TOO_SMALL":
        f["too_small_to_characterize"] = True
    elif lab == "MULTIPLE":
        f["multiple"] = True
    elif lab == "NOD_GGO":
        f["nodule_type"] = "ground-glass"
    elif lab == "NOD_PARTSOLID":
        f["nodule_type"] = "part-solid"
    elif lab == "SOLIDPART":
        f["solid_component_mm"] = _mm(s)
    elif lab.startswith("APPEAR_"):
        f["appearance"] = {"BENIGN": "benign", "SUSP": "suspicious", "FLASH": "flash-filling",
                           "INDET": "indeterminate"}[lab[7:]]
    elif lab == "FDG_POS":
        f["fdg_avid"] = True
    elif lab == "FDG_NEG":
        f["fdg_avid"] = False
    elif lab == "DUCT":
        f["duct_mm"] = _mm(s)
    elif lab == "MURAL":
        f["mural_nodule"] = True
    elif lab == "CHIASM":
        f["chiasm_contact"] = True
    elif lab == "GROWTH":
        f["growth"] = True
    elif lab.startswith("DENS_"):
        f["bone_density"] = lab[5:].lower()
    elif lab == "SIDE":
        w = s.lower()
        f["side"] = "left" if "left" in w else "right" if "right" in w else f.get("side", "unknown")


def _finalize(f: Dict, ctx: Dict) -> Finding:
    organ = f["organ"]
    if organ != "lung":
        f.pop("short_axis_cm", None)
    if organ in RISK_FIELDS:
        f["patient_risk"] = ctx["risk"].get(organ, "unknown")
    if organ in ("pancreas", "thyroid") and ctx.get("age") is not None:
        f["patient_age"] = ctx["age"]
    if organ == "thyroid" and ctx.get("limited"):
        f["limited_life_expectancy"] = True
    if organ == "brain" and ctx.get("sympt"):
        f["symptomatic"] = True
    if f.get("side") is None:
        f["side"] = "unknown"
    return Finding(**f)


def assemble(text: str, spans) -> ReportExtraction:
    secs = _sections(text)

    def section(pos):
        for a, b, s, _ in secs:
            if a <= pos <= b:
                return s
        return "header"

    ctx = {"risk": {}, "age": None}
    for lab, a, b in spans:
        s = text[a:b]
        if section(a) == "IMPRESSION":
            continue
        if lab == "AGE" and _nums(s):
            ctx["age"] = int(_nums(s)[0])
        elif lab == "RISK_SMOKER":
            ctx["risk"]["lung"] = "high"
        elif lab == "RISK_NONSMOKER":
            ctx["risk"]["lung"] = "low"
        elif lab == "RISK_CANCER":
            ctx["risk"].update(liver="high", bone="high")
        elif lab == "RISK_LIVERDZ":
            ctx["risk"]["liver"] = "high"
        elif lab == "RISK_LIVERLOW":
            ctx["risk"].setdefault("liver", "low")
        elif lab == "LIMITED_LE":
            ctx["limited"] = True
        elif lab == "SYMPT":
            ctx["sympt"] = True

    modality = exam_modality(text)
    findings: List[Dict] = []
    # FINDINGS: one line at a time, split into clauses; a clause holds at most one lesion
    for la, lb, sec, head in secs:
        if sec != "FINDINGS":
            continue
        head_organs = {ORGAN_WORDS[w] for w in re.findall(r"[a-z]+", head) if w in ORGAN_WORDS}
        line = text[la:lb]
        bounds, start = [], 0
        for m in CLAUSE_SPLIT.finditer(line):
            bounds.append((la + start, la + m.start()))
            start = m.end()
        bounds.append((la + start, lb))
        line_find = None
        for ca, cb in bounds:
            cs = [(lab, a, b) for lab, a, b in spans if ca <= a < cb or (a < ca < b)]
            orgs = [x for x in cs if x[0] in ORG]
            cur = None
            if orgs:
                cur = {"organ": ORG[orgs[0][0]], "modality": modality}
                findings.append(cur)
            elif line_find is not None:
                cur = line_find
            elif len(head_organs) == 1 and any(x[0] == "SIZE" for x in cs):
                # lesion described under an organ heading without naming the organ again ("Kidneys: 1.9 cm lesion ...")
                cur = {"organ": head_organs.pop(), "modality": modality}
                findings.append(cur)
            if cur is None:
                continue
            for lab, a, b in cs:
                if lab not in ORG:
                    _apply(cur, lab, text[a:b])
            line_find = cur

    # IMPRESSION: walk the spans in order; each organ mention sets the lesion(s) that the following
    # recommendations refer to. A numbered item resets the context.
    imp = [(a, b) for a, b, s, _ in secs if s == "IMPRESSION"]
    if imp and findings:
        ia, ib = imp[0][0], imp[-1][1]
        starts = [ia + m.start() for m in re.finditer(r"(?m)^\s*\d+[.)]\s*", text[ia:ib])]
        targets, side_hint, item = (findings if len(findings) == 1 else []), None, -1
        for lab, a, b in sorted(((l, a, b) for l, a, b in spans if ia <= a < ib), key=lambda x: x[1]):
            cur_item = sum(1 for s0 in starts if s0 <= a)
            if cur_item != item:
                item, side_hint = cur_item, None
                targets = findings if len(findings) == 1 else []
            if lab == "SIDE":
                w = text[a:b].lower()
                side_hint = "left" if "left" in w else "right" if "right" in w else None
            elif lab in ORG:
                cands = [f for f in findings if f["organ"] == ORG[lab]]
                sided = [f for f in cands if side_hint and f.get("side") == side_hint and
                         text[max(ia, a - 25):a].lower().find(side_hint) >= 0]
                targets = sided or cands
                side_hint = None
            elif lab in ACT:
                for f in targets:
                    st = f.setdefault("stated_actions", [])
                    if ACT[lab] not in st:
                        st.append(ACT[lab])
            elif lab == "CYSTIC":
                for f in targets:
                    if f["organ"] == "kidney":
                        f["composition"] = "cystic"
    return ReportExtraction(findings=[_finalize(f, ctx) for f in findings])


def extract(text: str) -> ReportExtraction:
    return assemble(text, tag(text))
