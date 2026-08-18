"""The one-command entrypoint: python -m app.cli run --topic "AI agents for SMBs"

Writes outputs/<topic-slug>/{candidates.json, analysis/*.json, memos/*.html}.
"""

import argparse
import asyncio
import logging
import sys

from app.pipeline import run_pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Sourcing -> Analysis -> Recommendation pipeline for VC deal triage.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full pipeline for a topic.")
    run.add_argument(
        "--topic", required=True, help='Seed topic, e.g. "AI agents for SMBs"'
    )
    run.add_argument(
        "--limit", type=int, default=15, help="Max candidates to carry through (default 15)"
    )
    run.add_argument(
        "--skip-sourcing",
        action="store_true",
        help="Reuse committed candidates.json instead of re-hitting sourcing APIs.",
    )
    run.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Reuse committed analysis/*.json instead of re-calling OpenAI "
        "(just re-renders memos).",
    )
    run.add_argument(
        "-v", "--verbose", action="store_true", help="Debug-level logging."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    result = asyncio.run(
        run_pipeline(
            topic=args.topic,
            limit=args.limit,
            skip_sourcing=args.skip_sourcing,
            skip_analysis=args.skip_analysis,
        )
    )

    if not result.analyses:
        print(f"\nNo memos produced for {args.topic!r} — check the warnings above.")
        return 1

    print(f"\n{len(result.analyses)} memos written to {result.memos_dir}/")
    print(f"Start here: {result.memos_dir}/index.html\n")
    ranked = sorted(result.analyses, key=lambda a: a.score, reverse=True)
    for a in ranked:
        print(f"  {a.score:>5.1f}  {a.call:<15}  {a.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
