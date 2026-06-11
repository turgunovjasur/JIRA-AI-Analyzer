from __future__ import annotations

from typing import Any

from services.checkers.tz_pr_checker import TZPRService


class TZPRMultiAgentService(TZPRService):
    """Service boundary used by the run-based multi-agent checker.

    For now this class keeps the proven context/result helper behavior from the
    legacy TZPR service, but it explicitly blocks the legacy single-prompt
    analysis entrypoint. The remaining shared helpers can be moved here in
    smaller follow-up patches while webhook continues using TZPRService.
    """

    def analyze_task(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "TZPRMultiAgentService does not support legacy analyze_task(); "
            "use create_multi_agent_run/execute_multi_agent_run instead."
        )
