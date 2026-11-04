# IncidentaLens

*Incidental findings follow-up checker for 9 organs on CT, MRI and PET-CT*

**AI · Radiology · Incidental findings · NLP · Python/scikit-learn/Streamlit**

**Live demo:** https://shaminiramkumart.github.io/incidentaloma-navigator/web/ (runs in the browser, no install)

**Result:** I trained a small model on 600 synthetic reports and compared it with a hand-written regex reader, both covering all nine organs. On 150 new synthetic reports the model gave the same follow-up flag as the answer key for 85% of lesions, the regex for 38%. On 51 real sentences from published case reports, the model found 82% of lesions and the regex 70%. On reports I wrote myself the regex does better, which says more about who wrote the test than about the regex. [Details below](#results).

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
- Three readers, scored the same way: a regex baseline, a trained token-labelling model, and an optional Claude reader that needs an API key. The regex and the model both cover all nine organs. The regex started in the first version of the project, which covered kidney and adrenal only; I later added rules for the other seven organs so the comparison is complete.
- The trained model is logistic regression from scikit-learn, trained from scratch on synthetic reports. Everything it learns comes from the synthetic reports in this repository, so nothing has to be downloaded or signed for. It trains in about 10 seconds on a laptop.
- Data: 600 generated training reports, 150 generated test reports that include wordings the model never saw in training, the original 46 hand-written kidney and adrenal reports (30 dev, 16 held-out), and 27 hand-written held-out reports for the seven newer organs.

## Results

Four test sets, from least to most independent of me:

| | Regex baseline | Trained model |
|---|---|---|
| **Hand-written held-out, kidney and adrenal** (16 reports, 17 lesions) | | |
| Lesions found | 76% | 88% |
| Guideline category agreement | 53% | 47% |
| Flag agreement | 59% | 53% |
| Discordances caught | 100% | 100% |
| Flags that were real (PPV) | 67% | 55% |
| High-severity under-calls caught | 2/2 | 0/2 |
| **Hand-written held-out, seven newer organs** (27 reports, 28 lesions) | | |
| Lesions found | 100% | 100% |
| Guideline category agreement | 100% | 89% |
| Flag agreement | 100% | 79% |
| Discordances caught | 100% | 86% |
| Flags that were real (PPV) | 100% | 75% |
| High-severity under-calls caught | 3/3 | 3/3 |
| **Synthetic test, 9 organs** (150 reports, 190 lesions) | | |
| Lesions found | 43% | 100% |
| Guideline category agreement | 37% | 78% |
| Flag agreement | 38% | 85% |
| Discordances caught | 52% | 88% |
| Flags that were real (PPV) | 86% | 66% |
| High-severity under-calls caught | 7/12 | 9/12 |
| **Real sentences from case reports** (51 sentences, 44 lesions; reading only, see below) | | |
| Lesions found | 70% | 82% |

Flag agreement on the synthetic test, by organ:

| | Kidney | Adrenal | Lung | Liver | Pancreas | Thyroid | Pituitary | Brain | Bone |
|---|---|---|---|---|---|---|---|---|---|
| Regex | 11% | 17% | 32% | 46% | 61% | 35% | 44% | 71% | 40% |
| Trained model | 89% | 67% | 82% | 88% | 83% | 82% | 81% | 100% | 100% |

**What this shows:**
- On the 27 new hand-written reports the regex scores 100%. I wrote those reports and I wrote the regex rules for those organs, so both use my wording. I wrote the reports first and did not tune the regex on them, but the overlap in vocabulary is still there. That result says little about how the regex would do on someone else's reports.
- On the two tests I didn't write sentence by sentence, the picture flips. On generated reports with varied wording, the model's flag agreement is 85% against 38% for the regex. On real published sentences, it finds 82% of lesions against 70%.
- The model is weak on words it has never seen. On the synthetic test, lung nodules described as "nonsolid", "semisolid" or "numerous" were misread, and "millimetres" was read as centimetres.
- On the new hand-written reports, most of the model's mistakes were in the impression: in three pancreas reports it added a specialist referral the report didn't ask for.
- On the original 16 held-out reports, both model misses on high-severity cases came from details: in H10 it missed the irregular 4 mm wall (so Bosniak III became Bosniak I), and in H12 it put 85 HU on the wrong contrast phase and missed "heterogeneous enhancement". Dangerous cases need their own metric, because a good average can hide them.
- The 30 dev reports were used to debug both readers, so their scores (regex 100%, model 84% flag agreement) are optimistic and are left out of the table.

**Two fixes made while building the new held-out set:**
- *Thyroid rule.* Writing the reports showed that the engine called an FNA unnecessary for an FDG-avid thyroid nodule. The ACR paper recommends ultrasound and FNA there, so the rule now expects both, and accepts ultrasound with FNA for nodules with suspicious features.
- *Scoring.* The scorer required the side of the lesion to match even for organs without sides, so "the left side of the pituitary" counted as a miss. It now ignores side when the answer key has none. This did not change any earlier result.

**What I'd change first:** add more varied wording to the generator (units, nodule types, phase descriptions, bone words), look at the word after a number when reading units, and get a radiologist to write a fresh held-out set, so the test is not written by the person who built both readers.

To see exactly where each reader went wrong, open the CSV files in `results/` (for example `eval_ml_holdout_all.csv` or `eval_rules_synth_test.csv`). They have one row per lesion with the correct answer, what the reader produced and which details it got wrong. The same tables appear as "Error log" in the Validation dashboard tab of the Streamlit app (`streamlit run app.py`).

## Real-wording check (published case reports)

The synthetic test only shows how the model handles wording I generated. To see how it copes with real clinical language, I took 51 imaging sentences word for word from open-access case reports licensed CC BY (found through Europe PMC). 44 describe a lesion in one of the nine organs; 7 describe lesions elsewhere (spleen, mesentery, gallbladder and so on) to count false alarms. I wrote the answer key (organ, side where stated, largest size) from each sentence. No account, data agreement or credentialed access was needed, and every sentence is attributed below.

These are case-report sentences, not radiology reports, so this checks the reading step only. It does not test the follow-up flag: case reports describe the treatment a patient got, not the follow-up a radiologist advised. The model was not retrained on any of them.

| 51 real sentences | Regex baseline | Trained model |
|---|---|---|
| Lesions found (44) | 70% | 82% |
| Side correct, where the sentence states it | 93% | 96% |
| Largest size read correctly | 59% | 61% |
| False alarms on the 7 negative sentences | 0/7 | 1/7 |

Found by organ:

| | Kidney | Adrenal | Lung | Liver | Pancreas | Thyroid | Pituitary | Brain | Bone |
|---|---|---|---|---|---|---|---|---|---|
| Regex | 50% | 62% | 75% | 100% | 100% | 75% | 100% | 0% | 0% |
| Trained model | 100% | 100% | 75% | 100% | 50% | 75% | 83% | 100% | 0% |

The misses follow a pattern. The model often reads the wrong number from a size like "8.2 x 6.4 cm" or "4.0 × 3.8 cm, SUVmax 3.4", and it doesn't know bone words such as "osteochondroma", "mandible" or "scapula", which never appear in its training data. Both are fixable with more varied training sentences. Per-sentence results are in `results/eval_ml_real.csv`; run it with `python data/build_real_snippets.py && python run_real_eval.py`.

<details>
<summary>Sources of the 51 sentences (all CC BY)</summary>

1. N A, Suraj N, Anne D, et al. The Malignant Imposter: Cystic Renal Oncocytoma Challenging Bosniak Criteria. *Cureus*. 2026. doi:10.7759/cureus.104622 PMC13046212, CC BY.
2. Wu Y, Zheng H, Pokhrel G, et al. Primary enteric-type adenocarcinoma of the renal parenchyma in a patient with bilateral renal malrotation: a case report and review of the literature. *Front Oncol*. 2026. doi:10.3389/fonc.2026.1977843 PMC13713323, CC BY.
3. Jiang B, Zhang S, Luo H, et al. Robot-assisted partial nephrectomy for TFE3-rearranged renal cell carcinoma: a case report and literature review. *Front Oncol*. 2026. doi:10.3389/fonc.2026.1740901 PMC13046509, CC BY.
4. Taur P, Kannan D, Penchala Reddy N, et al. Renal Hydatid Cyst: Diagnostic Quandaries and Surgical Strategies. *Cureus*. 2024. doi:10.7759/cureus.66289 PMC11376425, CC BY.
5. Mehrabi M, Eslami M, Payandeh M Multimodal treatment approach with sunitinib, pembrolizumab, bevacizumab, sirolimus, and zoledronic acid for locally advanced clear cell renal cell carcinoma: a case report. *Croat Med J*. 2025. PMC12424197, CC BY.
6. Maachi Y, Fadriq H, El Kacemi H, et al. Case Report: Fatal convergence of two confirmed and one radiologically suspected synchronous urological malignancies in a young patient. *Front Oncol*. 2026. doi:10.3389/fonc.2026.1852834 PMC13391280, CC BY.
7. Badiani A, Siew S, Al-Ansari M Silent Phaeochromocytoma in a Young Normotensive Woman. *Cureus*. 2026. doi:10.7759/cureus.110981 PMC13375148, CC BY.
8. Salzle M, Szafran-Swietlik A, LaRue M, et al. Large asymptomatic pheochromocytoma with incidental metastatic midgut carcinoid tumor. *JCEM Case Rep*. 2026. doi:10.1210/jcemcr/luag192 PMC13389709, CC BY.
9. Che J, Dintakurti A, Rafii DC To Resect or Not to Resect: An Incidental Finding of an Adrenal Schwannoma. *Cureus*. 2026. doi:10.7759/cureus.104068 PMC13012397, CC BY.
10. Adas M, Koc B, Adas G, et al. Ganglioneuroma presenting as an adrenal incidentaloma: a case report. *J Med Case Rep*. 2014. doi:10.1186/1752-1947-8-131 PMC4031973, CC BY.
11. Jain A, Rana A, Nonglait PL, et al. Incidental Adrenal Hemangioma: A Diagnostic and Management Challenge. *JCEM Case Rep*. 2025. doi:10.1210/jcemcr/luaf209 PMC12448940, CC BY.
12. Francisco Ferreira M, Valente F, Correia R, et al. A Challenging Diagnosis of Cushing's Syndrome in Primary Care: A Case Report. *Cureus*. 2026. doi:10.7759/cureus.108265 PMC13233115, CC BY.
13. Sage H, Jones E, Neychev V Cavernous Hemangioma: A Rare Adrenal Tumor Associated With Hyperaldosteronism. *Cureus*. 2025. doi:10.7759/cureus.79251 PMC11929149, CC BY.
14. Nistor C, Ciobica ML, Sima OC, et al. Ectopic Mediastinal Thyroid: A Crossroad Between a Multi-Layered Endocrine Perspective and a Contemporary Approach in Thoracic Surgery. *Life (Basel)*. 2024. doi:10.3390/life14111374 PMC11595551, CC BY.
15. Magliochetti Cammarata TM, Gupta S, Rallabhandi SSH, et al. Pulmonary Langerhans Cell Histiocytosis: An Unusual Differential for a Solitary Lung Nodule. *Case Rep Pulmonol*. 2024. doi:10.1155/2024/1315222 PMC10838197, CC BY.
16. Dessalegn N, Felux K, Seid E, et al. Primary Lung Adenocarcinoma Presenting as Cardiac Tamponade in a 40-Year-Old Non-Smoker. *Cureus*. 2022. doi:10.7759/cureus.21631 PMC8877732, CC BY.
17. Ajai Mokan Dasan SL, Flores AP, Misbahuddin K Pulmonary sequestration in a septuagenarian: a rare congenital lung lesion diagnosed in adulthood. *J Cardiothorac Surg*. 2026. doi:10.1186/s13019-026-04098-6 PMC13251046, CC BY.
18. Aberkane M, Karich N, Daoudi C, et al. Incidentally Discovered Pulmonary Hamartoma: A Case Report and Review of the Literature. *Cureus*. 2026. doi:10.7759/cureus.104563 PMC13043216, CC BY.
19. Aluisio G, Ralston G, Saylors G Solitary Melanoma Lesion in a Pulmonary Nodule: A Case Report. *Cureus*. 2025. doi:10.7759/cureus.85472 PMC12229246, CC BY.
20. Oki T, Iizuka S, Miwa H, et al. Combined Posterior and Interlobar Approaches Enable S10 Segmentectomy for a Centrally Located Intrapulmonary Schwannoma. *Surg Case Rep*. 2025. doi:10.70352/scrj.cr.25-0501 PMC12583920, CC BY.
21. Nozaka Y, Ohtsuki Y, Horie Y, et al. Pulmonary Squamous Cell Carcinoma with Repeated Increases and Decreases in Size. *Surg Case Rep*. 2025. doi:10.70352/scrj.cr.25-0067 PMC12223788, CC BY.
22. Fan C, Sang G, Liang Z, et al. Synchronous lung adenocarcinoma in situ and type B2-B3 thymoma in a frozen hemithorax: a case report and multidisciplinary approach. *Front Oncol*. 2026. doi:10.3389/fonc.2026.1846848 PMC13218942, CC BY.
23. Liang B, Shi H, Zeng Q, et al. Laparoscopic partial hepatectomy for primary hepatic PEComa: a case report. *BMC Gastroenterol*. 2026. doi:10.1186/s12876-026-04884-5 PMC13281640, CC BY.
24. Kamiya H, Yoshizawa E, Yamada A, et al. A case of hepatic segmental atrophy mimicking spontaneously necrotized hepatocellular carcinoma. *Radiol Case Rep*. 2026. doi:10.1016/j.radcr.2025.09.072 PMC12613024, CC BY.
25. Khazar V, Escobar S, Huang A, et al. A Case of an 80-Year-Old Woman With Chronic Eosinophilic Pneumonia and Clinically Significant Giant Hepatic Hemangioma. *Cureus*. 2025. doi:10.7759/cureus.98917 PMC12788885, CC BY.
26. Abdulkarim F, Kheruwala A, Erabia W, et al. Right-Sided Empyema Thoracis Mimicking Pulmonary Tuberculosis Secondary to a Complicated Hepatic Cyst: A Diagnostic Pitfall. *Cureus*. 2026. doi:10.7759/cureus.108362 PMC13240968, CC BY.
27. Balderas-Ortega JC, Escandon-Espinoza Y, Lopez Garcia K, et al. Pancreatic Intraductal Papillary Mucinous Neoplasm in a Carrier of a Reported Pathogenic BRCA2 Variant. *Cureus*. 2026. doi:10.7759/cureus.116881 PMC13695697, CC BY.
28. Pandian K, Priya S, Sivakumaran A, et al. Solid Pseudopapillary Neoplasm of the Pancreatic Tail With Splenic Hilar Involvement: A Case Report. *Cureus*. 2026. doi:10.7759/cureus.117340 PMC13723721, CC BY.
29. da Costa AC, Kumar J, Chaouch MA, et al. Solid Serous Cystadenoma Mimicking Neuroendocrine Tumor of the Pancreas: A Case Report. *Case Rep Gastrointest Med*. 2025. doi:10.1155/crgm/4945872 PMC12419928, CC BY.
30. Bland S, Thompson W III Microcystic serous cystadenoma of the pancreas causing biliary obstruction: a case report and review of the literature. *J Surg Case Rep*. 2024. doi:10.1093/jscr/rjae105 PMC10924709, CC BY.
31. Goddard J, Gaunt A, Markham DH Positron emission tomography detected thyroid incidentaloma. *Ann R Coll Surg Engl*. 2013. doi:10.1308/003588413x13511609956732 PMC3964670, CC BY.
32. Bravo Quiroz JG, Lizarraga Payan H, Prado Calleros HM, et al. Incidental Detection With 18F-PSMA-1007 PET/CT of Multifocal Papillary Thyroid Carcinoma During Staging of Very High-Risk Prostate Adenocarcinoma: A Case Report. *Cureus*. 2026. doi:10.7759/cureus.112857 PMC13477678, CC BY.
33. Amalo RB, Tuti Y, Dewi AR Diagnostic Challenges in a Case of Suspected Breast Cancer with Low FDG Uptake and an Incidental Thyroid Lesion: A Case Report and Literature Review. *World J Nucl Med*. 2025. doi:10.1055/s-0045-1809310 PMC12774523, CC BY.
34. Nicholas Z, Sughrue M, Battiste J, et al. When Evaluating a New Thyroid Mass and a Ring-Enhancing Brain Lesion (When Two Presentations Collide). *Cureus*. 2016. doi:10.7759/cureus.600 PMC4895081, CC BY.
35. Lemelin A, Lapoirie M, Abeillon J, et al. Pheochromocytoma, paragangliomas, and pituitary adenoma: An unusual association in a patient with an SDHD mutation. Case report. *Medicine (Baltimore)*. 2019. doi:10.1097/md.0000000000016594 PMC6708967, CC BY.
36. Rockwell S, Boley JS, Pulido N, et al. Acromegaly Discovered After Head Trauma: Multivessel Coronary Disease and Postoperative Meningitis Complicating a Pituitary Macroadenoma. *Cureus*. 2026. doi:10.7759/cureus.113532 PMC13521552, CC BY.
37. Rozenek EB, Gurnell M, Kunicki J, et al. Case Report: Development of a thyrotropinoma in a patient with thyroid hemiagenesis. *Front Endocrinol (Lausanne)*. 2026. doi:10.3389/fendo.2026.1902011 PMC13557997, CC BY.
38. Modi J, Ibrahim E, LaFoe K, et al. Craniofacial and Radiological Features as Diagnostic Clues to Unmask Acromegaly: A Case Report. *Cureus*. 2025. doi:10.7759/cureus.100144 PMC12832130, CC BY.
39. De Sanctis SA, Chiloiro S, Giampietro A, et al. Acromegaly and Morris Syndrome: Description of a Clinical Case. *Endocr Metab Immune Disord Drug Targets*. 2026. doi:10.2174/0118715303424098250925063845 PMC13316851, CC BY.
40. Chang C, Samlal KS, Maharaj ND, et al. Persistent Rhinosinusitis-Like Symptoms Revealing a Lactotroph Pituitary Neuroendocrine Tumour: A Case Report. *Cureus*. 2026. doi:10.7759/cureus.112575 PMC13463908, CC BY.
41. Hashikata H, Futamura G, Maki Y, et al. Pitfalls of Preoperative Embolization for Meningiomas: A Case Report on Occult Anastomosis Between the Middle and Posterior Meningeal Arteries. *Cureus*. 2025. doi:10.7759/cureus.80182 PMC11972430, CC BY.
42. Djukic M, Gossner J, Larsen J, et al. Foramen magnum meningioma: long-term follow up without neurosurgery - A case report. *J Med Case Rep*. 2025. doi:10.1186/s13256-025-05725-x PMC12670719, CC BY.
43. Meiyappan SK, Reddy GM, Pushpasekaran N, et al. Reviving a Skewed Dyskinetic Scapula Secondary to Ventral Exostosis: A Case Report. *Cureus*. 2026. doi:10.7759/cureus.102928 PMC12963672, CC BY.
44. Putro YAP, Magetsari R, Taroeno-Hariadi KW, et al. Classic and rare manifestations of multiple osteoma: A case report. *Int J Surg Case Rep*. 2023. doi:10.1016/j.ijscr.2023.108713 PMC10509817, CC BY.
45. Lin H, Wang X, Zhang L Isolated splenic littoral cell angioma in a child: a case report. *Front Oncol*. 2026. doi:10.3389/fonc.2026.1770088 PMC13314417, CC BY.
46. Monteiro DL, Eiró F, Contente H, et al. Mesenteric Cyst: A Case Report of a Rare Entity. *Cureus*. 2025. doi:10.7759/cureus.94731 PMC12619651, CC BY.
47. Tran H, Nguyen KH, Nguyen TPC, et al. Gallbladder tuberculosis as an incidental calcified mass in an elderly male: a case report. *J Surg Case Rep*. 2026. doi:10.1093/jscr/rjag123 PMC12966777, CC BY.
48. Hou Y, Yang Y, Li B, et al. Laparoscopic resection of an incidental retroperitoneal schwannoma in a 74-year-old male: a case report and literature review. *Front Oncol*. 2025. doi:10.3389/fonc.2025.1668644 PMC12685626, CC BY.
49. Zubi AR, Moosa AS, Adam IM, et al. Lateral Abdominal Wall Hibernoma: A Rare Case From the Maldives. *Cureus*. 2026. doi:10.7759/cureus.111221 PMC13386390, CC BY.
50. Touilite M, Zakaria Y, Chraa M, et al. Visual Epilepsy Mimicking Migraine Aura Leading to Delayed Diagnosis of an Occipital Cavernoma: A Case Report. *Cureus*. 2026. doi:10.7759/cureus.106768 PMC13067294, CC BY.
51. Khor J, Nguk Chai D Intrathoracic Schwannoma With Horner Syndrome: A Rare Association. *Cureus*. 2025. doi:10.7759/cureus.77453 PMC11826100, CC BY.

</details>

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

### How the guideline rules were checked

The rules for kidney and adrenal come from the first version of the project. For the seven organs added later, I checked each rule against a copy of the guideline before coding it. Not every original paper was openly readable, so this is what was actually read:

| Guideline | What was read | What could not be confirmed |
|---|---|---|
| Fleischner 2017 (lung) | Summary tables from [UW eRadiology](https://sites.uw.edu/eradsite/trauma-radiology-reference-resource/4-chest/fleischner-guidelines-for-pulmonary-nodules-2017), [North York General](https://www.nygh.on.ca/wp-content/uploads/2024/03/3133_Fleischner_Society_2017_Guidelines.pdf) and [PulmCCM](https://www.pulmccm.org/p/fleischner-society-guideline-update-2017) | The original paper was not read in full |
| ACR liver 2017 | The paper itself ([Dartmouth copy](https://geiselmed.dartmouth.edu/radiology/wp-content/uploads/sites/47/2019/04/incidental_liver.pdf)) and the [Canadian adaptation](https://journals.sagepub.com/doi/full/10.1177/0846537120928349) | The flowchart is an image, so the rules were rebuilt from the paper's text and figure notes. Volume and pages of the citation were taken from a secondary site |
| ACR pancreas 2017 | The paper itself ([University of Wisconsin copy](https://wiki.radiology.wisc.edu/images/1/13/Acrpancfull.pdf)) and the [UCSD summary](https://radres.ucsd.edu/pancreas) | The interval charts are images; schedules for patients over 80 were not readable. The issue number was not confirmed |
| ACR thyroid 2015 | Secondary summaries only: [Radiopaedia](https://radiopaedia.org/articles/69951), [AuntMinnie](https://www.auntminnie.com/clinical-news/ultrasound/article/15610817/acr-committee-offers-tips-for-incidental-thyroid-nodules) and the authors' [letter in *Thyroid*](https://core.ac.uk/download/70381401.pdf) | The original paper was not read |
| Endocrine Society pituitary 2011 | The guideline itself ([University of Liège copy](https://orbi.uliege.be/bitstream/2268/71283/1/JCEMFreda-2010.pdf)) | Nothing important |
| EANO meningioma 2021 | The [publisher's page](https://academic.oup.com/neuro-oncology/article/23/11/1821/6310843) | About half the text was read word for word; the follow-up interval came from the rest of the page and should be checked against the PDF |
| Bone-RADS 2022 | The paper's text ([SciSpace copy](https://scispace.com/pdf/society-of-skeletal-radiology-white-paper-guidelines-for-the-jumd1zv5.pdf)) | The flowcharts are images and only about half the text was available, so the rules follow the paper's prose. The MRI branch with low signal on both sequences was not read |

The real test sentences were found with the [Europe PMC search service](https://europepmc.org/RestfulWebService), limited to open-access case reports licensed CC BY.

## Browser demo

`web/index.html` runs in any browser, with no install and no API key. Open the file directly, or serve the repository with GitHub Pages. It has four tabs.

"Check a report" lets you paste a report and check it live, for all nine organs. It runs `web/engine.js`, a JavaScript copy of the regex reader and the rules engine. `web/parity_export.py` and `web/parity_check.js` confirm that the browser copy gives exactly the same lesions, fields, categories and flags as the Python on all 223 hand-written and synthetic test reports.

"Worklist" lists the 73 hand-written reports across all nine organs, sorted by severity.

"All organs: trained model" shows the 150 synthetic test reports read by the trained model, with each verdict next to the answer key. The model runs in Python, and `web/build_model_results.py` writes its results to `web/model_results.js`.

"Guideline rules" has the tables above.

## Run it

```bash
pip install -r requirements.txt
python data/build_reports.py && (cd data && python build_holdout.py)   # hand-written kidney/adrenal reports
python data/build_holdout_all.py      # hand-written held-out reports, seven newer organs
python data/generate_synthetic.py     # 600 training + 150 test reports, all organs
python train_model.py                 # trains the model (about 10 s) -> models/extractor.joblib
python run_eval.py both all           # score regex and model on dev, both held-out sets and synthetic test
ANTHROPIC_API_KEY=... python run_eval.py llm all   # optional: score the Claude reader
python web/build_model_results.py     # refresh the demo's all-organ tab
python web/parity_export.py > py_out.json && node web/parity_check.js py_out.json   # browser engine = Python
python data/build_real_snippets.py && python run_real_eval.py   # real-wording check
python -m pytest -q tests             # 97 guideline tests
streamlit run app.py
```

## Layout

```
navigator/schema.py          Finding model + action vocabulary
navigator/guidelines.py      Rules engine for all nine organs + concordance check
navigator/extract_rules.py   Regex baseline reader (all nine organs)
navigator/extract_ml.py      Trained token-labelling reader (all organs)
navigator/extract_llm.py     Claude structured-output reader
navigator/evaluate.py        Matching + three-level scoring, fields scored per organ
data/generate_synthetic.py   Labelled report generator (train and test phrase banks)
data/build_real_snippets.py  Real CC BY sentences with sources and answer key
data/                        Hand-written, synthetic and real-sentence data with gold labels
results/                     Per-lesion CSVs and summary JSON per run
train_model.py               Trains and saves the model
app.py                       Streamlit app (report checker, validation dashboard, guideline tables)
web/                         Browser demo (index.html) and its JavaScript engine
```

## Limitations

- All reports are synthetic and written or generated by one author, who also built the rules and both readers. The held-out sets reduce tuning bias but don't remove it, as the regex's 100% on my own new reports shows. Gold labels haven't been reviewed by a radiologist.
- The model learns from wording I generated, so it inherits my phrasing habits. It is weak on words it has never seen.
- Guidelines are simplified to the type of action, not the interval. Pancreas schedules for patients over 80, liver rules on MRI and the Bone-RADS MRI branches are condensed. Brain covers suspected meningioma only.
- Educational prototype on fictional data. Not a medical device and not for clinical use.

## Next steps

1. Widen the generator's wording and score again on a held-out set written by someone else.
2. Try the Claude reader on the same test sets and compare cost, speed and accuracy with the trained model.
3. Test on real, anonymised radiology reports (for example MIMIC-IV-Note, which needs approved access).
4. Ask a radiologist to check my answer key, and see how often we agree.

## Author and license

Built by Shamini Ramkumar T, 2026.

What this repository contains, who it belongs to, and under which terms:

| Part | Where | Owner and licence |
|---|---|---|
| Code, browser demo, rules engine, trained model | `navigator/`, `web/`, scripts | Shamini Ramkumar T, MIT license ([LICENSE](LICENSE)) |
| 73 hand-written reports | `data/reports.json`, `data/reports_holdout.json`, `data/reports_holdout_all.json` | Shamini Ramkumar T, MIT. Fictional, no patient data |
| 750 generated reports | `data/synthetic_*.json` | Shamini Ramkumar T, MIT. Fictional, made by `data/generate_synthetic.py`, no patient data |
| 51 real sentences | `data/real_snippets.json` | The original authors of each case report, under CC BY. Copied word for word, not changed, each stored with its full source. They are not covered by the MIT license. All 51 references: see [Sources of the 51 sentences](#real-wording-check-published-case-reports) |
| Answer key for the 51 sentences | `data/real_snippets.json` (`gold` fields) | Shamini Ramkumar T, MIT. Written by me from each sentence; not reviewed by a radiologist |
| Guideline tables | README, `navigator/guidelines.py`, demo | My simplified summaries of the cited guidelines. The guidelines belong to their publishers, and the societies that wrote them have not reviewed or endorsed this project. References and the copies read: see [Guideline logic](#guideline-logic-simplified) and [How the guideline rules were checked](#how-the-guideline-rules-were-checked) |
| Fonts on the demo page | Google Fonts (Archivo, IBM Plex) | Their designers, under the SIL Open Font License |

No real patient records, credentialed datasets (such as MIMIC) or data under restrictive terms were used. Sources I looked at and decided not to use, because their terms don't allow public redistribution, are MTSamples and the Indiana University chest X-ray reports (Open-i).

This is an educational prototype. It is not a medical device, it has not been clinically validated, and it must not be used to make decisions about patients.
