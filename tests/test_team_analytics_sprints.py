from datetime import timedelta

import pytest

from services.team_analytics_sprints import clip_interval, sprint_window
from tests.test_team_analytics import BASE

pytestmark = pytest.mark.no_db


def test_closed_sprint_uses_actual_completion_not_planned_end():
    assert sprint_window(
        {"state": "closed", "started_at": BASE.isoformat(), "ends_at": (BASE + timedelta(hours=2)).isoformat(),
         "completed_at": (BASE + timedelta(hours=4)).isoformat()}, BASE + timedelta(hours=8)
    ) == (BASE, BASE + timedelta(hours=4))


def test_active_sprint_continues_after_planned_end():
    assert sprint_window(
        {"state": "active", "started_at": BASE.isoformat(), "ends_at": (BASE + timedelta(hours=2)).isoformat(),
         "completed_at": (BASE + timedelta(hours=1)).isoformat()},
        BASE + timedelta(hours=3)
    ) == (BASE, BASE + timedelta(hours=3))


@pytest.mark.parametrize("sprint", [
    {"state": "closed", "started_at": BASE.isoformat()},
    {"state": "active"},
    {"state": "future", "started_at": BASE.isoformat()},
    {"state": "closed", "started_at": "broken", "ends_at": BASE.isoformat()},
])
def test_missing_dates_do_not_fall_back_to_task_lifetime(sprint):
    with pytest.raises(ValueError):
        sprint_window(sprint, BASE + timedelta(hours=8))


def test_interval_straddling_sprint_is_clipped_at_both_boundaries():
    window = (BASE + timedelta(hours=1), BASE + timedelta(hours=3))
    assert clip_interval(BASE, BASE + timedelta(hours=4), window) == window
    assert clip_interval(BASE, BASE + timedelta(hours=1), window) is None
