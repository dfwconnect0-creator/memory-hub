---
description: Guidelines for planning and executing multi-phase projects with AI agents
---

# Superpowers Workflow — Planning & Execution Guide

> Use this guide when starting any new conversation that involves planning or building software.
> Last updated: 2026-03-16 | Proven on: Memory Hub v5 (27 files, 124 tests, 4.5 hours)

---

## 1. Agent Roles — Who Does What

| Agent | Role | Strengths | Do NOT |
|:---|:---|:---|:---|
| **Antigravity (Opus)** | Architect, Planner, Reviewer, Debugger | Big-picture thinking, spec writing, code review, troubleshooting | Write implementation code directly |
| **Claude CLI (Sonnet)** | Builder, Implementer, Tester | TDD, fast coding, consistent patterns, running tests | Make architecture decisions, skip tests |
| **OpenCode CLI** | Repetitive tasks | Boilerplate, file creation, renaming | Complex multi-file refactoring |
| **Mohamed (User)** | Decision maker, Executor | Final approval, running commands, choosing direction | — |

### Key Rule: Antigravity plans, Claude CLI builds, Antigravity reviews.

---

## 2. Planning Phase (Antigravity)

When the user asks to plan or start a new feature:

### Step 1: Understand
- Ask clarifying questions before writing any plan
- Read existing project files first (README, ARCHITECTURE.md, plans/)
- Check what's already built to avoid duplication

### Step 2: Specify
- Write a clear specification with:
  - **Goal**: What are we building and why
  - **Scope**: What's included and what's NOT
  - **Inputs/Outputs**: Data flow
  - **Success Criteria**: How we know it's done

### Step 3: Plan in Phases
- Break work into **small phases** (30-60 min each)
- Each phase must be **independently testable**
- Define **file-level tasks** for each phase
- Include **test expectations** per phase

### Step 4: Write Claude CLI Prompts
- Generate a **single-paragraph** prompt for each phase
- The prompt must contain everything Claude CLI needs to execute
- Follow the prompting rules below

### Step 5: Wait for User Approval
- Present the plan to the user
- Do NOT start execution until the user says "go" or "approved"

---

## 3. Execution Phase (Claude CLI)

### Prompting Rules for Claude CLI

These rules prevent security warnings and ensure clean execution:

1. **Single paragraph** — no newlines in the prompt
2. **No `#` characters** — causes zsh warnings
3. **No numbered lists** — use commas to separate items
4. **Include full file paths** — Claude CLI needs explicit paths
5. **Include test expectations** — "Write tests first, expect N tests to pass"
6. **Include the methodology** — "Use TDD: write failing tests first, then implement, then verify with pytest"

### Example Claude CLI Prompt (Good)

```
Execute Phase 3 from plans/multi_agent_memory_plan_v5.md. Build the REST API using FastAPI with an app factory pattern in src/memory_hub/app.py. Create routes in src/memory_hub/transport/rest/ for memory (POST add, POST search, POST batch, GET export), health (GET), and agents (GET list). Add dependency injection in deps.py. Write integration tests first in tests/integration/test_memory_api.py, then implement. Run uv run pytest after each file to verify. Target: all tests pass, zero ruff errors.
```

### Example Claude CLI Prompt (Bad — Don't Do This)

```
# Phase 3 - REST API
1. Build the app factory
2. Create routes:
   - memory routes
   - health routes
3. Write tests
```

(This has newlines, `#`, and numbered lists — Claude CLI will show security warnings)

---

## 4. Review Phase (Antigravity)

After Claude CLI finishes a phase:

1. **Check test results** — all must pass
2. **Check lint** — `uv run ruff check src/`
3. **Check types** — `uv run mypy src/ --strict` (if configured)
4. **Review architecture** — does it match the plan?
5. **Commit** — clean conventional commit message

---

## 5. Development Standards

### TDD Flow (RED → GREEN → REFACTOR)
1. Write failing tests first (RED)
2. Implement until tests pass (GREEN)
3. Clean up code without changing behavior (REFACTOR)

### Commit Convention
```
feat(scope): description    — new features
fix(scope): description     — bug fixes
docs: description           — documentation only
sec: description             — security fixes
chore: description          — tooling, deps
```

### Shell Command Rules
- Always prefix with `cd ~/project-dir &&`
- Quote packages with brackets: `uv add 'uvicorn[standard]'`
- Use `kill $(lsof -ti:PORT) 2>/dev/null;` to free ports
- Never put `#` comments in multi-line pasted commands

### Package Manager
- Always use **uv**, never pip
- `uv add` to install, `uv run` to execute, `uv sync` to restore

### Security
- `.env` must be in `.gitignore` (never commit secrets)
- Rotate keys if they ever touch git history
- API keys in `.env`, validated via middleware

---

## 6. Git Safety Rules

> ⚠️ **Lesson learned (2026-03-15):** `.env` with real API keys was committed to git.
> Keys had to be rotated and `.env` removed with `git rm --cached`.
> This section exists to prevent that from ever happening again.

### Before EVERY `git add`

1. **Check `.gitignore` includes these patterns:**
   ```
   .env
   .env.*
   .coverage
   *.key
   *.pem
   ```

2. **Run this check before committing:**
   ```bash
   git diff --cached --name-only | grep -E '\.env|\.key|\.pem|secret|password'
   ```
   If anything shows up — **STOP and unstage it.**

3. **Never use `git add -A` blindly.** Prefer explicit file lists:
   ```bash
   # RISKY — stages everything including secrets
   git add -A

   # SAFER — stage specific files
   git add src/ tests/ docs/
   ```

4. **If a secret IS committed, do ALL of these:**
   ```bash
   git rm --cached .env
   git commit -m "sec: remove secrets from tracking"
   ```
   Then **rotate every key** that was exposed — even in a private repo.

### Commit Message Convention

```
feat(scope): description    — new features
fix(scope): description     — bug fixes
docs: description           — documentation only
sec: description            — security fixes
chore: description          — tooling, deps
```

### Pre-Push Checklist

Before running `git push`, verify:
- [ ] `.env` is NOT in `git status` output
- [ ] No API keys in any staged file
- [ ] `.gitignore` is up to date
- [ ] Tests pass (`uv run pytest`)
- [ ] Lint clean (`uv run ruff check src/`)

---

## 7. Project Context Files

When starting a new conversation, read these files first:

| File | Purpose |
|:---|:---|
| `plans/roadmap_v5_post_mvp.md` | What to build next |
| `docs/ARCHITECTURE.md` | System design, patterns, directory structure |
| `docs/TROUBLESHOOTING.md` | Known issues and fixes (TSG-001 through TSG-015) |
| `docs/QUICKSTART.md` | How to run the project |
| `docs/CHANGELOG.md` | What's been built so far |
| `config/agents.yaml` | Agent registry (9 agents, 4 projects) |

---

## 7. Starter Prompt Template

When opening a new conversation for the next phase:

```
Read ~/cognee-mcp/plans/roadmap_v5_post_mvp.md and ~/cognee-mcp/docs/ARCHITECTURE.md.

We completed the Memory Hub v5 MVP. I want to work on [TRACK/TASK FROM ROADMAP].

Plan it first — give me the spec, phased breakdown, and Claude CLI prompts.
Do NOT start coding. Wait for my approval before execution.
```
