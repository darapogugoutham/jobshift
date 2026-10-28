from dataclasses import dataclass
from typing import Protocol

from app.engines.contracts import (
    PlanResult,
    ScenarioResult,
    SkillSuggestion,
    TaskEvidence,
    TaskMatch,
)


@dataclass
class EngineContext:
    session_id: str
    input_revision: int
    tasks: list[dict]


class TaskMatcher(Protocol):
    """Match each task to released reference tasks; similarity must be in [0,1]."""

    def match(self, context: EngineContext) -> list[TaskMatch]: ...


class ExposureScorer(Protocol):
    """Return evidence-linked task categories and indicators validated by TaskEvidence."""

    def score(self, context: EngineContext, matches: list[TaskMatch]) -> list[TaskEvidence]: ...


class ScenarioEngine(Protocol):
    """Calculate a versioned scenario from a validated input snapshot and assumptions."""

    def calculate(
        self, context: EngineContext, evidence: list[TaskEvidence], adoption: str, horizon: int
    ) -> ScenarioResult: ...


class SkillRecommender(Protocol):
    """Return skill suggestions with valid task and evidence references."""

    def recommend(
        self, context: EngineContext, evidence: list[TaskEvidence]
    ) -> list[SkillSuggestion]: ...


class PlanGenerator(Protocol):
    """Return a budget-valid plan whose actions reference actual task and evidence IDs."""

    def generate(
        self,
        context: EngineContext,
        evidence: list[TaskEvidence],
        skills: list[SkillSuggestion],
        learning_hours: float,
    ) -> PlanResult: ...
