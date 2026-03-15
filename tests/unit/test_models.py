"""Phase 1 — Pydantic model tests (RED phase)."""
import pytest
from pydantic import ValidationError


def test_valid_memory_add_request():
    from memory_hub.models.requests import MemoryAddRequest
    req = MemoryAddRequest(
        content="TikTok trending: Ramadan content +40%",
        project="content-creation",
        agent_id="research_agent",
        category="trend",
    )
    assert req.content == "TikTok trending: Ramadan content +40%"
    assert req.project == "content-creation"
    assert req.agent_id == "research_agent"


def test_invalid_category_rejected():
    from memory_hub.models.requests import MemoryAddRequest
    with pytest.raises(ValidationError):
        MemoryAddRequest(
            content="test",
            project="content-creation",
            agent_id="research_agent",
            category="invalid_category",
        )


def test_default_category_is_general():
    from memory_hub.models.requests import MemoryAddRequest
    req = MemoryAddRequest(
        content="test",
        project="content-creation",
        agent_id="research_agent",
    )
    assert req.category.value == "general"


def test_search_request_defaults():
    from memory_hub.models.requests import SearchRequest
    req = SearchRequest(query="ramadan trends", project="content-creation")
    assert req.limit == 10
    assert req.agent_id is None


def test_search_request_custom_limit():
    from memory_hub.models.requests import SearchRequest
    req = SearchRequest(query="test", project="seo-audit", limit=5)
    assert req.limit == 5


def test_memory_add_requires_content():
    from memory_hub.models.requests import MemoryAddRequest
    with pytest.raises(ValidationError):
        MemoryAddRequest(project="content-creation", agent_id="research_agent")  # type: ignore[call-arg]


def test_error_response_has_message():
    from memory_hub.models.responses import ErrorResponse
    err = ErrorResponse(message="Something went wrong", code="INTERNAL_ERROR")
    assert err.message == "Something went wrong"
    assert err.code == "INTERNAL_ERROR"


def test_memory_response_shape():
    from memory_hub.models.responses import MemoryAddResponse
    resp = MemoryAddResponse(memory_id="mem-123", status="ok")
    assert resp.memory_id == "mem-123"


def test_search_response_has_results():
    from memory_hub.models.responses import SearchResponse
    resp = SearchResponse(results=[], query="test", total=0)
    assert resp.results == []
    assert resp.total == 0


def test_agent_config_model():
    from memory_hub.models.domain import AgentConfig
    agent = AgentConfig(
        name="Research Agent",
        framework="langchain",
        project="content-creation",
        role="researcher",
    )
    assert agent.name == "Research Agent"
    assert agent.permissions.read_shared is True


def test_memory_category_values():
    from memory_hub.models.domain import MemoryCategory
    assert MemoryCategory.TREND.value == "trend"
    assert MemoryCategory.GENERAL.value == "general"
    assert MemoryCategory.CODE.value == "code"
