"""IncidentaLens - Streamlit app.  Run: streamlit run app.py"""
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from navigator import extract_rules
from navigator.evaluate import load_reports
from navigator.guidelines import classify, concordance
from navigator.schema import ACTION_LABELS, Action, Finding

ROOT = Path(__file__).parent
st.set_page_config(page_title="IncidentaLens", page_icon="🩻", layout="wide")

STATUS_STYLE = {
    "concordant": ("✅", "green", "Concordant"),
    "under-call": ("🚩", "red", "Under-call"),
    "over-call": ("⚠️", "orange", "Over-call"),
}


def labels(actions):
    acts = [a for a in actions if a != Action.NO_FOLLOWUP] or [Action.NO_FOLLOWUP]
    return ", ".join(ACTION_LABELS[a] for a in acts)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🩻 IncidentaLens")
st.sidebar.caption("Renal & adrenal incidental findings on CT: does the report's follow-up match the guidelines?")
has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
mode = st.sidebar.radio(
    "Extractor", ["Rules (regex baseline)", "Claude (LLM)"],
    help="The extractor reads the report. The guideline decision is always the same deterministic engine.")
if mode.startswith("Claude") and not has_key:
    st.sidebar.warning("Set ANTHROPIC_API_KEY to use the Claude extractor. Falling back to rules.")
    mode = "Rules (regex baseline)"
st.sidebar.divider()
st.sidebar.markdown(
    "**Guidelines encoded**\n"
    "- Bosniak v2019 (Silverman, *Radiology* 2019)\n"
    "- ACR renal mass white paper (Herts, *JACR* 2018)\n"
    "- ESE/ENSAT adrenal incidentaloma (Fassnacht, *EJE* 2023)")
st.sidebar.info("Portfolio prototype on synthetic reports. Not a medical device; not for clinical use.")


@st.cache_data
def all_reports():
    out = {}
    for split in ("dev", "holdout"):
        for r in load_reports(split):
            out[f"{r['id']} ({split})"] = r
    return out


def run_extractor(text):
    if mode.startswith("Claude"):
        from navigator import extract_llm
        return extract_llm.extract(text)
    return extract_rules.extract(text)


tab_check, tab_dash, tab_rules = st.tabs(["Check a report", "Validation dashboard", "Guideline logic"])

# ---------------------------------------------------------------- tab 1
with tab_check:
    reports = all_reports()
    left, right = st.columns([5, 6], gap="large")
    with left:
        choice = st.selectbox("Load a synthetic report", ["(paste your own)"] + list(reports))
        default = "" if choice == "(paste your own)" else reports[choice]["text"]
        text = st.text_area("Radiology report", default, height=380, key=f"txt_{choice}")
        go = st.button("Check follow-up", type="primary", use_container_width=True)
    with right:
        if go and text.strip():
            try:
                with st.spinner("Extracting findings..."):
                    extraction = run_extractor(text)
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                extraction = None
            if extraction is not None and not extraction.findings:
                st.success("No incidental renal or adrenal lesions found in this report.")
            for i, f in enumerate(extraction.findings if extraction else []):
                g = classify(f)
                c = concordance(f, g)
                icon, color, word = STATUS_STYLE[c.status]
                size = f"{f.size_cm:g} cm" if f.size_cm else "size n/a"
                with st.container(border=True):
                    st.markdown(f"#### {icon} {f.side.title()} {f.organ} · {size}")
                    st.markdown(f":{color}[**{word}**]" + (f" · severity **{c.severity}**" if c.severity != "none" else "")
                                + f" — {c.message}")
                    a, b = st.columns(2)
                    a.markdown(f"**Guideline**  \n{g.category}  \n→ {labels(g.actions)}")
                    b.markdown("**Report says**  \n"
                               + (f"{f.reported_category}  \n" if f.reported_category else "")
                               + "→ " + (labels(f.stated_actions) if f.stated_actions else "*nothing recommended*"))
                    st.caption(f"{g.rationale}  Source: {g.source}.")
                    with st.expander("Extracted fields"):
                        d = {k: v for k, v in f.model_dump().items() if v not in (None, False, [])}
                        if f.enhancement_hu is not None:
                            d["enhancement_hu (derived)"] = f.enhancement_hu
                        st.json(d)
            if choice != "(paste your own)" and text == default:
                gold = reports[choice]["findings"]
                with st.expander(f"Gold labels for this report ({len(gold)} finding(s))"):
                    for x in gold:
                        gf = Finding(**x["gold"])
                        gg = classify(gf)
                        gc = concordance(gf, gg)
                        st.markdown(f"- {gf.side} {gf.organ} {gf.size_cm or ''} cm → **{gg.category}**, "
                                    f"{STATUS_STYLE[gc.status][2].lower()}")
        else:
            st.info("Pick a sample report (or paste one) and press **Check follow-up**.")

# ---------------------------------------------------------------- tab 2
with tab_dash:
    st.subheader("How well does the extractor work?")
    st.caption("Dev set (30 reports) was used to build the regex rules. The held-out set (16 reports) was written "
               "afterwards in different phrasing, so it is the honest test.")
    summaries = []
    for p in sorted((ROOT / "results").glob("summary_*.json")):
        summaries.append(json.loads(p.read_text()))
    if not summaries:
        st.warning("No results yet. Run `python run_eval.py`.")
    else:
        rows = []
        for s in summaries:
            rows.append({
                "Extractor": s["extractor"], "Split": s["split"], "Reports": s["reports"],
                "Lesions": s["gold_findings"], "Detection recall": s["detection_recall"],
                "Guideline category agreement": s["category_agreement"],
                "Concordance flag agreement": s["status_agreement"],
                "Discordance sensitivity": s["discordance_sensitivity"],
                "Discordance PPV": s["discordance_ppv"], "High-severity caught": s["high_severity_caught"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, column_config={
            c: st.column_config.ProgressColumn(c, format="percent", min_value=0, max_value=1)
            for c in ["Detection recall", "Guideline category agreement", "Concordance flag agreement",
                      "Discordance sensitivity", "Discordance PPV"]})

        st.markdown("##### Field-level accuracy on matched lesions")
        fa = pd.DataFrame({f"{s['extractor']} · {s['split']}": s["field_accuracy"] for s in summaries})
        st.dataframe(fa.style.format("{:.0%}"), use_container_width=True)

        st.markdown("##### Error log")
        files = sorted((ROOT / "results").glob("eval_*.csv"))
        pick = st.selectbox("Run", [p.stem.replace("eval_", "") for p in files])
        ev = pd.read_csv(ROOT / "results" / f"eval_{pick}.csv")
        errs = ev[ev["field_errors"].fillna("") != ""]
        st.dataframe(errs[["report", "organ", "side", "gold_category", "pred_category", "gold_status",
                           "pred_status", "field_errors"]], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Discordance worklist (gold labels)")
    st.caption("What a quality lead would see: lesions whose report recommendation does not match the guideline.")
    wl = []
    for split in ("dev", "holdout"):
        for r in load_reports(split):
            for x in r["findings"]:
                f = Finding(**x["gold"])
                g = classify(f)
                c = concordance(f, g)
                wl.append({"Report": r["id"], "Lesion": f"{f.side} {f.organ} {f.size_cm or ''} cm",
                           "Guideline": g.category, "Guideline action": labels(g.actions),
                           "Report action": labels(f.stated_actions) if f.stated_actions else "none stated",
                           "Status": c.status, "Severity": c.severity})
    wl = pd.DataFrame(wl)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lesions", len(wl))
    m2.metric("Concordant", int((wl.Status == "concordant").sum()))
    m3.metric("Under-calls", int((wl.Status == "under-call").sum()),
              help="Guideline calls for more than the report recommends")
    m4.metric("Over-calls", int((wl.Status == "over-call").sum()), help="Report recommends more than the guideline")
    sev_order = {"high": 0, "medium": 1, "low": 2, "none": 3}
    show = wl[wl.Status != "concordant"].sort_values("Severity", key=lambda s: s.map(sev_order))
    st.dataframe(show, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- tab 3
with tab_rules:
    st.subheader("Decision logic (simplified)")
    st.markdown("""
**Kidney (Bosniak v2019 + ACR 2018)**

| Imaging feature | Category | Action |
|---|---|---|
| Macroscopic fat | Angiomyolipoma | None (<4 cm) · urology review (≥4 cm) |
| Cystic, enhancing nodule | Bosniak IV | Urology referral |
| Cystic, wall/septa ≥4 mm or irregular | Bosniak III | Urology referral |
| Cystic, wall/septa 3 mm or ≥4 thin septa | Bosniak IIF | Imaging at 6 and 12 months, then yearly to 5 years |
| Cystic, 1-3 thin septa | Bosniak II | None |
| Simple fluid (-9 to 20 HU), thin wall, no septa | Bosniak I | None |
| Homogeneous ≥70 HU unenhanced; 21-30 HU portal venous; too small to characterize | Bosniak II | None |
| Solid, enhances ≥20 HU, no fat | Suspicious for RCC | Urology referral (<1 cm: imaging follow-up acceptable) |
| Anything else | Indeterminate | Renal mass protocol CT or MRI |

**Adrenal (ESE/ENSAT 2023)**

| Imaging feature | Category | Action |
|---|---|---|
| <1 cm | Below guideline threshold | None |
| Macroscopic fat | Myelolipoma | None |
| Homogeneous, ≤10 HU unenhanced | Lipid-rich adenoma | No more imaging; **1 mg dexamethasone suppression test** |
| ≥4 cm or heterogeneous, not benign on imaging | Indeterminate, high risk | MDT / surgical review + full hormonal work-up |
| >10 HU or no unenhanced phase | Indeterminate | Further imaging or repeat in 6-12 months + hormonal work-up |

**Concordance:** *under-call* = the guideline calls for an action the report omits (high severity if a referral is missing);
*over-call* = the report asks for follow-up the guideline does not; any imaging satisfies an imaging requirement, and a referral
covers an imaging requirement.
""")
    st.caption("Simplifications: CT only (no MRI or ultrasound rules); patient history (e.g. known cancer) and adrenal washout "
               "are not modelled; ACR solid-mass branches are condensed. Check thresholds against the source papers.")
    st.markdown(
        "**Sources**\n\n"
        "1. Silverman SG, Pedrosa I, Ellis JH, et al. Bosniak Classification of Cystic Renal Masses, Version 2019: "
        "An Update Proposal and Needs Assessment. *Radiology*. 2019;292(2):475-488. doi:10.1148/radiol.2019182646\n"
        "2. Herts BR, Silverman SG, Hindman NM, et al. Management of the Incidental Renal Mass on CT: A White Paper "
        "of the ACR Incidental Findings Committee. *J Am Coll Radiol*. 2018;15(2):264-273. "
        "doi:10.1016/j.jacr.2017.04.028\n"
        "3. Fassnacht M, Tsagarakis S, Terzolo M, et al. European Society of Endocrinology clinical practice "
        "guidelines on the management of adrenal incidentalomas, in collaboration with the European Network for "
        "the Study of Adrenal Tumors. *Eur J Endocrinol*. 2023;189(1):G1-G42. doi:10.1093/ejendo/lvad066")
