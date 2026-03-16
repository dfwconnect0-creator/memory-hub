"""TDD tests for Content Researcher CLI — no real HTTP or Gemini calls."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

# ── build_parser ──────────────────────────────────────────────────────────────


def test_parser_has_topic_flag() -> None:
    from agents.content_researcher.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["--topic", "AI trends"])
    assert args.topic == "AI trends"


def test_parser_has_recall_flag() -> None:
    from agents.content_researcher.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["--recall", "search query"])
    assert args.recall == "search query"


def test_parser_has_summarize_flag() -> None:
    from agents.content_researcher.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["--summarize", "AI topic"])
    assert args.summarize == "AI topic"


def test_parser_has_api_key_and_base_url() -> None:
    from agents.content_researcher.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["--api-key", "mykey", "--base-url", "http://hub:9000"])
    assert args.api_key == "mykey"
    assert args.base_url == "http://hub:9000"


# ── main --recall ─────────────────────────────────────────────────────────────


def test_main_recall_calls_agent_recall(capsys) -> None:
    from agents.content_researcher.cli import main

    mock_agent = MagicMock()
    mock_agent.recall.return_value = [{"content": "[TREND] AI is rising"}]

    with patch("agents.content_researcher.cli.ContentResearcherAgent", return_value=mock_agent):
        rc = main(["--recall", "AI trends"])

    assert rc == 0
    mock_agent.recall.assert_called_once_with("AI trends")
    captured = capsys.readouterr()
    assert "[TREND] AI is rising" in captured.out


def test_main_recall_prints_no_memories_when_empty(capsys) -> None:
    from agents.content_researcher.cli import main

    mock_agent = MagicMock()
    mock_agent.recall.return_value = []

    with patch("agents.content_researcher.cli.ContentResearcherAgent", return_value=mock_agent):
        rc = main(["--recall", "obscure topic"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "No memories" in captured.out


# ── main --topic ──────────────────────────────────────────────────────────────


def test_main_topic_calls_agent_research(capsys) -> None:
    from agents.content_researcher.cli import main

    mock_agent = MagicMock()
    mock_agent.research.return_value = [
        "[TREND] AI content tools are growing",
        "[INSIGHT] Automation reduces creation time",
    ]

    with patch("agents.content_researcher.cli.ContentResearcherAgent", return_value=mock_agent):
        rc = main(["--topic", "AI writing tools"])

    assert rc == 0
    mock_agent.research.assert_called_once_with("AI writing tools")
    captured = capsys.readouterr()
    assert "[TREND]" in captured.out


# ── main --summarize ──────────────────────────────────────────────────────────


def test_main_summarize_calls_agent_summarize(capsys) -> None:
    from agents.content_researcher.cli import main

    mock_agent = MagicMock()
    mock_agent.summarize.return_value = "AI is transforming content creation rapidly."

    with patch("agents.content_researcher.cli.ContentResearcherAgent", return_value=mock_agent):
        rc = main(["--summarize", "AI trends"])

    assert rc == 0
    mock_agent.summarize.assert_called_once_with("AI trends")
    captured = capsys.readouterr()
    assert "transforming content creation" in captured.out


# ── main no flags → REPL ─────────────────────────────────────────────────────


def test_main_no_flags_calls_run_repl() -> None:
    from agents.content_researcher.cli import main

    mock_agent = MagicMock()

    with (
        patch("agents.content_researcher.cli.ContentResearcherAgent", return_value=mock_agent),
        patch("agents.content_researcher.cli.run_repl") as mock_repl,
    ):
        rc = main([])

    assert rc == 0
    mock_repl.assert_called_once_with(mock_agent)


# ── run_repl dispatch ─────────────────────────────────────────────────────────


def test_repl_research_command_dispatches_to_agent(capsys) -> None:
    from agents.content_researcher.cli import run_repl

    mock_agent = MagicMock()
    mock_agent.research.return_value = ["[TREND] AI is fast"]

    inputs = iter(["/research quantum computing", "quit"])
    with patch("builtins.input", side_effect=inputs):
        run_repl(mock_agent)

    mock_agent.research.assert_called_once_with("quantum computing")


def test_repl_recall_command_dispatches_to_agent(capsys) -> None:
    from agents.content_researcher.cli import run_repl

    mock_agent = MagicMock()
    mock_agent.recall.return_value = [{"content": "[TREND] LLMs dominate"}]

    inputs = iter(["/recall AI", "quit"])
    with patch("builtins.input", side_effect=inputs):
        run_repl(mock_agent)

    mock_agent.recall.assert_called_once_with("AI")


def test_repl_plain_input_calls_chat(capsys) -> None:
    from agents.content_researcher.cli import run_repl

    mock_agent = MagicMock()
    mock_agent.chat.return_value = "Here is some content research advice."

    inputs = iter(["tell me about AI", "quit"])
    with patch("builtins.input", side_effect=inputs):
        run_repl(mock_agent)

    mock_agent.chat.assert_called_once_with("tell me about AI")
    captured = capsys.readouterr()
    assert "content research advice" in captured.out


# ── agent.chat ────────────────────────────────────────────────────────────────


def test_agent_chat_searches_memory_and_calls_gemini() -> None:
    from agents.content_researcher.agent import ContentResearcherAgent

    mock_resp = MagicMock()
    mock_resp.text = "Great question about content research!"
    mock_genai = MagicMock()
    mock_genai.models.generate_content.return_value = mock_resp

    with patch("agents.content_researcher.agent.genai.Client", return_value=mock_genai):
        agent = ContentResearcherAgent(api_key="test-key")

    from unittest.mock import patch as _patch

    with _patch("httpx.Client") as mock_http_cls:
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value.json.return_value = {"results": []}
        mock_http.post.return_value.raise_for_status = MagicMock()
        mock_http_cls.return_value = mock_http

        reply = agent.chat("What are the best content research strategies?")

    assert isinstance(reply, str)
    assert len(reply) > 0
    mock_genai.models.generate_content.assert_called_once()


def test_agent_chat_returns_fallback_on_gemini_error() -> None:
    from agents.content_researcher.agent import ContentResearcherAgent

    mock_genai = MagicMock()
    mock_genai.models.generate_content.side_effect = RuntimeError("API down")

    with patch("agents.content_researcher.agent.genai.Client", return_value=mock_genai):
        agent = ContentResearcherAgent(api_key="test-key")

    with patch("httpx.Client") as mock_http_cls:
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value.json.return_value = {"results": []}
        mock_http.post.return_value.raise_for_status = MagicMock()
        mock_http_cls.return_value = mock_http

        reply = agent.chat("Hello?")

    assert isinstance(reply, str)
    assert len(reply) > 0
