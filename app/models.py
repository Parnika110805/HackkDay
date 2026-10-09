import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str = Field(default="member")  # member | peer | dietitian | admin
    is_verified: bool = Field(default=False)  # True for dietitians approved by admin
    credential_note: Optional[str] = Field(default=None)  # e.g. "Registered Dietitian"
    reputation: int = Field(default=0)
    language: str = Field(default="en")
    avatar_color: str = Field(default="bg-purple-600")

    passport: Optional["Passport"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False})
    posts: List["Post"] = Relationship(back_populates="author")
    replies: List["Reply"] = Relationship(back_populates="author")


class Passport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    allergies_raw: str = Field(default="[]")  # JSON string e.g. ["peanuts", "dairy"]
    diet_type: str = Field(default="veg")  # veg | vegan | egg | non-veg | jain
    avoid_list_raw: str = Field(default="[]")  # JSON string
    goals_raw: str = Field(default="[]")  # JSON string e.g. ["high protein", "low sugar"]
    conditions_note: Optional[str] = Field(default=None)
    budget_note: Optional[str] = Field(default=None)
    language: str = Field(default="en")

    user: Optional[User] = Relationship(back_populates="passport")

    @property
    def allergies(self) -> List[str]:
        try:
            return json.loads(self.allergies_raw)
        except Exception:
            return []

    @allergies.setter
    def allergies(self, val: List[str]):
        self.allergies_raw = json.dumps(val)

    @property
    def avoid_list(self) -> List[str]:
        try:
            return json.loads(self.avoid_list_raw)
        except Exception:
            return []

    @avoid_list.setter
    def avoid_list(self, val: List[str]):
        self.avoid_list_raw = json.dumps(val)

    @property
    def goals(self) -> List[str]:
        try:
            return json.loads(self.goals_raw)
        except Exception:
            return []

    @goals.setter
    def goals(self, val: List[str]):
        self.goals_raw = json.dumps(val)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allergies": self.allergies,
            "diet_type": self.diet_type,
            "avoid_list": self.avoid_list,
            "goals": self.goals,
            "conditions_note": self.conditions_note,
            "budget_note": self.budget_note,
            "language": self.language
        }


class Community(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    kind: str = Field(default="general")  # hostel_mess | canteen | general
    description: str

    posts: List["Post"] = Relationship(back_populates="community")


class LabelProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name_guess: str
    barcode: Optional[str] = Field(default=None)
    label_json_raw: str = Field(default="{}")  # Extracted nutritional fields
    image_path: Optional[str] = Field(default=None)
    scanned_by: Optional[int] = Field(foreign_key="user.id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scan_count: int = Field(default=1)

    posts: List["Post"] = Relationship(back_populates="label_product")

    @property
    def label_data(self) -> Dict[str, Any]:
        try:
            return json.loads(self.label_json_raw)
        except Exception:
            return {}

    @label_data.setter
    def label_data(self, val: Dict[str, Any]):
        self.label_json_raw = json.dumps(val)


class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="user.id")
    image_path: Optional[str] = Field(default=None)
    image_kind: str = Field(default="meal")  # meal | label | both | none
    question_text: str
    voice_transcript: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    community_id: Optional[int] = Field(foreign_key="community.id", default=None)
    status: str = Field(default="open")  # open | answered | dietitian_approved
    analysis_json_raw: Optional[str] = Field(default=None)
    final_plan_json_raw: Optional[str] = Field(default=None)
    label_product_id: Optional[int] = Field(foreign_key="labelproduct.id", default=None)

    author: Optional[User] = Relationship(back_populates="posts")
    community: Optional[Community] = Relationship(back_populates="posts")
    label_product: Optional[LabelProduct] = Relationship(back_populates="posts")
    replies: List["Reply"] = Relationship(back_populates="post")

    @property
    def analysis(self) -> Optional[Dict[str, Any]]:
        if not self.analysis_json_raw:
            return None
        try:
            return json.loads(self.analysis_json_raw)
        except Exception:
            return None

    @analysis.setter
    def analysis(self, val: Optional[Dict[str, Any]]):
        self.analysis_json_raw = json.dumps(val) if val is not None else None

    @property
    def final_plan(self) -> Optional[Dict[str, Any]]:
        if not self.final_plan_json_raw:
            return None
        try:
            return json.loads(self.final_plan_json_raw)
        except Exception:
            return None

    @final_plan.setter
    def final_plan(self, val: Optional[Dict[str, Any]]):
        self.final_plan_json_raw = json.dumps(val) if val is not None else None


class Reply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id")
    author_id: Optional[int] = Field(foreign_key="user.id", default=None)  # None for AI
    author_type: str = Field(default="peer")  # ai | peer | dietitian
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audit_json_raw: Optional[str] = Field(default=None)
    audit_status: str = Field(default="unchecked")  # safe | caution | unsafe | unchecked
    helpful_votes: int = Field(default=0)

    author: Optional[User] = Relationship(back_populates="replies")
    post: Optional[Post] = Relationship(back_populates="replies")

    @property
    def audit(self) -> Optional[Dict[str, Any]]:
        if not self.audit_json_raw:
            return None
        try:
            return json.loads(self.audit_json_raw)
        except Exception:
            return None

    @audit.setter
    def audit(self, val: Optional[Dict[str, Any]]):
        self.audit_json_raw = json.dumps(val) if val is not None else None

