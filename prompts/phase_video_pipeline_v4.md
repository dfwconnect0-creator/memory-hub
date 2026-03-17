# Video Pipeline V4 — Spec + Phases + Claude CLI Prompts

**Date:** 2026-03-17 | **Role:** Planner (Antigravity) | **Builder:** Claude CLI
**Prereqs:** Memory Hub v5 running, Content Researcher (2B) done, `research_agent` key in AGENT_KEYS

---

## Critical Warnings (Baked into Every Prompt)

| Warning | Fix |
|:---|:---|
| W1: dotenv crash | Copy `_load_env()` from `agents/content_researcher/cli.py` — load `.env` BEFORE any imports |
| W2: Use google.genai directly | `from google import genai` + `genai.Client(api_key=key)` — no LangChain wrappers |
| W3: Real Gemini calls | `client.models.generate_content(model="gemini-2.5-flash", ...)` — no stubs |
| W4: UV cache | `UV_CACHE_DIR=/tmp/uv-cache` prefix if cache corruption errors |
| W5: Never `git add -A` | Stage specific dirs only, run secrets grep before commit |
| W6: Remotion path has space | Always quote: `"~/Downloads/SamCV /video"` |

---

## 1. Specification

### Goal

Build a **pipeline connector** in cognee-mcp that chains: Topic → Content Researcher (web-grounded findings) → Gemini (Gulf Arabic video script) → VideoData JSON compatible with the existing Remotion FahadYouTubeShort template.

This proves **end-to-end production**: research goes in, rendered video script comes out.

### Scope

| In Scope | Out of Scope |
|:---|:---|
| CLI: `python -m pipeline.topic_to_video --topic "..."` | Remotion rendering (already works separately) |
| Research via Content Researcher agent | Marketing-agent integration (separate repo) |
| Gemini generates Gulf Arabic 5-6 scene scripts | Voiceover/audio generation |
| `--skip-research` flag reads findings from Memory Hub | Scheduling / cron jobs |
| JSON output compatible with Remotion template | Web UI / API server |

### Architecture

```
CLI Input: --topic "AI jobs Saudi 2026"
        │
        ▼
┌─────────────────────────────┐
│ pipeline/topic_to_video.py  │  CLI entry point
│  _load_env() at top         │
└─────────┬───────────────────┘
          │
          ├── agent.research(topic)  ─── Gemini + Google Search ──► [TREND], [INSIGHT], [SOURCE]
          │                                                          │
          │                                                          ▼
          │                                                   Memory Hub :8000
          │                                                   (stored for other agents)
          │
          ▼
┌─────────────────────────────┐
│ pipeline/script_generator.py │  Gemini call: findings → VideoData JSON
│  Gulf Arabic system prompt   │
│  Scene pattern: hook→intro   │
│    →points/list→cta          │
└─────────┬───────────────────┘
          │
          ▼
  pipeline/output/{video_id}.json   ← valid VideoData for Remotion
```

### VideoData Target Shape

```json
{
  "id": "fahad-ep-20260317-ai-jobs-ksa",
  "title": "وظائف الذكاء الاصطناعي في السعودية",
  "pillar": "ai",
  "bgMusic": "EleEnergetic, Social Media Creator_pre_sp109_s50_sb75_v3.mp3",
  "bgMusicVolume": 0.15,
  "scenes": [
    {"type": "hook",  "emoji": "🤖", "headline": "الذكاء الاصطناعي\nبياخد شغلك؟",      "camera": "zoom",   "durationInFrames": 90},
    {"type": "intro", "emoji": "💼", "headline": "معكم فهد الحربي", "body": "خبير مهني — SamimlyCV", "camera": "static", "durationInFrames": 75},
    {"type": "point", "emoji": "💡", "headline": "...", "body": "...",                   "camera": "pan",    "durationInFrames": 120},
    {"type": "list",  "emoji": "✅", "headline": "...", "items": ["...","...","..."],     "camera": "tilt",   "durationInFrames": 150},
    {"type": "cta",   "emoji": "🚀", "headline": "تابعني عشان تعرف أكثر\nعن مستقبل الشغل", "body": "SamimlyCV", "camera": "zoom", "durationInFrames": 90}
  ]
}
```

### Success Criteria

1. `uv run python -m pipeline.topic_to_video --topic "AI jobs Saudi 2026"` produces valid JSON ✅
2. JSON has 5-6 scenes following hook→intro→points→cta pattern ✅
3. Arabic text is Gulf dialect, not MSA ✅
4. `--skip-research` reads from Memory Hub instead of re-researching ✅
5. `ruff check pipeline/` = zero errors ✅
6. All tests pass ✅

---

## 2. Phased Breakdown

### Phase 1: Scaffold + Script Generator (30 min)

| Task | File |
|:---|:---|
| Create `pipeline/__init__.py` | new |
| Create `pipeline/output/.gitkeep` | new |
| Create `pipeline/script_generator.py` with Gemini prompt templates | new |
| Copy VIDEO_SYSTEM_PROMPT + VIDEO_USER_PROMPT from marketing-agent reference | copied, not imported |
| Implement `generate_video_script(findings, topic) -> dict` | `script_generator.py` |
| Implement `_parse_video_response(raw_text) -> dict` | `script_generator.py` |
| Write `tests/unit/test_script_generator.py` — mock Gemini, verify JSON shape | new |
| **Target:** 3-4 tests pass, `ruff check pipeline/` = 0 errors | — |

### Phase 2: CLI Entry Point (30 min)

| Task | File |
|:---|:---|
| Create `pipeline/topic_to_video.py` with `_load_env` at top | new |
| argparse: `--topic`, `--skip-research`, `--output-dir`, `--lang` | `topic_to_video.py` |
| Main flow: research → generate_video_script → save JSON | `topic_to_video.py` |
| Print progress: 🔍 Researching → 📝 Found N findings → 🎬 Generating → ✅ Saved | `topic_to_video.py` |
| Print Remotion render command at end | `topic_to_video.py` |
| Write `tests/unit/test_topic_to_video.py` — test argparse, test main with mocks | new |
| **Target:** 3-4 tests pass, `--topic` runs end-to-end with mocked Gemini | — |

### Phase 3: Memory Hub Integration + `--skip-research` (30 min)

| Task | File |
|:---|:---|
| Implement `--skip-research`: call `agent.recall(topic)` instead of `agent.research(topic)` | `topic_to_video.py` |
| Format recall results into findings list for script generator | `topic_to_video.py` |
| Write test: verify `--skip-research` calls recall not research | `test_topic_to_video.py` |
| Manual E2E: run `--topic` first (stores to Memory Hub), then `--skip-research` (reads back) | — |
| **Target:** both modes work, 2 extra tests pass | — |

### Phase 4: E2E Validation + Polish (20 min)

| Task | File |
|:---|:---|
| Run full test suite: `uv run pytest tests/ -v` | — |
| Run `ruff check pipeline/ agents/ tests/` | — |
| E2E: `--topic "AI jobs Saudi 2026"` → verify JSON is valid for Remotion | — |
| E2E: `--skip-research` → verify pulls from Memory Hub | — |
| Cross-agent: verify Career Coach can `--recall "[TREND]"` and see research findings | — |
| Git: stage `pipeline/ tests/unit/test_script_generator.py tests/unit/test_topic_to_video.py` only | — |
| Secrets check: `git diff --cached --name-only \| grep -E '\.env\|\.key\|\.pem\|secret\|password'` | — |
| Commit: `feat(pipeline): topic-to-video connector with Content Researcher` | — |
| **Target:** all tests pass, zero ruff errors, clean commit | — |

---

## 3. Claude CLI Prompts

### Phase 1 Prompt

```
Read ~/cognee-mcp/agents/content_researcher/agent.py and ~/Documents/antigravity/marketing-agent/src/video_converter.py as reference. Create ~/cognee-mcp/pipeline/__init__.py (empty), ~/cognee-mcp/pipeline/output/.gitkeep (empty). Create ~/cognee-mcp/pipeline/script_generator.py — copy the VIDEO_SYSTEM_PROMPT and VIDEO_USER_PROMPT from marketing-agent/src/video_converter.py into this file (do NOT import across repos, copy the text). The system prompt is an Arabic prompt instructing Gemini to produce Gulf dialect 5-6 scene video scripts. The user prompt template has placeholders for topic, findings text, date_slug, and topic_slug. Also copy the _parse_video_response function that strips markdown fences and parses JSON. Write a generate_video_script(findings: list[str], topic: str) -> dict function that takes a list of research findings (like "[TREND] ..." strings), builds the user prompt with the findings joined by newlines as context, calls genai.Client(api_key=os.environ["GEMINI_API_KEY"]).models.generate_content(model="gemini-2.5-flash", contents=[system_prompt, user_prompt]) to generate a VideoData JSON, parses it with _parse_video_response, ensures fallback values for id (fahad-ep-{date}-{slug}), bgMusic, and bgMusicVolume, then returns the dict. Also write a _make_topic_slug(text) function copied from video_converter.py for generating URL slugs from Arabic/English titles. Write tests first in ~/cognee-mcp/tests/unit/test_script_generator.py: test that _make_topic_slug converts Arabic to slugs, test that _parse_video_response handles JSON with and without markdown fences, test that generate_video_script with a mocked genai client returns a dict with id-title-pillar-scenes keys, test that scenes list has at least 4 items. Use unittest.mock.patch to mock the genai client. Run "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_script_generator.py -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check pipeline/" to verify. Target: 4 tests pass, zero ruff errors.
```

### Phase 2 Prompt

```
Read ~/cognee-mcp/pipeline/script_generator.py (just created in phase 1) and ~/cognee-mcp/agents/content_researcher/cli.py for the proven _load_env pattern. Create ~/cognee-mcp/pipeline/topic_to_video.py — CRITICAL: copy the _load_env function from agents/content_researcher/cli.py exactly and call it at the very top of the file BEFORE any other imports, loading Path(__file__).resolve().parents[1] / ".env". This is non-negotiable, without it GEMINI_API_KEY and CONTENT_RESEARCHER_API_KEY are not available and everything crashes. After _load_env, import ContentResearcherAgent from agents.content_researcher.agent and generate_video_script from pipeline.script_generator. Create a build_parser() function returning argparse.ArgumentParser with: --topic TEXT (required positional or flag), --skip-research (store_true, if set read from Memory Hub instead of live research), --output-dir (default "pipeline/output"), --api-key (override CONTENT_RESEARCHER_API_KEY), --base-url (default http://localhost:8000). Create a main() function that: creates ContentResearcherAgent(api_key, base_url), if not skip_research calls agent.research(topic) printing "🔍 Researching: {topic}..." and "📝 Found {n} findings", else calls agent.recall(topic) and extracts content strings from results printing "📚 Loaded {n} findings from memory", then calls generate_video_script(findings, topic) printing "🎬 Generating video script...", saves result to output_dir/{video_id}.json with json.dump(ensure_ascii=False, indent=2) printing "✅ Saved: {path}", finally prints the Remotion render command: cd "~/Downloads/SamCV /video" && npx remotion render FahadYouTubeShort --props="{absolute_path}" out/{video_id}.mp4. Add if __name__ == "__main__": sys.exit(main()). Write tests in ~/cognee-mcp/tests/unit/test_topic_to_video.py: test build_parser returns parser with expected flags, test main with --topic calls agent.research (mock the agent and script generator), test main with --skip-research calls agent.recall not research. Run "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_topic_to_video.py tests/unit/test_script_generator.py -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check pipeline/" to verify. Target: 3+ new tests pass, all phase 1 tests still pass, zero ruff errors.
```

### Phase 3 Prompt

```
Read ~/cognee-mcp/pipeline/topic_to_video.py and ~/cognee-mcp/pipeline/script_generator.py. This phase polishes the --skip-research flow and adds edge case handling. In topic_to_video.py: when --skip-research is used and agent.recall returns results, extract the "content" or "memory" field from each result dict and filter to only lines containing "[TREND]" or "[INSIGHT]" or "[SOURCE]" tags, if no findings found print "⚠ No stored findings for this topic. Run without --skip-research first." and sys.exit(1). When --topic research returns zero findings, print a warning and exit instead of passing empty list to script generator. Add a --dry-run flag that prints what would happen without calling Gemini (useful for testing the research step alone). In script_generator.py: add validation after parsing — verify the returned dict has "scenes" key with at least 3 items, verify each scene has "type" and "headline" keys, if validation fails raise ValueError with a clear message. Add a test in test_topic_to_video.py: test that --skip-research with empty recall prints warning and exits with code 1. Add a test in test_script_generator.py: test that generate_video_script raises ValueError when Gemini returns invalid JSON (mock it to return garbage text). Run "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_script_generator.py tests/unit/test_topic_to_video.py -v" then "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v" to check no regressions across the whole project. Target: 2 new tests pass, all existing tests still pass, zero ruff errors.
```

### Phase 4 Prompt

```
This is the E2E validation and commit phase. First ensure the Memory Hub server is running on port 8000 — if not, start it: kill $(lsof -ti:8000) 2>/dev/null; sleep 1; cd ~/cognee-mcp && UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn memory_hub.app:create_app --factory --port 8000 & and wait 3 seconds. Run the full test suite with "UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v" and fix any failures. Run "UV_CACHE_DIR=/tmp/uv-cache uv run ruff check pipeline/ agents/ tests/" and fix any lint errors. Now do E2E validation: run "UV_CACHE_DIR=/tmp/uv-cache uv run python -m pipeline.topic_to_video --topic 'AI jobs in Saudi Arabia 2026'" and verify it produces a valid JSON file in pipeline/output/ with 5-6 scenes in Gulf Arabic dialect. Check the JSON with "cat pipeline/output/fahad-ep-*.json | python -m json.tool" to confirm valid structure. Then test --skip-research: run "UV_CACHE_DIR=/tmp/uv-cache uv run python -m pipeline.topic_to_video --topic 'AI' --skip-research" and verify it pulls findings from Memory Hub. Finally test cross-agent: run "UV_CACHE_DIR=/tmp/uv-cache uv run python -m agents.content_researcher.cli --recall '[TREND]'" to verify findings are searchable. IMPORTANT GIT SAFETY: stage ONLY specific paths, never use git add -A. Run "git diff --cached --name-only | grep -E '\.env|\.key|\.pem|secret|password'" before committing to check for secrets. Stage with "git add pipeline/ tests/unit/test_script_generator.py tests/unit/test_topic_to_video.py" then commit with "git commit -m 'feat(pipeline): topic-to-video connector with Content Researcher'". Target: all tests pass, zero ruff errors, E2E produces valid VideoData JSON, clean git commit with no secrets.
```

---

> **Run order:** Phase 1 → Phase 2 → Phase 3 → Phase 4. Come back to Antigravity for review after each phase.

> **Total estimated time:** ~2 hours
