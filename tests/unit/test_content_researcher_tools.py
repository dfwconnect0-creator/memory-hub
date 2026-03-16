"""TDD tests for ContentResearcherAgent tools — no real HTTP or Gemini calls."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.content_researcher.agent import ContentResearcherAgent

# ── Shared fixtures ───────────────────────────────────────────────────────────

FAKE_ADD_RESPONSE = {"id": "mem-001", "status": "stored"}
FAKE_SEARCH_RESPONSE = {
    "results": [
        {"content": "[TREND] AI is growing fast", "category": "trend"},
        {"content": "[INSIGHT] Gemini surpasses GPT-4", "category": "insight"},
    ]
}
FAKE_GEMINI_RESEARCH = (
    "[TREND] AI content generation is accelerating\n"
    "[INSIGHT] Multimodal models outperform text-only models\n"
    "[SOURCE] https://example.com — AI Weekly Report"
)
FAKE_GEMINI_SUMMARY = (
    "AI is rapidly transforming content creation through multimodal models "
    "and automated generation pipelines."
)


def _make_http_mock(response_json: dict) -> MagicMock:
    """Return a context-manager mock for httpx.Client returning the given JSON."""
    resp = MagicMock()
    resp.json.return_value = response_json
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.post.return_value = resp
    return client


def _make_agent(gemini_text: str | None = None) -> ContentResearcherAgent:
    """Build agent with a mocked genai.Client (no real API key needed)."""
    resp = MagicMock()
    resp.text = gemini_text or ""
    mock_genai = MagicMock()
    mock_genai.models.generate_content.return_value = resp
    with patch("agents.content_researcher.agent.genai.Client", return_value=mock_genai):
        agent = ContentResearcherAgent(api_key="test-key", base_url="http://localhost:8000")
    return agent


# ── store_finding ─────────────────────────────────────────────────────────────


class TestStoreFinding:
    def test_posts_to_memory_endpoint(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.store_finding("AI tools are rising")
        http.post.assert_called_once()
        url: str = http.post.call_args[0][0]
        assert url.endswith("/api/v1/memory")

    def test_includes_correct_project_and_agent_id(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.store_finding("some finding")
        body = http.post.call_args[1]["json"]
        assert body["project"] == "content-creation"
        assert body["agent_id"] == "research_agent"

    def test_prepends_trend_tag_when_no_bracket(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.store_finding("AI tools are booming")
        body = http.post.call_args[1]["json"]
        assert body["content"].startswith("[TREND]")

    def test_does_not_double_tag_already_tagged_content(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.store_finding("[INSIGHT] LLMs are multimodal")
        body = http.post.call_args[1]["json"]
        assert body["content"].startswith("[INSIGHT]")
        assert "[[" not in body["content"]

    def test_custom_category_is_forwarded(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.store_finding("some insight", category="insight")
        body = http.post.call_args[1]["json"]
        assert body["category"] == "insight"

    def test_returns_dict_from_response(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            result = agent.store_finding("a finding")
        assert isinstance(result, dict)
        assert result.get("status") == "stored"


# ── recall ────────────────────────────────────────────────────────────────────


class TestRecall:
    def test_posts_to_search_endpoint(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_SEARCH_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.recall("AI trends")
        url: str = http.post.call_args[0][0]
        assert url.endswith("/api/v1/memory/search")

    def test_includes_correct_project(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_SEARCH_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.recall("AI trends")
        body = http.post.call_args[1]["json"]
        assert body["project"] == "content-creation"

    def test_returns_list_of_results(self) -> None:
        agent = _make_agent()
        http = _make_http_mock(FAKE_SEARCH_RESPONSE)
        with patch("httpx.Client", return_value=http):
            results = agent.recall("AI trends")
        assert isinstance(results, list)
        assert len(results) == 2

    def test_returns_empty_list_when_no_results(self) -> None:
        agent = _make_agent()
        http = _make_http_mock({"results": []})
        with patch("httpx.Client", return_value=http):
            results = agent.recall("obscure topic xyz")
        assert results == []


# ── research ──────────────────────────────────────────────────────────────────


class TestResearch:
    def test_research_returns_three_findings(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_RESEARCH)
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            findings = agent.research("AI in content creation")
        assert len(findings) == 3

    def test_research_findings_are_tagged(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_RESEARCH)
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        valid_tags = ("[TREND]", "[INSIGHT]", "[SOURCE]")
        with patch("httpx.Client", return_value=http):
            findings = agent.research("AI in content creation")
        for f in findings:
            assert any(f.startswith(t) for t in valid_tags), f"Untagged finding: {f!r}"

    def test_research_calls_gemini_with_flash_model(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_RESEARCH)
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.research("AI in content creation")
        agent._client.models.generate_content.assert_called_once()
        call = agent._client.models.generate_content.call_args
        # model kwarg must be gemini-2.5-flash
        assert call.kwargs.get("model") == "gemini-2.5-flash"

    def test_research_stores_each_finding(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_RESEARCH)
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.research("AI in content creation")
        # One POST per finding (3 findings → 3 store calls)
        assert http.post.call_count == 3

    def test_research_prompt_contains_topic(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_RESEARCH)
        http = _make_http_mock(FAKE_ADD_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.research("quantum computing trends")
        call = agent._client.models.generate_content.call_args
        prompt: str = call.kwargs.get("contents", "")
        assert "quantum computing trends" in prompt


# ── summarize ─────────────────────────────────────────────────────────────────


class TestSummarize:
    def test_summarize_returns_non_empty_string(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_SUMMARY)
        http = _make_http_mock(FAKE_SEARCH_RESPONSE)
        with patch("httpx.Client", return_value=http):
            result = agent.summarize("AI trends")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_summarize_calls_recall_then_gemini(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_SUMMARY)
        http = _make_http_mock(FAKE_SEARCH_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.summarize("AI trends")
        # recall → one POST to /api/v1/memory/search
        http.post.assert_called_once()
        search_url: str = http.post.call_args[0][0]
        assert search_url.endswith("/api/v1/memory/search")
        # then Gemini is called once for the synthesis
        agent._client.models.generate_content.assert_called_once()

    def test_summarize_prompt_contains_topic(self) -> None:
        agent = _make_agent(gemini_text=FAKE_GEMINI_SUMMARY)
        http = _make_http_mock(FAKE_SEARCH_RESPONSE)
        with patch("httpx.Client", return_value=http):
            agent.summarize("machine learning ops")
        call = agent._client.models.generate_content.call_args
        prompt: str = call.kwargs.get("contents", "")
        assert "machine learning ops" in prompt
