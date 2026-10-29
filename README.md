# WebPilot

A self-correcting AI agent that completes multi-step web workflows, **verifies every action**, and
**recovers** when websites misbehave. Built on LLM tool use (Google Gemini free tier by default, or
Claude) and Playwright.

## Quick start (free, using Gemini)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium
```
Get a free key at https://aistudio.google.com/apikey, then set it in your terminal:
```bash
export GEMINI_API_KEY=your-key                        # Windows PowerShell: $env:GEMINI_API_KEY="your-key"
webpilot run "Find the cheapest book on the first page and report its title and price" \
  --url https://books.toscrape.com --headed
```
Free tiers have rate limits (WebPilot retries automatically when it hits them); check Google's current limits.

### Using Claude instead (paid)
```bash
export ANTHROPIC_API_KEY=your-key
webpilot run "<goal>" --url <url> --provider anthropic
```
Provider and model can also be set with `WEBPILOT_PROVIDER` and `WEBPILOT_MODEL`.

## How it works
Each cycle: **observe → act → verify → recover**. After every action the `Verifier` compares the
page before and after. Failures are classified; overlays are dismissed, transient errors retried
with exponential backoff, and missing elements are handed back to the model to re-plan.
Every run writes a JSON trace to `runs/`. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Project layout
```
src/webpilot/   agent, llm (Gemini/Claude adapters), tools, verifier, recovery, browser, models, config, cli
tests/          24 unit tests with a fake browser and a scripted LLM (no key needed)
docs/           architecture notes
```

## Development
```bash
pytest          # no browser or API key required
ruff check .
```

## Safety
Run it only against sites you own or have permission to automate. The agent never invents form data,
and it reports failure honestly instead of claiming success.

## License
MIT
