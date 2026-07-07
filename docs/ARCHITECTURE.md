# Architecture

## 5.1 High-Level Flow

```
User / AP Analyst
      |
      v
 [FastAPI /review-invoice]
      |
      v
 Planner Agent (Orchestrator, Google ADK SequentialAgent)
      |-- Intake Agent ---------> OCR + structured extraction        (Gemini 2.5 Flash)
      |-- Policy/RAG Agent -----> Chroma (policies, playbooks, vendor history) (Gemini 2.5 Flash)
      |-- Vendor Verification --> tools (sanctions list, bank-detail change log) (Gemini 2.5 Flash)
      |-- Risk Scoring Agent ---> weighted rule + LLM rationale       (Gemini 2.5 Pro)
      |-- Compliance/Security --> PII redaction, prompt-injection screen, audit log, report (Gemini 2.5 Flash)
      v
 Decision Engine (ALLOW / HOLD / BLOCK)
      |
      v (BLOCK-tier only)
 Critic Agent ------------------> independent re-check              (Gemini 2.5 Pro, adversarial framing)
      |
      v
 Streamlit dashboard + notification
      |
      v
 Human-in-the-loop approval (required for BLOCK, optional for HOLD)
```

## 5.2 Agent Roster (7 agents, 100% Gemini)

| # | Agent | Model | Responsibility | Tools |
|---|---|---|---|---|
| 1 | Planner (Orchestrator) | — (ADK SequentialAgent) | Sequences the pipeline, aggregates results | composition only |
| 2 | Intake Agent | Gemini 2.5 Flash | OCR + structured field extraction, email header spoof detection | `ocr_extract`, `parse_email_headers` |
| 3 | Policy/RAG Agent | Gemini 2.5 Flash | Retrieves relevant policy clauses + this vendor's historical case notes | `retrieve_policy` (Chroma similarity search) |
| 4 | Vendor Verification Agent | Gemini 2.5 Flash | Confirms vendor identity, bank-detail change history, sanctions screening | `vendor_lookup`, `sanctions_check`, `bank_change_lookup` |
| 5 | Risk Scoring Agent | Gemini 2.5 Pro | Combines rule-based signals + LLM rationale into a 0–100 score with reason codes | `risk_score` |
| 6 | Compliance/Security Agent | Gemini 2.5 Flash | PII redaction, prompt-injection screen, immutable audit log, report generation, notification | `redact_pii`, `scan_prompt_injection`, `write_audit_log`, `generate_report`, `notify` |
| 7 | **Critic Agent** | **Gemini 2.5 Pro** | Independent re-check for BLOCK-tier cases only — argues the false-positive case first, then decides | `retrieve_policy`, `vendor_lookup`, `bank_change_lookup`, `sanctions_check` (via MCP) |

## 5.3 Why the Critic Agent Counts as Genuine Independence

A natural objection: "isn't a second Gemini call just the same model checking
itself?" Three structural choices address that directly (see
`agents/critic_agent.py` for the full docstring):

1. **Different model tier.** Gemini 2.5 Pro is a different checkpoint from
   the 2.5 Flash models used everywhere else in the pipeline — different
   training run, different capacity, different failure modes.
2. **Adversarial prompting stance.** The Critic is explicitly instructed to
   build the strongest *false-positive* case first — the same "debate before
   deciding" pattern used in LLM self-critique research to counteract
   confirmation bias in a single forward pass.
3. **Re-derivation from raw facts, not the pipeline's narrative.** The
   Critic calls `retrieve_policy`, `vendor_lookup`, `bank_change_lookup`, and
   `sanctions_check` itself via the MCP tool server, rather than being handed
   the Risk Scoring Agent's prose summary — so a bad summary can't propagate
   into the second opinion.

This keeps the entire submission on a single, free-tier-accessible model
family — no participant needs a second vendor's API key to reproduce the
full pipeline, and there's no cost-reasonableness question to adjudicate
under the competition rules.

## 5.4 Sequence Diagram (text form)

```
Analyst -> API: POST /review-invoice
API -> Planner: run(case)
Planner -> Intake: extract(case.raw)
Intake -> Planner: InvoiceRecord
Planner -> RAG: retrieve(vendor_id, invoice)
Planner -> VendorVerification: verify(vendor_id, bank_details)   [parallel with RAG]
RAG -> Planner: policy_passages
VendorVerification -> Planner: verification_flags
Planner -> RiskScoring: score(InvoiceRecord, policy_passages, verification_flags)
RiskScoring -> Planner: RiskScore
Planner -> Compliance: sanitize_audit_report(case)
Compliance -> Planner: sanitized_case, audit_id, report
alt RiskScore.tier == BLOCK
    Planner -> Critic (Gemini 2.5 Pro): review(sanitized_case)
    Critic -> Planner: agrees_with_block / recommended_tier + rationale
end
Planner -> API: final decision + report
API -> Analyst: decision + report + (human approval required if BLOCK)
```

## 5.5 Memory Architecture

- **Short-term (session):** ADK `SessionService` holds the in-flight case
  state across agent hops within one review.
- **Long-term:** SQLite table `case_history` (structured: vendor_id, decision,
  reason codes, analyst override) + Chroma collection `vendor_notes`
  (unstructured: free-text case summaries, embedded via Gemini's
  `text-embedding-004` for future retrieval).

## 5.6 Deployment Diagram

```
                +-------------------+
                |  Cloud Run (API)  |  <-- FastAPI + Planner + ADK agents (Gemini via Vertex AI)
                +-------------------+
                     |         |
        +------------+         +--------------+
        v                                       v
+---------------+                     +-------------------+
| Chroma (PVC / |                     | Cloud SQL / SQLite |
| Cloud Storage)|                     | (case_history)     |
+---------------+                     +-------------------+
                     ^
                     |
             +-------------------+
             | Cloud Run (UI)    |  <-- Streamlit dashboard
             +-------------------+
                     ^
                     |
             +-------------------+
             | MCP Server        |  <-- exposes fraud-signal tools; Critic agent +
             | (Cloud Run/local) |      any external MCP IDE (Antigravity, Gemini CLI)
             +-------------------+

Kubernetes manifests (deploy/k8s/) are provided for a GKE Autopilot
deployment path when horizontal scaling beyond Cloud Run's concurrency
model is required; the reference/demo deployment for the capstone
submission uses Cloud Run for simplicity and cost.
```
