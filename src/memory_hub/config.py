"""Config loading: .env + config/agents.yaml via Pydantic Settings."""
from __future__ import annotations

import json
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required — startup fails fast if missing
    GEMINI_API_KEY: str
    HUB_API_KEY: str

    # Optional
    AGENT_KEYS: str = "{}"  # JSON: {"api_key": "agent_id"}
    AGENTS_YAML_PATH: str = "config/agents.yaml"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Qdrant Cloud URL — set to enable cross-machine memory sync
    QDRANT_URL: str = ""
    # Qdrant Cloud API key
    QDRANT_API_KEY: str = ""

    @property
    def agent_key_map(self) -> dict[str, str]:
        """Parsed mapping of api_key → agent_id."""
        try:
            result: dict[str, str] = json.loads(self.AGENT_KEYS)
            return result
        except (json.JSONDecodeError, ValueError):
            return {}


def load_agents_config(yaml_path: str = "config/agents.yaml") -> dict[str, object]:
    """Load agents.yaml and return the parsed dict. Raises FileNotFoundError if missing."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Agents config not found: {yaml_path}")
    with open(path) as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data
