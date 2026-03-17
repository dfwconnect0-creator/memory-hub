"""CogneeAdapter: bridges Memory Hub to local Cognee knowledge graph.

Uses subprocess to call the local Cognee installation, keeping
Memory Hub's venv isolated from Cognee's dependencies.

Cognee installation: ~/Desktop/install_link/cognee-official/cognee-mcp/
Cognee venv:         ~/Desktop/install_link/cognee-official/cognee-mcp/.venv/
Cognee env:          ~/Desktop/install_link/cognee/.env

Storage layers used by Cognee:
  - Neo4j + APOC  (knowledge graph — entities & relationships)
  - LanceDB       (vector embeddings — semantic search)
  - SQLite         (metadata — pipeline state)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from memory_hub.config import Settings
from memory_hub.models.domain import MemoryCategory, MemoryEntry, SearchResult

logger = logging.getLogger(__name__)

# Cognee's Python binary in its own venv
_DEFAULT_COGNEE_PYTHON = (
    Path.home()
    / "Desktop/install_link/cognee-official/cognee-mcp/.venv/bin/python"
)

# Cognee's .env path (contains Neo4j, Ollama, LanceDB config)
_DEFAULT_COGNEE_ENV = Path.home() / "Desktop/install_link/cognee/.env"


def _build_cognee_script(action: str) -> str:
    """Build a self-contained Python script that runs a Cognee operation.

    The script loads Cognee's .env, runs the requested action, and prints
    JSON output to stdout. This keeps Memory Hub's process clean.
    """
    return f'''
import asyncio, json, os, sys
from pathlib import Path

# Load Cognee's .env
env_path = os.environ.get("COGNEE_ENV_PATH", "")
if env_path and Path(env_path).exists():
    for line in Path(env_path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)

# Suppress Cognee's noisy startup logging
os.environ.setdefault("COGNEE_LOG_LEVEL", "ERROR")

import cognee

params = json.loads(os.environ.get("COGNEE_PARAMS", "{{}}"))

async def run():
    try:
        action = "{action}"

        if action == "add":
            content = params["content"]
            # Wrap with personal framing for mem0 fact extraction
            wrapped = f"User researched and found: {{content}}"
            await cognee.add(wrapped)
            print(json.dumps({{"status": "ok", "action": "add"}}))

        elif action == "cognify":
            await cognee.cognify()
            print(json.dumps({{"status": "ok", "action": "cognify"}}))

        elif action == "search":
            from cognee.api.v1.search import SearchType
            query = params["query"]
            search_type = params.get("search_type", "CHUNKS")
            limit = params.get("limit", 10)

            st = getattr(SearchType, search_type, SearchType.CHUNKS)
            results = await cognee.search(query, query_type=st)

            # Normalize results to a serializable format
            out = []
            if isinstance(results, list):
                for r in results[:limit]:
                    if isinstance(r, dict):
                        out.append(r)
                    elif hasattr(r, "dict"):
                        out.append(r.dict())
                    else:
                        out.append({{"content": str(r), "score": 0.0}})
            elif isinstance(results, str):
                out.append({{"content": results, "score": 1.0}})

            print(json.dumps({{"status": "ok", "results": out}}))

        elif action == "list_data":
            datasets = await cognee.datasets.list_datasets()
            items = []
            for ds in (datasets or []):
                ds_dict = ds.dict() if hasattr(ds, "dict") else {{"id": str(ds)}}
                items.append(ds_dict)
            print(json.dumps({{"status": "ok", "datasets": items}}))

        elif action == "delete":
            data_id = params.get("data_id")
            if data_id:
                await cognee.prune.prune_data()
            print(json.dumps({{"status": "ok", "action": "delete"}}))

        elif action == "status":
            print(json.dumps({{"status": "ok", "cognee_version": cognee.__version__}}))

        else:
            print(json.dumps({{"status": "error", "message": f"Unknown action: {{action}}"}}))

    except Exception as e:
        print(json.dumps({{"status": "error", "message": str(e)}}), file=sys.stderr)
        sys.exit(1)

asyncio.run(run())
'''


class CogneeAdapter:
    """Storage backend that delegates to the local Cognee installation.

    Implements MemoryStore Protocol via subprocess calls to Cognee's venv,
    keeping Memory Hub's dependencies isolated.
    """

    def __init__(self, settings: Settings) -> None:
        self._python = Path(
            getattr(settings, "COGNEE_PYTHON_PATH", str(_DEFAULT_COGNEE_PYTHON))
        )
        self._env_path = Path(
            getattr(settings, "COGNEE_ENV_PATH", str(_DEFAULT_COGNEE_ENV))
        )
        self._search_type = getattr(settings, "COGNEE_SEARCH_TYPE", "CHUNKS")
        self._auto_cognify = getattr(settings, "COGNEE_AUTO_COGNIFY", True)

        if not self._python.exists():
            logger.warning(
                "Cognee Python not found at %s — adapter will be non-functional",
                self._python,
            )

    async def _run_cognee(self, action: str, **kwargs: Any) -> dict[str, Any]:
        """Run a Cognee operation in a subprocess and return parsed JSON."""
        script = _build_cognee_script(action)

        env = {
            **dict(__import__("os").environ),
            "COGNEE_ENV_PATH": str(self._env_path),
            "COGNEE_PARAMS": json.dumps(kwargs),
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self._python),
                "-c",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=120  # 2 min timeout for cognify
            )

            if proc.returncode != 0:
                err_msg = stderr.decode().strip() if stderr else "Unknown error"
                logger.error("Cognee %s failed: %s", action, err_msg)
                return {"status": "error", "message": err_msg}

            output = stdout.decode().strip()
            # Find the last JSON line (Cognee may print warnings before it)
            for line in reversed(output.splitlines()):
                line = line.strip()
                if line.startswith("{"):
                    result: dict[str, Any] = json.loads(line)
                    return result

            return {"status": "error", "message": f"No JSON output: {output[:200]}"}

        except asyncio.TimeoutError:
            logger.error("Cognee %s timed out (120s)", action)
            return {"status": "error", "message": f"Cognee {action} timed out"}
        except Exception as e:
            logger.error("Cognee %s error: %s", action, e)
            return {"status": "error", "message": str(e)}

    async def add(self, entry: MemoryEntry) -> str:
        """Ingest content into Cognee's knowledge graph."""
        result = await self._run_cognee("add", content=entry.content)

        if result.get("status") != "ok":
            logger.warning("Cognee add failed: %s", result.get("message"))
            return ""

        # Fire cognify in background if auto-cognify is enabled
        if self._auto_cognify:
            asyncio.create_task(self._background_cognify())

        # Cognee doesn't return IDs from add — generate a tracking ID
        return f"cognee-{uuid.uuid4().hex[:12]}"

    async def _background_cognify(self) -> None:
        """Run cognify in background — builds the knowledge graph."""
        try:
            result = await self._run_cognee("cognify")
            if result.get("status") == "ok":
                logger.info("Cognee cognify completed successfully")
            else:
                logger.warning("Cognee cognify issue: %s", result.get("message"))
        except Exception as e:
            logger.error("Background cognify failed: %s", e)

    async def search(
        self,
        query: str,
        project: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search Cognee's knowledge graph."""
        result = await self._run_cognee(
            "search",
            query=query,
            search_type=self._search_type,
            limit=limit,
        )

        if result.get("status") != "ok":
            logger.warning("Cognee search failed: %s", result.get("message"))
            return []

        raw_results = result.get("results", [])
        search_results: list[SearchResult] = []

        for i, item in enumerate(raw_results[:limit]):
            content = ""
            score = 0.0

            if isinstance(item, dict):
                content = item.get("content", item.get("text", str(item)))
                score = float(item.get("score", 0.5))
            else:
                content = str(item)
                score = 0.5

            search_results.append(
                SearchResult(
                    id=f"cognee-{i}",
                    content=content,
                    project=project,
                    agent_id=agent_id or "",
                    score=score,
                    category=MemoryCategory.GENERAL,
                    metadata={"source": "cognee", "search_type": self._search_type},
                )
            )

        return search_results

    async def delete(self, memory_id: str) -> bool:
        """Delete from Cognee (limited — Cognee uses prune for bulk deletion)."""
        result = await self._run_cognee("delete", data_id=memory_id)
        return result.get("status") == "ok"

    async def export(self, project: str) -> list[MemoryEntry]:
        """Export data from Cognee (returns dataset list)."""
        result = await self._run_cognee("list_data")

        if result.get("status") != "ok":
            return []

        entries: list[MemoryEntry] = []
        for ds in result.get("datasets", []):
            entries.append(
                MemoryEntry(
                    content=str(ds),
                    project=project,
                    agent_id="cognee",
                    category=MemoryCategory.GENERAL,
                    metadata={"source": "cognee"},
                )
            )
        return entries

    async def cognify(self) -> dict[str, Any]:
        """Explicitly trigger Cognee's cognify pipeline."""
        return await self._run_cognee("cognify")

    async def status(self) -> dict[str, Any]:
        """Check if Cognee is reachable and working."""
        return await self._run_cognee("status")
