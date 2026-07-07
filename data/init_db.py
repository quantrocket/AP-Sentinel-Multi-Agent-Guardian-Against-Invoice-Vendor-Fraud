"""Creates data/ap_sentinel.db with schema + a handful of seed rows so the
eval scenarios and demo are reproducible out of the box."""
import sqlite3, hashlib, os

os.makedirs("data", exist_ok=True)
conn = sqlite3.connect("data/ap_sentinel.db")
c = conn.cursor()

c.executescript("""
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id TEXT PRIMARY KEY,
    vendor_name TEXT UNIQUE,
    tenure_months INTEGER,
    known_account_hash TEXT,
    prior_flags TEXT
);
CREATE TABLE IF NOT EXISTS bank_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id TEXT,
    changed_at TEXT
);
CREATE TABLE IF NOT EXISTS watchlist (
    vendor_name TEXT PRIMARY KEY,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS case_history (
    case_id TEXT PRIMARY KEY,
    vendor_id TEXT,
    decision TEXT,
    reason_codes TEXT,
    analyst_override TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT,
    actor TEXT,
    action TEXT,
    details TEXT,
    ts REAL
);
""")

def h(acc): return hashlib.sha256(acc.encode()).hexdigest()

seed_vendors = [
    ("V001", "Acme Industrial Supply", 36, h("ACC-1001-ACME"), "[]"),
    ("V002", "Brightline Logistics", 4, h("ACC-2002-BRIGHT"), "[]"),
    ("V003", "Nova Consulting Group", 18, h("ACC-3003-NOVA"), '["prior_dispute_2025"]'),
]
c.executemany("INSERT OR IGNORE INTO vendors VALUES (?,?,?,?,?)", seed_vendors)

c.executemany("INSERT INTO bank_change_log (vendor_id, changed_at) VALUES (?, date('now','-2 months'))",
              [("V003",), ("V003",)])

c.executemany("INSERT OR IGNORE INTO watchlist VALUES (?,?)",
              [("Zenith Offshore Holdings", "Matches FinCEN advisory pattern (mock)")])

conn.commit()
conn.close()
print("data/ap_sentinel.db initialized.")
