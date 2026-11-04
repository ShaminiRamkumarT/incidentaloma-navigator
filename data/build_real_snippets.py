"""Builds data/real_snippets.json: real imaging sentences from published, openly licensed case reports.

Each snippet is copied word for word from the abstract of an open-access case report licensed CC BY,
found through the Europe PMC search service. CC BY allows reuse with attribution, so every snippet
carries its full source (authors, title, journal, year, PMCID, DOI, licence).

The answer key (organ, side, largest size) was written by the project author from the sentence
itself: side is only given when the sentence states it. These are case-report sentences, not
radiology reports, so they test whether the reader copes with real clinical wording. They do not
test the follow-up check, because case reports describe treatment rather than a report's advice.
Negatives are real sentences about lesions outside the nine covered organs (spleen, mesentery...),
used to count false alarms.

Label review: the author then checked all 51 labels one by one against the sentence. 41 were accepted
as written and 10 were flagged. Each flagged snippet carries a "review" entry with the reviewer's
comment and what was done about it (REVIEW below). Two labels changed (liver side now "right" in P23
and P26, since a right hepatic lobe lesion is right-sided). The rest were clarified: a note on what
the label leaves out and why, and the described appearance where the sentence gives one. Appearance
is recorded for reference and is not scored.

Usage:  python data/build_real_snippets.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCES = {  # PMCID: (authors, title, journal, year, doi)
    "PMC13046212": ("N A, Suraj N, Anne D, et al.", "The Malignant Imposter: Cystic Renal Oncocytoma Challenging Bosniak Criteria", "Cureus", 2026, "10.7759/cureus.104622"),
    "PMC13713323": ("Wu Y, Zheng H, Pokhrel G, et al.", "Primary enteric-type adenocarcinoma of the renal parenchyma in a patient with bilateral renal malrotation: a case report and review of the literature", "Front Oncol", 2026, "10.3389/fonc.2026.1977843"),
    "PMC13046509": ("Jiang B, Zhang S, Luo H, et al.", "Robot-assisted partial nephrectomy for TFE3-rearranged renal cell carcinoma: a case report and literature review", "Front Oncol", 2026, "10.3389/fonc.2026.1740901"),
    "PMC11376425": ("Taur P, Kannan D, Penchala Reddy N, et al.", "Renal Hydatid Cyst: Diagnostic Quandaries and Surgical Strategies", "Cureus", 2024, "10.7759/cureus.66289"),
    "PMC12424197": ("Mehrabi M, Eslami M, Payandeh M", "Multimodal treatment approach with sunitinib, pembrolizumab, bevacizumab, sirolimus, and zoledronic acid for locally advanced clear cell renal cell carcinoma: a case report", "Croat Med J", 2025, None),
    "PMC13391280": ("Maachi Y, Fadriq H, El Kacemi H, et al.", "Case Report: Fatal convergence of two confirmed and one radiologically suspected synchronous urological malignancies in a young patient", "Front Oncol", 2026, "10.3389/fonc.2026.1852834"),
    "PMC13375148": ("Badiani A, Siew S, Al-Ansari M", "Silent Phaeochromocytoma in a Young Normotensive Woman", "Cureus", 2026, "10.7759/cureus.110981"),
    "PMC13389709": ("Salzle M, Szafran-Swietlik A, LaRue M, et al.", "Large asymptomatic pheochromocytoma with incidental metastatic midgut carcinoid tumor", "JCEM Case Rep", 2026, "10.1210/jcemcr/luag192"),
    "PMC13012397": ("Che J, Dintakurti A, Rafii DC", "To Resect or Not to Resect: An Incidental Finding of an Adrenal Schwannoma", "Cureus", 2026, "10.7759/cureus.104068"),
    "PMC4031973": ("Adas M, Koc B, Adas G, et al.", "Ganglioneuroma presenting as an adrenal incidentaloma: a case report", "J Med Case Rep", 2014, "10.1186/1752-1947-8-131"),
    "PMC12448940": ("Jain A, Rana A, Nonglait PL, et al.", "Incidental Adrenal Hemangioma: A Diagnostic and Management Challenge", "JCEM Case Rep", 2025, "10.1210/jcemcr/luaf209"),
    "PMC13233115": ("Francisco Ferreira M, Valente F, Correia R, et al.", "A Challenging Diagnosis of Cushing's Syndrome in Primary Care: A Case Report", "Cureus", 2026, "10.7759/cureus.108265"),
    "PMC11929149": ("Sage H, Jones E, Neychev V", "Cavernous Hemangioma: A Rare Adrenal Tumor Associated With Hyperaldosteronism", "Cureus", 2025, "10.7759/cureus.79251"),
    "PMC11595551": ("Nistor C, Ciobica ML, Sima OC, et al.", "Ectopic Mediastinal Thyroid: A Crossroad Between a Multi-Layered Endocrine Perspective and a Contemporary Approach in Thoracic Surgery", "Life (Basel)", 2024, "10.3390/life14111374"),
    "PMC10838197": ("Magliochetti Cammarata TM, Gupta S, Rallabhandi SSH, et al.", "Pulmonary Langerhans Cell Histiocytosis: An Unusual Differential for a Solitary Lung Nodule", "Case Rep Pulmonol", 2024, "10.1155/2024/1315222"),
    "PMC8877732": ("Dessalegn N, Felux K, Seid E, et al.", "Primary Lung Adenocarcinoma Presenting as Cardiac Tamponade in a 40-Year-Old Non-Smoker", "Cureus", 2022, "10.7759/cureus.21631"),
    "PMC13251046": ("Ajai Mokan Dasan SL, Flores AP, Misbahuddin K", "Pulmonary sequestration in a septuagenarian: a rare congenital lung lesion diagnosed in adulthood", "J Cardiothorac Surg", 2026, "10.1186/s13019-026-04098-6"),
    "PMC13043216": ("Aberkane M, Karich N, Daoudi C, et al.", "Incidentally Discovered Pulmonary Hamartoma: A Case Report and Review of the Literature", "Cureus", 2026, "10.7759/cureus.104563"),
    "PMC12229246": ("Aluisio G, Ralston G, Saylors G", "Solitary Melanoma Lesion in a Pulmonary Nodule: A Case Report", "Cureus", 2025, "10.7759/cureus.85472"),
    "PMC12583920": ("Oki T, Iizuka S, Miwa H, et al.", "Combined Posterior and Interlobar Approaches Enable S10 Segmentectomy for a Centrally Located Intrapulmonary Schwannoma", "Surg Case Rep", 2025, "10.70352/scrj.cr.25-0501"),
    "PMC12223788": ("Nozaka Y, Ohtsuki Y, Horie Y, et al.", "Pulmonary Squamous Cell Carcinoma with Repeated Increases and Decreases in Size", "Surg Case Rep", 2025, "10.70352/scrj.cr.25-0067"),
    "PMC13218942": ("Fan C, Sang G, Liang Z, et al.", "Synchronous lung adenocarcinoma in situ and type B2-B3 thymoma in a frozen hemithorax: a case report and multidisciplinary approach", "Front Oncol", 2026, "10.3389/fonc.2026.1846848"),
    "PMC13281640": ("Liang B, Shi H, Zeng Q, et al.", "Laparoscopic partial hepatectomy for primary hepatic PEComa: a case report", "BMC Gastroenterol", 2026, "10.1186/s12876-026-04884-5"),
    "PMC12613024": ("Kamiya H, Yoshizawa E, Yamada A, et al.", "A case of hepatic segmental atrophy mimicking spontaneously necrotized hepatocellular carcinoma", "Radiol Case Rep", 2026, "10.1016/j.radcr.2025.09.072"),
    "PMC12788885": ("Khazar V, Escobar S, Huang A, et al.", "A Case of an 80-Year-Old Woman With Chronic Eosinophilic Pneumonia and Clinically Significant Giant Hepatic Hemangioma", "Cureus", 2025, "10.7759/cureus.98917"),
    "PMC13240968": ("Abdulkarim F, Kheruwala A, Erabia W, et al.", "Right-Sided Empyema Thoracis Mimicking Pulmonary Tuberculosis Secondary to a Complicated Hepatic Cyst: A Diagnostic Pitfall", "Cureus", 2026, "10.7759/cureus.108362"),
    "PMC13695697": ("Balderas-Ortega JC, Escandon-Espinoza Y, Lopez Garcia K, et al.", "Pancreatic Intraductal Papillary Mucinous Neoplasm in a Carrier of a Reported Pathogenic BRCA2 Variant", "Cureus", 2026, "10.7759/cureus.116881"),
    "PMC13723721": ("Pandian K, Priya S, Sivakumaran A, et al.", "Solid Pseudopapillary Neoplasm of the Pancreatic Tail With Splenic Hilar Involvement: A Case Report", "Cureus", 2026, "10.7759/cureus.117340"),
    "PMC12419928": ("da Costa AC, Kumar J, Chaouch MA, et al.", "Solid Serous Cystadenoma Mimicking Neuroendocrine Tumor of the Pancreas: A Case Report", "Case Rep Gastrointest Med", 2025, "10.1155/crgm/4945872"),
    "PMC10924709": ("Bland S, Thompson W III", "Microcystic serous cystadenoma of the pancreas causing biliary obstruction: a case report and review of the literature", "J Surg Case Rep", 2024, "10.1093/jscr/rjae105"),
    "PMC3964670": ("Goddard J, Gaunt A, Markham DH", "Positron emission tomography detected thyroid incidentaloma", "Ann R Coll Surg Engl", 2013, "10.1308/003588413x13511609956732"),
    "PMC13477678": ("Bravo Quiroz JG, Lizarraga Payan H, Prado Calleros HM, et al.", "Incidental Detection With 18F-PSMA-1007 PET/CT of Multifocal Papillary Thyroid Carcinoma During Staging of Very High-Risk Prostate Adenocarcinoma: A Case Report", "Cureus", 2026, "10.7759/cureus.112857"),
    "PMC12774523": ("Amalo RB, Tuti Y, Dewi AR", "Diagnostic Challenges in a Case of Suspected Breast Cancer with Low FDG Uptake and an Incidental Thyroid Lesion: A Case Report and Literature Review", "World J Nucl Med", 2025, "10.1055/s-0045-1809310"),
    "PMC4895081": ("Nicholas Z, Sughrue M, Battiste J, et al.", "When Evaluating a New Thyroid Mass and a Ring-Enhancing Brain Lesion (When Two Presentations Collide)", "Cureus", 2016, "10.7759/cureus.600"),
    "PMC6708967": ("Lemelin A, Lapoirie M, Abeillon J, et al.", "Pheochromocytoma, paragangliomas, and pituitary adenoma: An unusual association in a patient with an SDHD mutation. Case report", "Medicine (Baltimore)", 2019, "10.1097/md.0000000000016594"),
    "PMC13521552": ("Rockwell S, Boley JS, Pulido N, et al.", "Acromegaly Discovered After Head Trauma: Multivessel Coronary Disease and Postoperative Meningitis Complicating a Pituitary Macroadenoma", "Cureus", 2026, "10.7759/cureus.113532"),
    "PMC13557997": ("Rozenek EB, Gurnell M, Kunicki J, et al.", "Case Report: Development of a thyrotropinoma in a patient with thyroid hemiagenesis", "Front Endocrinol (Lausanne)", 2026, "10.3389/fendo.2026.1902011"),
    "PMC12832130": ("Modi J, Ibrahim E, LaFoe K, et al.", "Craniofacial and Radiological Features as Diagnostic Clues to Unmask Acromegaly: A Case Report", "Cureus", 2025, "10.7759/cureus.100144"),
    "PMC13316851": ("De Sanctis SA, Chiloiro S, Giampietro A, et al.", "Acromegaly and Morris Syndrome: Description of a Clinical Case", "Endocr Metab Immune Disord Drug Targets", 2026, "10.2174/0118715303424098250925063845"),
    "PMC13463908": ("Chang C, Samlal KS, Maharaj ND, et al.", "Persistent Rhinosinusitis-Like Symptoms Revealing a Lactotroph Pituitary Neuroendocrine Tumour: A Case Report", "Cureus", 2026, "10.7759/cureus.112575"),
    "PMC11972430": ("Hashikata H, Futamura G, Maki Y, et al.", "Pitfalls of Preoperative Embolization for Meningiomas: A Case Report on Occult Anastomosis Between the Middle and Posterior Meningeal Arteries", "Cureus", 2025, "10.7759/cureus.80182"),
    "PMC12670719": ("Djukic M, Gossner J, Larsen J, et al.", "Foramen magnum meningioma: long-term follow up without neurosurgery - A case report", "J Med Case Rep", 2025, "10.1186/s13256-025-05725-x"),
    "PMC12963672": ("Meiyappan SK, Reddy GM, Pushpasekaran N, et al.", "Reviving a Skewed Dyskinetic Scapula Secondary to Ventral Exostosis: A Case Report", "Cureus", 2026, "10.7759/cureus.102928"),
    "PMC10509817": ("Putro YAP, Magetsari R, Taroeno-Hariadi KW, et al.", "Classic and rare manifestations of multiple osteoma: A case report", "Int J Surg Case Rep", 2023, "10.1016/j.ijscr.2023.108713"),
    "PMC13314417": ("Lin H, Wang X, Zhang L", "Isolated splenic littoral cell angioma in a child: a case report", "Front Oncol", 2026, "10.3389/fonc.2026.1770088"),
    "PMC12619651": ("Monteiro DL, Eiró F, Contente H, et al.", "Mesenteric Cyst: A Case Report of a Rare Entity", "Cureus", 2025, "10.7759/cureus.94731"),
    "PMC12966777": ("Tran H, Nguyen KH, Nguyen TPC, et al.", "Gallbladder tuberculosis as an incidental calcified mass in an elderly male: a case report", "J Surg Case Rep", 2026, "10.1093/jscr/rjag123"),
    "PMC12685626": ("Hou Y, Yang Y, Li B, et al.", "Laparoscopic resection of an incidental retroperitoneal schwannoma in a 74-year-old male: a case report and literature review", "Front Oncol", 2025, "10.3389/fonc.2025.1668644"),
    "PMC13386390": ("Zubi AR, Moosa AS, Adam IM, et al.", "Lateral Abdominal Wall Hibernoma: A Rare Case From the Maldives", "Cureus", 2026, "10.7759/cureus.111221"),
    "PMC13067294": ("Touilite M, Zakaria Y, Chraa M, et al.", "Visual Epilepsy Mimicking Migraine Aura Leading to Delayed Diagnosis of an Occipital Cavernoma: A Case Report", "Cureus", 2026, "10.7759/cureus.106768"),
    "PMC11826100": ("Khor J, Nguk Chai D", "Intrathoracic Schwannoma With Horner Syndrome: A Rare Association", "Cureus", 2025, "10.7759/cureus.77453"),
}

# (PMCID, sentence copied verbatim, gold organ or None for a negative, side as stated, largest size in cm)
SNIPPETS = [
    ("PMC13046212", "A 70-year-old male was found to have a right renal cyst on abdominal imaging conducted for right upper quadrant fullness. Contrast-enhanced CT tomography of the abdomen revealed a 6.8 x 6.6 x 6.4 cm exophytic hypodense cystic lesion with an internal soft tissue component measuring 13 mm in thickness, which exhibited significant enhancement after contrast administration.", "kidney", "right", 6.8),
    ("PMC13713323", "We report a 47-year-old asymptomatic female with an incidental 68 mm cystic-solid left renal mass detected during a trauma evaluation.", "kidney", "left", 6.8),
    ("PMC13046509", "Abdominal contrast-enhanced computed tomography (CT) revealed a Bosniak category III cystic renal lesion, raising suspicion for renal cell carcinoma, measuring approximately 2.1 × 2.4 × 2.1 cm.", "kidney", "unknown", 2.4),
    ("PMC11376425", "Ultrasonography and contrast-enhanced computed tomography identified a 15 cm Bosniak type 3 complex cystic lesion arising from the left kidney, causing hydronephrosis and hydroureter.", "kidney", "left", 15.0),
    ("PMC12424197", "A 45-year-old woman presented with an incidentally discovered 9-cm mass in the left kidney, which was later diagnosed as grade-2 ccRCC with adrenal and lymph node involvement.", "kidney", "left", 9.0),
    ("PMC13391280", "Surveillance imaging revealed a recurrence at the right nephrectomy bed (12 cm) and an incidentally discovered left renal mass (4 cm).", "kidney", "left", 4.0),
    ("PMC13375148", "Contrast-enhanced CT of the abdomen and pelvis revealed a 4cm right adrenal lesion with high attenuation of ~90 Hounsfield units (HU) and a heterogeneous appearance, raising suspicion of a non-adenomatous adrenal mass.", "adrenal", "right", 4.0),
    ("PMC13389709", "Computed tomography (CT) showed a hyperenhancing mass of the left adrenal gland with central necrosis, calcification, mass effect, and measuring 9.1 × 8.3 cm.", "adrenal", "left", 9.1),
    ("PMC13012397", "In this report, we present a case of a 61-year-old male patient who underwent an MRI of the abdomen for the evaluation of gallstones and was found to have an incidental left adrenal mass measuring approximately 6 cm.", "adrenal", "left", 6.0),
    ("PMC4031973", "Our patient underwent computed tomography of his abdomen, which showed a relatively homogenous left adrenal tumor measuring 5.2 × 4.3 × 7.1cm.", "adrenal", "left", 7.1),
    ("PMC12448940", "Here, we present the case of a 43-year-old male individual who was incidentally found to have a right adrenal mass during evaluation for polycythemia. Initial imaging revealed a 3.1 × 2.3 cm mass.", "adrenal", "right", 3.1),
    ("PMC13233115", "After presenting with abdominal pain, a computed tomography scan incidentally revealed a 35 mm left adrenal mass suggestive of an adenoma.", "adrenal", "left", 3.5),
    ("PMC11929149", "A 53-year-old male patient was referred for a surgical consultation with a 5 cm heterogeneous, lipid-poor, incidental left adrenal mass.", "adrenal", "left", 5.0),
    ("PMC11595551", "Also, CT identified a thymus-like mass and a left adrenal incidentaloma of 3 cm.", "adrenal", "left", 3.0),
    ("PMC10838197", "Our patient was an elderly male and an active smoker, who was referred to the pulmonology clinic for an incidental 19 mm lung nodule seen on a chest CT scan.", "lung", "unknown", 1.9),
    ("PMC8877732", "This revealed a left upper lobe mass measuring 3.6 x 2.8 cm without mediastinal or hilar lymphadenopathy.", "lung", "left", 3.6),
    ("PMC13251046", "Initial CT revealed a 3.2 cm triangular mass in the posteromedial aspect of the left lower lobe abutting the descending thoracic aorta.", "lung", "left", 3.2),
    ("PMC13043216", "A computed tomography (CT) scan revealed a solid, bilobed pulmonary nodule in the lingula measuring 8 mm in the long axis, for which he underwent surgical resection.", "lung", "unknown", 0.8),
    ("PMC12229246", "This case describes a 63-year-old female with an incidental 12 x 11 mm nodule found on chest computed tomography (CT) in the upper lobe of the left lung.", "lung", "left", 1.2),
    ("PMC12583920", "A 46-year-old non-smoking woman presented with an incidental 2.4 cm pulmonary nodule centrally located in segment 10 (S10) of the left lower lobe.", "lung", "left", 2.4),
    ("PMC12223788", "The scan also showed a 1.1 cm snowball-like shadow in the right lower lobe of the lung.", "lung", "right", 1.1),
    ("PMC13218942", "A 73-year-old woman with prior tuberculosis and stented coronary artery disease presented with a hypermetabolic right upper lobe (RUL) nodule (2.3 cm, SUVmax 5.0) and an anterior mediastinal mass (SUVmax 3.0) on PET/CT.", "lung", "right", 2.3),
    ("PMC13281640", "Comprehensive imaging studies, including ultrasound, computed tomography (CT), and magnetic resonance imaging (MRI), revealed a 58 mm-diameter space-occupying lesion in segments V and VIII of the right hepatic lobe.", "liver", "right", 5.8),
    ("PMC12613024", "An 80-year-old man presented with a new 3 cm hepatic lesion that met LI-RADS-5 criteria.", "liver", "unknown", 3.0),
    ("PMC12788885", "Abdominal and pelvic CT scan showed a hepatic hemangioma, measuring approximately 8.2 x 6.4 cm.", "liver", "unknown", 8.2),
    ("PMC13240968", "Thoracoabdominal computed tomography (CT) unexpectedly identified a large (12.5 x 9 cm), multiloculated cystic lesion in the right hepatic lobe exhibiting mass effect and transdiaphragmatic extension into the pleural space.", "liver", "right", 12.5),
    ("PMC13695697", "In June 2025, during long-term oncologic follow-up, positron emission tomography-computed tomography incidentally identified a 21×21 mm pancreatic tail cyst.", "pancreas", "unknown", 2.1),
    ("PMC13723721", "Contrast-enhanced computed tomography revealed a 7.4 × 7.0 × 6.4 cm well-defined cystic lesion with solid components arising from the pancreatic tail, suggestive of SPEN.", "pancreas", "unknown", 7.4),
    ("PMC12419928", "Preoperative abdominal magnetic resonance imaging (MRI) with contrast demonstrated a solid, hypervascular lesion at the pancreas, measuring 3.5 × 2.2 × 1.9 cm, with marked enhancement on dynamic imaging.", "pancreas", "unknown", 3.5),
    ("PMC10924709", "Abdominal computed tomography scan showed a 16 cm obstructive pancreatic mass near the porta hepatis region.", "pancreas", "unknown", 16.0),
    ("PMC3964670", "Subsequent clinical examination and investigations revealed a 3 cm nodule in the left lower pole of the thyroid.", "thyroid", "left", 3.0),
    ("PMC13477678", "Imaging demonstrated a focal PSMA-avid hypodense nodule in the right thyroid lobe, measuring 15 mm with a maximum standardized uptake value (SUVmax) of 6.33.", "thyroid", "right", 1.5),
    ("PMC12774523", "Additionally, an incidental left thyroid lesion (4.0 × 3.8 cm, SUVmax 3.4) with calcifications was detected, raising suspicion for malignancy.", "thyroid", "left", 4.0),
    ("PMC4895081", "A CT of the chest noted a 4-cm cystic thyroid lesion that was diagnosed as a thyroid cancer with brain metastases.", "thyroid", "unknown", 4.0),
    ("PMC6708967", "A pituitary magnetic resonance imaging (MRI) confirmed the presence of a 14 mm pituitary macroadenoma.", "pituitary", "unknown", 1.4),
    ("PMC13521552", "We report the case of a 59-year-old man whose acromegaly was identified incidentally after a 1.6 cm pituitary macroadenoma was found on MRI obtained for trauma evaluation following a bicycle accident.", "pituitary", "unknown", 1.6),
    ("PMC13557997", "Pituitary MRI demonstrated an 11mm macroadenoma.", "pituitary", "unknown", 1.1),
    ("PMC12832130", "MRI of the head showed a 1.9 cm pituitary macroadenoma.", "pituitary", "unknown", 1.9),
    ("PMC13316851", "A contrasted pituitary MRI showed the presence of an 8 mm intrasellar pituitary adenoma.", "pituitary", "unknown", 0.8),
    ("PMC13463908", "Subsequent magnetic resonance imaging (MRI) confirmed a 3.4cm pituitary macroadenoma with left cavernous and sphenoid sinus invasion, left internal carotid artery encasement, optic nerve involvement, and imaging features of pituitary apoplexy.", "pituitary", "unknown", 3.4),
    ("PMC11972430", "A 61-year-old woman with no prior medical history was incidentally found to have a right parietal extra-axial tumor on magnetic resonance imaging (MRI). She was neurologically intact upon admission, but perifocal cerebral edema was observed surrounding the tumor, which measured approximately 33 mm × 27 mm × 22 mm.", "brain", "right", 3.3),
    ("PMC12670719", "In a white German 79-year-old woman, a small dorsal foramen magnum meningioma was detected by cerebral magnetic resonance imaging. After 7 years, cerebral magnetic resonance imaging showed considerable tumor growth (an increase in diameters from 15 × 16 × 20 mm to 28 × 30 × 37 mm), brain stem compression, and obstructive hydrocephalus.", "brain", "unknown", 3.7),
    ("PMC12963672", "Magnetic resonance imaging (MRI) showed a 5 × 4 cm osteochondroma in the ventral surface of the scapula, with distorted and irregular cartilage cap, risking features of sarcomatous changes.", "bone", "unknown", 5.0),
    ("PMC10509817", "On physical examination, there were several masses in the head with the largest on the left mandible measuring 5.6 × 6.0 × 4.5 cm from MSCT examination.", "bone", "left", 6.0),
    # negatives: real lesions outside the nine covered organs
    ("PMC13314417", "Abdominal computed tomography (CT) showed a round-like hypodense mass (4.8 cm×4.8 cm×5.3 cm) in the upper pole of the spleen (plain CT value: ~43 HU).", None, None, None),
    ("PMC12619651", "Cross-sectional imaging demonstrated a 56 mm cystic lesion within the mesentery, located adjacent to the celiac trunk, a previously unreported site.", None, None, None),
    ("PMC12966777", "Contrast-enhanced computed tomography (CT) demonstrated a 2 × 4 cm calcified fundal lesion with focal wall thickening, raising strong suspicion of malignancy.", None, None, None),
    ("PMC12685626", "The patient, a 74-year-old male with hypertension, presented with an incidental finding of a retroperitoneal mass (3.0 x 2.5 cm) on abdominal CT.", None, None, None),
    ("PMC13386390", "Magnetic resonance imaging (MRI) revealed a well-defined 9.7 × 6.6 × 5.7 cm soft tissue mass within the myofascial plane between the external and internal oblique muscles.", None, None, None),
    ("PMC13067294", "Brain magnetic resonance imaging (MRI) revealed a rounded left occipital cortico-subcortical lesion measuring 17 x 16.5 x 16 mm, with imaging features suggestive of a cavernoma and without significant mass effect or perilesional edema.", None, None, None),
    ("PMC11826100", "A contrast computed tomography (CT) of the thorax showed a large (8.1 x 7.3 x 7.3 cm), well-defined, heterogeneous enhancing mass over the left apical-posterior mediastinum.", None, None, None),
]


# Reviewer flags on the first pass, keyed by snippet id: (verdict, reviewer comment, what was done)
REVIEW = {
    "P03": ("disagree", "Side", "Kept side as unknown: the sentence does not say left or right."),
    "P05": ("unsure", "Involves adrenal and lymph nodes as well",
            "Kept one lesion. The adrenal and lymph node involvement is spread of the kidney cancer, "
            "not a separate incidental finding, so it gets no follow-up advice of its own."),
    "P06": ("disagree", "Both left and right kidney",
            "Kept the left renal mass as the only target. The 12 cm right-sided mass is a recurrence in "
            "the nephrectomy bed after the right kidney was removed: known cancer, outside the incidental "
            "lesion guidelines. Now stated in the label."),
    "P08": ("disagree", "Why is it not mentioning the status/nature of the mass",
            "Added the appearance: hyperenhancing, central necrosis, calcification, mass effect."),
    "P10": ("unsure", "Why is it not mentioning the status/nature of the mass",
            "Added the appearance: relatively homogeneous."),
    "P23": ("disagree", "Right", "Changed side from unknown to right (right hepatic lobe)."),
    "P26": ("disagree", "Right", "Changed side from unknown to right (right hepatic lobe)."),
    "P28": ("unsure", "", "No change: pancreatic tail lesion, 7.4 cm, as stated."),
    "P34": ("unsure", "What about brain?",
            "Kept the thyroid lesion as the only target. The brain metastases are spread of the thyroid "
            "cancer, with no size or location given, and not an incidental finding."),
    "P50": ("disagree", "Brain",
            "Kept as a negative, now with the reason stated: it is a brain lesion, but a cavernoma. The "
            "brain rules here cover meningioma only, so a reader should not raise a finding for it."),
}

# Label notes and described appearance added after the review
NOTES = {
    "P05": {"note": "Adrenal and lymph node involvement is spread of the kidney cancer; not scored as separate lesions."},
    "P06": {"note": "The 12 cm right nephrectomy-bed recurrence is known cancer, not an incidental lesion; not a target."},
    "P08": {"appearance": "hyperenhancing, central necrosis, calcification, mass effect"},
    "P10": {"appearance": "relatively homogeneous"},
    "P34": {"note": "Brain metastases are spread of the thyroid cancer; not scored as a separate lesion."},
    "P50": {"note": "Brain cavernoma: outside the meningioma-only brain rules, so it counts as a negative."},
}


def main():
    out = []
    for i, (pmcid, text, organ, side, size) in enumerate(SNIPPETS, 1):
        authors, title, journal, year, doi = SOURCES[pmcid]
        sid = f"P{i:02d}"
        gold = None if organ is None else {"organ": organ, "side": side, "size_cm": size}
        if gold is not None:
            gold.update(NOTES.get(sid, {}))
        out.append({
            "id": sid,
            "text": text,
            "gold": gold,
            **({"gold_note": NOTES[sid]["note"]} if gold is None and sid in NOTES else {}),
            "review": ({"verdict": REVIEW[sid][0], "comment": REVIEW[sid][1], "action": REVIEW[sid][2]}
                       if sid in REVIEW else {"verdict": "agree"}),
            "source": {"pmcid": pmcid, "doi": doi, "license": "CC BY", "authors": authors, "title": title,
                       "journal": journal, "year": year,
                       "url": f"https://europepmc.org/article/PMC/{pmcid}"},
        })
    (ROOT / "data" / "real_snippets.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(out)} snippets ({sum(x['gold'] is not None for x in out)} with a target lesion)")


if __name__ == "__main__":
    main()
