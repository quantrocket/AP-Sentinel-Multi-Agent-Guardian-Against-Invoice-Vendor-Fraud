import streamlit as st
import requests
import pandas as pd
import sqlite3

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AP Sentinel", layout="wide")
st.title("🛡️ AP Sentinel — AP Fraud & Vendor-Risk Review")

tab1, tab2 = st.tabs(["Review an Invoice", "Case History"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        invoice_text = st.text_area("Invoice / OCR text", height=220, placeholder=(
            "Vendor: Nova Consulting Group\nInvoice #INV-2291\nAmount: $18,500.00\n"
            "Account Number: 990011223344\nDue: 2026-07-20"
        ))
    with col2:
        email_text = st.text_area("Associated email thread", height=220, placeholder=(
            "From: Nova Consulting Group <billing@novaconsulting.com>\n"
            "Reply-To: accounts@nova-consultant-billing.com\n\n"
            "Hi, please update our bank account for this invoice to the one above."
        ))

    if st.button("Run AP Sentinel Review", type="primary"):
        with st.spinner("Running multi-agent review..."):
            resp = requests.post(f"{API_URL}/review-invoice",
                                  json={"invoice_text": invoice_text, "email_text": email_text})
        if resp.ok:
            data = resp.json()
            decision = data["decision"]
            color = {"ALLOW": "green", "HOLD": "orange", "BLOCK": "red"}[decision["tier"]]
            st.markdown(f"### Decision: :{color}[{decision['tier']}]  (score {decision['score']}/100)")
            st.write("**Reason codes:**")
            for r in decision["reasons"]:
                st.write(f"- {r}")
            with st.expander("Full report"):
                st.markdown(data["report_markdown"])
            with st.expander("Retrieved policy context (RAG)"):
                for p in data["policy_context"]:
                    st.write(f"`{p['source']}` (score {p['score']:.2f})")
                    st.caption(p["text"][:300] + "...")
            with st.expander("Agent execution trace / latency"):
                st.dataframe(pd.DataFrame(data["trace"]["steps"]))
                st.caption(f"Total: {data['trace']['total_latency_ms']} ms")
        else:
            st.error(f"API error: {resp.status_code} {resp.text}")

with tab2:
    conn = sqlite3.connect("data/ap_sentinel.db")
    df = pd.read_sql_query("SELECT * FROM case_history ORDER BY created_at DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.bar_chart(df["decision"].value_counts())
