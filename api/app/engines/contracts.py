from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class TaskMatch(BaseModel):
    task_id: str
    reference_task_id: str
    similarity: float = Field(ge=0, le=1)
    source: str
    release: str
    source_url: HttpUrl | None = None


class TaskEvidence(BaseModel):
    task_id: str
    category: Literal[
        "automatable", "ai_accelerated", "human_critical", "emerging_value", "unresolved"
    ]
    explanation: str
    automation_indicator: float = Field(ge=0, le=1)
    acceleration_indicator: float = Field(ge=0, le=1)
    matched_references: list[TaskMatch]
    raw_signals: list[str]
    transformed_signals: list[str]
    contributions: list[str]
    missing_evidence: list[str]
    uncertainty_reasons: list[str]
    scoring_version: str


class ScenarioResult(BaseModel):
    original_hours: float = Field(ge=0)
    freed_hours: float = Field(ge=0)
    remaining_hours: float = Field(ge=0)
    unresolved_hours: float = Field(ge=0)
    version: str


class SkillSuggestion(BaseModel):
    title: str
    explanation: str
    task_ids: list[str]
    evidence_ids: list[str]


class PlannedAction(BaseModel):
    title: str
    explanation: str
    weekly_hours: float = Field(ge=0)
    task_ids: list[str]
    evidence_ids: list[str]


class PlanResult(BaseModel):
    learning_hours_per_week: float = Field(gt=0)
    phases: dict[Literal["30_days", "60_days", "90_days"], list[PlannedAction]]
    version: str
