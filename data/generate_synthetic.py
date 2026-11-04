"""Generates labelled synthetic imaging reports for all nine organs (CT, MRI, PET-CT).

Every report is fictional. Each phrase that carries information is written together with its
label, so the gold findings and the token labels used to train the extractor come for free.

Two phrase banks:
  * train  - the phrasings the model learns from
  * test   - the same pools plus extra wordings the model never sees in training, and a
             different random seed. Used to check that the model copes with new phrasing.

Usage:  python data/generate_synthetic.py            (writes synthetic_train.json / synthetic_test.json)
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from navigator.guidelines import classify, concordance  # noqa: E402
from navigator.schema import Action, Finding  # noqa: E402

NF, SURV, CHAR, REF, HORM = (a.value for a in (Action.NO_FOLLOWUP, Action.IMAGING_SURVEILLANCE,
                                               Action.CHARACTERIZATION_IMAGING, Action.SPECIALIST_REFERRAL,
                                               Action.HORMONAL_WORKUP))


class Gen:
    def __init__(self, split, seed):
        self.split, self.r = split, random.Random(seed)

    # ---- phrase pools: (train variants, extra variants only used in the test split) ----
    def pick(self, train, extra=()):
        if self.split == "test" and extra and self.r.random() < 0.5:
            return self.r.choice(list(extra))
        return self.r.choice(list(train))

    def chance(self, p):
        return self.r.random() < p


def L(text, label):
    return (text, label)


# --------------------------------------------------------------------------- formatting helpers
def fmt_size(g: Gen, cm, short=None, allow_mm=True):
    """Returns a labelled SIZE piece. Long axis first."""
    use_mm = allow_mm and (cm < 1.5 and g.chance(0.6) or g.chance(0.2))
    if use_mm:
        a, b = f"{round(cm * 10):g}", (f"{round(short * 10):g}" if short else None)
        unit = g.pick(["mm"], ["millimetres", "millimeters"])
    else:
        a, b = f"{cm:g}", (f"{short:g}" if short else None)
        unit = g.pick(["cm"], ["centimetres"])
    if b:
        sep = g.pick([" x ", " x ", " × "], [" by "])
        return L(f"{a}{sep}{b} {unit}", "SIZE")
    return L(f"{a} {unit}", "SIZE")


def fmt_hu(g: Gen, hu, label):
    return L(g.pick([f"{hu} HU", f"{hu} HU", f"{hu} Hounsfield units"], [f"HU {hu}", f"{hu} H.U."]), label)


def pre_cue(g):
    return g.pick(["on unenhanced images", "on non-contrast images", "precontrast", "on the non-contrast phase"],
                  ["prior to contrast", "on native images"])


def post_cue(g):
    return g.pick(["on portal venous images", "after contrast", "on the nephrographic phase", "post-contrast"],
                  ["following IV contrast", "in the venous phase"])


NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


# --------------------------------------------------------------------------- organ samplers
# Each returns dict(header, pieces, gold, imp_pieces) where imp_pieces names the lesion in the impression.

def side_word(g, side):
    return L(side, "SIDE") if side in ("left", "right") else ""


def kidney(g: Gen, ctx):
    used = ctx.setdefault("kidney_sides", [])
    side = g.r.choice([x for x in ("left", "right") if x not in used])
    used.append(side)
    pole = g.pick(["upper pole", "lower pole", "interpolar region", "mid kidney"], ["lower pole cortex"])
    gold = {"organ": "kidney", "side": side}
    phase = ctx["contrast"]
    kinds = ["simple", "septa", "septa", "wall", "nodule", "fat", "tiny"] + (["solid"] * 3 if phase == "both" else [])
    if phase == "without":
        kinds.append("dense")
    kind = g.r.choice(kinds)
    size = round(g.r.uniform(0.8, 6.0), 1)
    gold["size_cm"] = size
    style = g.r.choice(["loc", "loc", "adj", "header"])
    header = "Kidneys"
    if style == "header":   # "Right kidney: 3.0 cm cystic lesion in the lower pole ..."
        header = [L(side.capitalize(), "SIDE"), " ", L("kidney", "ORG_KIDNEY")]
        loc = [f"in the {pole}"]
    elif style == "adj":    # "... in the lower pole of the right kidney" / "right renal ..."
        loc = [f"in the {pole} of the ", L(side, "SIDE"), " ", L("kidney", "ORG_KIDNEY")]
    else:
        head = [L(g.pick(["kidney", "kidney", "renal"], ["renal parenchyma"]), "ORG_KIDNEY")]
        loc = ["in the ", side_word(g, side), " ", *head, f" {pole}"]
    p = []
    if kind == "simple":
        hu = g.r.randint(0, 18)
        lab = "HU_PRE" if phase == "without" else "HU_POST"
        gold.update(composition="cystic", homogeneous=True)
        gold["unenhanced_hu" if lab == "HU_PRE" else "enhanced_hu"] = hu
        p = [fmt_size(g, size), " ", L("homogeneous", "HOMOG"), " ",
             L(g.pick(["cyst", "cystic lesion"], ["fluid-density cyst"]), "CYSTIC"), " ", *loc, " measuring ",
             fmt_hu(g, hu, lab), ", ", g.pick(["with an imperceptible wall", "with a thin smooth wall"],
                                              ["thin-walled"]), "."]
    elif kind == "septa":
        n = g.r.randint(1, 6)
        mm = g.r.choice([1, 2, 2, 3])
        gold.update(composition="cystic", septa_count=n, septa_mm=mm)
        nword = NUM_WORDS[n] if g.chance(0.5) else str(n)
        sep = "septum" if n == 1 else "septa"
        if n == 1:
            nword = g.pick(["a single", "one", "a"])
        septa = g.r.choice([
            [" with ", L(nword, "SEPTA_N"), " ", g.pick(["thin", "smooth"], ["fine"]), f" {sep} up to ",
             L(f"{mm} mm", "SEPTA_MM"), " thick"],
            [" with ", L(nword, "SEPTA_N"), " thin (", L(f"{mm} mm", "SEPTA_MM"), f") {sep}"],
            [" with ", L(nword, "SEPTA_N"), " ", L(f"{mm} mm", "SEPTA_MM"), f" {g.pick(['enhancing', 'smooth'])} {sep}"]])
        if g.chance(0.5):
            p = [L(g.pick(["Cystic lesion", "Cyst"], ["Complex cyst"]), "CYSTIC"), " ", *loc, " measuring ",
                 fmt_size(g, size), *septa, "."]
        else:
            p = [fmt_size(g, size), " ", L(g.pick(["cystic lesion", "cyst"]), "CYSTIC"), " ", *loc, *septa, "."]
    elif kind == "wall":
        mm = g.r.choice([3, 4, 5, 6])
        gold.update(composition="cystic", wall_mm=mm)
        irr = g.chance(0.4)
        if irr:
            gold["irregular_wall_or_septa"] = True
        part = g.pick(["wall", "wall", "septum"])
        if part == "septum":
            gold.pop("wall_mm")
            gold.update(septa_mm=mm, septa_count=1)
        lab = "WALL_MM" if part == "wall" else "SEPTA_MM"
        p = [fmt_size(g, size), " ", L(g.pick(["cystic lesion", "cyst"], ["cystic mass"]), "CYSTIC"), " ", *loc,
             " with ", L("a", "SEPTA_N") if part == "septum" else "a", " ",
             L("irregular", "IRREG") if irr else "smooth", ", ",
             g.pick(["thickened", "thick", "enhancing"]), " ", L(f"{mm} mm", lab), f" {g.pick(['enhancing ', ''])}{part}",
             "."]
    elif kind == "nodule":
        gold.update(composition="cystic", enhancing_nodule=True)
        p = [fmt_size(g, size), " ", L(g.pick(["cystic mass", "cystic lesion"], ["cystic renal lesion"]), "CYSTIC"),
             " ", *loc, " containing an ", L(g.pick(["enhancing mural nodule", "enhancing soft tissue nodule"],
                                                     ["nodular enhancing soft tissue component"]), "ENH_NODULE"), "."]
    elif kind == "fat":
        gold.update(macroscopic_fat=True)
        p = [fmt_size(g, size), " lesion ", *loc, " containing ",
             L(g.pick(["macroscopic fat", "fat"], ["gross fat"]), "FAT")]
        if g.chance(0.5):
            hu = g.r.randint(-90, -30)
            lab = "HU_PRE" if phase == "without" else "HU_POST"
            gold["unenhanced_hu" if lab == "HU_PRE" else "enhanced_hu"] = hu
            p += [" (", fmt_hu(g, hu, lab), ")"]
        p += [", consistent with angiomyolipoma."]
    elif kind == "tiny":
        size = round(g.r.uniform(0.3, 0.9), 1)
        gold.update(size_cm=size, too_small_to_characterize=True)
        p = [fmt_size(g, size), " hypodense lesion ", *loc, ", ",
             L(g.pick(["too small to characterize", "too small to characterise"], ["too small to accurately characterize"]),
               "TOO_SMALL"), "."]
    elif kind == "dense":
        hu = g.r.randint(72, 95)
        gold.update(homogeneous=True, unenhanced_hu=hu)
        p = [fmt_size(g, size), " ", L("homogeneous", "HOMOG"), " hyperdense lesion ", *loc, " measuring ",
             fmt_hu(g, hu, "HU_PRE"), "."]
    else:  # solid enhancing
        size = round(g.r.uniform(0.6, 5.0), 1)
        gold["size_cm"] = size
        pre, post = g.r.randint(25, 40), None
        post = pre + g.r.choice([5, 8, 12, 25, 40, 70])
        gold.update(composition="solid", unenhanced_hu=pre, enhanced_hu=post)
        p = [fmt_size(g, size), " ", L(g.pick(["solid", "solid-appearing"], ["soft-tissue density"]), "SOLID"),
             " mass ", *loc, " measuring ", fmt_hu(g, pre, "HU_PRE"), " ", pre_cue(g), " and ",
             fmt_hu(g, post, "HU_POST"), " ", post_cue(g), "."]
    cystic = gold.get("composition") == "cystic"
    noun = [" ", L(g.pick(["cyst", "cystic lesion", "cystic mass"]), "CYSTIC")] if cystic and g.chance(0.6) else \
        [g.pick([" lesion", " mass"])]
    cat = classify(Finding(**gold)).category
    desc = [f", {cat.split(' (')[0]}"] if cat.startswith("Bosniak") and g.chance(0.5) else []
    if cat.startswith("Solid enhancing") and g.chance(0.5):
        desc = [", suspicious for renal cell carcinoma"]
    imp = [g.pick(["", "", "Enhancing ", "Simple "]) if False else "", L(side.capitalize(), "SIDE"), " ",
           L("renal", "ORG_KIDNEY"), *noun, *desc]
    return dict(header=header, pieces=p, gold=gold, imp=imp, opp="right" if side == "left" else "left")


def adrenal(g: Gen, ctx):
    side = g.r.choice(["left", "right"])
    gold = {"organ": "adrenal", "side": side}
    phase = ctx["contrast"]
    kinds = ["small", "fat", "large"] + (["pre"] * 3 if phase in ("without", "both") else ["post"] * 2)
    kind = g.r.choice(kinds)
    size = round(g.r.uniform(1.1, 3.8), 1)
    if kind == "small":
        size = round(g.r.uniform(0.5, 0.9), 1)
    if kind == "large":
        size = round(g.r.uniform(4.0, 7.0), 1)
    gold["size_cm"] = size
    org = L(g.pick(["adrenal"], ["suprarenal"]), "ORG_ADRENAL")
    noun = g.pick(["nodule", "mass"], ["lesion"])
    header = "Adrenals"
    if g.chance(0.25):
        header = [L(side.capitalize(), "SIDE"), " ", L("adrenal", "ORG_ADRENAL")]
        p = [fmt_size(g, size), " ", noun]
    elif g.chance(0.3):
        p = [noun.capitalize(), " in the ", side_word(g, side), " ", org, " gland measuring ", fmt_size(g, size)]
    else:
        p = [fmt_size(g, size), " ", side_word(g, side), " ", org, " ", noun]
    if kind == "pre":
        hu = g.r.randint(-8, 35)
        gold.update(unenhanced_hu=hu, homogeneous=True)
        p += [", ", L("homogeneous", "HOMOG"), ", ", fmt_hu(g, hu, "HU_PRE"), " ", pre_cue(g), "."]
    elif kind == "post":
        hu = g.r.randint(35, 90)
        gold["enhanced_hu"] = hu
        p += [" measuring ", fmt_hu(g, hu, "HU_POST"), " ", post_cue(g), "."]
    elif kind == "fat":
        gold["macroscopic_fat"] = True
        p += [" containing ", L(g.pick(["macroscopic fat", "bulk fat"], ["gross fat"]), "FAT"),
              ", consistent with myelolipoma."]
    elif kind == "large":
        het = g.chance(0.6)
        if het:
            gold["homogeneous"] = False
            p += [", ", L(g.pick(["heterogeneous"], ["inhomogeneous"]), "HETEROG"), "."]
        else:
            p += ["."]
    else:
        p += ["."]
    imp = [L(side.capitalize(), "SIDE"), " ", L("adrenal", "ORG_ADRENAL"), g.pick([" nodule", " lesion", " mass"])]
    return dict(header=header, pieces=p, gold=gold, imp=imp, opp="right" if side == "left" else "left")


LOBES = {"right": ["upper lobe", "middle lobe", "lower lobe"], "left": ["upper lobe", "lower lobe", "lingula"]}


def lung(g: Gen, ctx):
    side = g.r.choice(["left", "right"])
    lobe = g.r.choice(LOBES[side])
    ntype = g.r.choice(["solid", "solid", "solid", "ground-glass", "part-solid"])
    multiple = g.chance(0.25)
    mm = g.r.choice([3, 4, 5, 6, 7, 8, 9, 11, 14, 18])
    cm = mm / 10
    gold = {"organ": "lung", "side": side, "size_cm": cm, "patient_risk": ctx.get("lung_risk", "unknown")}
    short = None
    if g.chance(0.3) and mm >= 5:
        short = (mm - g.r.randint(1, 3)) / 10
        gold["short_axis_cm"] = short
    if ntype != "solid":
        gold["nodule_type"] = ntype
    if multiple:
        gold["multiple"] = True
    tword = {"solid": g.pick(["solid"], ["soft-tissue attenuation"]),
             "ground-glass": g.pick(["ground-glass", "pure ground-glass"], ["nonsolid"]),
             "part-solid": g.pick(["part-solid"], ["semisolid"])}[ntype]
    tlab = {"solid": "NOD_SOLID", "ground-glass": "NOD_GGO", "part-solid": "NOD_PARTSOLID"}[ntype]
    loc = ["in the ", L(side, "SIDE"), " ", L(lobe, "ORG_LUNG")]
    if multiple:
        p = [L(g.pick(["Multiple", "Several"], ["Numerous"]), "MULTIPLE"), " ", L(tword, tlab), " ",
             g.pick(["pulmonary nodules", "nodules"]), ", the largest ", fmt_size(g, cm, short), " ", *loc, "."]
    else:
        p = [fmt_size(g, cm, short), " ", L(tword, tlab), " ", g.pick(["nodule", "pulmonary nodule"]), " ", *loc]
        if ntype == "part-solid":
            sc = g.r.choice([2, 3, 4, 6, 7, 8])
            if sc < mm:
                gold["solid_component_mm"] = sc
                p += [" with a ", L(f"{sc} mm", "SOLIDPART"), " solid component"]
        p += ["."]
    imp = [L(side.capitalize(), "SIDE"), " ", L(lobe, "ORG_LUNG"), " nodule"]
    return dict(header="Lungs", pieces=p, gold=gold, imp=imp)


def liver(g: Gen, ctx):
    gold = {"organ": "liver", "patient_risk": ctx.get("liver_risk", "unknown")}
    seg = g.r.choice(["segment 2", "segment 4a", "segment 5", "segment 6", "segment 7", "segment 8"])
    size = round(g.r.choice([g.r.uniform(0.4, 0.9), g.r.uniform(1.0, 1.5), g.r.uniform(1.6, 4.5)]), 1)
    gold["size_cm"] = size
    kinds = ["word_benign", "suspicious", "flash", "indet"]
    if ctx["modality"] != "MRI":
        kinds += ["hu_benign", "hu_susp"]
    kind = g.r.choice(kinds)
    org = L(g.pick(["hepatic", "liver"], ["hepatic parenchymal"]), "ORG_LIVER")
    lead = [fmt_size(g, size), " "]
    if kind == "hu_benign":
        hu = g.r.randint(2, 18)
        gold.update(homogeneous=True, enhanced_hu=hu)
        p = lead + [L("homogeneous", "HOMOG"), " ", g.pick(["hypodense", "low-attenuation"]), " ", org,
                    f" lesion in {seg}, sharply marginated, measuring ", fmt_hu(g, hu, "HU_POST"), "."]
    elif kind == "word_benign":
        gold["appearance"] = "benign"
        p = lead + [org, f" lesion in {seg} with ",
                    L(g.pick(["peripheral nodular discontinuous enhancement, typical of haemangioma",
                              "features of focal fatty sparing", "a central scar, typical of FNH"],
                             ["classic haemangioma enhancement pattern"]), "APPEAR_BENIGN"), "."]
    elif kind == "suspicious":
        gold["appearance"] = "suspicious"
        p = lead + [L(g.pick(["ill-defined, heterogeneous", "ill-defined", "heterogeneous enhancing"],
                             ["poorly marginated"]), "APPEAR_SUSP"), " ", org, f" lesion in {seg}."]
    elif kind == "hu_susp":
        hu = g.r.randint(40, 80)
        gold["enhanced_hu"] = hu
        p = lead + [org, f" lesion in {seg} measuring ", fmt_hu(g, hu, "HU_POST"), " ", post_cue(g), "."]
    elif kind == "flash":
        gold["appearance"] = "flash-filling"
        p = lead + [org, f" lesion in {seg} with ",
                    L(g.pick(["uniform arterial hyperenhancement (flash-filling)", "flash-filling arterial enhancement"],
                             ["homogeneous early arterial enhancement"]), "APPEAR_FLASH"),
                    ", isodense on later phases."]
    else:
        gold["appearance"] = "indeterminate"
        p = lead + [g.pick(["hypodense"]), " ", org, f" lesion in {seg}, ",
                    L(g.pick(["indeterminate on this single-phase study", "incompletely characterized"],
                             ["not fully characterisable on this exam"]), "APPEAR_INDET"), "."]
    if ctx["modality"] == "PET-CT":
        avid = g.chance(0.5)
        gold["fdg_avid"] = avid
        p = p[:-1] + [", ", L("FDG-avid (SUVmax 6.1)", "FDG_POS") if avid else L("without FDG uptake", "FDG_NEG"), "."]
    imp = [L(g.pick(["Hepatic", "Liver"]), "ORG_LIVER"), " lesion"]
    return dict(header="Liver", pieces=p, gold=gold, imp=imp)


def pancreas(g: Gen, ctx):
    gold = {"organ": "pancreas", "patient_age": ctx["age"]}
    part = g.r.choice(["head", "body", "tail", "uncinate process"])
    size = round(g.r.choice([g.r.uniform(0.4, 1.4), g.r.uniform(1.5, 2.5), g.r.uniform(2.6, 4.0)]), 1)
    gold["size_cm"] = size
    p = [fmt_size(g, size), " ", L(g.pick(["cystic lesion", "cyst"], ["unilocular cyst"]), "CYSTIC"),
         f" in the {part} of the ", L("pancreas", "ORG_PANCREAS")]
    gold["composition"] = "cystic"
    extra = g.r.choice(["none", "none", "none", "duct", "mural", "solid", "wall"])
    if extra == "mural":
        gold["mural_nodule"] = True
        p += [" with a ", L(g.pick(["non-enhancing mural nodule"], ["nonenhancing nodule along the wall"]), "MURAL")]
    elif extra == "solid":
        gold["enhancing_nodule"] = True
        p += [" with an ", L(g.pick(["enhancing solid component", "enhancing mural nodule"]), "ENH_NODULE")]
    elif extra == "wall":
        gold["irregular_wall_or_septa"] = True
        p += [" with a ", L(g.pick(["thickened, enhancing wall"], ["thick enhancing rim"]), "IRREG")]
    p += ["."]
    if extra == "duct" or g.chance(0.4):
        mm = g.r.choice([7, 8, 11]) if extra == "duct" else g.r.choice([2, 3, 4])
        gold["duct_mm"] = mm
        p += [" ", g.pick(["The main pancreatic duct measures", "Main duct calibre"], ["The MPD measures"]), " ",
              L(f"{mm} mm", "DUCT"), "."]
    imp = [L("Pancreatic", "ORG_PANCREAS"), " cyst"]
    return dict(header="Pancreas", pieces=p, gold=gold, imp=imp)


def thyroid(g: Gen, ctx):
    side = g.r.choice(["left", "right"])
    gold = {"organ": "thyroid", "side": side, "patient_age": ctx["age"]}
    size = round(g.r.choice([g.r.uniform(0.5, 0.9), g.r.uniform(1.0, 1.4), g.r.uniform(1.5, 3.5)]), 1)
    gold["size_cm"] = size
    p = [fmt_size(g, size), " ", g.pick(["hypodense", "low-attenuation"], ["hypoattenuating"]), " nodule in the ",
         L(side, "SIDE"), " ", L(g.pick(["thyroid lobe", "lobe of the thyroid"], ["thyroid"]), "ORG_THYROID")]
    if g.chance(0.15):
        gold["appearance"] = "suspicious"
        p += [" with ", L(g.pick(["adjacent abnormal lymph nodes", "extrathyroidal extension"],
                                 ["invasion of adjacent soft tissue"]), "APPEAR_SUSP")]
    if ctx["modality"] == "PET-CT":
        avid = g.chance(0.5)
        gold["fdg_avid"] = avid
        p += [", ", L("with focal FDG uptake", "FDG_POS") if avid else L("without FDG uptake", "FDG_NEG")]
    p += ["."]
    if ctx.get("limited"):
        gold["limited_life_expectancy"] = True
    imp = [L(side.capitalize(), "SIDE"), " ", L("thyroid", "ORG_THYROID"), " nodule"]
    return dict(header="Thyroid", pieces=p, gold=gold, imp=imp)


def pituitary(g: Gen, ctx):
    gold = {"organ": "pituitary"}
    size = round(g.r.choice([g.r.uniform(0.3, 0.9), g.r.uniform(1.0, 2.5)]), 1)
    gold["size_cm"] = size
    p = [fmt_size(g, size), " ", g.pick(["hypoenhancing lesion", "non-enhancing lesion"], ["focal hypoenhancement"]),
         " in the ", L(g.pick(["pituitary gland", "pituitary"], ["adenohypophysis"]), "ORG_PITUITARY")]
    if size >= 1 and g.chance(0.4):
        gold["chiasm_contact"] = True
        p += [" which ", L(g.pick(["abuts the optic chiasm", "contacts the optic chiasm"],
                                  ["elevates the chiasm"]), "CHIASM")]
    elif size >= 1:
        p += [", ", g.pick(["remote from the optic chiasm", "with clearance below the chiasm"])]
    p += [", consistent with ", g.pick(["an adenoma", "a pituitary adenoma"]), "."]
    imp = [L("Pituitary", "ORG_PITUITARY"), g.pick([" adenoma", " lesion"])]
    return dict(header="Sella", pieces=p, gold=gold, imp=imp)


def brain(g: Gen, ctx):
    side = g.r.choice(["left", "right"])
    gold = {"organ": "brain", "side": side}
    size = round(g.r.uniform(0.8, 3.5), 1)
    gold["size_cm"] = size
    site = g.r.choice(["frontal convexity", "parietal convexity", "falx", "sphenoid wing", "tentorium"])
    p = [fmt_size(g, size), " ", L(g.pick(["extra-axial dural-based", "dural-based extra-axial"],
                                          ["extra-axial"]), "ORG_BRAIN"),
         " enhancing mass along the ", L(side, "SIDE"), f" {site}, ",
         g.pick(["consistent with a meningioma", "likely meningioma"], ["most in keeping with meningioma"])]
    if ctx["prior"]:
        if g.chance(0.4):
            gold["growth"] = True
            prior = round(size - g.r.uniform(0.3, 0.7), 1)
            p += [", ", L(f"increased from {prior:g} cm on the prior study", "GROWTH")]
        else:
            p += [", ", g.pick(["unchanged from the prior study", "stable compared with prior"])]
    p += ["."]
    if ctx.get("neuro_sympt"):
        gold["symptomatic"] = True
    imp = [L(side.capitalize(), "SIDE"), " ", L(g.pick(["meningioma"]), "ORG_BRAIN")]
    return dict(header="Brain", pieces=p, gold=gold, imp=imp)


BONES = [("femur", True), ("humerus", True), ("iliac bone", True), ("rib", True), ("T10 vertebral body", False),
         ("L3 vertebral body", False), ("sacrum", False), ("calvarium", False)]


def bone(g: Gen, ctx):
    site, sided = g.r.choice(BONES)
    side = g.r.choice(["left", "right"]) if sided else "unknown"
    gold = {"organ": "bone", "side": side, "patient_risk": "high" if ctx.get("cancer") else "unknown"}
    size = round(g.r.uniform(0.6, 4.0), 1)
    gold["size_cm"] = size
    dens = g.r.choice(["lucent", "sclerotic", "mixed"])
    gold["bone_density"] = dens
    dw = {"lucent": g.pick(["lucent", "lytic"], ["radiolucent"]), "sclerotic": g.pick(["sclerotic", "dense"],
          ["blastic"]), "mixed": g.pick(["mixed lytic-sclerotic"], ["mixed density"])}[dens]
    org = [side_word(g, side), " " if sided else "", L(site, "ORG_BONE")]
    p = [fmt_size(g, size), " ", L(dw, "DENS_" + dens.upper()), " lesion in the ", *org]
    kind = g.r.choice(["benign_hu", "benign_word", "susp", "plain"])
    if kind == "benign_hu" and ctx["modality"] != "MRI" and dens in ("sclerotic", "lucent"):
        hu = g.r.randint(900, 1300) if dens == "sclerotic" else g.r.randint(-90, -30)
        gold["unenhanced_hu"] = hu
        p += [" measuring ", fmt_hu(g, hu, "HU_PRE")]
    elif kind == "benign_word":
        gold["appearance"] = "benign"
        p += [", ", L(g.pick(["consistent with a bone island", "typical of a non-ossifying fibroma",
                              "with coarsened vertical trabeculae typical of haemangioma"],
                             ["classic appearance of an enostosis"]), "APPEAR_BENIGN")]
    elif kind == "susp":
        gold["appearance"] = "suspicious"
        p += [" with ", L(g.pick(["cortical destruction", "aggressive periosteal reaction",
                                  "extraosseous soft tissue extension"], ["cortical breakthrough"]), "APPEAR_SUSP")]
    p += ["."]
    imp = ([L(side.capitalize(), "SIDE"), " "] if sided else []) + [L(site, "ORG_BONE"), " lesion"]
    return dict(header="Bones", pieces=p, gold=gold, imp=imp)


SAMPLERS = {"kidney": kidney, "adrenal": adrenal, "lung": lung, "liver": liver, "pancreas": pancreas,
            "thyroid": thyroid, "pituitary": pituitary, "brain": brain, "bone": bone}

EXAMS = [  # (modality, exam title template, organs that can appear, normal-organ filler headers)
    ("CT", "CT abdomen and pelvis {c}", ["kidney", "adrenal", "liver", "pancreas", "bone"],
     ["Spleen", "Bowel", "Bladder", "Gallbladder"]),
    ("MRI", "MRI abdomen {c}", ["liver", "pancreas"], ["Spleen", "Gallbladder", "Biliary tree"]),
    ("CT", "CT chest {c}", ["lung", "thyroid", "adrenal", "bone"], ["Heart", "Mediastinum", "Pleura"]),
    ("CT", "CT chest, abdomen and pelvis {c}", ["lung", "liver", "kidney", "adrenal", "pancreas", "bone"],
     ["Spleen", "Mediastinum", "Bowel"]),
    ("CT", "CT neck {c}", ["thyroid", "bone"], ["Salivary glands", "Airway", "Lymph nodes"]),
    ("MRI", "MRI brain {c}", ["brain", "pituitary"], ["Ventricles", "Brain parenchyma", "Orbits"]),
    ("CT", "CT head {c}", ["brain", "pituitary"], ["Ventricles", "Brain parenchyma", "Sinuses"]),
    ("MRI", "MRI pituitary {c}", ["pituitary"], ["Cavernous sinuses", "Brain parenchyma"]),
    ("PET-CT", "FDG PET-CT skull base to mid-thigh", ["lung", "liver", "thyroid", "bone", "adrenal"],
     ["Mediastinum", "Spleen", "Bowel"]),
    ("MRI", "MRI lumbar spine {c}", ["bone"], ["Discs", "Spinal canal"]),
]

CONTRAST = {"with": ["with IV contrast", "with contrast, portal venous phase", "with contrast"],
            "without": ["without contrast", "non-contrast"],
            "both": ["with and without IV contrast", "multiphase (unenhanced and portal venous)"]}

INDICATIONS = ["Abdominal pain.", "Cough.", "Trauma.", "Headache.", "Fever of unknown origin.", "Weight loss.",
               "Dizziness.", "Back pain.", "Shortness of breath."]


def actions_options(gold):
    """Concordant, under-call and over-call action sets for this finding."""
    g = classify(Finding(**gold))
    conc = [list(a) for a in [g.actions, *g.alternatives]]
    req = set(g.actions) - {Action.NO_FOLLOWUP}
    under, over = [[]], []
    if req:
        if Action.SPECIALIST_REFERRAL in req:
            under += [[Action.IMAGING_SURVEILLANCE], [Action.NO_FOLLOWUP]]
        if req & {Action.IMAGING_SURVEILLANCE, Action.CHARACTERIZATION_IMAGING}:
            under += [[Action.NO_FOLLOWUP]]
        if Action.HORMONAL_WORKUP in req:
            under += [[a for a in g.actions if a != Action.HORMONAL_WORKUP] or [Action.NO_FOLLOWUP]]
        over = [[Action.SPECIALIST_REFERRAL]] if Action.SPECIALIST_REFERRAL not in req else []
    else:
        over = [[Action.IMAGING_SURVEILLANCE], [Action.SPECIALIST_REFERRAL]]
    return conc, under, over


# Each template: text with [brackets] around the labelled key phrase.
ACTION_TEXT = {
    NF: (["[No follow-up needed].", "[No further imaging] is required.", "[No further work-up] is necessary.",
          "[no follow-up].", "[No follow-up]."], ["[Requires no additional evaluation]."]),
    SURV: (["Recommend [follow-up {m} in {t}].", "Suggest [surveillance {m} in {t}].",
            "[Follow-up {m} in {t}] is recommended.", "Recommend [follow-up imaging in {t}].",
            "[Repeat {m} in {t}]."], ["[Interval {m} in {t}] advised."]),
    CHAR: (["Recommend [{c}].", "[Further characterization with {c}] is recommended.", "[{C}] recommended.",
            "Suggest [{c}] to further evaluate."], ["[{C} for characterisation] would help."]),
    REF: (["[{R} referral] recommended.", "Recommend [referral to {r}].", "[{R} referral].",
           "[Refer to {r}]."], ["Please consider [discussion with {r}]."]),
    HORM: (["Recommend [{h}].", "[{H}] is advised.", "Suggest [{h}]."], ["[Laboratory {h}] suggested."]),
}
CHAR_WORDS = {"kidney": ["renal mass protocol CT or MRI", "dedicated renal MRI", "renal ultrasound"],
              "adrenal": ["adrenal washout CT", "chemical-shift MRI", "dedicated adrenal protocol CT"],
              "liver": ["liver MRI", "contrast-enhanced MRI"], "thyroid": ["thyroid ultrasound",
              "dedicated thyroid ultrasound"], "bone": ["MRI", "bone scintigraphy"], "pituitary": ["dedicated pituitary MRI"],
              "lung": ["PET-CT"], "pancreas": ["pancreatic protocol MRI", "MRCP"], "brain": ["contrast-enhanced MRI"]}
REF_WORDS = {"kidney": ["urology", "urology"], "adrenal": ["endocrine surgery", "the endocrine MDT"],
             "lung": ["pulmonology", "the lung nodule clinic"], "liver": ["hepatology", "biopsy"],
             "pancreas": ["gastroenterology for EUS-FNA", "surgical consultation"], "thyroid": ["endocrinology for FNA"],
             "pituitary": ["neurosurgery", "the pituitary MDT"], "brain": ["neurosurgery"],
             "bone": ["orthopaedic oncology", "biopsy"]}
HORM_WORDS = ["hormonal work-up", "biochemical evaluation for hormone excess", "endocrine evaluation",
              "1 mg dexamethasone suppression test", "pituitary hormone panel"]


def action_pieces(g: Gen, act, organ, two=None):
    """Returns labelled pieces for one recommendation sentence (optionally two actions in one sentence)."""
    tr, ex = ACTION_TEXT[act]
    t = g.pick(tr, ex)
    m = g.pick(["CT", "MRI"] if organ not in ("brain", "pituitary") else ["MRI"])
    c = g.r.choice(CHAR_WORDS[organ])
    r = g.r.choice(REF_WORDS[organ])
    h = g.r.choice(HORM_WORDS)
    t = (t.replace("{m}", m).replace("{t}", g.pick(["6 months", "12 months", "3-6 months", "one year"]))
          .replace("{C}", c[0].upper() + c[1:]).replace("{c}", c).replace("{R}", r[0].upper() + r[1:])
          .replace("{r}", r).replace("{H}", h[0].upper() + h[1:]).replace("{h}", h))
    a, rest = t.split("[", 1)
    key, b = rest.split("]", 1)
    if two and act in (CHAR, SURV, REF) and b == "." and a.startswith("Recommend"):
        hh = g.r.choice(HORM_WORDS)
        return [a, L(key, "ACT_" + act), " and ", L(hh, "ACT_" + two), "."]
    return [a, L(key, "ACT_" + act), b]


IMP_EXTRA = ["No acute abnormality.", "Mild colitis.", "Uncomplicated sigmoid diverticulitis.", "No pulmonary embolism.",
             "No acute intracranial abnormality.", "Moderate stool burden.", "No fracture."]
DISTRACT = {
    "kidney": ["No hydronephrosis.", "No calculi.", "{Opp} kidney normal.", "3 mm non-obstructing {opp} lower pole calculus.",
               "No hydronephrosis or calculi."],
    "adrenal": ["{Opp} adrenal normal.", "Contralateral adrenal gland unremarkable."],
    "lung": ["No pleural effusion.", "Mild centrilobular emphysema.", "No consolidation."],
    "liver": ["Mild hepatic steatosis.", "Patent portal vein.", "No biliary dilatation."],
    "pancreas": ["No peripancreatic inflammation.", "No pancreatic atrophy."],
    "thyroid": ["{Opp} thyroid lobe unremarkable.", "No cervical lymphadenopathy."],
    "pituitary": ["Normal pituitary stalk.", "Normal posterior pituitary bright spot."],
    "brain": ["No acute infarct.", "No hydrocephalus.", "Mild small vessel disease."],
    "bone": ["Degenerative changes of the spine.", "No acute fracture."],
}
ORGAN_HEADER = {"kidney": "Kidneys", "adrenal": "Adrenals", "lung": "Lungs", "liver": "Liver", "pancreas": "Pancreas",
                "thyroid": "Thyroid", "pituitary": "Sella", "brain": "Brain", "bone": "Bones"}
DESCRIPTOR = [", likely benign", ", indeterminate", "", "", "", ", incidental", ", suspicious for malignancy",
              ", consistent with adenoma", ", likely cyst"]


def make_report(g: Gen, rid):
    target = g.r.choice(list(SAMPLERS))            # balance organs: pick the organ first, then a fitting exam
    modality, title, organs, fillers = g.r.choice([e for e in EXAMS if target in e[2]])
    contrast = g.r.choice(list(CONTRAST))
    if modality == "PET-CT":
        contrast = "without"
    exam = title.format(c=g.r.choice(CONTRAST[contrast])) if "{c}" in title else title
    n = g.r.choices([1, 2, 3], [0.65, 0.28, 0.07])[0]
    chosen = [target]
    for _ in range(n - 1):
        o = g.r.choice(organs)
        if o != "kidney" and o in chosen or chosen.count("kidney") >= 2:
            continue
        chosen.append(o)
    # patient context
    ctx = {"modality": modality, "contrast": contrast, "age": None, "prior": g.chance(0.4)}
    ind, ind_pieces = g.r.choice(INDICATIONS), []
    age = g.r.randint(25, 88)
    if any(o in ("pancreas", "thyroid") for o in chosen) or g.chance(0.5):
        ctx["age"] = age
        ind_pieces += [L(str(age), "AGE"), g.pick(["-year-old", " year old"], ["-yr-old"]), " ",
                       g.pick(["man", "woman", "patient"]), ". "]
    risk_kind = g.r.choice(["none", "none", "smoker", "never", "cancer", "liverdz", "liverlow"])
    if "lung" in chosen and risk_kind == "cancer":
        risk_kind = "none"   # Fleischner does not apply to known cancer
    if risk_kind == "smoker":
        ind_pieces += [L(g.pick(["Heavy smoker", "40 pack-year smoking history"], ["Current smoker"]), "RISK_SMOKER"), ". "]
        ctx["lung_risk"] = "high"
    elif risk_kind == "never":
        ind_pieces += [L(g.pick(["Never smoker", "Lifelong non-smoker"], ["No smoking history"]), "RISK_NONSMOKER"), ". "]
        ctx["lung_risk"] = "low"
    elif risk_kind == "cancer":
        ind_pieces += [L(g.pick(["Known colorectal cancer", "History of breast cancer", "Staging of lung cancer"],
                                ["Known melanoma"]), "RISK_CANCER"), ". "]
        ctx["liver_risk"], ctx["cancer"] = "high", True
    elif risk_kind == "liverdz":
        ind_pieces += [L(g.pick(["Known cirrhosis", "Chronic hepatitis B"], ["Alcohol-related liver disease"]),
                         "RISK_LIVERDZ"), ". "]
        ctx["liver_risk"] = "high"
    elif risk_kind == "liverlow":
        ind_pieces += [L(g.pick(["No history of malignancy or liver disease"], ["No known cancer or liver disease"]),
                         "RISK_LIVERLOW"), ". "]
        ctx["liver_risk"] = "low"
    if "thyroid" in chosen and g.chance(0.12):
        ind_pieces += [L(g.pick(["Limited life expectancy", "Receiving palliative care"]), "LIMITED_LE"), ". "]
        ctx["limited"] = True
    if "brain" in chosen and g.chance(0.2):
        ind_pieces += [L(g.pick(["New focal seizures", "Progressive left-sided weakness"], ["New-onset seizures"]),
                         "SYMPT"), ". "]
        ctx["neuro_sympt"] = True
    ind_pieces += [ind]

    finds = [SAMPLERS[o](g, ctx) for o in chosen]
    for f, o in zip(finds, chosen):
        f["organ"] = o
    pieces = [f"EXAM: {exam}.\n", "INDICATION: ", *ind_pieces, "\n"]
    if ctx["prior"]:
        pieces.append(f"COMPARISON: {g.pick(['Prior study from 2024.', 'CT from 14 months ago.'])}\n")
    pieces.append("FINDINGS:\n")
    sections = {}
    for f in finds:
        key = f["header"] if isinstance(f["header"], str) else id(f)
        sections.setdefault(key, []).append(f)
    normal_orgs = [ORGAN_HEADER[o] for o in organs if o not in chosen]
    fill = g.r.sample(fillers, k=min(len(fillers), g.r.randint(1, 2))) + \
        g.r.sample(normal_orgs, k=min(len(normal_orgs), g.r.randint(0, 2)))
    keys = list(sections) + fill
    g.r.shuffle(keys)
    for k in keys:
        if k in sections:
            fs = sections[k]
            hdr = fs[0]["header"]
            pieces += ([hdr, ": "] if isinstance(hdr, str) else [*hdr, ": "])
            body = []
            if len(fs) == 2 and g.chance(0.5):  # two lesions in one sentence
                a, b = fs[0]["pieces"], fs[1]["pieces"]
                body += [*a[:-1], g.pick([" and a ", "; also a "], [", plus a "]), *b]
            else:
                for f in fs:
                    body += [*f["pieces"], " "]
            o = fs[0]["organ"]
            if g.chance(0.5):
                d = g.r.choice(DISTRACT[o])
                opp = fs[0].get("opp", "left")
                d = d.replace("{Opp}", opp.capitalize()).replace("{opp}", opp)
                body = ([d, " "] + body) if g.chance(0.5) else (body + [" ", d])
            pieces += body
        else:
            pieces.append(f"{k}: " + g.pick(["Normal.", "Unremarkable.", "No abnormality."]))
        pieces.append("\n")
    if "kidney" in organs and g.chance(0.3):
        pieces.append(g.pick(["Left kidney and adrenals: Normal.", "Right kidney: Normal.", "Left kidney: Unremarkable.",
                              "Adrenal glands: Normal.", "Right adrenal: Normal."]))
        pieces.append("\n")
    pieces.append("IMPRESSION:\n")
    golds, items = [], []
    if g.chance(0.4):
        items.append([g.r.choice(IMP_EXTRA)])
    for f in finds:
        conc, under, over = actions_options(f["gold"])
        kind = g.r.choices(["conc", "under", "over"], [0.6, 0.25, 0.15])[0]
        pool = {"conc": conc, "under": under, "over": over}[kind] or conc
        acts = [a.value if isinstance(a, Action) else a for a in g.r.choice(pool)]
        item = [*f["imp"], g.r.choice(DESCRIPTOR)]
        i = 0
        while i < len(acts):
            joiner = g.pick([". ", ". ", "; ", ", "])
            nxt = acts[i + 1] if i + 1 < len(acts) and acts[i + 1] == HORM else None
            ap = action_pieces(g, acts[i], f["organ"], two=nxt)
            if joiner != ". " and ap[0] == "":
                ap = ap[1:]
                ap[0] = (ap[0][0].lower() + ap[0][1:]) if isinstance(ap[0], str) else \
                    L(ap[0][0][0].lower() + ap[0][0][1:], ap[0][1])
            elif joiner != ". " and isinstance(ap[0], str):
                ap[0] = ap[0][:1].lower() + ap[0][1:]
            item += [joiner if i == 0 else " ", *ap]
            i += 2 if (nxt and any(isinstance(x, tuple) and x[1] == "ACT_" + HORM for x in ap)) else 1
        if not acts:
            item.append(".")
        items.append(item)
        gold = dict(f["gold"], modality=modality, stated_actions=acts)
        gold = {k: v for k, v in gold.items() if v not in (None, "unknown") or k == "side"}
        golds.append({"gold": gold, "expected_category": classify(Finding(**gold)).category})
    numbered = len(items) > 1 or g.chance(0.5)
    for i, it in enumerate(items, 1):
        pieces += ([f"{i}. "] if numbered else []) + it + ["\n" if numbered else " "]
    # render
    text, spans = "", []
    for pc in pieces:
        if not pc:
            continue
        if isinstance(pc, tuple):
            s, lab = pc
            spans.append([len(text), len(text) + len(s), lab])
            text += s
        else:
            text += pc
    return {"id": rid, "text": text.strip(), "spans": spans, "findings": golds}


def build(split, n, seed):
    g = Gen(split, seed)
    return [make_report(g, f"{'S' if split == 'train' else 'T'}{i:03d}") for i in range(1, n + 1)]


if __name__ == "__main__":
    out = ROOT / "data"
    train, test = build("train", 600, 11), build("test", 150, 2027)
    (out / "synthetic_train.json").write_text(json.dumps(train, indent=1))
    (out / "synthetic_test.json").write_text(json.dumps(test, indent=1))
    from collections import Counter
    for name, d in (("train", train), ("test", test)):
        c = Counter(x["gold"]["organ"] for r in d for x in r["findings"])
        st = Counter(concordance(Finding(**x["gold"]), classify(Finding(**x["gold"]))).status
                     for r in d for x in r["findings"])
        print(name, len(d), "reports", dict(c), dict(st))
