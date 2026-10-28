import math
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Frequency = Literal["daily", "weekly", "monthly", "occasional"]


class TaskInput(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_description: str
    hours_per_week: float
    frequency: Frequency | None = None
    tools_used: list[str] | None = None
    skills_used: list[str] | None = None
    involves_people: bool | None = None
    physical_presence_required: bool | None = None
    decision_authority: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None

    @field_validator("task_description")
    @classmethod
    def description_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task description must contain non-whitespace text")
        return value

    @field_validator("hours_per_week")
    @classmethod
    def finite_positive_hours(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Weekly hours must be a positive finite number")
        return value

    @field_validator("tools_used", "skills_used")
    @classmethod
    def clean_lists(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        cleaned = [value.strip() for value in values if value.strip()]
        return cleaned or None

    @field_validator("notes")
    @classmethod
    def blank_notes_are_unknown(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class TaskRead(TaskInput):
    model_config = ConfigDict(from_attributes=True)


class TaskCollection(BaseModel):
    tasks: list[TaskInput] = Field(max_length=60)

    @model_validator(mode="after")
    def total_within_week(self):
        if sum(task.hours_per_week for task in self.tasks) > 168:
            raise ValueError("Total weekly hours cannot exceed 168")
        if len({task.id for task in self.tasks}) != len(self.tasks):
            raise ValueError("Task IDs must be unique")
        return self


class TaskList(BaseModel):
    tasks: list[TaskRead]
    input_revision: int
    total_hours: float


class TaskMutation(BaseModel):
    task: TaskRead
    input_revision: int
    total_hours: float
