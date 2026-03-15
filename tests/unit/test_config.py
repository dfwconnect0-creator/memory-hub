"""Phase 1 — Config tests (RED phase: run before implementation)."""

import pytest


def test_loads_env_values(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("HUB_API_KEY", "test-hub-secret")
    # Re-import to pick up monkeypatched env
    import importlib

    import memory_hub.config as cfg_module
    importlib.reload(cfg_module)
    from memory_hub.config import Settings
    s = Settings()
    assert s.GEMINI_API_KEY == "test-gemini-key"
    assert s.HUB_API_KEY == "test-hub-secret"


def test_missing_gemini_key_fails(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("HUB_API_KEY", raising=False)
    from pydantic import ValidationError

    from memory_hub.config import Settings
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_missing_hub_api_key_fails(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("HUB_API_KEY", raising=False)
    from pydantic import ValidationError

    from memory_hub.config import Settings
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_loads_agents_yaml(tmp_path):
    yaml_content = """
agents:
  research_agent:
    name: "Research Agent"
    framework: "langchain"
    project: "content-creation"
    role: "researcher"
    other_mcps: []
    permissions:
      read_shared: true
      write_shared: true
settings:
  log_level: "INFO"
"""
    yaml_file = tmp_path / "agents.yaml"
    yaml_file.write_text(yaml_content)

    from memory_hub.config import load_agents_config
    data = load_agents_config(str(yaml_file))
    assert "agents" in data
    assert "research_agent" in data["agents"]
    assert data["agents"]["research_agent"]["project"] == "content-creation"


def test_invalid_yaml_path_raises():
    from memory_hub.config import load_agents_config
    with pytest.raises(FileNotFoundError):
        load_agents_config("/nonexistent/path/agents.yaml")


def test_default_values(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setenv("HUB_API_KEY", "secret")
    from memory_hub.config import Settings
    s = Settings()
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 8000
    assert s.LOG_LEVEL == "INFO"
