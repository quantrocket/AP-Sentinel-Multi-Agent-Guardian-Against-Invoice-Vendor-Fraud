"""
FastAPI entrypoint. Wraps the ADK planner + the conditional Gemini-Pro Critic
step into a single REST endpoint, and writes the case to case_history for
audit/reporting.
"""
import os, sys, time, uuid, sqlite3, json, logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel

from tools.function_tools import (
    ocr_extract, parse_email_headers, vendor_lookup, bank_change_lookup,
    sanctions_check, risk_score, redact_pii, scan_prompt_injection,
    write_audit_log, generate_report,
)
from rag.ingest import get_retriever
from agents.critic_agent import run_critic_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ap-sentinel")

app = FastAPI(title="AP Sentinel", version="1.0")


class InvoiceCase(BaseModel):
    invoice_text: str
    email_text: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/review-invoice")
def review_invoice(case: InvoiceCase):
    t0 = time.time()
    case_id = str(uuid.uuid4())[:8]
    trace = {"case_id": case_id, "steps": []}

    def step(name, fn, *args, **kwargs):
        s0 = time.time()
        result = fn(*args, **kwargs)
        trace["steps"].append({"agent": name, "latency_ms": round((time.time() - s0) * 1000, 1)})
        log.info(f"[{case_id}] {name} completed in {trace['steps'][-1]['latency_ms']}ms")
        return result

    # 1. Intake
    invoice = step("intake_agent.ocr_extract", ocr_extract, case.invoice_text)
    headers = step("intake_agent.parse_email_headers", parse_email_headers, case.email_text)

    # 2. Policy / RAG
    retriever = get_retriever()
    policy_hits = step("policy_rag_agent.retrieve_policy", retriever, invoice["vendor_name"])

    # 3. Vendor verification
    vendor = step("vendor_verification_agent.vendor_lookup", vendor_lookup, invoice["vendor_name"])
    bank_check = step(
        "vendor_verification_agent.bank_change_lookup",
        bank_change_lookup, vendor.get("vendor_id", ""), invoice.get("bank_account"),
    )
    sanctions = step("vendor_verification_agent.sanctions_check", sanctions_check, invoice["vendor_name"])

    # 4. Risk scoring
    signals = {
        "domain_mismatch": headers.get("domain_mismatch", False),
        "bank_account_changed": bank_check.get("changed", False),
        "changes_last_12mo": bank_check.get("changes_last_12mo", 0),
        "sanctions_hit": sanctions.get("hit", False),
        "vendor_found": vendor.get("found", False),
        "tenure_months": vendor.get("tenure_months", 999),
    }
    scored = step("risk_scoring_agent.risk_score", risk_score, signals)

    # 5. Compliance / security
    injection_scan = step("compliance_security_agent.scan_prompt_injection", scan_prompt_injection, case.email_text)
    sanitized_notes = step("compliance_security_agent.redact_pii", redact_pii, case.email_text)
    step("compliance_security_agent.write_audit_log", write_audit_log, case_id, "system", "auto_review", {
        "signals": signals, "score": scored, "injection_scan": injection_scan,
    })

    # 6. Critic Agent — independent second opinion (BLOCK-tier only), Gemini-Pro,
    #    same model family as the rest of the pipeline (see agents/critic_agent.py
    #    for why independence doesn't require a different vendor).
    validator_note = "not run (below BLOCK threshold or GOOGLE_API_KEY unset)"
    if scored["tier"] == "BLOCK":
        sanitized_case = {
            "vendor_name": invoice["vendor_name"], "amount": invoice["amount"],
            "signals": signals, "score": scored, "notes": sanitized_notes,
        }
        critique = step("critic_agent.run_critic_review", run_critic_review, sanitized_case)
        if critique.get("ran"):
            validator_note = f"agrees_with_block={critique.get('agrees_with_block')}: {critique.get('final_rationale')}"
            if critique.get("agrees_with_block") is False:
                scored["tier"] = critique.get("recommended_tier", scored["tier"])
                scored["reasons"].append("Downgraded/upgraded after Gemini-Pro critic disagreement")

    # 7. Reporting
    report_payload = {
        "case_id": case_id, "vendor_name": invoice["vendor_name"],
        "invoice_number": invoice["invoice_number"], "amount": invoice["amount"],
        "currency": invoice["currency"], "tier": scored["tier"], "score": scored["score"],
        "reasons": scored["reasons"], "validator_note": validator_note, "audit_id": case_id,
    }
    report = step("reporting_agent.generate_report", generate_report, report_payload)

    conn = sqlite3.connect("data/ap_sentinel.db")
    conn.execute(
        "INSERT INTO case_history (case_id, vendor_id, decision, reason_codes) VALUES (?,?,?,?)",
        (case_id, vendor.get("vendor_id", "UNKNOWN"), scored["tier"], json.dumps(scored["reasons"])),
    )
    conn.commit(); conn.close()

    trace["total_latency_ms"] = round((time.time() - t0) * 1000, 1)
    return {"decision": scored, "report_markdown": report, "policy_context": policy_hits, "trace": trace}
