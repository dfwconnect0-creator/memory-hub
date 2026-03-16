"""Career Coach CLI — interactive REPL backed by Memory Hub."""
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

from agents.career_coach.agent import CareerCoachAgent  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="career-coach",
        description="Interactive career coach with persistent memory.",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Memory Hub API key (overrides CAREER_COACH_API_KEY env var)",
    )
    p.add_argument("--base-url", default="http://localhost:8000", help="Memory Hub base URL")
    p.add_argument("--remember", metavar="TEXT", help="Store a memory and exit")
    p.add_argument("--recall", metavar="QUERY", help="Search memories and exit")
    return p


def run_repl(agent: CareerCoachAgent) -> None:
    print("Career Coach ready. Type your question or career info. Ctrl+C or 'quit' to exit.\n")
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
        response = agent.chat(user_input)
        print(f"{response}\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    agent = CareerCoachAgent(api_key=args.api_key, base_url=args.base_url)

    if args.remember:
        result = agent.remember(args.remember)
        print(f"Stored: {result}")
        return 0

    if args.recall:
        results = agent.recall(args.recall)
        if results:
            for r in results:
                print(f"- {r.get('content', r)}")
        else:
            print("No memories found.")
        return 0

    run_repl(agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
