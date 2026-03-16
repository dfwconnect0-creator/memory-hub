"""Career Coach Agent — LangChain-compatible memory-backed career advisor."""
from __future__ import annotations

import json
import os
from typing import Any

from google import genai

from adapters.langchain_tool import MemoryAddTool, MemorySearchTool

PROJECT = "personal"
AGENT_ID = "career_coach_agent"

SYSTEM_PROMPT = """You are a career coach with persistent memory. You help users with:
- Resume and job application advice
- Interview preparation
- Career planning and goal setting
- Skill development recommendations
- Salary negotiation tips

You can STORE memories about the user's career (goals, experience, skills, applications).
You can SEARCH your memory to recall past context and provide personalized advice.

When a user shares career information, store it. When they ask a question, search first.
Keep responses concise and actionable.
"""


class CareerCoachAgent:
    """Memory-backed career coach using Memory Hub tools."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "http://localhost:8000",
    ) -> None:
        key = api_key or os.environ.get("CAREER_COACH_API_KEY", "")
        common: dict[str, Any] = dict(
            project=PROJECT,
            agent_id=AGENT_ID,
            api_key=key,
            base_url=base_url,
        )
        self.memory_add = MemoryAddTool(**common)
        self.memory_search = MemorySearchTool(**common)
        self.system_prompt = SYSTEM_PROMPT

        # Initialize Gemini client
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self._client = genai.Client(api_key=gemini_key)
        self._history: list[dict[str, str]] = []

    def remember(self, content: str, category: str = "career") -> dict[str, Any]:
        """Store a career-related memory."""
        payload = json.dumps({"content": content, "category": category})
        result: dict[str, Any] = json.loads(self.memory_add._run(payload))
        return result

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search career memories."""
        payload = json.dumps({"query": query, "limit": limit})
        data: dict[str, Any] = json.loads(self.memory_search._run(payload))
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    def chat(self, user_input: str) -> str:
        """Process user input: search memory for context, generate AI response."""
        # Search memory for relevant context
        memories = self.recall(user_input)
        context = ""
        if memories:
            snippets = [m.get("content", "") for m in memories[:3] if m.get("content")]
            if snippets:
                joined = "\n".join(f"- {s}" for s in snippets)
                context = f"\n\nRelevant memories about this user:\n{joined}"

        # Build prompt with memory context
        prompt = f"{self.system_prompt}{context}\n\nUser: {user_input}\n\nCareer Coach:"

        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            reply = response.text.strip() if response.text else "I'm here to help with your career. Could you tell me more?"
        except Exception as e:
            reply = f"(LLM error: {e})"

        # Auto-store if the user shared career info
        lower = user_input.lower()
        if any(kw in lower for kw in ["goal", "want to", "plan", "working on", "learned", "built", "finished"]):
            try:
                self.remember(user_input)
            except Exception:
                pass

        return reply

