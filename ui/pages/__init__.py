"""
UI Pages Module - REFACTORED

Bu module barcha sahifalarni export qiladi.
Har bir sahifa UI komponentlarni ishlatadi.
"""

from .tz_pr_checker import render_tz_pr_checker
from .testcase_generator import render_testcase_generator

__all__ = [
    'render_tz_pr_checker',
    'render_testcase_generator',
]