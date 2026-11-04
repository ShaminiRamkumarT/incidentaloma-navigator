// JavaScript port of navigator/extract_rules.py + navigator/guidelines.py (all nine organs), for the browser demo.
// Keep in step with the Python; web/parity_check.js compares both on every hand-written and synthetic test report.
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
    [A.SPECIALIST_REFERRAL, /urolog|referr|\brefer\b|surgical (consult|evaluation)|multidisciplinary|\bMDT\b|neurosurg|\bEUS\b|\bFNA\b|fine[- ]needle|biopsy|oncolog|pulmonolog/i],
    [A.HORMONAL_WORKUP, /dexamethasone|\bDST\b|biochemical|hormon|metanephrine|aldosterone|endocrin/i],
    [A.IMAGING_SURVEILLANCE, /follow[- ]?up (CT|MRI|ultrasound|imaging|US)\b|in \d+ (months|years)|surveillance|repeat (CT|MRI|imaging)|short[- ]interval/i],
    [A.CHARACTERIZATION_IMAGING, /protocol (CT|MRI)|mass protocol|adrenal protocol|dedicated|further evaluat|\bMRI\b|characteri[sz]ation|thyroid ultrasound|\bPET\b/i],
  ];
  const EXPLICIT_CHAR = /protocol|dedicated/i;
  const NO_FU_RE = /no (further )?(follow[- ]?up|imaging)|no further (imaging|evaluation|work)/i;

  function newFinding(organ, side, size) {
    return { organ, modality: "CT", side, size_cm: size, short_axis_cm: null, composition: "indeterminate",
      unenhanced_hu: null, enhanced_hu: null, homogeneous: null, wall_mm: null, septa_count: null, septa_mm: null,
      irregular_wall_or_septa: false, enhancing_nodule: false, macroscopic_fat: false, too_small_to_characterize: false,
      nodule_type: null, solid_component_mm: null, multiple: false, patient_risk: "unknown", patient_age: null,
      appearance: null, fdg_avid: null, duct_mm: null, mural_nodule: false, limited_life_expectancy: false,
      chiasm_contact: false, growth: false, symptomatic: false, bone_density: null,
      stated_actions: [], reported_category: null };
  }

  const lines = (t) => t.split(/\r\n|\r|\n/);
  function sentences(text) {
    const out = [];
    for (const line of lines(text)) {
      for (const s of line.split(/(?<=[.;])\s+/)) if (s.trim()) out.push(s.trim());
    }
    return out;
  }
  const ORGAN_PATTERNS = [
    ["adrenal", /adrenal/i], ["kidney", /kidney|renal/i],
    ["pituitary", /pituitar|\bsella|adenohypophysis|macroadenoma|microadenoma/i], ["thyroid", /thyroid/i],
    ["pancreas", /pancrea/i], ["liver", /liver|hepatic|\bsegment \d/i], ["lung", /\blungs?\b|pulmonary|\blobe\b|lingula/i],
    ["brain", /meningioma|extra-?axial|dural/i],
    ["bone", /\bbones?\b|osseous|vertebra|femur|femoral|humer|iliac|\bribs?\b|sacrum|calvari|\blytic\b|sclerotic/i],
  ];
  const NEW_ORGANS = new Set(["lung", "liver", "pancreas", "thyroid", "pituitary", "brain", "bone"]);
  function organOf(s) {
    for (const [organ, rx] of ORGAN_PATTERNS) if (rx.test(s)) return organ;
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

  // ---- readers for the seven organs added after the first version
  const SIZE_ANY_RE = /(\d+(?:\.\d+)?)(?:\s*(?:x|×|by)\s*(\d+(?:\.\d+)?))?\s*(cm|mm)\b/gi;
  const LESION_NEW_RE = /\b(lesion|cyst|mass|nodule|focus|adenoma|macroadenoma|microadenoma|meningioma|haemangioma|hemangioma|island)/i;
  const r2 = (x) => Math.round(x * 100) / 100;
  const negated = (s, start) => /\b(no|without|not)\b[^.;,]{0,25}$/i.test(s.slice(0, start));
  function has(s, src) {
    const m = new RegExp(src, "i").exec(s);
    return !!m && !negated(s, m.index);
  }
  function sizeNew(s) {
    for (const m of s.matchAll(SIZE_ANY_RE)) {
      const end = m.index + m[0].length;
      const after = s.slice(end, end + 30).toLowerCase();
      if (/^\s*(solid component|wall|duct|septum)/.test(after) || s.slice(Math.max(0, m.index - 25), m.index).toLowerCase().includes("duct")) continue;
      const k = m[3].toLowerCase() === "mm" ? 0.1 : 1.0;
      const a = parseFloat(m[1]) * k, b = m[2] ? parseFloat(m[2]) * k : null;
      return [r2(Math.max(a, b || 0)), b !== null ? r2(Math.min(a, b)) : null];
    }
    return [null, null];
  }
  function context(header) {
    const ctx = { modality: /\bPET/.test(header) ? "PET-CT" : /\bMRI?\b/.test(header) ? "MRI" : "CT" };
    const m = header.match(/(\d{1,3})[- ]year[- ]old|aged (\d{1,3})/i);
    if (m) ctx.age = parseInt(m[1] || m[2], 10);
    if (/never[- ]smoker|non-?smoker|no smoking/i.test(header)) ctx.lung_risk = "low";
    else if (/smoker|pack[- ]year|smoking/i.test(header)) ctx.lung_risk = "high";
    if (/cancer|carcinoma|malignan|melanoma|lymphoma|metasta/i.test(header) && !/no (known |history of )?(cancer|malignan)/i.test(header)) ctx.cancer = true;
    if (/cirrhosis|hepatitis|NASH|alcohol/i.test(header)) ctx.liver_disease = true;
    if (/no (history of |known )?(malignancy|cancer) or liver disease/i.test(header)) ctx.liver_low = true;
    if (/limited life expectancy|palliative/i.test(header)) ctx.limited = true;
    if (/seizure|weakness|deficit/i.test(header)) ctx.neuro = true;
    return ctx;
  }
  function featuresNew(s, f) {
    const low = s.toLowerCase(), o = f.organ;
    if (o === "lung") {
      if (has(s, "ground[- ]glass|non-?solid")) f.nodule_type = "ground-glass";
      else if (has(s, "part[- ]solid|semi-?solid")) f.nodule_type = "part-solid";
      if (/\b(multiple|several|scattered|numerous)\b/.test(low)) f.multiple = true;
      const m = low.match(/(\d+(?:\.\d+)?)\s*mm solid component/);
      if (m) f.solid_component_mm = parseFloat(m[1]);
    } else if (o === "liver") {
      if (has(s, "haemangioma|hemangioma|focal fat|\\bFNH\\b|peripheral nodular|simple cyst")) f.appearance = "benign";
      else if (has(s, "ill-defined|heterogeneous|poorly marginated")) f.appearance = "suspicious";
      else if (has(s, "flash[- ]filling|arterial hyperenhancement")) f.appearance = "flash-filling";
      else if (has(s, "too small to characteri|indeterminate|incompletely characteri")) f.appearance = "indeterminate";
    } else if (o === "pancreas") {
      if (/\bcyst/.test(low)) f.composition = "cystic";
      const m = low.match(/duct[^.;]{0,30}?(\d+(?:\.\d+)?)\s*mm/);
      if (m) f.duct_mm = parseFloat(m[1]);
      if (has(s, "non-?enhancing (mural )?nodule")) f.mural_nodule = true;
      else if (has(s, "enhancing (mural nodule|nodule|solid)")) f.enhancing_nodule = true;
      if (has(s, "thick(ened)?[^.;]{0,20}wall")) f.irregular_wall_or_septa = true;
    } else if (o === "thyroid") {
      if (has(s, "FDG (uptake|avid)|FDG-avid|focal uptake")) f.fdg_avid = true;
      else if (/(no|without) (focal )?FDG/i.test(s)) f.fdg_avid = false;
      if (has(s, "extrathyroidal|invasion|lymph node")) f.appearance = "suspicious";
    } else if (o === "pituitary") {
      if (/(abut|compress|contact|elevat|displac)\w*[^.;]{0,25}chiasm/.test(low)) f.chiasm_contact = true;
    } else if (o === "brain") {
      if (/\b(increased|grown|growth|enlarg)|previously \d/.test(low)) f.growth = true;
    } else if (o === "bone") {
      if (has(s, "\\blytic|lucent")) f.bone_density = "lucent";
      else if (has(s, "sclerotic|blastic")) f.bone_density = "sclerotic";
      if (has(s, "cortical (destruction|breach|breakthrough)|periosteal reaction|soft[- ]tissue (extension|mass)|pathologic(al)? fracture|endosteal scalloping")) f.appearance = "suspicious";
      else if (has(s, "bone island|enostosis|haemangioma|hemangioma|non-?ossifying|macroscopic fat")) f.appearance = "benign";
      const hus = [...s.matchAll(HU_RE)];
      if (hus.length) f.unenhanced_hu = parseFloat(hus[0][1]);
    }
  }
  function applyContext(f, ctx) {
    f.modality = ctx.modality;
    if (f.organ === "lung" && ctx.lung_risk) f.patient_risk = ctx.lung_risk;
    if (f.organ === "liver") { if (ctx.cancer || ctx.liver_disease) f.patient_risk = "high"; else if (ctx.liver_low) f.patient_risk = "low"; }
    if (f.organ === "bone" && ctx.cancer) f.patient_risk = "high";
    if ((f.organ === "pancreas" || f.organ === "thyroid") && ctx.age !== undefined) f.patient_age = ctx.age;
    if (f.organ === "thyroid" && ctx.limited) f.limited_life_expectancy = true;
    if (f.organ === "brain" && ctx.neuro) f.symptomatic = true;
  }

  function extract(text) {
    const sm = SPLIT_IMPRESSION.exec(text);
    const body = sm ? text.slice(0, sm.index) : text;
    const impression = sm ? text.slice(sm.index + sm[0].length) : "";
    const header = body.includes("FINDINGS") ? body.split("FINDINGS")[0] : lines(body)[0];
    const phase = examPhase(header);
    const ctx = context(header);
    const findings = [];
    let started = !body.includes("FINDINGS");
    for (const line of lines(body)) {
      if (line.includes("FINDINGS")) { started = true; continue; }
      if (!started) continue;
      const headerOrgan = line.includes(":") ? organOf(line.split(":")[0]) : null;
      let current = null;
      for (const s of sentences(line)) {
        const organ = organOf(s) || headerOrgan;
        if (NEW_ORGANS.has(organ)) {
          const [size, short] = sizeNew(s);
          if (size !== null && LESION_NEW_RE.test(s)) {
            current = newFinding(organ, sideOf(s), size);
            if (organ === "lung" && short) current.short_axis_cm = short;
            findings.push(current);
            featuresNew(s, current);
            applyContext(current, ctx);
          } else if (current && NEW_ORGANS.has(current.organ) && !/^no\b/i.test(s)) {
            featuresNew(s, current);
          }
          continue;
        }
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
  const R = (category, actions, rationale, source, notes, alternatives) =>
    ({ category, actions, rationale, source, notes: notes || [], alternatives: alternatives || [] });
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

  // ---- seven organs added after the first version
  const FLEISCHNER = "Fleischner Society 2017 (Radiology 2017)";
  const ACR_LIVER = "ACR liver lesion white paper (JACR 2017)";
  const ACR_PANCREAS = "ACR pancreatic cyst white paper (JACR 2017)";
  const ACR_THYROID = "ACR incidental thyroid nodule white paper (JACR 2015)";
  const ES_PITUITARY = "Endocrine Society pituitary incidentaloma guideline (JCEM 2011)";
  const EANO = "EANO meningioma guideline (Neuro-Oncology 2021)";
  const BONE_RADS = "Bone-RADS, Society of Skeletal Radiology (Skeletal Radiol 2022)";
  const NONE_ = [A.NO_FOLLOWUP], FU = [A.IMAGING_SURVEILLANCE], CHAR = [A.CHARACTERIZATION_IMAGING],
    REF = [A.SPECIALIST_REFERRAL], HORM = [A.HORMONAL_WORKUP];
  // Python's round(): halves go to the even number
  const pyRound = (x) => { const r = Math.round(x); return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r; };
  const g = (x) => String(+x);

  function classifyLung(f) {
    const mm = f.size_cm === null ? null : pyRound(f.short_axis_cm !== null ? (f.size_cm + f.short_axis_cm) / 2 * 10 : f.size_cm * 10);
    const n = f.multiple ? "multiple" : "single";
    const notes = f.short_axis_cm ? ["Size = mean of long and short axis, rounded to the nearest mm."] : [];
    if (f.modality === "MRI") notes.push("Fleischner applies to CT; MRI-reported nodule handled as if on CT.");
    if (mm === null) return R("Lung nodule, size not stated", FU, "Size is needed to apply Fleischner; follow-up CT is the safe default.", FLEISCHNER, notes);
    const kind = f.nodule_type || "solid";
    if (kind === "solid") {
      if (mm < 6) {
        const cat = `Solid nodule <6 mm (${n})`;
        if (f.patient_risk === "low") return R(cat, NONE_, "Low-risk patient: no routine follow-up.", FLEISCHNER, notes);
        if (f.patient_risk === "high") return R(cat, FU, "High-risk patient: optional CT at 12 months.", FLEISCHNER, notes, [NONE_]);
        return R(cat, NONE_, "Risk not stated: no follow-up (low risk) or optional CT at 12 months (high risk) are both acceptable.", FLEISCHNER, notes, [FU]);
      }
      if (mm <= 8) {
        const when = f.multiple ? "3-6 months" : "6-12 months";
        return R(`Solid nodule 6-8 mm (${n})`, FU, `CT at ${when}, then consider (low risk) or perform (high risk) CT at 18-24 months.`, FLEISCHNER, notes);
      }
      if (f.multiple) return R("Solid nodules >8 mm (multiple)", FU, "CT at 3-6 months, then consider CT at 18-24 months.", FLEISCHNER, notes);
      return R("Solid nodule >8 mm (single)", FU, "Consider CT at 3 months, PET-CT or tissue sampling.", FLEISCHNER, notes, [REF]);
    }
    if (f.multiple) {
      if (mm < 6) return R("Multiple subsolid nodules <6 mm", FU, "CT at 3-6 months; if stable, consider CT at 2 and 4 years.", FLEISCHNER, notes);
      return R("Multiple subsolid nodules, one or more ≥6 mm", FU, "CT at 3-6 months; further management based on the most suspicious nodule.", FLEISCHNER, notes);
    }
    if (kind === "ground-glass") {
      if (mm < 6) return R("Ground-glass nodule <6 mm", NONE_, "No routine follow-up.", FLEISCHNER, notes);
      return R("Ground-glass nodule ≥6 mm", FU, "CT at 6-12 months to confirm persistence, then every 2 years until 5 years.", FLEISCHNER, notes);
    }
    if (mm < 6) return R("Part-solid nodule <6 mm", NONE_, "No routine follow-up.", FLEISCHNER, notes);
    if ((f.solid_component_mm || 0) >= 6)
      return R("Part-solid nodule ≥6 mm, solid part ≥6 mm", FU, "CT at 3-6 months to confirm persistence; a persistent solid part ≥6 mm is highly suspicious, so referral or biopsy is also acceptable.", FLEISCHNER, notes, [REF]);
    return R("Part-solid nodule ≥6 mm", FU, "CT at 3-6 months to confirm persistence; if unchanged and solid part <6 mm, yearly CT for 5 years.", FLEISCHNER, notes);
  }

  function liverAppearance(f, notes) {
    if (f.modality === "PET-CT" && f.fdg_avid) {
      notes.push("FDG uptake above normal liver treated as a suspicious feature (IncidentaLens rule, not part of the ACR CT white paper).");
      return "suspicious";
    }
    if (f.appearance) return f.appearance;
    const enh = enhancement(f);
    if ((enh !== null && enh > 20) || f.homogeneous === false) return "suspicious";
    const hu = f.enhanced_hu !== null ? f.enhanced_hu : f.unenhanced_hu;
    if (hu !== null && f.homogeneous !== false && hu <= 20) return "benign";
    if (f.enhanced_hu !== null && f.enhanced_hu > 20) return "suspicious";
    return "indeterminate";
  }

  function classifyLiver(f) {
    const notes = [];
    if (f.modality === "MRI") notes.push("ACR white paper covers CT; the same feature rules are applied to this MRI finding.");
    const look = liverAppearance(f, notes);
    const size = f.size_cm, risk = f.patient_risk;
    if (look === "benign" && (size === null || size >= 1))
      return R("Liver lesion with benign features", NONE_, "Distinctly benign features: no further work-up, regardless of patient risk.", ACR_LIVER, notes);
    if (size === null) return R("Liver lesion, size not stated", CHAR, "Size is needed to apply the ACR algorithm; MRI is the safe default.", ACR_LIVER, notes);
    if (size < 1) {
      const cat = "Liver lesion <1 cm";
      if (risk === "high") {
        const alts = look === "benign" ? [NONE_] : [];
        return R(cat, FU, "High-risk patient: MRI in 3-6 months to characterise and check for growth" + (alts.length ? " (benign features: no work-up also acceptable)." : "."), ACR_LIVER, notes, alts);
      }
      if (risk === "low")
        return R(cat, NONE_, "Low-risk patient: can be considered benign, no work-up" + (look === "suspicious" ? "; MRI may be considered as features are suspicious." : "."), ACR_LIVER, notes, look === "suspicious" ? [CHAR] : []);
      return R(cat, NONE_, "Risk not stated: no work-up (low risk) or MRI in 3-6 months (high risk) are both acceptable.", ACR_LIVER, notes, [FU]);
    }
    const band = size <= 1.5 ? "1-1.5 cm" : ">1.5 cm";
    if (look === "flash-filling") {
      const cat = `Flash-filling liver lesion ${band}`;
      if (size > 1.5 || risk === "high") return R(cat, CHAR, "Prompt MRI is advised.", ACR_LIVER, notes);
      if (risk === "low") return R(cat, NONE_, "Low-risk patient, ≤1.5 cm: no further work-up.", ACR_LIVER, notes);
      return R(cat, NONE_, "Risk not stated: no work-up (low risk) or prompt MRI (high risk) are both acceptable.", ACR_LIVER, notes, [CHAR]);
    }
    if (look === "suspicious") {
      const biopsyOk = size > 1.5 && risk !== "low";
      return R(`Liver lesion ${band} with suspicious features`, CHAR, "Prompt MRI is advised" + (biopsyOk ? "; direct biopsy may be considered for a large, highly suspicious lesion in a high-risk patient." : "."), ACR_LIVER, notes, biopsyOk ? [REF] : []);
    }
    return R(`Indeterminate liver lesion ${band}`, CHAR, "Features cannot be assessed on this scan: MRI is advised.", ACR_LIVER, notes);
  }

  function classifyPancreas(f) {
    const size = f.size_cm, age = f.patient_age;
    if (f.enhancing_nodule || (f.duct_mm !== null && f.duct_mm >= 10))
      return R("Pancreatic cyst with high-risk stigmata", REF, "Enhancing solid component or main duct ≥10 mm: EUS-FNA and surgical consultation.", ACR_PANCREAS);
    const worrisome = [["thickened/enhancing wall", f.irregular_wall_or_septa], ["non-enhancing mural nodule", f.mural_nodule],
      ["main duct ≥7 mm", f.duct_mm !== null && f.duct_mm >= 7]].filter(([, hit]) => hit).map(([w]) => w);
    if (worrisome.length)
      return R("Pancreatic cyst with worrisome features", REF, `Worrisome feature (${worrisome.join(", ")}): EUS-FNA and surgical consultation.`, ACR_PANCREAS);
    if (age !== null && age >= 80)
      return R("Pancreatic cyst, patient ≥80", NONE_, "Age ≥80: surveillance is generally not advised; a single follow-up may be chosen depending on health and patient preference.", ACR_PANCREAS, [], [FU]);
    if (size === null) return R("Pancreatic cyst, size not stated", FU, "Size is needed to set the schedule; imaging follow-up is the safe default.", ACR_PANCREAS);
    if (size >= 3)
      return R("Pancreatic cyst ≥3 cm", REF, "Size ≥3 cm is a worrisome feature: EUS-FNA and surgical consultation; a cyst with no other feature can alternatively be followed.", ACR_PANCREAS, [], [FU]);
    if (size >= 1.5)
      return R(`Pancreatic cyst ${size <= 2.5 ? "1.5-2.5" : "2.5-3"} cm`, FU, "Imaging follow-up (6-12 monthly at first, depending on size and duct communication); EUS-FNA is an accepted alternative.", ACR_PANCREAS, [], [REF]);
    const when = (age || 0) >= 65 ? "every 2 years" : "yearly";
    return R("Pancreatic cyst <1.5 cm", FU, `Imaging follow-up ${age !== null ? when : "yearly (<65) or every 2 years (65-79)"}, stopping after 9-10 years or at age 80.`, ACR_PANCREAS);
  }

  function classifyThyroid(f) {
    const size = f.size_cm, age = f.patient_age;
    if (f.appearance === "suspicious")
      return R("Thyroid nodule with suspicious features", CHAR, "Local invasion or abnormal lymph nodes: dedicated thyroid ultrasound (ultrasound with FNA also acceptable).", ACR_THYROID, [], [CHAR.concat(REF)]);
    if (f.limited_life_expectancy)
      return R("Thyroid nodule, limited life expectancy", NONE_, "Limited life expectancy or serious comorbidity: no further evaluation.", ACR_THYROID);
    if (f.fdg_avid)
      return R("FDG-avid thyroid nodule", CHAR.concat(REF), "Focal FDG uptake is highly suspicious: thyroid ultrasound and FNA, with FNA regardless of the ultrasound findings.", ACR_THYROID);
    if (size === null) return R("Thyroid nodule, size not stated", CHAR, "Size is needed; thyroid ultrasound is the safe default.", ACR_THYROID);
    if (age === null) {
      if (size < 1) return R("Thyroid nodule <1 cm", NONE_, "Below the size threshold at any age.", ACR_THYROID);
      if (size < 1.5) return R("Thyroid nodule 1-1.5 cm, age not stated", NONE_, "Ultrasound if age <35, none if ≥35; age not stated, so both are accepted.", ACR_THYROID, [], [CHAR]);
      return R("Thyroid nodule ≥1.5 cm", CHAR, "Dedicated thyroid ultrasound.", ACR_THYROID);
    }
    const limit = age < 35 ? 1.0 : 1.5;
    const band = `age ${age < 35 ? "<35" : "≥35"}`;
    if (size >= limit) return R(`Thyroid nodule ≥${g(limit)} cm, ${band}`, CHAR, "Dedicated thyroid ultrasound.", ACR_THYROID);
    return R(`Thyroid nodule <${g(limit)} cm, ${band}`, NONE_, "Below the size threshold: no work-up.", ACR_THYROID);
  }

  function classifyPituitary(f) {
    const notes = [];
    if (f.chiasm_contact || f.symptomatic)
      return R("Pituitary lesion abutting/compressing the chiasm", REF.concat(HORM), "Formal visual field testing and surgical referral, plus hormonal evaluation.", ES_PITUITARY);
    let imaging = FU;
    if (f.modality !== "MRI") { imaging = CHAR; notes.push("Found on CT/PET-CT: dedicated pituitary MRI first."); }
    if (f.size_cm !== null && f.size_cm < 1)
      return R("Pituitary microincidentaloma (<1 cm)", imaging.concat(HORM), "Hormonal evaluation for hypersecretion and hypopituitarism; repeat MRI at 1 year, then every 1-2 years.", ES_PITUITARY, notes);
    if (f.size_cm === null) notes.push("Size not stated; handled as a macroincidentaloma.");
    return R("Pituitary macroincidentaloma (≥1 cm)", imaging.concat(HORM), "Hormonal evaluation for hypersecretion and hypopituitarism; repeat MRI at 6 months, then yearly for 3 years.", ES_PITUITARY, notes);
  }

  function classifyBrain(f) {
    if (f.growth || f.symptomatic)
      return R("Growing or symptomatic meningioma", REF, "Surgical resection is the first option for growing or symptomatic tumours: neurosurgical referral.", EANO);
    return R("Incidental asymptomatic meningioma", FU, "Observation: MRI yearly for 5 years, then every 2 years.", EANO, f.modality === "MRI" ? [] : ["Seen on CT/PET-CT: MRI is the follow-up modality."]);
  }

  function classifyBone(f) {
    let look = f.appearance;
    const hu = f.unenhanced_hu !== null ? f.unenhanced_hu : f.enhanced_hu;
    if (look === null && f.macroscopic_fat) look = "benign";
    if (look === null && hu !== null) {
      if (f.bone_density === "sclerotic" && hu > 885) look = "benign";
      else if (f.bone_density === "lucent" && hu < -10) look = "benign";
    }
    if (look === "suspicious") return R("Bone-RADS 4", REF, "Suspicious for malignancy or needs treatment: biopsy and/or orthopaedic oncology referral.", BONE_RADS);
    if (f.patient_risk === "high") return R("Bone-RADS 2/3 (known cancer)", CHAR, "Known cancer that spreads to bone: PET, bone scan or MRI, or follow-up imaging.", BONE_RADS, [], [FU]);
    if (look === "benign") return R("Bone-RADS 1", NONE_, "Likely benign: leave alone.", BONE_RADS);
    return R("Bone-RADS 3", FU, "Indeterminate: follow-up imaging at 6, 6 and 12 months (or a different modality, Bone-RADS 2).", BONE_RADS, [], [CHAR]);
  }

  const CLASSIFIERS = { kidney: classifyRenal, adrenal: classifyAdrenal, lung: classifyLung, liver: classifyLiver,
    pancreas: classifyPancreas, thyroid: classifyThyroid, pituitary: classifyPituitary, brain: classifyBrain, bone: classifyBone };
  const classify = (f) => CLASSIFIERS[f.organ](f);
  const IMAGING = [A.IMAGING_SURVEILLANCE, A.CHARACTERIZATION_IMAGING];

  function concordance(f, gr) {
    const first = concordanceOne(f, gr.actions);
    if (first.status === "concordant") return first;
    for (const alt of gr.alternatives || []) {
      const c = concordanceOne(f, alt);
      if (c.status === "concordant") { c.message = "Recommendation matches an option the guideline accepts."; return c; }
    }
    return first;
  }

  function concordanceOne(f, actions) {
    const required = new Set(actions.filter((a) => a !== A.NO_FOLLOWUP));
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
