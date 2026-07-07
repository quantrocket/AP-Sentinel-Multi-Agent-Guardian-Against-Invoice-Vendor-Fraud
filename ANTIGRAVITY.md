# Google Antigravity — how AP Sentinel uses it, and how it's demonstrated

Per the capstone's Evaluation table, **Antigravity is a "Video" concept** —
it's judged from the demonstration, not required in the submitted code.
This doc covers both: the concrete Antigravity artifacts now shipped in the
repo (`AGENTS.md`, the MCP hookup below), and exactly what to record for the
5-minute video so the concept is unambiguous to a judge who skims the repo
in one pass.

## 1. What Antigravity is (one paragraph, for the writeup)
Google Antigravity is Google's agent-first development platform: a
standalone **Antigravity 2.0** app for orchestrating multiple autonomous
coding agents, plus the more familiar **Antigravity IDE** (VS Code-based,
recommended for day-to-day work), both sharing one agent harness, one
`AGENTS.md` project-rules file, and one MCP server configuration. Agents
work from natural-language objectives, produce **Artifacts** (implementation
plans, test results, walkthrough recordings) for human review, and can be
given tool access via MCP — which is exactly the same protocol AP Sentinel
already uses for its Critic agent (`tools/mcp_server.py`).

## 2. What's already wired up in this repo
- **`AGENTS.md`** (repo root) — the project-rules file Antigravity reads
  automatically: domain boundaries (which files an agent may touch),
  the non-negotiable security rules, and the planning-gate requirement.
  This is the Antigravity-native equivalent of the `.agents/CONTEXT.md`
  pattern used by reference capstone projects, expressed in Antigravity's
  own convention.
- **MCP interoperability** — `tools/mcp_server.py` was *already* built to be
  MCP-native so any MCP-compatible IDE (Antigravity, Gemini CLI, Cursor)
  could attach to it. Antigravity is simply one more client of that same
  server; no new code was needed, only the config below.

## 3. Attaching Antigravity to AP Sentinel's tools (do this once, locally)

1. Start the server: `python tools/mcp_server.py` (SSE on `:8765`), or run
   it stdio-style via `python -m tools.mcp_server` if your Antigravity
   client prefers a `command`/`args` entry.
2. In **Antigravity IDE**: open the agent panel's `...` dropdown → **Manage
   MCP Servers** → **View raw config**. This opens
   `~/.gemini/config/mcp_config.json` (shared across Antigravity 2.0, IDE,
   and CLI). Add:

```json
{
  "mcpServers": {
    "ap-sentinel-tools": {
      "command": "python",
      "args": ["-m", "tools.mcp_server"],
      "cwd": "/absolute/path/to/ap-sentinel",
      "env": { "GOOGLE_API_KEY": "YOUR_ACTUAL_API_KEY" }
    }
  }
}
```

   (If you'd rather point at the already-running SSE server instead of
   letting Antigravity spawn its own process, use `"serverUrl":
   "http://localhost:8765"` instead of `command`/`args`.)

3. Save, then restart Antigravity so the new server loads (MCP config
   changes require a restart, same as any Antigravity security/config
   change).
4. In the agent panel, `@`-mention `ap-sentinel-tools` or just ask: *"Using
   ap-sentinel-tools, look up the vendor Nova Consulting Group and check
   for bank-change history."* Antigravity will ask for one-time approval
   before the first tool call — approve it — then show the tool result
   inline.

## 4. What to actually record for the video (≤ ~45 seconds of the 5 min)
1. Show `AGENTS.md` open in Antigravity IDE for one second — establishes
   "this project has Antigravity project rules," not a generic empty repo.
2. Show the MCP Store / raw config with `ap-sentinel-tools` listed as
   **installed**.
3. Give Antigravity a real objective in **Planning mode**, e.g.: *"Add a
   new risk signal: flag invoices where the amount is >3x the vendor's
   historical average, wire it into risk_score, and add a matching eval
   case."* Let it produce an implementation plan (an Artifact) — pause on
   that screen for a beat, it's the "why agents, not autocomplete" proof
   point judges are told to look for.
4. Approve the plan, let it edit `tools/function_tools.py` +
   `eval/test_cases.json`, then run `python eval/run_eval.py` from the
   Antigravity terminal to show the new case passing.
5. Cut back to the pipeline itself (the FastAPI/Streamlit demo) to close
   the loop: natural-language change → agent-authored code → passing eval →
   working product.

## 5. Honesty notes for the writeup (say these explicitly)
- Antigravity was used as a **development-time agent**, not a runtime
  component of AP Sentinel itself — AP Sentinel's own 7 agents run on
  Google ADK + Gemini directly, independent of Antigravity. Don't blur
  these into one thing; a judge can tell the difference between "we used
  an agentic IDE to build this" and "our product is built on Antigravity."
- The MCP server AP Sentinel exposes was designed for the Critic agent's
  own use first; Antigravity (or any other MCP client) attaching to it is
  a genuine but secondary interoperability win, not a retrofit built only
  to check this box.
