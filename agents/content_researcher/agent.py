"""Content Researcher Agent — memory-backed research and trend tracking."""
from __future__ import annotations

import contextlib
import json
import os
from typing import Any

from google import genai
from google.genai import types

from adapters.langchain_tool import MemoryAddTool, MemorySearchTool

PROJECT = "content-creation"
AGENT_ID = "research_agent"

_CATEGORY_TAG: dict[str, str] = {
    "trend": "[TREND]",
    "insight": "[INSIGHT]",
    "source": "[SOURCE]",
}

RESEARCH_PROMPT = """You are a content research assistant. Research the following topic and return
exactly one finding per line in these formats (no extra commentary):

[TREND] <a current trend related to the topic>
[INSIGHT] <a key insight or analysis>
[SOURCE] <url> — <title or description>

Return at least 3 findings. Topic: {topic}"""

SUMMARIZE_PROMPT = """You are a content strategist. Synthesize the following research findings
about "{topic}" into a concise, actionable summary (2-4 sentences).

Findings:
{findings}

Summary:"""

SYSTEM_PROMPT = """You are a content research assistant with persistent memory. You help users:
- Research topics and identify current trends
- Analyse insights from across the web and industry sources
- Surface relevant sources and references
- Summarise and synthesise research findings

You can STORE findings about topics (trends, insights, sources).
You can SEARCH your memory to recall past research and provide informed answers.

When a user asks a research question, search memory first for relevant context.
Keep responses concise and grounded in evidence.
"""


class ContentResearcherAgent:
    """Memory-backed content researcher using Memory Hub tools."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "http://localhost:8000",
    ) -> None:
        key = api_key or os.environ.get("CONTENT_RESEARCHER_API_KEY", "")
        common: dict[str, Any] = dict(
            project=PROJECT,
            agent_id=AGENT_ID,
            api_key=key,
            base_url=base_url,
        )
        self.memory_add = MemoryAddTool(**common)
        self.memory_search = MemorySearchTool(**common)

        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self._client = genai.Client(api_key=gemini_key)

    def store_finding(self, content: str, category: str = "trend") -> dict[str, Any]:
        """Store a research finding in memory, prepending a tag if not already present."""
        if not content.startswith("["):
            tag = _CATEGORY_TAG.get(category, "[TREND]")
            content = f"{tag} {content}"
        # Wrap for mem0's fact extraction — it needs "personal fact" framing
        storable = f"User researched and found: {content}"
        payload = json.dumps({"content": storable, "category": category})
        result: dict[str, Any] = json.loads(self.memory_add._run(payload))
        return result

    def recall(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search research memories."""
        payload = json.dumps({"query": query, "limit": limit})
        data: dict[str, Any] = json.loads(self.memory_search._run(payload))
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    def research(self, topic: str) -> list[str]:
        """Research a topic via Gemini, parse tagged findings, and store each one."""
        prompt = RESEARCH_PROMPT.format(topic=topic)
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            raw = response.text.strip() if response.text else ""
        except Exception as e:
            return [f"[INSIGHT] (research error: {e})"]

        findings: list[str] = []
        valid_tags = ("[TREND]", "[INSIGHT]", "[SOURCE]")
        for line in raw.splitlines():
            line = line.strip()
            if any(line.startswith(t) for t in valid_tags):
                findings.append(line)
                try:
                    self.store_finding(line, category="trend")
                except Exception as e:
                    print(f"  ⚠ store failed: {e}")

        return findings

    def chat(self, user_input: str) -> str:
        """Answer a general content research question using memory context + Gemini."""
        memories = self.recall(user_input)
        context = ""
        if memories:
            snippets = [m.get("content", "") for m in memories[:3] if m.get("content")]
            if snippets:
                joined = "\n".join(f"- {s}" for s in snippets)
                context = f"\n\nRelevant research findings:\n{joined}"

        prompt = f"{SYSTEM_PROMPT}{context}\n\nUser: {user_input}\n\nContent Researcher:"
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
            return "I can help with content research. Could you tell me more?"
        except Exception as e:
            return f"(LLM error: {e})"

    def summarize(self, topic: str) -> str:
        """Recall stored findings for a topic and synthesize a summary via Gemini."""
        memories = self.recall(topic)
        if memories:
            snippets = [m.get("content", "") for m in memories if m.get("content")]
            findings_text = "\n".join(f"- {s}" for s in snippets)
        else:
            findings_text = "(no stored findings)"

        prompt = SUMMARIZE_PROMPT.format(topic=topic, findings=findings_text)
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            return f"(summarize error: {e})"
