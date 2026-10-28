import pytest
from pydantic import ValidationError

from app.tasks.schemas import TaskCollection, TaskInput


def test_task_contract_preserves_unknowns_and_normalizes_lists():
    task = TaskInput(
        task_description="  Schedule service visits ",
        hours_per_week=2.5,
        tools_used=[" calendar ", ""],
        skills_used=None,
        involves_people=None,
        physical_presence_required=False,
    )
    assert task.task_description == "Schedule service visits"
    assert task.tools_used == ["calendar"] and task.skills_used is None
    assert task.involves_people is None and task.physical_presence_required is False


def test_task_contract_rejects_invalid_values_and_week_total():
    for hours in (0, -1, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            TaskInput(task_description="Work", hours_per_week=hours)
    with pytest.raises(ValidationError):
        TaskInput(task_description=" \n", hours_per_week=1)
    with pytest.raises(ValidationError):
        TaskInput(task_description="Work", hours_per_week=1, frequency="yearly")
    with pytest.raises(ValidationError):
        TaskInput(task_description="Work", hours_per_week=1, decision_authority=6)
    first = TaskInput(task_description="One", hours_per_week=100)
    second = TaskInput(task_description="Two", hours_per_week=69)
    with pytest.raises(ValidationError):
        TaskCollection(tasks=[first, second])


def test_no_hours_are_defaulted_when_unknown():
    with pytest.raises(ValidationError):
        TaskInput(task_description="Work")
