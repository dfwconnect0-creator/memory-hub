# Video Pipeline V5 — Tests + Polish for Existing Marketing Agent Converter

**Date:** 2026-03-17 | **Repo:** `~/Documents/antigravity/marketing-agent/`
**Prereqs:** Marketing agent runs, Gemini API key in `.env`

---

## What Already Exists (Don't Rebuild)

- `src/video_converter.py` — 250 lines, Gemini Gulf Arabic script generator, mock mode ✅
- `src/cli.py` — `video` command with `--mock`/`--pick`/`--output`/`--provider` ✅
- `src/ai_orchestrator.py` — multi-provider (Gemini/Claude/LMStudio) with fallback ✅
- `src/pipeline.py` — trend scanning + angle generation ✅

**What's missing:** Tests (zero test files). That's all V5 adds.

---

## Success Criteria

- `uv run pytest tests/ -v` → 10+ tests pass
- `uv run ruff check src/ tests/` → 0 errors
- `uv run python -m src.cli video --mock` → valid JSON in `output/videos/`

---

## Phase 1: Tests for `video_converter.py` (30 min)

| Task | File |
|:---|:---|
| Create `tests/__init__.py` | new |
| Create `tests/test_video_converter.py` (8 tests) | new |
| Test `_make_topic_slug` — Arabic + English inputs | test |
| Test `_parse_video_response` — clean JSON, fenced JSON, garbage raises ValueError | test |
| Test `_mock_video_data` — valid shape, hook→intro→cta scene order | test |
| Test `angle_to_video_data` — mock=True skips LLM, mock=False calls generate_content | test |
| **Target:** 8 tests pass, `ruff check src/ tests/` = 0 errors | — |

### Phase 1 Prompt

```
Read ~/Documents/antigravity/marketing-agent/src/video_converter.py, ~/Documents/antigravity/marketing-agent/src/models.py, and ~/Documents/antigravity/marketing-agent/src/ai_orchestrator.py. The video converter is already fully built — your job is to add tests only, do NOT change the source code. Create ~/Documents/antigravity/marketing-agent/tests/__init__.py (empty). Create ~/Documents/antigravity/marketing-agent/tests/test_video_converter.py with 8 tests using pytest and unittest.mock. Test _make_topic_slug: call it with Arabic text containing "الذكاء الاصطناعي" and assert result is "ai", call with "AI jobs Saudi" and assert result contains a slug, call with "hello world" and assert result is "hello-world". Test _parse_video_response: pass it a clean JSON string with id, title, pillar, scenes keys and assert the result is a dict with those keys, pass it markdown-fenced JSON (starting with triple backticks) and assert it still parses correctly, pass it "not json at all!!!" and assert it raises ValueError. Test _mock_video_data: create a ContentAngle (headline="Test", hook="Test hook") and Trend (title="AI testing", source=TrendSource.GOOGLE_TRENDS) from src.models, call _mock_video_data(angle, trend) and assert result has keys "id", "title", "pillar", "scenes", assert len(scenes) >= 3, assert scenes[0]["type"] == "hook" and scenes[-1]["type"] == "cta". Test angle_to_video_data: use asyncio.run() to call it with mock=True and assert it returns a dict without mocking anything (mock=True skips LLM), then test with mock=False by patching "src.video_converter.generate_content" to return a minimal valid JSON string and assert it was called once and result has a scenes key. Run "uv run pytest tests/test_video_converter.py -v" then "uv run ruff check src/ tests/" to verify. Target: 8 tests pass, zero ruff errors.
```

---

## Phase 2: Tests for CLI `video` command + E2E + Commit (30 min)

| Task | File |
|:---|:---|
| Create `tests/test_cli_video.py` (3-4 tests) | new |
| Test `video --mock` produces JSON file | test |
| Test `video --mock --pick 2` selects 2nd angle | test |
| Test `video --mock` with empty pipeline → exit code 1 | test |
| E2E: `uv run python -m src.cli video --mock` → verify JSON in `output/videos/` | manual |
| Git: `git add tests/` → secrets check → commit | — |
| **Target:** 3+ new tests + all phase 1 tests pass, valid E2E JSON | — |

### Phase 2 Prompt

```
Read ~/Documents/antigravity/marketing-agent/src/cli.py (the video command, lines 132-209) and ~/Documents/antigravity/marketing-agent/tests/test_video_converter.py (tests from phase 1). Create ~/Documents/antigravity/marketing-agent/tests/test_cli_video.py with 3-4 pytest tests for the video CLI command. The video command uses Typer and calls run_pipeline then angle_to_video_data then saves a JSON file. Test 1 (mock success): patch "src.cli.run_pipeline" to return a mock AgentOutput with 1 TrendWithAngles containing 2 ContentAngles with brand_alignment_score=0.9 and 0.8, patch "src.cli.angle_to_video_data" to return {"id": "fahad-ep-test", "title": "Test", "pillar": "ai", "scenes": []}, invoke using typer.testing.CliRunner().invoke(app, ["video", "--mock", "--output", "/tmp/test_video_out"]), assert result.exit_code == 0 and the file /tmp/test_video_out/fahad-ep-test.json exists. Test 2 (pick flag): same patches but add "--pick", "2" to args, assert angle_to_video_data was called with the second ContentAngle. Test 3 (no angles): patch run_pipeline to return AgentOutput(results=[]), invoke video with ["video", "--mock"], assert exit_code == 1. After tests, run a real E2E: "uv run python -m src.cli video --mock" from ~/Documents/antigravity/marketing-agent/ and verify output/videos/ has a JSON file, then check it with "cat output/videos/*.json | python -m json.tool". Run "uv run pytest tests/ -v" then "uv run ruff check src/ tests/". IMPORTANT GIT SAFETY: never use git add -A. Run "git diff --cached --name-only | grep -E '\.env|\.key|\.pem|secret|password'" before committing. Stage with "git add tests/" then commit with "git commit -m 'test: add video converter and CLI tests'". Target: 3+ new tests pass, all phase 1 tests still pass, zero ruff errors, clean commit.
```

---

> **Run order:** Phase 1 → Phase 2. Total: ~1 hour.
