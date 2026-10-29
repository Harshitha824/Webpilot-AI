# Architecture

```
CLI ──► Agent loop ──► LLM adapter ──► Gemini or Claude (tool use)
            │
            ▼
      ToolExecutor ──► Browser (Playwright)
        │      │
        │      └─► Verifier   postcondition check after every action
        └────────► Recovery   classify failure → fix → retry
```

| Module | Responsibility |
|---|---|
| `agent.py` | Plan-act loop, step budget, run trace saved to `runs/` |
| `tools.py` | Tool schemas and the act → verify → recover cycle |
| `verifier.py` | Compares before/after observations; never trusts an action blindly |
| `recovery.py` | Classifies failures (overlay, transient, missing) and applies fixes |
| `llm.py` | `LLM` interface with Gemini and Claude adapters; swap providers without touching the agent |
| `browser.py` | `Browser` protocol and Playwright implementation |
| `models.py` | Dataclasses shared by every layer |

## Design principles
1. **Verify, don't assume.** Each click, type and navigation is checked against the new page state.
2. **Recover locally, re-plan globally.** Mechanical failures (overlays, 5xx) are fixed in code.
   Semantic failures (renamed or missing elements) go back to the model with fresh observations.
3. **Bounded autonomy.** Step limit, retry limit, and an honest `finish(success=false)` path.
4. **Testable by design.** The agent depends on a `Browser` protocol and an injectable LLM client.
