"""
CATERYA Agentic Enterprise — Main App (Updated)
Entry point Streamlit dengan semua halaman baru terintegrasi.
© 2026 Caterya Tech. All Rights Reserved.

Cara run:
    streamlit run app.py
    # atau
    streamlit run app.py --server.port 8501
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Page config — harus paling atas
st.set_page_config(
    page_title=os.getenv("WL_BRAND_NAME", "CATERYA") + " — Agentic Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── White Label Support ──────────────────────────────────────
try:
    from src.whitelabel.config import load_white_label_from_env
    wl = load_white_label_from_env()
except ImportError:
    wl = None

BRAND_NAME = wl.brand_name if wl else os.getenv("WL_BRAND_NAME", "CATERYA")
PRIMARY_COLOR = wl.primary_color if wl else "#6366f1"

# ─── CSS ──────────────────────────────────────────────────────
st.markdown(f"""
<style>
:root {{ --primary: {PRIMARY_COLOR}; }}
.stSidebar {{ background: #16162a !important; }}
.sidebar-brand {{ text-align: center; padding: 1rem 0; font-size: 1.3rem; font-weight: 700; color: var(--primary); }}
.sidebar-subtitle {{ text-align: center; font-size: 0.75rem; color: #888; margin-top: -0.5rem; padding-bottom: 1rem; }}
</style>
""", unsafe_allow_html=True)

# ─── Onboarding Check ─────────────────────────────────────────
ONBOARDING_FILE = Path("data/onboarding_complete.json")

def show_onboarding():
    try:
        from src.onboarding.wizard import render_onboarding
        render_onboarding()
    except ImportError:
        st.warning("Onboarding module not found. Pastikan src/onboarding/wizard.py ada.")
        if st.button("Skip Onboarding (Dev Mode)"):
            ONBOARDING_FILE.parent.mkdir(parents=True, exist_ok=True)
            ONBOARDING_FILE.write_text('{"completed_at": "dev_skip"}')
            st.rerun()

if not ONBOARDING_FILE.exists():
    show_onboarding()
    st.stop()

# ─── Sidebar Navigation ───────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="sidebar-brand">⚡ {BRAND_NAME}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">Agentic Enterprise</div>', unsafe_allow_html=True)
    st.divider()

    # Check enabled agents
    enabled_agents = os.getenv("ENABLED_AGENTS", "").split(",")

    # Nav options
    nav_options = ["🏠 Dashboard", "🔀 Pipeline Studio", "🤖 Run Agent", "🛒 Marketplace", "🔗 Automations"]

    # SaaS features (show if SAAS_MODE_ENABLED)
    if os.getenv("SAAS_MODE_ENABLED", "true").lower() == "true":
        nav_options += ["🏭 SaaS Admin"]

    # Crypto (conditional)
    if os.getenv("CRYPTO_ENABLED", "true").lower() == "true":
        nav_options += ["₿ Crypto Ops"]

    nav_options += ["⚙️ Settings", "📚 API Docs"]

    if not (wl and not wl.show_powered_by):
        st.caption("Powered by CATERYA Tech")

    selected = st.radio("Menu", nav_options, label_visibility="collapsed")

# ─── Page Routing ─────────────────────────────────────────────

if selected == "🏠 Dashboard":
    _render_home_dashboard()

elif selected == "🔀 Pipeline Studio":
    try:
        from src.pipeline.pipeline_page import render_pipeline_page
        render_pipeline_page()
    except ImportError as e:
        st.error(f"Pipeline Studio module tidak ditemukan: {e}")

elif selected == "🤖 Run Agent":
    _render_agent_runner()

elif selected == "🛒 Marketplace":
    try:
        from src.marketplace.marketplace import render_marketplace_page
        render_marketplace_page()
    except ImportError:
        st.error("Marketplace module tidak ditemukan.")

elif selected == "🔗 Automations":
    _render_automations()

elif selected == "🏭 SaaS Admin":
    try:
        from src.dashboard.saas_page import render_saas_page
        render_saas_page()
    except ImportError:
        st.error("SaaS page module tidak ditemukan.")

elif selected == "₿ Crypto Ops":
    _render_crypto()  # Existing CATERYA crypto page

elif selected == "⚙️ Settings":
    _render_settings()

elif selected == "📚 API Docs":
    _render_api_docs_page()


# ─── Page Functions ───────────────────────────────────────────

def _render_home_dashboard():
    st.title(f"⚡ {BRAND_NAME} Dashboard")

    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tasks Hari Ini", "47", "+12 dari kemarin")
    col2.metric("Agent Aktif", "8", "dari 12 total")
    col3.metric("Success Rate", "98.7%", "+0.2%")
    col4.metric("Avg Latency", "1.2s", "-0.3s")

    st.divider()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📈 Activity (7 Hari Terakhir)")
        import pandas as pd, datetime, random
        dates = pd.date_range(end=datetime.date.today(), periods=7)
        random.seed(1)
        df = pd.DataFrame({"Tasks": [random.randint(30, 80) for _ in range(7)]}, index=dates)
        st.line_chart(df)

    with col2:
        st.subheader("🤖 Agent Status")
        agents_status = [
            ("lead_gen", "🟢 Aktif", "23 tasks"),
            ("content_writer", "🟢 Aktif", "18 tasks"),
            ("support", "🟢 Aktif", "34 tasks"),
            ("finance", "🟡 Idle", "0 tasks"),
            ("research", "🟢 Aktif", "12 tasks"),
        ]
        for agent, status, tasks in agents_status:
            with st.container(border=True):
                st.write(f"**{agent}** — {status}")
                st.caption(tasks)

    # Recent activity
    st.subheader("🕐 Aktivitas Terbaru")
    activities = [
        ("2 mnt lalu", "content_writer", "Selesai: Artikel SEO tentang AI UMKM", "✅"),
        ("5 mnt lalu", "lead_gen", "Selesai: 5 prospek baru ditemukan", "✅"),
        ("12 mnt lalu", "support", "Selesai: 3 tiket customer direspons", "✅"),
        ("1 jam lalu", "ethics_guard", "Diblokir: Konten melanggar ethics policy", "⛔"),
        ("2 jam lalu", "research", "Selesai: Market report Q1 2026", "✅"),
    ]
    for time, agent, desc, icon in activities:
        st.write(f"{icon} `{time}` — **{agent}**: {desc}")


def _render_agent_runner():
    st.title("🤖 Run Agent")
    st.caption("Jalankan agent AI secara manual atau via task queue.")

    AGENTS = {
        "lead_gen": "🎯 Lead Generation",
        "content_writer": "✍️ Content Writer",
        "sales_closer": "💼 Sales Closer",
        "support": "💬 Customer Support",
        "finance": "💰 Finance",
        "code_improver": "🔧 Code Improver",
        "research": "🔬 Research",
        "crypto_ops": "₿ Crypto Ops",
    }

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_agent = st.selectbox("Pilih Agent", list(AGENTS.keys()),
            format_func=lambda x: AGENTS[x])
    with col2:
        context_str = st.text_input("Context (JSON, opsional)", placeholder='{"tone": "formal", "language": "id"}')

    task = st.text_area("Task / Instruksi", height=150,
        placeholder=f"Masukkan instruksi untuk agent {AGENTS.get(selected_agent, '')}...")

    col1, col2 = st.columns([1, 3])
    with col1:
        run_btn = st.button("▶ Jalankan", type="primary", use_container_width=True)

    if run_btn and task:
        with st.spinner(f"🤖 {AGENTS[selected_agent]} sedang bekerja..."):
            import time
            time.sleep(2)

        st.success("✅ Agent selesai!")
        with st.container(border=True):
            st.markdown("**Output:**")
            st.write(f"[Demo Mode] Agent **{selected_agent}** telah memproses task Anda.\n\n"
                     f"Pada deployment real dengan Ollama, output agent akan muncul di sini.\n\n"
                     f"Task yang diproses: _{task[:100]}..._")
        st.caption("⚠️ Demo mode aktif. Connect Ollama untuk output real.")


def _render_automations():
    st.title("🔗 Automations")
    st.caption("Zapier-style: otomasi task berdasarkan trigger.")

    try:
        from src.webhooks.hub import AUTOMATION_TEMPLATES, TRIGGER_TYPES
    except ImportError:
        AUTOMATION_TEMPLATES = []
        TRIGGER_TYPES = {}

    st.subheader("📋 Template Otomasi")
    for tmpl in AUTOMATION_TEMPLATES:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{tmpl['name']}**")
                st.caption(f"Trigger: `{tmpl['trigger_type']}` → Agent: `{tmpl['action_agent_id']}`")
            with col2:
                st.code(tmpl['action_task_template'][:80] + "...", language=None)
            with col3:
                if st.button("Aktifkan", key=f"tmpl_{tmpl['action_agent_id']}", use_container_width=True):
                    st.success("Otomasi diaktifkan!")


def _render_settings():
    st.title("⚙️ Settings")

    tab1, tab2, tab3 = st.tabs(["🤖 LLM", "🔐 Security", "🔄 Reset"])

    with tab1:
        st.subheader("LLM Configuration")
        ollama_url = st.text_input("Ollama URL", value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        model = st.selectbox("Default Model", ["llama3.3", "qwen2.5:7b", "phi4", "deepseek-coder"])
        if st.button("Test Connection"):
            import httpx
            try:
                r = httpx.get(f"{ollama_url}/api/tags", timeout=5)
                if r.status_code == 200:
                    st.success("✅ Ollama terhubung!")
                    models = [m["name"] for m in r.json().get("models", [])]
                    st.write(f"Models tersedia: {', '.join(models[:5])}")
            except Exception:
                st.error("❌ Ollama tidak terhubung. Pastikan Ollama berjalan.")

    with tab2:
        st.subheader("Security")
        st.checkbox("Ethics Guard", value=os.getenv("ETHICS_GUARD_ENABLED", "true") == "true")
        st.info("Wallet vault menggunakan AES-256-GCM + PBKDF2 (480,000 iterations)")

    with tab3:
        st.subheader("Reset Onboarding")
        st.warning("Ini akan menghapus konfigurasi dan menjalankan wizard setup ulang.")
        if st.button("🔄 Reset & Re-onboard", type="secondary"):
            if ONBOARDING_FILE.exists():
                ONBOARDING_FILE.unlink()
            st.success("Reset berhasil! Refresh halaman untuk mulai onboarding.")


def _render_api_docs_page():
    st.title("📚 API Documentation")
    st.caption("CATERYA AaaS API — Agent as a Service endpoints.")

    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    st.info(f"API Server: `{api_url}` — Jalankan dengan: `uvicorn src.api.main:app --reload`")

    endpoints = [
        ("POST", "/api/auth/register", "Register tenant baru, dapatkan API key"),
        ("GET", "/api/agents", "List semua agents tersedia"),
        ("POST", "/api/agents/run", "⭐ Jalankan agent (core AaaS endpoint)"),
        ("GET", "/api/tenant/me", "Info tenant saat ini"),
        ("GET", "/api/tenant/usage", "Usage & quota stats"),
        ("POST", "/api/billing/invoice", "Buat invoice untuk upgrade plan"),
        ("POST", "/api/billing/confirm/{invoice_id}", "Konfirmasi pembayaran"),
        ("POST", "/api/webhooks", "Register webhook"),
        ("GET", "/api/admin/revenue", "Admin: revenue summary"),
    ]

    for method, path, desc in endpoints:
        color = {"POST": "🟢", "GET": "🔵", "DELETE": "🔴"}.get(method, "⚪")
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            col1.write(f"{color} **{method}** `{path}`")
            col2.write(desc)

    st.divider()
    st.markdown(f"**Full interactive docs:** [{api_url}/api/docs]({api_url}/api/docs)")
