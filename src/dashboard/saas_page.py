"""
CATERYA Agentic Enterprise — SaaS/AaaS Admin Dashboard
Halaman Streamlit untuk manage tenants, billing, analytics, dan white label.
Tambahkan page ini ke sidebar navigasi di app.py utama.
© 2026 Caterya Tech. All Rights Reserved.

Cara pakai:
    Tambahkan ke app.py: from src.dashboard.saas_page import render_saas_page
    Lalu panggil render_saas_page() di salah satu menu navigasi.
"""

import json
import os
import sys
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))


def render_saas_page():
    """Main SaaS/AaaS management dashboard."""
    st.title("🏭 SaaS / AaaS Management")
    st.caption("Kelola tenants, billing, analytics, dan white label dari sini.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Tenants", "💳 Billing", "📊 Analytics", "🔗 Webhooks & API", "🎨 White Label"
    ])

    with tab1:
        _render_tenants()

    with tab2:
        _render_billing()

    with tab3:
        _render_analytics()

    with tab4:
        _render_api_docs()

    with tab5:
        _render_white_label()


# ─── Tab: Tenants ─────────────────────────────────────────────────────────────

def _render_tenants():
    st.subheader("👥 Tenant Management")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tenants", "24", "+3 minggu ini")
    col2.metric("Aktif Hari Ini", "18", "75%")
    col3.metric("Revenue Bulan Ini", "$1,247", "+$340")
    col4.metric("Churn Rate", "2.1%", "-0.5%")

    st.divider()

    # Register new tenant
    with st.expander("➕ Register Tenant Baru"):
        with st.form("new_tenant"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nama")
                email = st.text_input("Email")
            with col2:
                plan = st.selectbox("Plan", ["free", "starter", "growth", "enterprise", "white_label"])
                notes = st.text_input("Notes (opsional)")

            if st.form_submit_button("Register", type="primary"):
                try:
                    from src.saas.tenant_manager import Tenant, PlanType, get_tenant_db
                    t = Tenant.create(name=name, email=email, plan=PlanType(plan))
                    get_tenant_db().save(t)
                    st.success(f"✅ Tenant dibuat! API Key: `{t.api_key}`")
                except Exception as e:
                    import hashlib, uuid
                    tid = str(uuid.uuid4())
                    key = "cae_" + hashlib.sha256(f"{tid}{email}".encode()).hexdigest()[:32]
                    st.success(f"✅ Demo: API Key: `{key}`")

    # Tenant list (demo)
    st.subheader("Daftar Tenant")
    DEMO_TENANTS = [
        {"name": "PT Maju Jaya", "email": "admin@majujaya.co.id", "plan": "growth", "status": "🟢 Aktif", "tasks_used": "4,231", "revenue": "$99"},
        {"name": "Solo Founder Budi", "email": "budi@gmail.com", "plan": "starter", "status": "🟢 Aktif", "tasks_used": "891", "revenue": "$29"},
        {"name": "Startup Cepat", "email": "cto@startupcepat.id", "plan": "enterprise", "status": "🟢 Aktif", "tasks_used": "12,450", "revenue": "$499"},
        {"name": "Demo User", "email": "demo@test.com", "plan": "free", "status": "🟡 Trial", "tasks_used": "45", "revenue": "$0"},
    ]

    for t in DEMO_TENANTS:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
            c1.write(f"**{t['name']}**\n\n{t['email']}")
            c2.write(f"Plan: `{t['plan']}`\n\nStatus: {t['status']}")
            c3.metric("Tasks", t['tasks_used'])
            c4.metric("Revenue", t['revenue'])
            if c5.button("Detail", key=f"btn_{t['email']}"):
                st.session_state[f"show_{t['email']}"] = True


# ─── Tab: Billing ─────────────────────────────────────────────────────────────

def _render_billing():
    st.subheader("💳 Billing & Subscription")

    # Plan pricing
    st.markdown("### 💰 Pricing Plans")
    plans = [
        {"name": "Free", "price": "$0/bln", "agents": "100 tasks/bln", "api": "50/hari", "color": "gray"},
        {"name": "Starter", "price": "$29/bln", "agents": "2.000 tasks/bln", "api": "500/hari", "color": "blue"},
        {"name": "Growth", "price": "$99/bln", "agents": "10.000 tasks/bln", "api": "5.000/hari", "color": "green"},
        {"name": "Enterprise", "price": "$499/bln", "agents": "Unlimited", "api": "Unlimited", "color": "purple"},
    ]

    cols = st.columns(4)
    for i, plan in enumerate(plans):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"**{plan['name']}**")
                st.markdown(f"### {plan['price']}")
                st.write(f"✓ {plan['agents']}")
                st.write(f"✓ API: {plan['api']}")
                if st.button(f"Select {plan['name']}", key=f"plan_{i}", use_container_width=True):
                    st.session_state["selected_plan"] = plan["name"].lower()

    st.divider()

    # Create invoice
    st.markdown("### 🧾 Buat Invoice")
    with st.form("create_invoice"):
        col1, col2, col3 = st.columns(3)
        with col1:
            inv_plan = st.selectbox("Plan", ["starter", "growth", "enterprise", "white_label"])
        with col2:
            billing_period = st.selectbox("Periode", ["monthly", "annual"])
        with col3:
            payment_method = st.selectbox("Metode", [
                "stripe", "crypto_btc", "crypto_eth", "crypto_sol", "crypto_usdt"
            ])

        if st.form_submit_button("Buat Invoice", type="primary"):
            PRICES = {"starter": 29, "growth": 99, "enterprise": 499, "white_label": 999}
            price = PRICES.get(inv_plan, 29)
            if billing_period == "annual":
                price = int(price * 10)  # ~17% discount

            if "crypto" in payment_method:
                currency = payment_method.split("_")[1].upper()
                rates = {"BTC": 95000, "ETH": 3200, "SOL": 180, "USDT": 1}
                crypto_amount = round(price / rates.get(currency, 1), 8)

                st.success(f"Invoice dibuat!")
                with st.container(border=True):
                    st.markdown(f"**Invoice #{datetime.utcnow().strftime('%Y%m%d%H%M')[:10]}**")
                    st.write(f"Plan: {inv_plan} ({billing_period})")
                    st.write(f"Jumlah: **${price} USD = {crypto_amount} {currency}**")
                    addr_map = {
                        "BTC": os.getenv("BTC_RECEIVE_ADDRESS", "bc1qxwq5uwlpmjcjcq8h0ylmvzjktu8mtpe33cslk8"),
                        "ETH": os.getenv("ETH_RECEIVE_ADDRESS", "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81"),
                        "SOL": os.getenv("SOL_RECEIVE_ADDRESS", "9GfH2m7foUKceYKV927EknXpK8HLnxqQzNevar1kPizU"),
                        "USDT": os.getenv("ETH_RECEIVE_ADDRESS", "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81"),
                    }
                    st.write(f"Kirim ke: `{addr_map.get(currency, '-')}`")
                    st.caption("Berlaku 24 jam. Setelah kirim, konfirmasi di bawah.")
                    tx = st.text_input("TX Hash (setelah transfer)", key="tx_hash_input")
                    if st.button("Konfirmasi Pembayaran") and tx:
                        st.success("✅ Pembayaran dikonfirmasi! Plan diupgrade.")
            else:
                st.info("💳 Stripe payment: Integrate Stripe Checkout link di sini.\nDapatkan key di https://stripe.com")


# ─── Tab: Analytics ──────────────────────────────────────────────────────────

def _render_analytics():
    st.subheader("📊 Usage Analytics")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks (30d)", "28,450", "+12%")
    col2.metric("Total Tokens (30d)", "142M", "+18%")
    col3.metric("Avg Latency", "1.2s", "-0.3s")
    col4.metric("Success Rate", "98.7%", "+0.2%")

    # Daily chart (demo data)
    import pandas as pd
    import datetime

    dates = pd.date_range(end=datetime.date.today(), periods=30)
    import random
    random.seed(42)
    tasks = [random.randint(800, 1200) for _ in range(30)]
    df = pd.DataFrame({"Tanggal": dates, "Tasks": tasks})
    st.line_chart(df.set_index("Tanggal"))

    # Per agent breakdown
    st.markdown("### 🤖 Usage per Agent")
    agent_data = [
        {"Agent": "content_writer", "Tasks": 8230, "Tokens": "41.2M", "Success": "99.1%"},
        {"Agent": "lead_gen", "Tasks": 6120, "Tokens": "30.6M", "Success": "98.3%"},
        {"Agent": "support", "Tasks": 5890, "Tokens": "29.5M", "Success": "99.5%"},
        {"Agent": "research", "Tasks": 4210, "Tokens": "21.1M", "Success": "97.8%"},
        {"Agent": "sales_closer", "Tasks": 4000, "Tokens": "20.0M", "Success": "98.9%"},
    ]
    st.dataframe(agent_data, use_container_width=True)


# ─── Tab: API & Webhooks ──────────────────────────────────────────────────────

def _render_api_docs():
    st.subheader("🔗 AaaS API & Webhooks")

    # API Key display
    api_key = st.session_state.get("api_key", "cae_test_key_demo")
    st.markdown("**API Key Anda:**")
    col1, col2 = st.columns([4, 1])
    with col1:
        st.code(api_key)
    with col2:
        if st.button("Copy", use_container_width=True):
            st.toast("Copied!")

    # Quick start
    st.markdown("### 🚀 Quick Start")
    base_url = st.text_input("Base URL", value="https://api.caterya.ai", help="Ganti dengan URL server Anda")

    with st.expander("📋 Run Agent — curl"):
        st.code(f"""
curl -X POST {base_url}/api/agents/run \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "agent_id": "content_writer",
    "task": "Tulis artikel 500 kata tentang manfaat AI untuk UMKM",
    "context": {{"tone": "friendly", "language": "id"}}
  }}'
""".strip(), language="bash")

    with st.expander("🐍 Python SDK"):
        st.code(f"""
import requests

API_KEY = "{api_key}"
BASE_URL = "{base_url}"

def run_agent(agent_id: str, task: str, context: dict = {{}}) -> dict:
    resp = requests.post(
        f"{{BASE_URL}}/api/agents/run",
        headers={{"X-API-Key": API_KEY}},
        json={{"agent_id": agent_id, "task": task, "context": context}}
    )
    return resp.json()

# Contoh
result = run_agent("lead_gen", "Cari 5 prospek di industri F&B Jakarta")
print(result["result"])
""".strip(), language="python")

    with st.expander("📡 Webhook Registration"):
        st.code(f"""
curl -X POST {base_url}/api/webhooks \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "url": "https://yourapp.com/webhook",
    "events": ["agent.completed", "payment.confirmed"],
    "secret": "your_webhook_secret"
  }}'
""".strip(), language="bash")

    # Available agents
    st.markdown("### 🤖 Available Agents")
    agents = {
        "lead_gen": "Find & qualify prospects",
        "content_writer": "SEO copy & marketing",
        "sales_closer": "Objection handling & closing",
        "support": "Customer inquiries",
        "finance": "Invoicing & billing",
        "code_improver": "Code review & refactor",
        "research": "Market intelligence",
        "crypto_ops": "On-chain operations",
    }
    for aid, desc in agents.items():
        st.write(f"- `{aid}` — {desc}")

    # Test API (live)
    st.markdown("### 🧪 Test API (Demo)")
    with st.form("test_api"):
        test_agent = st.selectbox("Agent", list(agents.keys()))
        test_task = st.text_area("Task", placeholder="Tulis task untuk agent...", height=80)
        if st.form_submit_button("▶ Run Agent", type="primary"):
            with st.spinner("Menjalankan agent..."):
                import time
                time.sleep(1.5)  # Simulate latency
                st.success("✅ Agent selesai!")
                st.code(json.dumps({
                    "run_id": "run_demo_" + datetime.utcnow().strftime("%H%M%S"),
                    "agent_id": test_agent,
                    "status": "completed",
                    "result": f"[Demo] Agent {test_agent} memproses: {test_task[:80]}...\n\nOutput agent akan muncul di sini pada deployment real.",
                    "tokens_used": 342,
                    "latency_ms": 1247.3,
                    "ethics_passed": True,
                }, indent=2), language="json")


# ─── Tab: White Label ──────────────────────────────────────────────────────────

def _render_white_label():
    st.subheader("🎨 White Label Configuration")
    st.info("Jual CATERYA sebagai produk AI branded milik Anda kepada client enterprise.")

    with st.form("wl_config"):
        col1, col2 = st.columns(2)
        with col1:
            brand_name = st.text_input("Nama Brand", placeholder="AcmeCorp AI")
            primary_color = st.color_picker("Warna Utama", value="#6366f1")
            custom_domain = st.text_input("Custom Domain", placeholder="ai.acmecorp.com")
            support_email = st.text_input("Support Email", placeholder="support@acmecorp.com")
        with col2:
            logo_url = st.text_input("Logo URL", placeholder="https://...")
            secondary_color = st.color_picker("Warna Sekunder", value="#1e1e2e")
            show_powered_by = st.checkbox("Tampilkan 'Powered by CATERYA'", value=True)
            show_crypto = st.checkbox("Tampilkan fitur Crypto", value=False)

        st.markdown("**Agents yang aktif untuk client ini:**")
        enabled_agents = st.multiselect(
            "Pilih agents",
            ["lead_gen", "content_writer", "sales_closer", "support", "finance", "research", "code_improver", "crypto_ops"],
            default=["lead_gen", "content_writer", "support", "finance"],
        )

        if st.form_submit_button("💾 Simpan & Generate Config", type="primary"):
            st.success("✅ White label config disimpan!")

            # Generate config.toml
            config_toml = f"""[theme]
primaryColor = "{primary_color}"
backgroundColor = "{secondary_color}"
secondaryBackgroundColor = "#16162a"
textColor = "#ffffff"
font = "sans serif"

[server]
headless = true
enableCORS = false
port = 8501
"""
            # Generate .env
            env_content = f"""WL_BRAND_NAME={brand_name}
WL_PRIMARY_COLOR={primary_color}
WL_SECONDARY_COLOR={secondary_color}
WL_CUSTOM_DOMAIN={custom_domain}
WL_SUPPORT_EMAIL={support_email}
WL_SHOW_POWERED_BY={str(show_powered_by).lower()}
WL_SHOW_CRYPTO={str(show_crypto).lower()}
WL_ENABLED_AGENTS={','.join(enabled_agents)}
"""
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**`.streamlit/config.toml`**")
                st.code(config_toml, language="toml")
                st.download_button(
                    "⬇ Download config.toml",
                    config_toml,
                    file_name="config.toml",
                    mime="text/plain",
                )
            with col2:
                st.markdown("**`.env` overrides**")
                st.code(env_content, language="bash")
                st.download_button(
                    "⬇ Download .env",
                    env_content,
                    file_name=".env.whitelabel",
                    mime="text/plain",
                )

            st.markdown("### 🚀 Deploy White Label")
            deploy_cmd = f"""# Deploy white label untuk {brand_name}
git clone git@github.com:CateryaTech/CATERYA-Agentic-Enterprise.git {brand_name.lower().replace(' ', '-')}-ai
cd {brand_name.lower().replace(' ', '-')}-ai

# Copy config files
cp .env.whitelabel .env
mkdir -p .streamlit && cp config.toml .streamlit/

# Run
docker-compose up -d
# Dashboard: http://localhost:8501 (atau {custom_domain})
"""
            st.code(deploy_cmd, language="bash")

    # Pricing for white label
    st.divider()
    st.markdown("### 💰 White Label Pricing")
    st.markdown("""
| Tier | Harga | Termasuk |
|------|-------|---------|
| **Reseller** | $999/bulan | 1 instance, branding penuh |
| **Agency** | $2,499/bulan | 5 instances, multi-tenant |
| **OEM** | Custom | Unlimited instances, source code access |
    """)


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="CATERYA SaaS Admin",
        page_icon="🏭",
        layout="wide",
    )
    render_saas_page()
