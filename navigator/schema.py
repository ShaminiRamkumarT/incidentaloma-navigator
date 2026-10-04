"""Shared data model for incidental renal and adrenal findings."""
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Action(str, Enum):
    NO_FOLLOWUP = "NO_FOLLOWUP"
    IMAGING_SURVEILLANCE = "IMAGING_SURVEILLANCE"          # interval follow-up imaging
    CHARACTERIZATION_IMAGING = "CHARACTERIZATION_IMAGING"  # dedicated renal/adrenal protocol CT or MRI
    SPECIALIST_REFERRAL = "SPECIALIST_REFERRAL"            # urology / endocrine surgery / MDT
    HORMONAL_WORKUP = "HORMONAL_WORKUP"                    # 1 mg DST +/- metanephrines, aldosterone/renin


ACTION_LABELS = {
    Action.NO_FOLLOWUP: "No follow-up",
    Action.IMAGING_SURVEILLANCE: "Interval imaging surveillance",
    Action.CHARACTERIZATION_IMAGING: "Dedicated characterization imaging",
    Action.SPECIALIST_REFERRAL: "Specialist referral",
    Action.HORMONAL_WORKUP: "Hormonal work-up",
}


class Finding(BaseModel):
    """One incidental renal or adrenal lesion as described in a CT report."""

    organ: Literal["kidney", "adrenal"]
    side: Literal["left", "right", "unknown"] = "unknown"
    size_cm: Optional[float] = Field(None, description="Largest dimension in cm")
    composition: Literal["cystic", "solid", "indeterminate"] = Field(
        "indeterminate", description="cystic if described as cyst/cystic, solid if described as solid, else indeterminate"
    )
    unenhanced_hu: Optional[float] = Field(None, description="Attenuation on non-contrast CT")
    enhanced_hu: Optional[float] = Field(None, description="Attenuation on a post-contrast (e.g. portal venous/nephrographic) phase")
    homogeneous: Optional[bool] = None
    wall_mm: Optional[float] = Field(None, description="Cyst wall thickness in mm")
    septa_count: Optional[int] = Field(None, description="Number of septa; 4 if 'many/multiple' without a number")
    septa_mm: Optional[float] = Field(None, description="Thickest septum in mm")
    irregular_wall_or_septa: bool = False
    enhancing_nodule: bool = Field(False, description="Enhancing mural/soft-tissue nodule within a renal cystic lesion")
    macroscopic_fat: bool = False
    too_small_to_characterize: bool = False
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
