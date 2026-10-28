from app.core.errors import DomainError

CAPABILITIES = [
    "task_matching",
    "exposure_scoring",
    "scenario_intelligence",
    "skill_recommendations",
    "plan_generation",
]


class UnimplementedProvider:
    capability = "unknown"
    available = False

    def require(self):
        raise DomainError(
            "capability_unavailable",
            f"{self.capability.replace('_', ' ').capitalize()} has not been implemented.",
            501,
            {"missing_capabilities": [self.capability]},
        )


class PlaceholderTaskMatcher(UnimplementedProvider):
    capability = "task_matching"


class PlaceholderExposureScorer(UnimplementedProvider):
    capability = "exposure_scoring"


class PlaceholderScenarioEngine(UnimplementedProvider):
    capability = "scenario_intelligence"


class PlaceholderSkillRecommender(UnimplementedProvider):
    capability = "skill_recommendations"


class PlaceholderPlanGenerator(UnimplementedProvider):
    capability = "plan_generation"


class EngineRegistry:
    """Replace a placeholder in one place when its real provider is implemented."""

    def __init__(self):
        self.task_matcher = PlaceholderTaskMatcher()
        self.exposure_scorer = PlaceholderExposureScorer()
        self.scenario_engine = PlaceholderScenarioEngine()
        self.skill_recommender = PlaceholderSkillRecommender()
        self.plan_generator = PlaceholderPlanGenerator()

    def missing_capabilities(self) -> list[str]:
        providers = {
            "task_matching": self.task_matcher,
            "exposure_scoring": self.exposure_scorer,
            "scenario_intelligence": self.scenario_engine,
            "skill_recommendations": self.skill_recommender,
            "plan_generation": self.plan_generator,
        }
        return [
            name
            for name, provider in providers.items()
            if not getattr(provider, "available", False)
        ]

    def capability_status(self) -> dict[str, str]:
        return {
            name: ("available" if name not in self.missing_capabilities() else "unavailable")
            for name in CAPABILITIES
        }
