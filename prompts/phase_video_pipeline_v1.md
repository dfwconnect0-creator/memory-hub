# Claude CLI Prompt: V1 Video Content Pipeline Connector

## ROLE
You are a senior Python engineer connecting existing components into a working video content pipeline. You are NOT building new UI or agents — you are writing GLUE CODE between components that already exist.

## CONTEXT
The user has these EXISTING pieces:

### 1. Content Researcher Agent (Python, `/Users/mohamedsalah/cognee-mcp/agents/content_researcher/`)
- `agent.py` — has `research(topic)` method that uses Gemini + Google Search grounding
- Returns tagged findings: `[TREND]`, `[INSIGHT]`, `[SOURCE]`
- CLI: `uv run python -m agents.content_researcher.cli --topic "..."`

### 2. Remotion Video Template (TypeScript, `/Users/mohamedsalah/Downloads/SamCV /video/`)
- `src/FahadYouTubeShort.tsx` — React component that renders YouTube Shorts
- `src/VideoData.ts` — TypeScript interfaces defining the data shape:

```typescript
interface VideoScene {
    type: 'hook' | 'intro' | 'point' | 'story' | 'list' | 'cta';
    emoji?: string;
    headline: string;
    body?: string;
    items?: string[];
    camera?: 'zoom' | 'pan' | 'tilt' | 'static';
    durationInFrames?: number;
}

interface VideoData {
    id: string;
    title: string;
    pillar: 'career' | 'workplace' | 'ai' | 'story' | 'sidehustle';
    voiceover?: string;
    bgMusic?: string;
    bgMusicVolume?: number;
    scenes: VideoScene[];
}
```

- 5 sample videos already in `VideoData.ts` (Arabic career content)
- FPS: 30, each scene needs `durationInFrames` (90-180 range typically)

### 3. Gemini API key is in `.env` as `GEMINI_API_KEY`

## TASK — Build the Pipeline Connector

Create a single Python script `pipeline/topic_to_video.py` that:

### Step 1: Accept a topic as input
```bash
uv run python -m pipeline.topic_to_video --topic "AI jobs in Saudi Arabia 2026" --lang ar
```

### Step 2: Research the topic (use Content Researcher)
Call the Content Researcher's `research(topic)` method to get live web findings.

### Step 3: Generate a video script via Gemini
Use Gemini to convert the research findings into a `VideoData` JSON object that matches the TypeScript interface above.

The prompt to Gemini should:
- Take the research findings as context
- Generate 5-6 scenes following the pattern: hook → intro → 2-3 points/list → cta
- Output valid JSON matching the `VideoData` interface
- Content should be in Arabic (Gulf dialect, career-focused)
- Include emojis, camera movements, and duration per scene
- The `id` should be auto-generated (e.g., `fahad-ep-{timestamp}`)
- Pillar should be inferred from the topic

### Step 4: Save the VideoData JSON to a file
Output to `pipeline/output/{video_id}.json`

### Step 5: (Optional) Generate the Remotion render command
Print the command the user would run to render the video:
```bash
cd "/Users/mohamedsalah/Downloads/SamCV /video" && npx remotion render FahadYouTubeShort --props="pipeline/output/{video_id}.json" out/{video_id}.mp4
```

## FILE STRUCTURE
```
pipeline/
├── __init__.py
├── topic_to_video.py      # Main pipeline script
├── script_generator.py    # Gemini call to convert findings → VideoData JSON
└── output/                # Generated video data JSONs go here
    └── .gitkeep
```

## CRITICAL RULES — READ BEFORE WRITING CODE

### From docs/DEBUGGING_GUIDE.md:
1. **Load .env BEFORE imports** — use the `_load_env()` pattern from `agents/content_researcher/cli.py`
2. **NEVER use `contextlib.suppress`** — always show errors during development
3. **Test with real data** — don't just test with "hello world"
4. **Use `UV_CACHE_DIR=/tmp/uv-cache`** if uv has cache permission issues

### Code quality:
5. **No placeholder code** — every function must work end-to-end
6. **Run `ruff check`** before considering done
7. **Test the full pipeline** — topic in → JSON file out
8. **Print progress** — show what's happening at each step (researching... generating script... saving...)

### Architecture:
9. **Keep it simple** — this is V1 glue code, NOT a framework
10. **No new dependencies** — only use what's already installed (google-genai, httpx)
11. **Don't import Memory Hub** — V1 doesn't need persistent memory
12. **The Gemini prompt for script generation is the most important part** — spend time making it produce good Arabic content

## VALIDATION CHECKLIST
After building, verify:
- [ ] `ruff check pipeline/` passes with 0 errors
- [ ] `uv run python -m pipeline.topic_to_video --topic "AI jobs Saudi Arabia" --lang ar` produces a valid JSON file
- [ ] The JSON file contains valid `VideoData` structure (5-6 scenes, all required fields)
- [ ] The scenes follow the pattern: hook → intro → points → cta
- [ ] Arabic text is natural Gulf dialect, not formal MSA
- [ ] The rendered JSON can be used directly with the Remotion template
- [ ] Run with 3 different topics to verify consistency

## EXAMPLE OUTPUT
For topic "AI jobs in Saudi Arabia 2026", the output JSON should look like:
```json
{
    "id": "fahad-ep-20260316-ai-jobs-ksa",
    "title": "وظائف الذكاء الاصطناعي في السعودية ٢٠٢٦",
    "pillar": "ai",
    "scenes": [
        {
            "type": "hook",
            "emoji": "🤖",
            "headline": "الذكاء الاصطناعي يغير سوق العمل\nفي السعودية — مستعد؟",
            "camera": "zoom",
            "durationInFrames": 90
        },
        {
            "type": "intro",
            "emoji": "💼",
            "headline": "معكم فهد الحربي",
            "body": "خبير مهني — SamimlyCV",
            "camera": "static",
            "durationInFrames": 75
        },
        ...3 more scenes (points/list about the topic)...,
        {
            "type": "cta",
            "emoji": "🚀",
            "headline": "تابعني عشان تعرف أكثر\nعن مستقبل الشغل",
            "body": "SamimlyCV",
            "camera": "zoom",
            "durationInFrames": 90
        }
    ]
}
```

## GIT COMMIT
After all checks pass:
```bash
git add pipeline/ && git commit -m "feat(pipeline): V1 topic-to-video connector" && git push
```
