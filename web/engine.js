// JavaScript port of navigator/extract_rules.py + navigator/guidelines.py, for the browser demo.
// Keep in step with the Python; web/parity_check.js compares both on every sample report.
(function (root) {
  "use strict";

  const A = {
    NO_FOLLOWUP: "NO_FOLLOWUP",
    IMAGING_SURVEILLANCE: "IMAGING_SURVEILLANCE",
    CHARACTERIZATION_IMAGING: "CHARACTERIZATION_IMAGING",
    SPECIALIST_REFERRAL: "SPECIALIST_REFERRAL",
    HORMONAL_WORKUP: "HORMONAL_WORKUP",
  };
  const ORDER = Object.values(A);
  const LABELS = {
    NO_FOLLOWUP: "No follow-up",
    IMAGING_SURVEILLANCE: "Interval imaging surveillance",
    CHARACTERIZATION_IMAGING: "Dedicated characterization imaging",
    SPECIALIST_REFERRAL: "Specialist referral",
    HORMONAL_WORKUP: "Hormonal work-up",
  };

  // ------------------------------------------------------------------ reader
  const SIZE_RE = /(\d+(?:\.\d+)?)\s*cm\b/i;
  const HU_RE = /(-?\d+(?:\.\d+)?)\s*HU\b/g;
  const LESION_RE = /\b(lesion|cyst|mass|nodule|hypodensity|angiomyolipoma|myelolipoma)/i;
  const UNENH_RE = /unenhanced|non-?contrast|pre-?contrast|\bpre\b|without contrast/i;
  const ENH_RE = /nephrographic|portal|post-?contrast|\bpost\b|after contrast|enhanced phase|arterial/i;
  const SPLIT_IMPRESSION = /\n\s*(?:IMPRESSION|IMP)\s*:/i;
  const COUNT_WORDS = { a: 1, an: 1, one: 1, single: 1, two: 2, three: 3, four: 4, five: 5, six: 6,
    few: 2, several: 4, multiple: 4, many: 4 };
  const SEPTA_COUNT_RE = new RegExp(
    "\\b(a|an|one|single|two|three|four|five|six|few|several|multiple|many)\\b(\\s*\\((\\d+)\\))?" +
    "((?:[\\s,]+(?:thin|thick|thickened|smooth|irregular|enhancing|minimally|\\(?\\d+(?:\\.\\d+)?\\s*mm\\)?))*)[\\s,]+sept", "i");
  const ACTION_PATTERNS = [
    [A.SPECIALIST_REFERRAL, /urolog|referr|\brefer\b|surgical (consult|evaluation)|multidisciplinary|\bMDT\b/i],
    [A.HORMONAL_WORKUP, /dexamethasone|\bDST\b|biochemical|hormonal|metanephrine|aldosterone|endocrin/i],
    [A.IMAGING_SURVEILLANCE, /follow[- ]?up (CT|MRI|ultrasound|imaging|US)\b|in \d+ months|surveillance|repeat (CT|MRI|imaging)/i],
    [A.CHARACTERIZATION_IMAGING, /protocol (CT|MRI)|mass protocol|adrenal protocol|dedicated|further evaluat|\bMRI\b|characteri[sz]ation/i],
  ];
  const EXPLICIT_CHAR = /protocol|dedicated/i;
  const NO_FU_RE = /no (further )?(follow[- ]?up|imaging)|no further (imaging|evaluation|work)/i;

  function newFinding(organ, side, size) {
    return { organ, side, size_cm: size, composition: "indeterminate", unenhanced_hu: null, enhanced_hu: null,
      homogeneous: null, wall_mm: null, septa_count: null, septa_mm: null, irregular_wall_or_septa: false,
      enhancing_nodule: false, macroscopic_fat: false, too_small_to_characterize: false, stated_actions: [],
      reported_category: null };
  }

  const lines = (t) => t.split(/\r\n|\r|\n/);
  function sentences(text) {
    const out = [];
    for (const line of lines(text)) {
      for (const s of line.split(/(?<=[.;])\s+/)) if (s.trim()) out.push(s.trim());
    }
    return out;
  }
  function organOf(s) {
    if (/adrenal/i.test(s)) return "adrenal";
    if (/kidney|renal/i.test(s)) return "kidney";
    return null;
  }
  function sideOf(s) {
    let m = s.match(/\b(left|right)\b/i);
    if (m) return m[1].toLowerCase();
    m = s.match(/\b([LR])\b/);
    if (m) return m[1] === "L" ? "left" : "right";
    return "unknown";
  }
  function examPhase(header) {
    if (/with and without|without and with|w\/wo|multiphase|renal (mass )?protocol/i.test(header)) return null;
    if (/without (iv )?contrast|non-?contrast|stone protocol/i.test(header)) return "unenhanced";
    if (/contrast|portal venous/i.test(header)) return "enhanced";
    return null;
  }
  function mmFeatures(s, f) {
    const re = /(\d+(?:\.\d+)?)\s*mm\b/g;
    let m;
    while ((m = re.exec(s))) {
      const val = parseFloat(m[1]);
      const end = m.index + m[0].length;
      const after = s.slice(end, end + 35).toLowerCase();
      const before = s.slice(Math.max(0, m.index - 30), m.index).toLowerCase();
      const keys = ["wall", "sept", "nodul"];
      let hits = keys.filter((k) => after.indexOf(k) >= 0).map((k) => [after.indexOf(k), k]);
      if (!hits.length) hits = keys.filter((k) => before.lastIndexOf(k) >= 0).map((k) => [before.length - before.lastIndexOf(k), k]);
      if (!hits.length) continue;
      hits.sort((x, y) => x[0] - y[0] || (x[1] < y[1] ? -1 : 1));
      const kind = hits[0][1];
      if (kind === "wall") f.wall_mm = val;
      else if (kind === "sept") f.septa_mm = Math.max(val, f.septa_mm || 0);
    }
  }
  function features(s, f, phase) {
    const low = s.toLowerCase();
    if (/\bcyst/.test(low)) f.composition = "cystic";
    else if (/\bsolid\b/.test(low)) f.composition = "solid";
    if (low.includes("heterogeneous")) f.homogeneous = false;
    else if (low.includes("homogeneous")) f.homogeneous = true;
    if (low.includes("irregular")) f.irregular_wall_or_septa = true;
    if (low.includes("too small to characterize")) f.too_small_to_characterize = true;
    if (/macroscopic fat|fat[- ]containing|containing fat/.test(low)) f.macroscopic_fat = true;
    if (f.organ === "kidney" && /(enhancing|mural|soft[- ]tissue)\s+(\d+\s*mm\s+)?(mural\s+)?nodul/.test(low)) f.enhancing_nodule = true;
    const m = s.match(SEPTA_COUNT_RE);
    if (m) f.septa_count = m[3] ? parseInt(m[3], 10) : COUNT_WORDS[m[1].toLowerCase()];
    mmFeatures(s, f);
    const hus = [...s.matchAll(HU_RE)];
    hus.forEach((h, i) => {
      const hend = h.index + h[0].length;
      const end = i + 1 < hus.length ? hus[i + 1].index : s.length;
      const after = s.slice(hend, Math.min(end, hend + 40));
      let kind;
      if (UNENH_RE.test(after)) kind = "unenhanced";
      else if (ENH_RE.test(after)) kind = "enhanced";
      else kind = phase || "enhanced";
      f[kind + "_hu"] = parseFloat(h[1]);
    });
  }

  function extract(text) {
    const sm = SPLIT_IMPRESSION.exec(text);
    const body = sm ? text.slice(0, sm.index) : text;
    const impression = sm ? text.slice(sm.index + sm[0].length) : "";
    const header = body.includes("FINDINGS") ? body.split("FINDINGS")[0] : lines(body)[0];
    const phase = examPhase(header);
    const findings = [];
    for (const line of lines(body)) {
      const headerOrgan = line.includes(":") ? organOf(line.split(":")[0]) : null;
      let current = null;
      for (const s of sentences(line)) {
        const organ = organOf(s) || headerOrgan;
        if (organ && SIZE_RE.test(s) && LESION_RE.test(s)) {
          current = newFinding(organ, sideOf(s), parseFloat(s.match(SIZE_RE)[1]));
          findings.push(current);
          features(s, current, phase);
        } else if (current && !/^no\b/i.test(s) && organOf(s) === null) {
          features(s, current, phase);
        }
      }
    }
    const bm = impression.match(/Bosniak\s+(IIF|IV|III|II|I)\b/);
    if (bm) findings.forEach((f) => { if (f.organ === "kidney") f.reported_category = "Bosniak " + bm[1]; });
    assignActions(impression, findings);
    return findings;
  }

  function assignActions(impression, findings) {
    const items = ("\n" + impression).split(/\n\s*\d+[.)]\s*/);
    for (const item of items) {
      let ctxOrgan = null, ctxSide = "unknown";
      for (const s of sentences(item)) {
        const organ = organOf(s);
        if (organ) {
          ctxOrgan = organ;
          ctxSide = /bilateral/i.test(s) ? "unknown" : sideOf(s);
        }
        let actions = ACTION_PATTERNS.filter(([, rx]) => rx.test(s)).map(([a]) => a);
        if (actions.includes(A.IMAGING_SURVEILLANCE) && actions.includes(A.CHARACTERIZATION_IMAGING) && !EXPLICIT_CHAR.test(s))
          actions = actions.filter((a) => a !== A.CHARACTERIZATION_IMAGING);
        if (NO_FU_RE.test(s)) {
          actions = actions.filter((a) => a !== A.IMAGING_SURVEILLANCE && a !== A.CHARACTERIZATION_IMAGING);
          actions.unshift(A.NO_FOLLOWUP);
        }
        if (!actions.length) continue;
        const targets = findings.filter((f) => ctxOrgan === null || f.organ === ctxOrgan);
        const sided = targets.filter((f) => ctxSide !== "unknown" && f.side === ctxSide);
        for (const f of (sided.length ? sided : targets))
          for (const a of actions) if (!f.stated_actions.includes(a)) f.stated_actions.push(a);
      }
    }
  }

  // ------------------------------------------------------------------ guidelines
  const BOSNIAK = "Bosniak v2019 (Radiology 2019)";
  const ACR_RENAL = "ACR renal mass white paper (JACR 2018)";
  const ESE = "ESE/ENSAT adrenal incidentaloma guideline (EJE 2023)";
  const R = (category, actions, rationale, source) => ({ category, actions, rationale, source });
  const fluid = (hu) => hu !== null && hu !== undefined && hu >= -9 && hu <= 20;
  const enhancement = (f) => (f.unenhanced_hu === null || f.enhanced_hu === null ? null : f.enhanced_hu - f.unenhanced_hu);

  function classifyRenal(f) {
    const enh = enhancement(f), size = f.size_cm;
    if (f.macroscopic_fat) {
      if (size !== null && size >= 4)
        return R("Angiomyolipoma ≥4 cm", [A.SPECIALIST_REFERRAL], "Macroscopic fat indicates angiomyolipoma; ≥4 cm carries haemorrhage risk, so urology review is advised.", ACR_RENAL);
      return R("Angiomyolipoma", [A.NO_FOLLOWUP], "Macroscopic fat without calcification indicates a benign angiomyolipoma.", ACR_RENAL);
    }
    if (f.composition === "cystic") {
      if (f.enhancing_nodule)
        return R("Bosniak IV", [A.SPECIALIST_REFERRAL], "Enhancing nodule in a cystic mass (~90% malignant): urology referral.", BOSNIAK);
      const vals = [f.wall_mm, f.septa_mm].filter((x) => x !== null);
      const thick = vals.length ? Math.max(...vals) : null;
      if (f.irregular_wall_or_septa || (thick !== null && thick >= 4))
        return R("Bosniak III", [A.SPECIALIST_REFERRAL], "Thick (≥4 mm) or irregular enhancing wall/septa (~50% malignant): urology referral.", BOSNIAK);
      if ((thick !== null && thick >= 3) || (f.septa_count || 0) >= 4)
        return R("Bosniak IIF", [A.IMAGING_SURVEILLANCE], "Minimally thickened (3 mm) wall/septa or ≥4 thin septa: imaging at 6 and 12 months, then yearly to 5 years.", BOSNIAK);
      if ((f.septa_count || 0) >= 1 && (f.septa_count || 0) <= 3)
        return R("Bosniak II", [A.NO_FOLLOWUP], "Few (1-3) thin septa: benign, no follow-up.", BOSNIAK);
      const hu = f.enhanced_hu !== null ? f.enhanced_hu : f.unenhanced_hu;
      if (hu === null || fluid(hu))
        return R("Bosniak I", [A.NO_FOLLOWUP], "Thin smooth wall, no septa, simple fluid attenuation: benign, no follow-up.", BOSNIAK);
    }
    if (f.too_small_to_characterize)
      return R("Bosniak II (too small to characterize)", [A.NO_FOLLOWUP], "Homogeneous low-attenuation lesion too small to characterize: presumed benign.", BOSNIAK);
    const solidEnh = enh !== null && enh >= 20;
    if (f.composition === "solid" || solidEnh) {
      if (solidEnh) {
        if (size !== null && size < 1)
          return R("Solid enhancing mass <1 cm", [A.IMAGING_SURVEILLANCE], "Very small enhancing solid mass: follow-up imaging is a reasonable option.", ACR_RENAL);
        return R("Solid enhancing mass (suspicious for RCC)", [A.SPECIALIST_REFERRAL], "Enhancement ≥20 HU without macroscopic fat: suspicious for renal cell carcinoma, urology referral.", ACR_RENAL);
      }
      if (enh === null)
        return R("Solid mass, enhancement not assessed", [A.CHARACTERIZATION_IMAGING], "Solid-appearing mass without pre- and post-contrast measurements: renal mass protocol CT or MRI.", ACR_RENAL);
    }
    if (f.homogeneous !== false) {
      if (f.unenhanced_hu !== null && f.unenhanced_hu >= 70)
        return R("Bosniak II (hyperattenuating)", [A.NO_FOLLOWUP], "Homogeneous ≥70 HU on non-contrast CT: benign hyperdense cyst.", BOSNIAK);
      if (enh !== null && enh < 10 && (f.unenhanced_hu || 0) > 20)
        return R("Bosniak II (non-enhancing)", [A.NO_FOLLOWUP], "Homogeneous, >20 HU and non-enhancing on renal mass protocol CT.", BOSNIAK);
      if (f.enhanced_hu === null && fluid(f.unenhanced_hu))
        return R("Bosniak II", [A.NO_FOLLOWUP], "Homogeneous -9 to 20 HU on non-contrast CT: benign.", BOSNIAK);
      if (f.unenhanced_hu === null && f.enhanced_hu !== null) {
        if (fluid(f.enhanced_hu))
          return R("Bosniak I/II (fluid attenuation)", [A.NO_FOLLOWUP], "Homogeneous fluid attenuation on post-contrast CT: benign.", BOSNIAK);
        if (f.enhanced_hu >= 21 && f.enhanced_hu <= 30)
          return R("Bosniak II", [A.NO_FOLLOWUP], "Homogeneous 21-30 HU on portal venous phase: benign.", BOSNIAK);
      }
    }
    return R("Indeterminate renal mass", [A.CHARACTERIZATION_IMAGING], "Cannot be classified from available phases: renal mass protocol CT or MRI.", BOSNIAK);
  }

  function classifyAdrenal(f) {
    const size = f.size_cm;
    if (size !== null && size < 1)
      return R("Sub-centimetre adrenal nodule", [A.NO_FOLLOWUP], "Guideline applies to masses ≥1 cm; no work-up needed.", ESE);
    if (f.macroscopic_fat)
      return R("Myelolipoma", [A.NO_FOLLOWUP], "Macroscopic fat indicates a benign myelolipoma.", ESE);
    if (f.unenhanced_hu !== null && f.unenhanced_hu <= 10 && f.homogeneous !== false)
      return R("Lipid-rich adenoma (benign imaging)", [A.HORMONAL_WORKUP],
        "Homogeneous ≤10 HU on non-contrast CT: benign, no further imaging; every patient still needs a 1 mg dexamethasone suppression test (plus aldosterone/renin if hypertensive or hypokalaemic).", ESE);
    if ((size !== null && size >= 4) || f.homogeneous === false)
      return R("Indeterminate adrenal mass, ≥4 cm or heterogeneous", [A.SPECIALIST_REFERRAL, A.HORMONAL_WORKUP],
        "Indeterminate mass that is large or heterogeneous: discuss in an expert multidisciplinary team (surgery usually considered) and complete hormonal work-up including metanephrines.", ESE);
    const why = f.unenhanced_hu === null ? "No non-contrast attenuation available" : `${f.unenhanced_hu} HU on non-contrast CT (>10 HU)`;
    return R("Indeterminate adrenal mass", [A.CHARACTERIZATION_IMAGING, A.HORMONAL_WORKUP],
      `${why}: further imaging (non-contrast/washout CT or chemical-shift MRI) or repeat imaging in 6-12 months, plus hormonal work-up including metanephrines.`, ESE);
  }

  const classify = (f) => (f.organ === "kidney" ? classifyRenal(f) : classifyAdrenal(f));
  const IMAGING = [A.IMAGING_SURVEILLANCE, A.CHARACTERIZATION_IMAGING];

  function concordance(f, g) {
    const required = new Set(g.actions.filter((a) => a !== A.NO_FOLLOWUP));
    const stated = new Set(f.stated_actions.filter((a) => a !== A.NO_FOLLOWUP));
    const noRec = f.stated_actions.length === 0;
    let missing = new Set([...required].filter((a) => !stated.has(a)));
    let extra = new Set([...stated].filter((a) => !required.has(a)));
    const has = (set, list) => list.some((a) => set.has(a));
    if (has(missing, IMAGING) && has(stated, IMAGING)) { IMAGING.forEach((a) => { missing.delete(a); extra.delete(a); }); }
    if (has(missing, IMAGING) && stated.has(A.SPECIALIST_REFERRAL)) IMAGING.forEach((a) => missing.delete(a));
    const sort = (s) => [...s].sort((x, y) => ORDER.indexOf(x) - ORDER.indexOf(y));
    const m = sort(missing), e = sort(extra);
    const words = (l) => l.map((a) => a.replace(/_/g, " ").toLowerCase()).join(", ");
    if (m.length) {
      const severity = missing.has(A.SPECIALIST_REFERRAL) ? "high" : "medium";
      const lead = noRec ? "No recommendation given" : "Recommendation falls short";
      return { status: "under-call", severity, missing: m, extra: e, no_recommendation: noRec, message: `${lead}: guideline calls for ${words(m)}.` };
    }
    if (e.length)
      return { status: "over-call", severity: "low", missing: m, extra: e, no_recommendation: noRec, message: `Guideline does not call for ${words(e)} (possible unnecessary follow-up).` };
    return { status: "concordant", severity: "none", missing: [], extra: [], no_recommendation: noRec, message: "Recommendation matches the guideline." };
  }

  const api = { A, LABELS, extract, classify, concordance };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Navigator = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
