"""Centralized setup checks for UI and webhook module execution."""
from core.setup_checks.engine import SetupCheckResult, SetupContext, run_setup_checks
from core.setup_checks.profiles import CHECK_PROFILES, profile_from_module_policy

__all__ = [
    "CHECK_PROFILES",
    "SetupCheckResult",
    "SetupContext",
    "profile_from_module_policy",
    "run_setup_checks",
]
