# AP Fraud Review Policy (v1.2)

## Bank Detail Change Rule
Any change to a vendor's on-file bank account must be independently verified
by a call-back to a phone number on file (not one supplied in the change
request email) before payment is released. If the change coincides with a
Reply-To domain mismatch, escalate to BLOCK regardless of invoice amount.

## New Vendor Rule
Vendors with less than 3 months tenure require Finance Manager sign-off for
any payment above $5,000, independent of the automated risk score.

## Sanctions Screening
Every vendor must be screened against the current watchlist before first
payment and on every bank-detail change. A hit is an automatic BLOCK.

## Escalation Tiers
- **ALLOW** (score < 30): auto-approved, logged for periodic audit sampling.
- **HOLD** (30-59): routed to an AP analyst for manual review within 1 business day.
- **BLOCK** (60+): payment frozen, Finance Manager + Security notified, vendor
  contacted via verified channel only.

## Prior Case Notes — Nova Consulting Group (V003)
Vendor disputed a bank-detail change in Q1 2025; investigation concluded the
change was legitimate but slow to verify. Analysts should expect this vendor
to occasionally change accounts and confirm via the verified callback number
already on file rather than treating tenure/history alone as disqualifying.
