import pytest

from app.core.errors import DomainError
from app.engines.placeholders import (
    PlaceholderExposureScorer,
    PlaceholderPlanGenerator,
    PlaceholderScenarioEngine,
    PlaceholderSkillRecommender,
    PlaceholderTaskMatcher,
)


@pytest.mark.parametrize(
    "provider,capability",
    [
        (PlaceholderTaskMatcher(), "task_matching"),
        (PlaceholderExposureScorer(), "exposure_scoring"),
        (PlaceholderScenarioEngine(), "scenario_intelligence"),
        (PlaceholderSkillRecommender(), "skill_recommendations"),
        (PlaceholderPlanGenerator(), "plan_generation"),
    ],
)
def test_placeholder_providers_fail_honestly(provider, capability):
    with pytest.raises(DomainError) as error:
        provider.require()
    assert error.value.status_code == 501
    assert error.value.details == {"missing_capabilities": [capability]}
