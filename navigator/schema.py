"""Shared data model for incidental findings (kidney, adrenal, lung, liver, pancreas,
thyroid, pituitary, brain and bone) on CT, MRI and PET-CT.."""
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Action(str, Enum):
    NO_FOLLOWUP = "NO_FOLLOWUP"
    IMAGING_SURVEILLANCE = "IMAGING_SURVEILLANCE"          # interval follow-up imaging
    CHARACTERIZATION_IMAGING = "CHARACTERIZATION_IMAGING"  # dedicated protocol CT/MRI, PET-CT
    SPECIALIST_REFERRAL = "SPECIALIST_REFERRAL"            # urology / endocrine surgery / pulmonology / MDT, incl. biopsy
    HORMONAL_WORKUP = "HORMONAL_WORKUP"                    # 1 mg DST +/- metanephrines, aldosterone/renin


ACTION_LABELS = {
    Action.NO_FOLLOWUP: "No follow-up",
    Action.IMAGING_SURVEILLANCE: "Interval imaging surveillance",
    Action.CHARACTERIZATION_IMAGING: "Dedicated characterization imaging",
    Action.SPECIALIST_REFERRAL: "Specialist referral",
    Action.HORMONAL_WORKUP: "Hormonal work-up",
}


class Finding(BaseModel):
    """One incidental lesion as described in an imaging report."""

    organ: Literal["kidney", "adrenal", "lung", "liver", "pancreas", "thyroid", "pituitary", "brain", "bone"] = Field(
        ..., description="brain = extra-axial lesion suspected to be a meningioma")
    modality: Literal["CT", "MRI", "PET-CT", "unknown"] = Field("CT", description="Modality of the study the finding was reported on")
    side: Literal["left", "right", "unknown"] = "unknown"
    size_cm: Optional[float] = Field(None, description="Largest dimension in cm")
    short_axis_cm: Optional[float] = Field(None, description="Perpendicular short-axis dimension in cm, if given")
    composition: Literal["cystic", "solid", "indeterminate"] = Field(
        "indeterminate", description="cystic if described as cyst/cystic, solid if described as solid, else indeterminate"
    )
    unenhanced_hu: Optional[float] = Field(None, description="Attenuation on non-contrast CT")
    enhanced_hu: Optional[float] = Field(None, description="Attenuation on a post-contrast (e.g. portal venous/nephrographic) phase")
    homogeneous: Optional[bool] = None
    wall_mm: Optional[float] = Field(None, description="Cyst wall thickness in mm")
    septa_count: Optional[int] = Field(None, description="Number of septa; 4 if 'many/multiple' without a number")
    septa_mm: Optional[float] = Field(None, description="Thickest septum in mm")
    irregular_wall_or_septa: bool = Field(False, description="Thick/irregular wall or septa (kidney); thickened or enhancing cyst wall (pancreas)")
    enhancing_nodule: bool = Field(False, description="Enhancing mural/soft-tissue nodule within a renal cystic lesion")
    macroscopic_fat: bool = False
    too_small_to_characterize: bool = False
    # --- lung (Fleischner 2017) ---
    nodule_type: Optional[Literal["solid", "ground-glass", "part-solid"]] = Field(
        None, description="Lung nodule attenuation; ground-glass and part-solid are both 'subsolid'")
    solid_component_mm: Optional[float] = Field(None, description="Size of the solid part of a part-solid nodule, in mm")
    multiple: bool = Field(False, description="True if the report describes multiple nodules of this kind")
    patient_risk: Literal["low", "high", "unknown"] = Field(
        "unknown", description="Risk as stated in the report: lung = e.g. heavy smoker; liver = known cancer, cirrhosis "
                               "or liver risk factor (hepatitis, NASH, alcohol...); bone = known cancer that spreads to "
                               "bone; unknown if not stated")
    patient_age: Optional[int] = Field(None, description="Age in years if the report states it")
    # --- liver (ACR 2017) ---
    appearance: Optional[Literal["benign", "suspicious", "flash-filling", "indeterminate"]] = Field(
        None, description="Liver (ACR): benign = sharp, homogeneous <=20 HU, or typical haemangioma/FNH/focal fat; "
                          "suspicious = ill-defined, heterogeneous, wall nodularity, thick septa, >20 HU; flash-filling = "
                          "uniform arterial hyperenhancement only. Thyroid: suspicious = local invasion or abnormal lymph "
                          "nodes. Bone (Bone-RADS): benign = macroscopic fat or a classic benign lesion; suspicious = pain, "
                          "cortical involvement, soft-tissue extension, pathologic fracture or aggressive periosteal "
                          "reaction. indeterminate = cannot tell")
    fdg_avid: Optional[bool] = Field(None, description="PET-CT: uptake above background (normal liver for liver lesions)")
    # --- pancreas (ACR 2017) ---
    duct_mm: Optional[float] = Field(None, description="Main pancreatic duct calibre in mm")
    mural_nodule: bool = Field(False, description="Non-enhancing mural nodule in a pancreatic cyst")
    # --- thyroid (ACR 2015) ---
    limited_life_expectancy: bool = Field(False, description="Report states limited life expectancy or serious comorbidity")
    # --- pituitary (Endocrine Society 2011) / brain (EANO 2021) ---
    chiasm_contact: bool = Field(False, description="Pituitary lesion abuts or compresses the optic chiasm/nerves")
    growth: bool = Field(False, description="Report says the lesion has grown since a prior study")
    symptomatic: bool = Field(False, description="Report links symptoms to the lesion (e.g. seizures, deficit, mass effect)")
    # --- bone (Bone-RADS 2022) ---
    bone_density: Optional[Literal["lucent", "sclerotic", "mixed"]] = None
    stated_actions: List[Action] = Field(
        default_factory=list,
        description="Follow-up actions the radiologist recommended for THIS lesion; NO_FOLLOWUP only if explicitly stated; empty if nothing stated",
    )
    reported_category: Optional[str] = Field(None, description="Category named in the report, e.g. 'Bosniak IIF'")

    @property
    def enhancement_hu(self) -> Optional[float]:
        if self.unenhanced_hu is None or self.enhanced_hu is None:
            return None
        return self.enhanced_hu - self.unenhanced_hu


class ReportExtraction(BaseModel):
    findings: List[Finding]
