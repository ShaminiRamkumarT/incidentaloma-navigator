# IncidentaLens

*Incidental findings follow-up checker for 9 organs on CT, MRI and PET-CT*

**AI · Radiology · Incidental findings · NLP · Python/scikit-learn/Streamlit**

**Live demo:** https://shaminiramkumart.github.io/incidentaloma-navigator/web/ (runs in the browser, no install)

**Result:** I trained a small model on 600 synthetic reports. On 150 new synthetic reports across all nine organs it found every lesion and gave the same follow-up flag as the answer key for 85% of them. On my 16 hand-written held-out kidney and adrenal reports, it found more lesions than the regex baseline (88% vs 76%) but read the details less accurately, and it missed both high-severity under-calls that the regex caught. [Details below](#results).

## Portfolio card

**Why?**
- Radiology reports often mention findings nobody was looking for: a kidney cyst, a lung nodule, a liver spot, a pituitary lesion. Most are harmless. A few are early cancers or hormone-producing tumours.
- The recommendation in the report drives what happens next. When it's missing, too weak or out of line with the guideline, a cancer can be missed. When it asks for more than the guideline does, patients get scans they don't need, and the worry that comes with them.
- Each organ has its own guideline, written by a different society, with different size cut-offs and risk rules. Nobody can keep all of them in their head.

**What?**
- A tool that reads an imaging report, pulls out every incidental lesion with its features, applies the right guideline for that organ, and flags **under-calls** (for example a Bosniak IV cyst sent for ultrasound) and **over-calls** (for example a benign cyst sent for follow-up).
- Nine organs: kidney, adrenal, lung, liver, pancreas, thyroid, pituitary, brain (meningioma) and bone. Three modalities: CT, MRI and PET-CT.
- A validation dashboard that reports how well the reader extracts each detail, plus a worklist of mismatches ranked by severity.

**How?**
- Two stages. A reader turns free text into fields. A **deterministic, cited rules engine** then makes the guideline call, so every flag can be traced to a threshold and a paper.
- Three readers, scored the same way: a regex baseline (kidney and adrenal only), a trained token-labelling model (all organs), and an optional Claude reader that needs an API key.
- The trained model is logistic regression from scikit-learn, trained from scratch on synthetic reports. Everything it learns comes from the synthetic reports in this repository, so nothing has to be downloaded or signed for. It trains in about 10 seconds on a laptop.
- Data: 600 generated training reports, 150 generated test reports that include wordings the model never saw in training, and the original 46 hand-written kidney and adrenal reports (30 dev, 16 held-out).

## Results

| | Regex baseline | Trained model |
|---|---|---|
| **Held-out, hand-written** (16 reports, 17 lesions) | | |
| Lesions found | 76% | 88% |
| Guideline category agreement | 53% | 47% |
| Flag agreement | 59% | 53% |
| Discordances caught | 100% | 100% |
| Flags that were real (PPV) | 67% | 55% |
| High-severity under-calls caught | 2/2 | 0/2 |
| **Synthetic test, 9 organs** (150 reports, 190 lesions) | | |
| Lesions found | 4% | 100% |
| Guideline category agreement | 3% | 78% |
| Flag agreement | 2% | 85% |
| Discordances caught | 6% | 88% |
| Flags that were real (PPV) | 50% | 66% |
| High-severity under-calls caught | 1/12 | 9/12 |
| **Dev, hand-written** (30 reports, 32 lesions) | | |
| Flag agreement | 100% | 84% |

The regex only knows kidney and adrenal, so its synthetic-test numbers mostly show what it doesn't cover. The fair comparison between the two readers is the held-out row.

Guideline category agreement on the synthetic test, by organ: bone 100%, brain 100%, pancreas 100%, thyroid 88%, kidney 83%, pituitary 75%, liver 73%, adrenal 71%, lung 44%.

**What this shows:**
- The model handles new sentence structure better than the regex: it found 15 of 17 held-out lesions where the regex found 13.
- It is weak on words it has never seen. Lung scored lowest because the test set describes nodules as "nonsolid", "semisolid" or "numerous", words that never appear in training. Sizes written as "millimetres" were read as centimetres for the same reason.
- Both held-out high-severity misses came from details: in H10 it missed the irregular 4 mm wall (so Bosniak III became Bosniak I), and in H12 it put 85 HU on the wrong contrast phase and missed "heterogeneous enhancement". A tool like this has to be measured on the dangerous cases separately, because a good average can hide them.
- The dev set was used to debug the model, so its 84% is optimistic. The 16 held-out reports were never used for tuning.

**What I'd change first:** add more varied wording to the generator (units, nodule types, phase descriptions), look at the word after a number when reading units, and get a radiologist to write a fresh held-out set so the test is not written by the same person who built the generator.

To see exactly where each reader went wrong, open `results/eval_ml_holdout.csv` or `results/eval_ml_synth_test.csv`. They have one row per lesion with the correct answer, what the reader produced and which details it got wrong. The same tables appear as "Error log" in the Validation dashboard tab of the Streamlit app (`streamlit run app.py`).

## Guideline logic (simplified)

The engine checks the type of action (no follow-up, imaging, specialist referral or biopsy, hormonal work-up), not the exact interval. When a report doesn't state the patient's risk or age, any answer the guideline allows for some patient counts as concordant.

### Kidney (Bosniak v2019, ACR 2018) and adrenal (ESE/ENSAT 2023)

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

### Lung nodules (Fleischner 2017)

Size is the mean of the long and short axis.

| Nodule | Low risk | High risk |
|---|---|---|
| Solid <6 mm | No follow-up | Optional CT at 12 months |
| Solid 6-8 mm | CT at 6-12 months (3-6 if multiple) | Same, plus CT at 18-24 months |
| Solid >8 mm | CT at 3 months, PET-CT or biopsy | Same |
| Ground-glass or part-solid <6 mm | No follow-up (multiple: CT at 3-6 months) | Same |
| Ground-glass ≥6 mm | CT at 6-12 months, then every 2 years to 5 years | Same |
| Part-solid ≥6 mm | CT at 3-6 months; solid part ≥6 mm: referral also acceptable | Same |

### Liver lesions (ACR 2017)

High risk means known cancer, cirrhosis or a liver risk factor.

| Size | Features | Low risk | High risk |
|---|---|---|---|
| <1 cm | Any | No follow-up | MRI in 3-6 months |
| ≥1 cm | Benign | No follow-up | No follow-up |
| 1-1.5 cm | Flash-filling | No follow-up | Prompt MRI |
| >1.5 cm | Flash-filling | Prompt MRI | Prompt MRI |
| ≥1 cm | Suspicious | Prompt MRI | Prompt MRI (biopsy acceptable if >1.5 cm) |
| >1 cm | Can't tell on this scan | MRI | MRI |

On PET-CT, uptake above normal liver counts as a suspicious feature. That rule is mine, not the ACR's, and the tool labels it as such.

### Pancreatic cysts (ACR 2017)

| Cyst | Action |
|---|---|
| Enhancing solid component or main duct ≥10 mm | EUS-FNA and surgical consultation |
| Thickened/enhancing wall, non-enhancing mural nodule or duct ≥7 mm | EUS-FNA and surgical consultation |
| ≥3 cm with nothing else | EUS-FNA, or imaging follow-up |
| 1.5-3 cm | Imaging follow-up, or EUS-FNA |
| <1.5 cm | Imaging yearly (<65) or every 2 years (65-79), stop after 9-10 years or at 80 |
| Patient ≥80 | Usually no follow-up |

### Thyroid nodules on CT, MRI or PET-CT (ACR 2015)

| Nodule | Action |
|---|---|
| Local invasion or abnormal lymph nodes | Thyroid ultrasound |
| Limited life expectancy or serious comorbidity | No further evaluation |
| Focal FDG uptake | Ultrasound and FNA |
| Age <35 and ≥1 cm, or age ≥35 and ≥1.5 cm | Thyroid ultrasound |
| Smaller | No work-up |

### Pituitary incidentaloma (Endocrine Society 2011) and meningioma (EANO 2021)

| Lesion | Action |
|---|---|
| Pituitary, any size | Hormonal work-up for excess and deficiency |
| Pituitary <1 cm | MRI at 1 year, then every 1-2 years |
| Pituitary ≥1 cm | MRI at 6 months, then yearly for 3 years |
| Pituitary touching the optic chiasm | Visual fields and neurosurgery referral |
| Found on CT | Dedicated pituitary MRI first |
| Meningioma, no symptoms, not growing | MRI yearly for 5 years, then every 2 years |
| Meningioma, growing or symptomatic | Neurosurgery referral |

### Bone lesions (Bone-RADS 2022)

| Lesion | Category | Action |
|---|---|---|
| Pain, cortical involvement, soft-tissue extension, pathologic fracture or aggressive periosteal reaction | Bone-RADS 4 | Biopsy and/or orthopaedic oncology |
| Known cancer that spreads to bone | Bone-RADS 2/3 | PET, bone scan or MRI, or follow-up imaging |
| Macroscopic fat, purely sclerotic >885 HU, or a classic benign lesion | Bone-RADS 1 | Leave alone |
| Anything else | Bone-RADS 3 | Imaging at 6, 6 and 12 months |

Sources:

1. Silverman SG, Pedrosa I, Ellis JH, et al. Bosniak Classification of Cystic Renal Masses, Version 2019: An Update Proposal and Needs Assessment. *Radiology*. 2019;292(2):475-488. doi:10.1148/radiol.2019182646
2. Herts BR, Silverman SG, Hindman NM, et al. Management of the Incidental Renal Mass on CT: A White Paper of the ACR Incidental Findings Committee. *J Am Coll Radiol*. 2018;15(2):264-273. doi:10.1016/j.jacr.2017.04.028
3. Fassnacht M, Tsagarakis S, Terzolo M, et al. European Society of Endocrinology clinical practice guidelines on the management of adrenal incidentalomas, in collaboration with the European Network for the Study of Adrenal Tumors. *Eur J Endocrinol*. 2023;189(1):G1-G42. doi:10.1093/ejendo/lvad066
4. MacMahon H, Naidich DP, Goo JM, et al. Guidelines for Management of Incidental Pulmonary Nodules Detected on CT Images: From the Fleischner Society 2017. *Radiology*. 2017;284(1):228-243. doi:10.1148/radiol.2017161659
5. Gore RM, Pickhardt PJ, Mortele KJ, et al. Management of Incidental Liver Lesions on CT: A White Paper of the ACR Incidental Findings Committee. *J Am Coll Radiol*. 2017;14(11):1429-1437. doi:10.1016/j.jacr.2017.07.018
6. Megibow AJ, Baker ME, Morgan DE, et al. Management of Incidental Pancreatic Cysts: A White Paper of the ACR Incidental Findings Committee. *J Am Coll Radiol*. 2017;14(7):911-923. doi:10.1016/j.jacr.2017.03.010
7. Hoang JK, Langer JE, Middleton WD, et al. Managing Incidental Thyroid Nodules Detected on Imaging: White Paper of the ACR Incidental Thyroid Findings Committee. *J Am Coll Radiol*. 2015;12(2):143-150. doi:10.1016/j.jacr.2014.09.038
8. Freda PU, Beckers AM, Katznelson L, et al. Pituitary Incidentaloma: An Endocrine Society Clinical Practice Guideline. *J Clin Endocrinol Metab*. 2011;96(4):894-904. doi:10.1210/jc.2010-1048
9. Goldbrunner R, Stavrinou P, Jenkinson MD, et al. EANO guideline on the diagnosis and management of meningiomas. *Neuro Oncol*. 2021;23(11):1821-1834. doi:10.1093/neuonc/noab150
10. Chang CY, Garner HW, Ahlawat S, et al. Society of Skeletal Radiology – white paper. Guidelines for the diagnostic management of incidental solitary bone lesions on CT and MRI in adults: bone reporting and data system (Bone-RADS). *Skeletal Radiol*. 2022;51(9):1743-1764. doi:10.1007/s00256-022-04022-8

## Browser demo

`web/index.html` runs in any browser, with no install and no API key. Open the file directly, or serve the repository with GitHub Pages. It has four tabs.

"Check a report" lets you paste a report and check it live. It uses the regex reader, so it covers kidney and adrenal only. `web/engine.js` is a JavaScript port of the regex reader and the kidney/adrenal rules, and `web/parity_check.js` confirms it matches the Python on every sample report.

"Worklist" lists the 46 hand-written reports, sorted by severity.

"All organs: trained model" shows the 150 synthetic test reports read by the trained model, with each verdict next to the answer key. The model runs in Python, and `web/build_model_results.py` writes its results to `web/model_results.js`.

"Guideline rules" has the tables above.

## Run it

```bash
pip install -r requirements.txt
python data/build_reports.py && (cd data && python build_holdout.py)   # hand-written kidney/adrenal reports
python data/generate_synthetic.py     # 600 training + 150 test reports, all organs
python train_model.py                 # trains the model (about 10 s) -> models/extractor.joblib
python run_eval.py both all           # score regex and trained model on dev, holdout and synthetic test
ANTHROPIC_API_KEY=... python run_eval.py llm all   # optional: score the Claude reader
python web/build_model_results.py     # refresh the demo's all-organ tab
python -m pytest -q tests             # 69 guideline tests
streamlit run app.py
```

## Layout

```
navigator/schema.py          Finding model + action vocabulary
navigator/guidelines.py      Rules engine for all nine organs + concordance check
navigator/extract_rules.py   Regex baseline reader (kidney and adrenal)
navigator/extract_ml.py      Trained token-labelling reader (all organs)
navigator/extract_llm.py     Claude structured-output reader
navigator/evaluate.py        Matching + three-level scoring, fields scored per organ
data/generate_synthetic.py   Labelled report generator (train and test phrase banks)
data/                        Hand-written and synthetic reports with gold labels
results/                     Per-lesion CSVs and summary JSON per run
train_model.py               Trains and saves the model
app.py                       Streamlit app (report checker, validation dashboard, guideline tables)
web/                         Browser demo (index.html) and its JavaScript engine
```

## Limitations

- All reports are synthetic and written or generated by one author, who also built the rules. The held-out set reduces tuning bias but doesn't remove it. Gold labels haven't been reviewed by a radiologist.
- The model learns from wording I generated, so it inherits my phrasing habits. It is weak on words it has never seen.
- Guidelines are simplified to the type of action, not the interval. Pancreas schedules for patients over 80, liver rules on MRI and the Bone-RADS MRI branches are condensed. Brain covers suspected meningioma only.
- Educational prototype on fictional data. Not a medical device and not for clinical use.

## Next steps

1. Widen the generator's wording and score again on a held-out set written by someone else.
2. Try the Claude reader on the same test sets and compare cost, speed and accuracy with the trained model.
3. Test on real, anonymised radiology reports (for example MIMIC-IV-Note, which needs approved access).
4. Ask a radiologist to check my answer key, and see how often we agree.

## Author and license

Built by Shamini Ramkumar T, 2026. Code and synthetic reports are released under the MIT license. See [LICENSE](LICENSE).
