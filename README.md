# IncidentaLens

*Incidentaloma follow-up checker for kidney and adrenal lesions on CT*

**AI · Radiology · Renal cell carcinoma · Adrenal incidentaloma · Python/Streamlit**

**Live demo:** https://shaminiramkumart.github.io/incidentaloma-navigator/web/ (runs in the browser, no install)

**Result:** on 16 held-out reports written in new phrasing, the regex baseline caught every discordant recommendation (6/6, including both high-severity under-calls), but overall flag agreement fell from 100% on the dev set to 59%. [Details below](#results-regex-baseline).

## Portfolio card

**Why?**
- Kidney and adrenal lesions turn up incidentally on a large share of abdominal CTs. Most are benign, but a few are early renal cell carcinoma or adrenal cancer.
- The recommendation in the report is what drives follow-up. When it's missing, too weak or out of line with the guidelines, a cancer can be missed. When it asks for more than the guidelines do, patients get unnecessary scans and worry.
- Commercial "incidental findings" tools mostly *track* follow-up. Few check whether the recommendation itself is guideline-concordant in a transparent way.

**What?**
- A tool that reads a CT report, extracts every renal and adrenal lesion with its imaging features, applies Bosniak v2019, the ACR renal mass white paper and the ESE/ENSAT 2023 adrenal guideline, and flags **under-calls** (e.g. a Bosniak IV cyst sent for ultrasound) and **over-calls** (e.g. a benign cyst sent for follow-up).
- A validation dashboard that reports extraction accuracy on a held-out test set, plus a discordance worklist ranked by severity.

**How?**
- Two-stage design. An extractor (regex baseline or Claude with schema-validated structured output) turns free text into fields. A **deterministic, cited rules engine** then makes the guideline call, so every flag can be traced to a threshold and a paper.
- 46 hand-labelled synthetic reports (49 lesions), split into a dev set used to build the rules and a held-out set written afterwards in new phrasing. Scored at three levels: lesion detection, field accuracy, and end-to-end flag agreement.

## Results (regex baseline)

| | Dev (30 reports, 32 lesions) | Held-out (16 reports, 17 lesions) |
|---|---|---|
| Lesion detection recall | 100% | 76% |
| Guideline category agreement | 97% | 53% |
| Concordance flag agreement | 100% | 59% |
| Discordances caught (sensitivity) | 100% | 100% |
| Flags that were real (PPV) | 100% | 67% |
| High-severity under-calls caught | 5/5 | 2/2 |

**What this shows:** the regex rules look perfect on the reports they were tuned on and break on new phrasing: sizes in mm, "Hounsfield units", "HU 30 (precontrast)", "2.9 x 2.5 cm", two lesions in one sentence, "nodular enhancing soft tissue component". This is why I also wrote an AI reader (`navigator/extract_llm.py`) that uses Claude to read the report instead of keyword rules. It fills in the same fields and is scored the same way, and I kept its instructions general so it doesn't know the test phrasings. I haven't run it yet because it needs a paid API key.

**What I'd change first:** all 7 held-out misses come from the reader, not the guideline rules (4 lesions not detected, 3 misread). So I'd normalise units and size formats before extraction (mm to cm, "Hounsfield units" to HU, "2.9 x 2.5 cm" to longest diameter), split sentences that describe two lesions, and then score the Claude extractor on the same 16 reports, with a fresh held-out set afterwards so I'm not tuning on this one.

To see exactly where the reader went wrong, open `results/eval_rules_holdout.csv`. It has one row per lesion in the 16 test reports, with the correct answer, what the reader produced and which details it got wrong (for example, report H02: size read as 2.5 cm instead of 2.9 cm). The same table appears as "Error log" in the Validation dashboard tab of the Streamlit app (`streamlit run app.py`). The browser demo does not include it.

## Guideline logic (simplified)

| Organ | Feature | Category | Action |
|---|---|---|---|
| Kidney | Macroscopic fat | Angiomyolipoma | None (<4 cm), urology review (≥4 cm) |
| Kidney | Cystic + enhancing nodule | Bosniak IV | Urology referral |
| Kidney | Wall/septa ≥4 mm or irregular | Bosniak III | Urology referral |
| Kidney | Wall/septa 3 mm or ≥4 thin septa | Bosniak IIF | Imaging at 6 and 12 months, then yearly to 5 years |
| Kidney | 1-3 thin septa; ≥70 HU unenhanced; 21-30 HU portal venous; too small to characterize | Bosniak II | None |
| Kidney | Simple fluid, thin wall, no septa | Bosniak I | None |
| Kidney | Solid, enhancement ≥20 HU, no fat | Suspicious for RCC | Urology referral (<1 cm: imaging follow-up) |
| Kidney | Anything else | Indeterminate | Renal mass protocol CT or MRI |
| Adrenal | <1 cm | Below threshold | None |
| Adrenal | Homogeneous ≤10 HU unenhanced | Lipid-rich adenoma | No more imaging; 1 mg dexamethasone suppression test |
| Adrenal | ≥4 cm or heterogeneous (not benign) | Indeterminate, high risk | MDT/surgical review + hormonal work-up |
| Adrenal | >10 HU or no unenhanced phase | Indeterminate | Further imaging or repeat in 6-12 months + hormonal work-up |

Sources:

1. Silverman SG, Pedrosa I, Ellis JH, et al. Bosniak Classification of Cystic Renal Masses, Version 2019: An Update Proposal and Needs Assessment. *Radiology*. 2019;292(2):475-488. doi:10.1148/radiol.2019182646
2. Herts BR, Silverman SG, Hindman NM, et al. Management of the Incidental Renal Mass on CT: A White Paper of the ACR Incidental Findings Committee. *J Am Coll Radiol*. 2018;15(2):264-273. doi:10.1016/j.jacr.2017.04.028
3. Fassnacht M, Tsagarakis S, Terzolo M, et al. European Society of Endocrinology clinical practice guidelines on the management of adrenal incidentalomas, in collaboration with the European Network for the Study of Adrenal Tumors. *Eur J Endocrinol*. 2023;189(1):G1-G42. doi:10.1093/ejendo/lvad066

## Browser demo

`web/index.html` is a self-contained version of the checker that runs in any browser, with no install and no API key. Open the file directly, or serve the repository with GitHub Pages. It has three tabs: check a pasted report, a worklist of all 46 sample reports sorted by severity, and the guideline tables. `web/engine.js` is a JavaScript port of the regex reader and guideline engine. `web/parity_check.js` compares it against the Python version, and it matched on every sample report.

## Run it

```bash
pip install -r requirements.txt
python data/build_reports.py && (cd data && python build_holdout.py)   # regenerate datasets
python run_eval.py rules all          # score the regex baseline
ANTHROPIC_API_KEY=... python run_eval.py llm all   # score the AI reader (needs an API key)
python -m pytest -q tests             # 53 guideline tests
streamlit run app.py
```

## Layout

```
navigator/schema.py         Finding model + action vocabulary
navigator/guidelines.py     Bosniak / ACR / ESE rules engine + concordance check
navigator/extract_rules.py  Regex baseline extractor
navigator/extract_llm.py    Claude structured-output extractor
navigator/evaluate.py       Matching + three-level scoring
data/                       Synthetic reports and gold labels (dev + held-out)
results/                    Per-lesion CSVs and summary JSON per run
app.py                      Streamlit app (report checker, validation dashboard, guideline tables)
web/                        Browser demo (index.html) and its JavaScript engine
```

## Limitations

- Synthetic reports written by one author, who also built the rules. The held-out set reduces tuning bias but doesn't remove it. Gold labels haven't been reviewed by a radiologist.
- CT only: no MRI or ultrasound rules. Patient context that changes management (known malignancy, age, symptoms, prior imaging, adrenal washout values) is not modelled. ACR solid-mass branches are condensed.
- Educational prototype on fictional data. Not a medical device and not for clinical use.

## Next steps

1. Try the AI reader on the 16 test reports and see if it does better than the keyword version.
2. Test it on real, anonymised radiology reports (for example MIMIC-IV, which needs approved access).
3. Ask a radiologist to check my answer key, and see how often we agree.
4. Add MRI rules and take patient history into account (for example a known cancer).

## Author and license

Built by Shamini Ramkumar T, 2026. Code and synthetic reports are released under the MIT license. See [LICENSE](LICENSE).
