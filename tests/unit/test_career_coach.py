"""Unit tests for the Career Coach agent (Phase 4)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _mock_add_tool(memory_id: str = "m1"):
    mock = MagicMock()
    mock._run.return_value = json.dumps({"memory_id": memory_id, "status": "ok"})
    return mock


def _mock_search_tool(results: list | None = None):
    mock = MagicMock()
    mock._run.return_value = json.dumps({
        "results": results or [],
        "total": len(results or []),
        "query": "test",
        "project": "personal",
    })
    return mock


# ── CareerCoachAgent construction ────────────────────────────────────────────

def test_agent_imports():
    from agents.career_coach.agent import CareerCoachAgent
    assert CareerCoachAgent is not None


def test_agent_instantiates():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="test-key")
    assert agent.memory_add is not None
    assert agent.memory_search is not None


def test_agent_has_system_prompt():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="test-key")
    assert "career" in agent.system_prompt.lower()


def test_agent_uses_personal_project():
    from agents.career_coach.agent import PROJECT
    assert PROJECT == "personal"


def test_agent_id_is_career_coach():
    from agents.career_coach.agent import AGENT_ID
    assert AGENT_ID == "career_coach_agent"


# ── remember() ───────────────────────────────────────────────────────────────

def test_remember_calls_memory_add():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_add = _mock_add_tool("mem-123")
    result = agent.remember("I want to become a senior engineer")
    agent.memory_add._run.assert_called_once()
    assert result["memory_id"] == "mem-123"


def test_remember_stores_category():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_add = _mock_add_tool()
    agent.remember("Python skills", category="career")
    call_arg = agent.memory_add._run.call_args.args[0]
    payload = json.loads(call_arg)
    assert payload["category"] == "career"


def test_remember_content_in_payload():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_add = _mock_add_tool()
    agent.remember("5 years of Python experience")
    call_arg = agent.memory_add._run.call_args.args[0]
    payload = json.loads(call_arg)
    assert "Python" in payload["content"]


# ── recall() ─────────────────────────────────────────────────────────────────

def test_recall_calls_memory_search():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool([{"content": "Senior engineer goal"}])
    results = agent.recall("career goals")
    agent.memory_search._run.assert_called_once()
    assert len(results) == 1


def test_recall_returns_list():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool()
    results = agent.recall("anything")
    assert isinstance(results, list)


def test_recall_passes_query():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool()
    agent.recall("interview tips", limit=3)
    call_arg = agent.memory_search._run.call_args.args[0]
    payload = json.loads(call_arg)
    assert payload["query"] == "interview tips"
    assert payload["limit"] == 3


def test_recall_empty_returns_empty_list():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool([])
    assert agent.recall("nothing") == []


# ── chat() ───────────────────────────────────────────────────────────────────

def test_chat_returns_string():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool()
    result = agent.chat("How do I get promoted?")
    assert isinstance(result, str)


def test_chat_includes_user_input_in_response():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool()
    result = agent.chat("salary negotiation")
    assert "salary negotiation" in result.lower()


def test_chat_uses_memory_context():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool([{"content": "User targets FAANG companies"}])
    result = agent.chat("Where should I apply?")
    assert "FAANG" in result


def test_chat_no_memory_still_responds():
    from agents.career_coach.agent import CareerCoachAgent
    agent = CareerCoachAgent(api_key="key")
    agent.memory_search = _mock_search_tool([])
    result = agent.chat("I need career advice")
    assert len(result) > 0


# ── CLI ──────────────────────────────────────────────────────────────────────

def test_cli_imports():
    from agents.career_coach.cli import build_parser, main
    assert callable(main)
    assert callable(build_parser)


def test_cli_parser_has_api_key_arg():
    from agents.career_coach.cli import build_parser
    p = build_parser()
    args = p.parse_args(["--api-key", "test-key"])
    assert args.api_key == "test-key"


def test_cli_parser_has_remember_arg():
    from agents.career_coach.cli import build_parser
    p = build_parser()
    args = p.parse_args(["--remember", "I have 5 years experience"])
    assert args.remember == "I have 5 years experience"


def test_cli_parser_has_recall_arg():
    from agents.career_coach.cli import build_parser
    p = build_parser()
    args = p.parse_args(["--recall", "interview prep"])
    assert args.recall == "interview prep"


def test_cli_remember_exits_zero():
    from agents.career_coach.cli import main
    with patch("agents.career_coach.cli.CareerCoachAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        mock_instance.remember.return_value = {"memory_id": "m1", "status": "ok"}
        result = main(["--api-key", "key", "--remember", "Python skills"])
    assert result == 0


def test_cli_recall_exits_zero():
    from agents.career_coach.cli import main
    with patch("agents.career_coach.cli.CareerCoachAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        mock_instance.recall.return_value = [{"content": "Python skills"}]
        result = main(["--api-key", "key", "--recall", "skills"])
    assert result == 0


def test_cli_recall_no_results():
    from agents.career_coach.cli import main
    with patch("agents.career_coach.cli.CareerCoachAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        mock_instance.recall.return_value = []
        result = main(["--api-key", "key", "--recall", "nothing"])
    assert result == 0
