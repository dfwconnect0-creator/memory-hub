# Claude CLI Prompt: V2 Video Pipeline Connector (Topic → Research → VideoData)

> **Paste the single paragraph below into Claude CLI.** Everything above this line is context for you.

## What Exists Already

| System | Location | Status |
|:---|:---|:---|
| Content Researcher agent | `~/cognee-mcp/agents/content_researcher/agent.py` | ✅ Built — `research(topic)` returns `[TREND]`/`[INSIGHT]`/`[SOURCE]` findings, stores to Memory Hub |
| Marketing Agent video converter | `~/Documents/antigravity/marketing-agent/src/video_converter.py` | ✅ Built — `angle_to_video_data()` converts ContentAngle→VideoData JSON via Gemini |
| Marketing Agent CLI | `~/Documents/antigravity/marketing-agent/src/cli.py` | ✅ Built — has `video` command that runs full pipeline |

## What This Prompt Builds

A **pipeline connector** in cognee-mcp at `pipeline/topic_to_video.py` that:
1. Takes a topic string
2. Calls Content Researcher's `research(topic)` for live web-grounded findings
3. Sends findings to Gemini to generate a VideoData JSON (Gulf Arabic, 5-6 scenes)
4. Saves the JSON to `pipeline/output/`

## The Prompt (Single Paragraph)

```
Read these files first for context: ~/cognee-mcp/agents/content_researcher/agent.py (the ContentResearcherAgent class with research method), ~/cognee-mcp/agents/content_researcher/cli.py (the _load_env pattern you must copy), ~/Documents/antigravity/marketing-agent/src/video_converter.py (the VIDEO_SYSTEM_PROMPT and VIDEO_USER_PROMPT and _parse_video_response function — reuse these exactly). Build a pipeline connector at ~/cognee-mcp/pipeline/topic_to_video.py that chains Content Researcher findings into a Remotion-compatible VideoData JSON. Create pipeline/__init__.py (empty) and pipeline/output/.gitkeep. In pipeline/topic_to_video.py: copy the _load_env function from agents/content_researcher/cli.py and call it at module top BEFORE any other imports — this is critical, without it GEMINI_API_KEY is not loaded and everything fails. Import ContentResearcherAgent from agents.content_researcher.agent. Import genai from google. Create a function generate_video_script(findings: list[str], topic: str) -> dict that takes research findings, builds a prompt using the exact same VIDEO_SYSTEM_PROMPT and VIDEO_USER_PROMPT templates from marketing-agent/src/video_converter.py (copy them into this file, do NOT import across repos), calls genai.Client(api_key=os.environ["GEMINI_API_KEY"]).models.generate_content(model="gemini-2.5-flash", contents=prompt) to generate a VideoData JSON in Gulf Arabic dialect with 5-6 scenes following the pattern hook->intro->2-3 points/list->cta, parses the response using the same _parse_video_response logic (copy it, do NOT import), and returns the dict. Create a main function that uses argparse with --topic TEXT (required), --lang ar/en (default ar), --output-dir (default pipeline/output), --skip-research flag (if set, skip research and load findings from Memory Hub via agent.recall instead). The main flow: create ContentResearcherAgent(), if not --skip-research call agent.research(topic) to get findings and store them to Memory Hub, else call agent.recall(topic), then call generate_video_script(findings, topic), save the JSON to output_dir/{video_id}.json with ensure_ascii=False and indent=2, print the Remotion render command: cd "~/Downloads/SamCV /video" && npx remotion render FahadYouTubeShort --props="path/to/json" out/{video_id}.mp4. Also create pipeline/script_generator.py and move the generate_video_script function there for clean separation, keep topic_to_video.py as the CLI entry point. The VIDEO_USER_PROMPT must use these Arabic style examples in the prompt to Gemini: hook correct "هل الذكاء الاصطناعي\nبياخد شغلك؟" incorrect "هل سيحل الذكاء الاصطناعي محل وظيفتك", point correct "الحقيقة اللي محدش بيقولها:" incorrect "الحقائق التي لا يخبرك بها أحد", cta correct "تابعني عشان نتكلم\nعن مستقبل الشغل" incorrect "تابعنا للمزيد". Print progress at each step: "🔍 Researching: {topic}...", "📝 Found {n} findings", "🎬 Generating video script...", "✅ Saved: {path}". Run ruff check pipeline/ to verify zero errors. Test with: UV_CACHE_DIR=/tmp/uv-cache uv run python -m pipeline.topic_to_video --topic "AI jobs in Saudi Arabia 2026". Verify the output JSON has valid VideoData structure with 5-6 scenes, all scenes have type/headline/camera/durationInFrames, Arabic text is Gulf dialect not formal MSA. After verification: git add pipeline/ and git commit -m "feat(pipeline): V2 topic-to-video connector with Content Researcher" — never use git add -A, and run git diff --cached --name-only | grep -E "\.env|\.key|\.pem|secret|password" before committing to check for secrets.
```

## Validation After Running

```bash
# Test 1: Full pipeline (research + generate)
UV_CACHE_DIR=/tmp/uv-cache uv run python -m pipeline.topic_to_video --topic "AI jobs Saudi Arabia 2026"

# Test 2: Memory-only (skip research, use stored findings)
UV_CACHE_DIR=/tmp/uv-cache uv run python -m pipeline.topic_to_video --topic "AI" --skip-research

# Test 3: Check JSON is valid for Remotion
cat pipeline/output/fahad-ep-*.json | python -m json.tool
```
