[README.md](https://github.com/user-attachments/files/29729062/README.md)
# AP Sentinel — Multi-Agent Accounts-Payable Fraud & Vendor-Risk Guardian

**Track:** Agents for Business
**Domain:** Finance (B2B Accounts Payable / Vendor Fraud)
**Stack:** 100% Google — Google ADK, Gemini (via Vertex AI / Google AI Studio), Google-native tooling only. No third-party model providers, no AWS/Azure.

## 1. Problem Statement

Business Email Compromise (BEC) and vendor-impersonation invoice fraud cost
organizations billions annually (FBI IC3 consistently ranks BEC as the
costliest cybercrime category). The typical attack: a fraudster impersonates
a known vendor, submits a legitimate-looking invoice, and quietly changes the
bank routing details. Traditional AP controls (manual 3-way match, static
vendor allow-lists) catch obvious duplicates but miss socially-engineered,
first-time-look-legitimate changes — because the fraud signal isn't in the
invoice math, it's in the *behavioral and contextual* deviation from a
vendor's known history.

Existing anti-fraud tooling in this space is either (a) rules-based OCR/3-way
match systems with high false-negative rates on novel scams, or (b) generic
LLM chatbots with no persistent vendor memory, no retrieval over policy/playbook
documents, and no auditable decision trail — which makes them unusable in a
regulated finance workflow that needs explainability and human sign-off.

## 2. Proposed Solution

A 7-agent system, orchestrated with **Google ADK** and running entirely on
**Gemini** models, that ingests an incoming invoice + supporting email
thread, reconstructs vendor history from a vector-backed knowledge base
(RAG), cross-checks banking/sanctions details against verification tools,
scores risk, and — for the highest-stakes decisions only — runs an
**independent Gemini-2.5-Pro Critic pass** before recommending ALLOW / HOLD /
BLOCK to a human approver.

The key innovation is *how* that Critic pass achieves independence without
leaving the Google ecosystem: it uses a different model checkpoint
(2.5-Pro vs. the pipeline's 2.5-Flash), an adversarial "argue the false-positive
case first" prompting stance, and re-derives its judgement from the raw tool
outputs rather than trusting the pipeline's narrative summary (see
`agents/critic_agent.py` for the full rationale). This keeps the entire
submission reproducible with a single `GOOGLE_API_KEY` — no second vendor's
billing account required to run the complete pipeline, which matters both
for grader reproducibility and for the competition's cost-reasonableness
rules (see `docs/KAGGLE_COMPLIANCE.md`).

## 3. Why Agents (not a single LLM call)?

The task decomposes naturally into specialized, independently-testable
responsibilities (intake/OCR, vendor history retrieval, external verification,
risk scoring, compliance/security, independent critique) — each with its own
tools, prompts, and failure modes. A single monolithic prompt cannot cleanly
separate "extract facts" from "judge risk" from "enforce policy," can't
parallelize the independent verification calls, and can't give an auditable
per-step trace, which finance compliance requires.

See `docs/ARCHITECTURE.md` for diagrams and `docs/KAGGLE_COMPLIANCE.md` for
how this submission complies with the Vibecoding Agents Capstone rules.

## 4. Repo Map

```
agents/     Google ADK agent definitions (Planner + 5 pipeline specialists) + the Gemini-Pro Critic agent
tools/      Function tools + MCP server exposing them (to the Critic agent and to any external MCP IDE)
rag/        Knowledge base ingestion (policies, playbooks, vendor history) -> Chroma
api/        FastAPI backend (the orchestration entrypoint / REST API)
ui/         Streamlit analyst dashboard
eval/       Test scenarios + scoring harness (precision/recall/latency)
deploy/     Dockerfile, docker-compose, Kubernetes manifests
docs/       Architecture diagrams, compliance notes, writeup outline
```

## 5. Quickstart

```bash
cp .env.example .env               # add GOOGLE_API_KEY / GOOGLE_CLOUD_PROJECT
pip install -r requirements.txt
python data/init_db.py             # seeds the vendor/watchlist/audit tables
python rag/ingest.py               # builds the Chroma vector store from data/knowledge_base
uvicorn api.main:app --reload      # backend on :8000
streamlit run ui/streamlit_app.py  # dashboard on :8501
python eval/run_eval.py            # prints precision/recall/latency report
```

Everything above runs on one `GOOGLE_API_KEY` — there is no second model
provider anywhere in this stack. If the key is unset, the pipeline still
runs end-to-end for the deterministic/tool-only parts and logs the Gemini
steps as skipped, so the repo structure and eval harness are inspectable
without billing enabled.

## 6. Interoperability via MCP

`tools/mcp_server.py` exposes the verified tool set (vendor lookup,
bank-change history, sanctions screening, policy retrieval, risk scoring)
over the open Model Context Protocol — the same pattern used by reference
projects like Lighthouse Agentic Hub. Any MCP-compatible IDE (Google
Antigravity, Gemini CLI, Cursor, etc.) can attach to it directly to query
AP Sentinel's fraud-signal tools outside the main pipeline; internally, the
Critic agent uses the same server so its re-check calls the exact tools the
main pipeline used rather than a paraphrased summary.
