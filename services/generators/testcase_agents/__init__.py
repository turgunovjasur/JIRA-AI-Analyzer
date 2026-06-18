"""Testcase generator agentlari.

Agent1 (talab ajratish) checker modulidan qayta ishlatiladi
(`services.checkers.tzpr_agents.agent1`) — bu yerda faqat testcase-ga xos
Agent2 (testcase yozuvchi) kontrakti turadi.
"""

from services.generators.testcase_agents import agent2_testcase, agent3_testcase_auditor

__all__ = ["agent2_testcase", "agent3_testcase_auditor"]
