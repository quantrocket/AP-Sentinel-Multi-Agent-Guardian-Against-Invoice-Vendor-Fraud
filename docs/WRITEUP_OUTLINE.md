# Kaggle Writeup Outline (≤2500 words)

1. **Title + Tagline + Track** (Agents for Business) — 30 words
2. **Executive Summary** — problem, solution, why it matters, one-line
   architecture snapshot — 150 words
3. **Problem Statement** — BEC/invoice fraud cost stats, why rules-based AP
   controls miss it, why generic chatbots can't be trusted for this workflow
   — 250 words
4. **Solution & Architecture** — the 7-agent diagram from
   `docs/ARCHITECTURE.md` §5.1/5.2, one paragraph per agent's responsibility
   — 500 words
5. **Key Innovation: The Critic Agent** — why a different Gemini checkpoint +
   adversarial framing + raw-tool re-derivation counts as genuine
   independence without a second vendor — 250 words
6. **Memory & RAG** — session state vs. Chroma/SQLite long-term memory, what's
   in the knowledge base, why retrieval beats a static prompt — 250 words
7. **Security & Compliance** — PII redaction, prompt-injection screening,
   immutable audit log, human-in-the-loop on BLOCK — 200 words
8. **Evaluation** — the 5 scenarios in `eval/test_cases.json`, accuracy/
   precision/recall/latency table from `eval/run_eval.py` output — 250 words
9. **Deployment & Production Readiness** — Docker/Cloud Run primary path,
   Kubernetes manifests for scale-out, MCP server for external IDE
   integration, observability via structured logs + per-agent latency trace
   — 200 words
10. **Demo Walkthrough** — 2-3 screenshots from the Streamlit dashboard
    (legit ALLOW, BEC BLOCK with a Critic disagreement example if one occurs)
    — 150 words
11. **Business Impact & Future Work** — quantify time/cost saved per
    analyst-hour vs. manual 3-way match, roadmap (Document AI OCR, live
    sanctions API, voice intake) — 150 words
12. **Compliance & Reproducibility** — link to `docs/KAGGLE_COMPLIANCE.md`,
    one line confirming CC-BY 4.0 + single-vendor reproducibility (one
    `GOOGLE_API_KEY`, no second billing account needed) — 100 words

**Total: ~2,530 words before trimming** — cut Future Work first if over
budget; judges weight architecture/innovation/evaluation more than roadmap
speculation.

## Video (≤5 min, YouTube)
- 0:00-0:30 problem + who it's for
- 0:30-2:00 architecture walkthrough (use the sequence diagram)
- 2:00-4:00 live demo: run the BEC scenario end-to-end in the Streamlit UI,
  show the agent trace tab and the Critic disagreement path if it fires
- 4:00-5:00 eval numbers + close

## Cover image
Use the architecture diagram (`docs/architecture_cover.png`) — a visual
system diagram reads better as a cover image than a UI screenshot for a
judging audience skimming many entries.
