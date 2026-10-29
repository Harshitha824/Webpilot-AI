"""Command-line interface: `webpilot run "<goal>" --url <start-url>`."""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from .agent import Agent
from .browser import PlaywrightBrowser
from .config import Settings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="webpilot", description="Self-correcting web agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Run a goal")
    r.add_argument("goal")
    r.add_argument("--url", help="Start URL")
    r.add_argument("--headed", action="store_true", help="Show the browser window")
    r.add_argument("--max-steps", type=int)
    r.add_argument("--provider", choices=["gemini", "anthropic"], help="LLM provider (default: gemini)")
    r.add_argument("--model", help="Override the model name")
    args = p.parse_args(argv)

    settings = Settings.from_env()
    if args.headed:
        settings = replace(settings, headless=False)
    if args.max_steps:
        settings = replace(settings, max_steps=args.max_steps)

    if args.provider:
        settings = replace(settings, provider=args.provider)
    if args.model:
        settings = replace(settings, model=args.model)

    browser = PlaywrightBrowser(headless=settings.headless)
    browser.start()
    try:
        report = Agent(browser, settings).run(args.goal, args.url)
    finally:
        browser.close()
    status = "SUCCESS" if report.success else "FAILED"
    print(f"[{status}] steps={report.steps} failures={report.failures} recoveries={report.recoveries}")
    print(report.summary)
    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
