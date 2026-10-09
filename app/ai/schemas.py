from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class Observation(BaseModel):
    text: str
    evidence: Literal["seen_on_plate", "printed_on_label", "not_visible"]
    quote: Optional[str] = None
    box: Optional[List[int]] = None  # [ymin, xmin, ymax, xmax] normalized 0-1000

class Conflict(BaseModel):
    item: str
    reason: str
    severity: Literal["high", "medium", "low"] = "medium"
    evidence_quote: Optional[str] = None

class NutrientBreakdown(BaseModel):
    energy_kcal: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    fat_g: Optional[float] = None
    protein_g: Optional[float] = None

class LabelData(BaseModel):
    product_name: Optional[str] = None
    serving_size_g: Optional[float] = None
    servings_per_pack: Optional[float] = None
    per_100g: Optional[NutrientBreakdown] = Field(default_factory=NutrientBreakdown)
    per_serving: Optional[NutrientBreakdown] = Field(default_factory=NutrientBreakdown)
    ingredients: List[str] = []
    allergen_statement: Optional[str] = None

class AnalysisOut(BaseModel):
    image_kind_detected: Literal["meal", "label", "both", "unclear"] = "unclear"
    verdict: Literal["good_fit", "okay_with_changes", "not_recommended", "cannot_tell"] = "cannot_tell"
    summary: str
    observations: List[Observation] = []
    possible_conflicts: List[Conflict] = []
    label_data: Optional[LabelData] = Field(default_factory=LabelData)
    swap_suggestions: List[str] = []
    needs_dietitian: bool = False
    unreadable_regions: List[str] = []
    follow_up_questions: List[str] = []
    disclaimer_shown: bool = True

class AuditFinding(BaseModel):
    phrase: str
    conflicts_with: str
    reason: str
    severity: Literal["high", "medium", "low"] = "medium"

class AuditOut(BaseModel):
    status: Literal["safe", "caution", "unsafe"] = "safe"
    findings: List[AuditFinding] = []
    safer_alternative: Optional[str] = None
    user_message: str

class FinalPlanBullet(BaseModel):
    text: str
    source: Literal["ai", "peer", "dietitian"]

class FinalPlanOut(BaseModel):
    bullets: List[FinalPlanBullet] = []
    check_line: str
    language: str = "en"
