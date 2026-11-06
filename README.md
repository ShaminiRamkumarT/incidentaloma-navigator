# IncidentaLens

**AI · Radiology · Incidental findings · CT, MRI, PET-CT · Python/Streamlit**

**Live demo:** <https://shaminiramkumart.github.io/incidentaloma-navigator/web/> (runs in the browser, no install)

IncidentaLens reads a radiology report, finds the incidental lesions in it, applies the published guideline for each organ and flags follow-up recommendations that ask for too little or too much.

> Portfolio prototype on fictional reports. Not a medical device and not for clinical use.

## Portfolio card

**Why?**

- Incidental lesions turn up on a large share of CT, MRI and PET-CT scans. Most are harmless, but a few are early cancers or hormone-producing tumours.
- The recommendation in the report is what drives follow-up. When it is missing, too weak or out of line with the guideline, a cancer can be missed. When it asks for more than the guideline does, patients get scans and worry they do not need.
- Each organ has its own guideline with its own size cut-offs and risk rules, and radiologists who report across body regions cannot keep all of them in mind.
- Commercial "incidental findings" tools mostly *track* follow-up. Few check in a transparent way whether the recommendation itself matches the guideline.

**What?**

- A checker that reads a report, extracts every incidental lesion with its features, applies the guideline for that organ and flags **under-calls** (for example a Bosniak IV cyst sent for ultrasound) and **over-calls** (for example a benign cyst sent for follow-up).
- Nine organs, one published guideline each, ten guidelines in total.
- A validation dashboard and a worklist of flagged reports ranked by severity, with missed specialist referrals at the top.

**How?**

- Two-stage design. A reader turns free text into fields: a model trained on 600 synthetic reports labels each word (organ, size, density, features, and what the radiologist recommended), with a keyword (regex) reader as the baseline.
- A **deterministic, cited rules engine** then makes the guideline call, so every flag can be traced to a threshold and a paper. The model only reads the report; it never makes the guideline decision.
- Scored on synthetic reports, on hand-written reports in new phrasing, and on real sentences from published case reports.

## Coverage

| Organ | Guideline |
| --- | --- |
| Kidney | Bosniak v2019 · ACR renal mass white paper 2018 |
| Adrenal | ESE/ENSAT 2023 |
| Lung | Fleischner Society 2017 |
| Liver | ACR white paper 2017 |
| Pancreas | ACR white paper 2017 |
| Thyroid | ACR white paper 2015 |
| Pituitary | Endocrine Society 2011 |
| Brain (meningioma) | EANO 2021 |
| Bone | Bone-RADS 2022 |

## Results

The trained model against the keyword (regex) reader. Both cover all nine organs, and neither was tuned on these test reports.

| Test set | Regex | Model |
| --- | --- | --- |
| 150 synthetic reports, 9 organs: same flag as the answer key | 38% | 85% |
| 150 synthetic reports: high-severity cases caught | 7/13 | 10/13 |
| 51 real published sentences: lesions found | 70% | 82% |
| 27 hand-written reports, newer organs: same flag | 100% | 79% |
| 16 hand-written reports, kidney/adrenal: same flag | 59% | 53% |
| 16 hand-written reports: high-severity caught | 2/2 | 0/2 |

**What this shows**

- On wording I did not write myself (generated reports and real published sentences), the model clearly beats the regex reader.
- On reports I wrote, the regex reader does as well or better, because I also wrote its rules. That says more about who wrote the test than about the regex.
- The model missed both dangerous cases in the hand-written kidney/adrenal set. That is why high-severity cases get their own metric, and why catching them is the first thing to improve.

## Real wording check: published case reports

51 imaging sentences taken word for word from open-access case reports (CC BY). The model was not trained on them. This checks the reading step only, not the follow-up flag.

| Metric | Result |
| --- | --- |
| Real lesions found (44 lesions) | 82% (regex: 70%) |
| Side read correctly | 96% |
| Largest size read correctly | 61% |
| False alarms on lesions in other organs | 1/7 |

The model is weakest on bone terms it never saw in training and on sizes written next to other numbers.

Each sentence, its source and its answer key are in `data/real_snippets.json`. Per-sentence results are in `results/eval_ml_real.csv` (model) and `results/eval_rules_real.csv` (regex).

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

## Browser demo

`web/index.html` is a self-contained version of the checker that runs in any browser, with no install and no API key. Nothing you paste leaves the browser. It has a report checker, a worklist of 73 sample reports sorted by severity, and the guideline rules for all nine organs.

The browser checker uses the regex reader. The trained model's results come from Python, run offline on the synthetic test reports.

## Run it

```
pip install -r requirements.txt
python data/generate_synthetic.py    # 600 training + 150 test reports
python train_model.py                # train the model (about 10 s)
python run_eval.py both all          # score the regex reader and the model on all test sets
python data/build_real_snippets.py && python run_real_eval.py   # real wording check
python -m pytest -q tests            # guideline tests
streamlit run app.py
```

## Limitations

- Synthetic and hand-written reports come from one author, who also built the rules. Held-out sets reduce tuning bias but do not remove it.
- Gold labels have not been reviewed by a radiologist.
- The model missed both high-severity under-calls in the hand-written kidney/adrenal set.
- Reports are in English. German reports have not been tested.
- Patient context that changes management (known cancer, age, symptoms, prior imaging, hormone results) is only partly modelled. Several guideline branches are condensed.
- Educational prototype on fictional data. Not a medical device and not for clinical use.

## Next steps

1. Wider training wording, so the model catches the high-severity cases it currently misses.
2. A test set written by a radiologist instead of by me.
3. Real anonymised reports, and a radiologist-labelled subset with inter-rater agreement reported alongside model accuracy.
4. German-language reports.

## Author and license

Built by Shamini Ramkumar T, 2026.

- Code and fictional reports: MIT license.
- Real test sentences: CC BY, copyright of their original authors, with each source listed alongside the per-sentence results.
