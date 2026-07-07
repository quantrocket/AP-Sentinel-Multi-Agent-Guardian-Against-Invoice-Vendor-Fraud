# AGENTS.md — Antigravity project rules for AP Sentinel

This file is read by Google Antigravity (Agent Manager, Antigravity IDE, and
Antigravity CLI) whenever an agent works inside this repo. It is the
"paved road" contract: what agents are allowed to touch, what they must
verify before touching it, and which MCP tools they should reach for.

## What this project is
AP Sentinel is a 7-agent Google ADK + Gemini pipeline that screens AP
invoices for BEC/vendor-impersonation fraud. See `README.md` and
`docs/ARCHITECTURE.md` for the full picture before making changes.

## Environment
- Python 3.11+, dependencies pinned in `requirements.txt`.
- Single credential: `GOOGLE_API_KEY` (Google AI Studio). Never hardcode it —
  read it from the environment (`.env`, loaded via `python-dotenv`).
- No second model vendor is ever to be added — this keeps the submission
  reproducible on one free-tier key (see `docs/KAGGLE_COMPLIANCE.md`).

## Domain boundaries (which agent may touch which files)
| Area | Owner | Antigravity should NOT... |
|---|---|---|
| `agents/agents.py`, `agents/critic_agent.py` | Pipeline/agent logic | ...change agent instructions without updating `eval/test_cases.json` expectations to match |
| `tools/function_tools.py`, `tools/mcp_server.py` | Tool + MCP surface | ...add a tool here without also registering it in `mcp_server.py` if it should be externally reachable |
| `api/main.py` | Orchestration/REST layer | ...bypass the deterministic `risk_score` step or call the Critic agent outside the BLOCK-tier gate |
| `rag/`, `data/` | Knowledge base + seed data | ...commit real/production vendor data; only synthetic seed data belongs here |
| `eval/` | Regression harness | ...delete or loosen a test case to make a change "pass" |
| `deploy/` | Container/K8s manifests | ...point the demo config at anything other than Cloud Run without flagging it in `docs/KAGGLE_COMPLIANCE.md` |

## Non-negotiable rules
1. **Security before LLM judgement.** `scan_prompt_injection` and `redact_pii`
   must run before any free-text field is shown to an LLM agent or logged.
2. **No secrets in code.** `GOOGLE_API_KEY` and any future credential must
   come from the environment. Flag (don't silently fix) any hardcoded key
   an agent encounters.
3. **The Critic agent (`agents/critic_agent.py`) only runs on BLOCK-tier
   cases.** Don't wire it into the main `SequentialAgent` — it's invoked
   imperatively from `api/main.py` on purpose (cost + latency).
4. **Every new tool is a FunctionTool AND, if it should be reachable
   externally, an MCP tool.** Keep `agents/agents.py` and
   `tools/mcp_server.py` in sync.
5. **Every behavior change needs an eval update.** Add/adjust a case in
   `eval/test_cases.json` alongside any change to `risk_score` weights or
   agent instructions, then re-run `python eval/run_eval.py`.

## Planning gate
Before an agent proposes an implementation plan for a change, the plan must
include a **Security Boundaries** note: which of (prompt injection, PII
exposure, sanctioned-vendor bypass, bulk/first-payment risk) the change
could affect, and how the change keeps them contained.

## MCP tools available to agents in this project
`tools/mcp_server.py` exposes `vendor_lookup`, `bank_change_lookup`,
`sanctions_check`, `retrieve_policy`, and `risk_score` over MCP (stdio via
`python -m tools.mcp_server`, or SSE on :8765). Register it in Antigravity
via the IDE's MCP Store → "Manage MCP Servers" → "View raw config", or by
editing `~/.gemini/config/mcp_config.json` directly — see
`docs/ANTIGRAVITY.md` for the exact JSON block and screenshots checklist.

## Preferred workflow inside Antigravity
1. Open this repo as an Antigravity **Project** (Add Folder → this repo).
2. Use **Planning mode** for anything touching `agents/`, `api/main.py`, or
   `tools/function_tools.py` — review the plan before the agent writes code.
3. Use **Fast mode** only for docs/formatting/test-data edits.
4. Keep the AP Sentinel MCP server attached (see above) so an agent working
   in Antigravity can query the same fraud-signal tools the pipeline uses,
   instead of guessing at vendor/risk data.
5. Save the Antigravity **Artifact** (implementation plan + walkthrough
   recording) for any non-trivial change — these are the same artifacts
   referenced in the capstone video (see `docs/ANTIGRAVITY.md`).
