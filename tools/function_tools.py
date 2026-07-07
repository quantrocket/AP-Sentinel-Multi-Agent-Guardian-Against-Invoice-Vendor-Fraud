"""
Shared function tools. These are registered as ADK FunctionTools for the
Gemini pipeline agents AND exposed via tools/mcp_server.py so the Gemini-Pro
Critic agent (agents/critic_agent.py) reasons over the exact same facts, not
a paraphrase, when it re-checks a BLOCK-tier case.
"""
from __future__ import annotations
import re, sqlite3, time, json, hashlib
from dataclasses import dataclass, asdict
from typing import Optional

DB_PATH = "data/ap_sentinel.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def ocr_extract(document_text: str) -> dict:
    """Extract structured invoice fields from raw OCR/email text.

    Input: raw text (str) pulled from an invoice PDF or forwarded email.
    Output: dict with vendor_name, invoice_number, amount, currency,
             bank_account, due_date (best-effort regex extraction; a real
             deployment would swap this for Document AI / Gemini Vision).
    """
    amount = re.search(r"(?:USD|\$)\s?([\d,]+\.\d{2})", document_text)
    invoice_no = re.search(r"Invoice\s*#?\s*([A-Z0-9\-]+)", document_text, re.I)
    account = re.search(r"Account\s*(?:No\.?|Number)?[:\s]*([A-Z0-9\-]{6,})", document_text, re.I)
    vendor = re.search(r"(?:From|Vendor)[:\s]*([A-Za-z0-9 &.,'-]+)", document_text)
    return {
        "vendor_name": (vendor.group(1).strip() if vendor else "UNKNOWN"),
        "invoice_number": (invoice_no.group(1) if invoice_no else "UNKNOWN"),
        "amount": float(amount.group(1).replace(",", "")) if amount else None,
        "currency": "USD",
        "bank_account": account.group(1) if account else None,
        "extracted_at": time.time(),
    }


def parse_email_headers(raw_email: str) -> dict:
    """Pull From/Reply-To/Return-Path to detect display-name spoofing.

    Output: dict with from_display, from_domain, reply_to_domain,
             domain_mismatch (bool) — a classic BEC tell is From display
             name matching the real vendor but Reply-To on a lookalike domain.
    """
    frm = re.search(r"From:\s*(.+)", raw_email)
    reply_to = re.search(r"Reply-To:\s*(.+)", raw_email)
    def domain(s):
        m = re.search(r"@([\w.-]+)", s or "")
        return m.group(1).lower() if m else None
    from_domain = domain(frm.group(1) if frm else "")
    reply_domain = domain(reply_to.group(1) if reply_to else "")
    return {
        "from_display": frm.group(1).strip() if frm else None,
        "from_domain": from_domain,
        "reply_to_domain": reply_domain,
        "domain_mismatch": bool(reply_domain and from_domain and reply_domain != from_domain),
    }


def vendor_lookup(vendor_name: str) -> dict:
    """Look up a vendor's on-file profile (tenure, known bank account hash, prior flags)."""
    conn = _conn()
    row = conn.execute(
        "SELECT vendor_id, tenure_months, known_account_hash, prior_flags FROM vendors WHERE vendor_name = ?",
        (vendor_name,),
    ).fetchone()
    conn.close()
    if not row:
        return {"found": False, "vendor_name": vendor_name}
    return {
        "found": True,
        "vendor_id": row[0],
        "tenure_months": row[1],
        "known_account_hash": row[2],
        "prior_flags": json.loads(row[3] or "[]"),
    }


def bank_change_lookup(vendor_id: str, new_account: Optional[str]) -> dict:
    """Check whether the supplied bank account differs from the vendor's known account
    and how many times the account has changed in the last 12 months (churn = risk signal)."""
    if not new_account:
        return {"changed": False, "reason": "no_account_supplied"}
    conn = _conn()
    row = conn.execute("SELECT known_account_hash FROM vendors WHERE vendor_id = ?", (vendor_id,)).fetchone()
    changes = conn.execute(
        "SELECT COUNT(*) FROM bank_change_log WHERE vendor_id = ? AND changed_at > date('now','-12 months')",
        (vendor_id,),
    ).fetchone()
    conn.close()
    new_hash = hashlib.sha256(new_account.encode()).hexdigest()
    known_hash = row[0] if row else None
    return {
        "changed": known_hash is not None and new_hash != known_hash,
        "changes_last_12mo": changes[0] if changes else 0,
    }


def sanctions_check(vendor_name: str, country: str = "") -> dict:
    """Screen a vendor name against a local mock sanctions/watchlist table.
    (Swap for OFAC/UN API in production; kept local+free for reproducibility.)"""
    conn = _conn()
    hit = conn.execute("SELECT reason FROM watchlist WHERE vendor_name = ?", (vendor_name,)).fetchone()
    conn.close()
    return {"hit": bool(hit), "reason": hit[0] if hit else None}


def retrieve_policy(query: str, top_k: int = 4) -> list[dict]:
    """Thin wrapper the RAG agent calls; actual vector search lives in rag/ingest.py's
    get_retriever(). Kept here as a stable tool signature for ADK/MCP registration."""
    from rag.ingest import get_retriever
    retriever = get_retriever()
    return retriever(query, top_k)


@dataclass
class RiskScoreResult:
    score: int
    tier: str
    reasons: list[str]


def risk_score(signals: dict) -> dict:
    """Weighted rule-based risk score (0-100) + tier, with human-readable reason codes.
    LLM agents layer qualitative rationale on top of this deterministic base score so the
    number itself stays auditable/reproducible."""
    score = 0
    reasons = []
    if signals.get("domain_mismatch"):
        score += 30; reasons.append("Reply-To domain differs from From domain")
    if signals.get("bank_account_changed"):
        score += 25; reasons.append("Bank account differs from vendor's known account on file")
    if signals.get("changes_last_12mo", 0) >= 2:
        score += 15; reasons.append("Vendor bank details changed 2+ times in 12 months")
    if signals.get("sanctions_hit"):
        score += 40; reasons.append("Vendor name matched watchlist")
    if not signals.get("vendor_found", True):
        score += 10; reasons.append("Vendor not found in vendor master (first-time payee)")
    if signals.get("tenure_months", 999) < 3:
        score += 10; reasons.append("Vendor relationship younger than 3 months")
    score = min(score, 100)
    tier = "BLOCK" if score >= 60 else "HOLD" if score >= 30 else "ALLOW"
    return asdict(RiskScoreResult(score=score, tier=tier, reasons=reasons))


def redact_pii(text: str) -> str:
    """Mask bank account numbers, tax IDs, and long digit runs before anything is logged
    or sent to the cross-model validator."""
    text = re.sub(r"\b\d{8,}\b", lambda m: m.group(0)[:2] + "*" * (len(m.group(0)) - 4) + m.group(0)[-2:], text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****", text)  # SSN-like
    return text


INJECTION_PATTERNS = [
    r"ignore (all|previous) instructions",
    r"disregard (the|your) (system|above) prompt",
    r"you are now",
    r"reveal (the|your) (system prompt|instructions)",
]


def scan_prompt_injection(text: str) -> dict:
    """Flag free-text fields (invoice notes, email body) that look like an attempt to
    manipulate the downstream LLM agents rather than describe an invoice."""
    hits = [p for p in INJECTION_PATTERNS if re.search(p, text, re.I)]
    return {"suspicious": bool(hits), "matched_patterns": hits}


def write_audit_log(case_id: str, actor: str, action: str, details: dict) -> dict:
    """Append-only audit trail. Every agent decision writes here; nothing is ever
    updated or deleted from this table (required for finance compliance review)."""
    conn = _conn()
    conn.execute(
        "INSERT INTO audit_log (case_id, actor, action, details, ts) VALUES (?, ?, ?, ?, ?)",
        (case_id, actor, action, json.dumps(details), time.time()),
    )
    conn.commit()
    conn.close()
    return {"logged": True}


def generate_report(case: dict) -> str:
    """Render the final analyst-facing Markdown report."""
    return f"""# AP Sentinel Case Report — {case.get('case_id')}

**Vendor:** {case.get('vendor_name')}  **Invoice:** {case.get('invoice_number')}  **Amount:** {case.get('currency')} {case.get('amount')}

**Decision:** {case.get('tier')}  (score {case.get('score')}/100)

**Reason codes:**
{chr(10).join('- ' + r for r in case.get('reasons', []))}

**Independent verification (Gemini 2.5 Pro critic):** {case.get('validator_note', 'not run (below BLOCK threshold or GOOGLE_API_KEY unset)')}

**Audit ID:** {case.get('audit_id')}
"""


def notify(channel: str, message: str) -> dict:
    """Stub notification dispatcher (email/Slack/webhook). Logs instead of sending
    in this reproducible demo build."""
    return {"channel": channel, "sent": True, "preview": message[:120]}
