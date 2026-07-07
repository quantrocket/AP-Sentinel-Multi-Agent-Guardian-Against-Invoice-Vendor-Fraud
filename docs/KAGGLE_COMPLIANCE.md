# Vibecoding Agents Capstone — Compliance Checklist

Mapped against the Official Competition Rules
(`kaggle.com/competitions/vibecoding-agents-capstone-project/rules`).

| Requirement | How this submission complies |
|---|---|
| One submission per team (Hackathon rule, Sec 1.2) | Submitting solo as a single Kaggle account/team; no other entry filed under this account. |
| Track selection (Sec "Tracks and Awards") | Submitted under **Agents for Business** (B2B AP fraud/vendor-risk is an enterprise finance-ops use case). |
| Winner License: CC-BY 4.0 (Sec 1.6, 2.5) | Repository carries a `LICENSE` file (CC-BY 4.0); no third-party code is bundled that carries an incompatible license. |
| External Data & Tools — Reasonableness Standard (Sec 2.6) | The entire pipeline — Google ADK, Gemini (2.5 Flash + 2.5 Pro), Chroma, SQLite, FastAPI, Streamlit — is free-tier/open-source and equally accessible to all participants. **There is no second model vendor anywhere in this submission**, so there's no cost-reasonableness question to resolve: everyone can reproduce the full pipeline, including the Critic agent's independent re-check, with a single `GOOGLE_API_KEY`. |
| No hand-labeling of test data (Sec 3.4.b) | N/A — no shared competition test/validation dataset; all seed data (`data/init_db.py`, `eval/test_cases.json`) is self-authored synthetic data, clearly labeled as such. |
| Public code sharing (Sec 3.6.b) | Repository is public on GitHub, licensed OSI-approved (CC-BY 4.0 / MIT for code), no restriction on commercial use. |
| Winner's Obligations — reproducibility (Sec 2.8) | `README.md` gives full setup/run instructions; `deploy/` includes Dockerfile + docker-compose for one-command reproduction; `eval/run_eval.py` reproduces the reported precision/recall/latency numbers exactly. |
| Original work warranty (Sec 3.14.a) | All code, prompts, sample data, and documents in this repo are original for this submission; no proprietary or copyrighted third-party content is reproduced. |
| Eligibility (Sec 3.1) | Individual entrant, registered Kaggle account, not affiliated with Google/Kaggle as an employee/contractor. |
| Submission format (Overview page) | Kaggle Writeup (≤2500 words, see `docs/WRITEUP_OUTLINE.md`) + cover image + ≤5-min YouTube video + public GitHub repo link with setup instructions. |
| ≥3 required course concepts (Evaluation section) | Six of six are demonstrated: **Multi-agent system (ADK)** — `agents/agents.py` (Code); **MCP Server** — `tools/mcp_server.py` (Code); **Security features** — `tools/function_tools.py` PII redaction/injection scanning + `agents/critic_agent.py` (Code); **Agent skills** — the deterministic `risk_score`/`generate_report` tools + eval harness (Code); **Deployability** — `deploy/` Dockerfile, docker-compose, k8s manifests (Video); **Antigravity** — `AGENTS.md` + `docs/ANTIGRAVITY.md` MCP hookup, demonstrated live in the video (Video). |

## Course-concept-to-evidence map

| Key Concept | Required location | Evidence in this repo |
|---|---|---|
| Agent / Multi-agent system (ADK) | Code | `agents/agents.py` (5-agent `SequentialAgent` pipeline) + `agents/critic_agent.py` (7th, independent agent) |
| MCP Server | Code | `tools/mcp_server.py` |
| Antigravity | Video | `AGENTS.md` (project rules Antigravity reads) + `docs/ANTIGRAVITY.md` (MCP config + recorded plan-and-edit walkthrough) |
| Security features | Code or Video | `tools/function_tools.py::redact_pii`/`scan_prompt_injection` (Code) + `agents/critic_agent.py` independent re-check (Code) |
| Deployability | Video | `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/k8s/deployment.yaml`, recorded in video per `docs/PREREQUISITES_AND_RUN.md` |
| Agent skills (e.g., Agents CLI) | Code or Video | Deterministic tool-as-skill pattern: `risk_score`, `generate_report`, `estimate`-style helpers in `tools/function_tools.py`, each callable standalone the way an Agents CLI skill would be |

## Notes on the target technical profile

This project was designed against a benchmark of ~120 comparable capstone
submissions (Finance domain, multi-agent, Google ADK, RAG, MCP, memory,
Chroma/SQLite, FastAPI + Streamlit, Cloud Run/Docker/Kubernetes, eval +
observability + security all present). Two honesty notes worth stating
explicitly in the Writeup, matching what separated the strongest scanned
submissions from the rest:

1. **Kubernetes manifests are included and valid, but the demo deployment
   target is Cloud Run** — cheaper, faster to demo, sufficient for the
   submission's traffic. Say so plainly rather than implying a live GKE
   cluster backs the demo if it doesn't.
2. **The "second opinion" is a structural design choice, not a second
   vendor.** The Critic agent achieves independence through a different
   Gemini checkpoint, an adversarial prompting stance, and re-derivation
   from raw tool outputs — call this out explicitly as the innovation,
   rather than implying multi-vendor model diversity that isn't there.
