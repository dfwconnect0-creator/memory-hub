"""Smoke tests: verify content_researcher modules import cleanly."""
from __future__ import annotations


def test_agent_module_imports() -> None:
    from agents.content_researcher import agent

    assert hasattr(agent, "ContentResearcherAgent")


def test_cli_module_imports() -> None:
    from agents.content_researcher import cli

    assert hasattr(cli, "ContentResearcherAgent")
