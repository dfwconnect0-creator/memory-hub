"""Content Researcher CLI — interactive REPL backed by Memory Hub."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    """Minimal .env loader — no external dependency needed."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


# Load .env from project root
_load_env(Path(__file__).resolve().parents[2] / ".env")

from agents.content_researcher.agent import ContentResearcherAgent  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="content-researcher",
        description="Content researcher with persistent memory.",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Memory Hub API key (overrides CONTENT_RESEARCHER_API_KEY env var)",
    )
    p.add_argument("--base-url", default="http://localhost:8000", help="Memory Hub base URL")
    p.add_argument("--topic", metavar="TEXT", help="Research a topic and exit")
    p.add_argument("--recall", metavar="QUERY", help="Search memories and exit")
    p.add_argument("--summarize", metavar="QUERY", help="Summarize findings for a topic and exit")
    return p


def run_repl(agent: ContentResearcherAgent) -> None:
    print(
        "Content Researcher ready. Commands: /research <topic>, /recall <query>, "
        "or just ask a question. Ctrl+C or 'quit' to exit.\n"
    )
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break
        if user_input.startswith("/research "):
            topic = user_input[len("/research "):].strip()
            findings = agent.research(topic)
            if findings:
                for f in findings:
                    print(f"- {f}")
            else:
                print("No findings returned.")
        elif user_input.startswith("/recall "):
            query = user_input[len("/recall "):].strip()
            results = agent.recall(query)
            if results:
                for r in results:
                    print(f"- {r.get('content', r)}")
            else:
                print("No memories found.")
        else:
            response = agent.chat(user_input)
            print(f"{response}\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    agent = ContentResearcherAgent(api_key=args.api_key, base_url=args.base_url)

    if args.topic:
        findings = agent.research(args.topic)
        for f in findings:
            print(f"- {f}")
        return 0

    if args.recall:
        results = agent.recall(args.recall)
        if results:
            for r in results:
                print(f"- {r.get('content', r)}")
        else:
            print("No memories found.")
        return 0

    if args.summarize:
        summary = agent.summarize(args.summarize)
        print(summary or "No summary available.")
        return 0

    run_repl(agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
