from typing import Literal

from pydantic import BaseModel, model_validator

ImportField = Literal[
    "task_description",
    "hours_per_week",
    "frequency",
    "tools_used",
    "skills_used",
    "involves_people",
    "physical_presence_required",
    "decision_authority",
    "notes",
]


class ImportMappingUpdate(BaseModel):
    sheet_name: str | None = None
    mapping: dict[ImportField, int] | None = None

    @model_validator(mode="after")
    def unique_columns(self):
        if self.mapping is not None and len(set(self.mapping.values())) != len(self.mapping):
            raise ValueError("A column can map to only one task field")
        return self


class ImportConfirmation(BaseModel):
    mode: Literal["append", "replace"]
