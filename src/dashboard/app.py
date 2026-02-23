"""
CATERYA Agentic Enterprise Dashboard
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>

Mobile-first PWA dashboard — run from your phone anywhere on Earth.
100% works offline with local Ollama.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─── Optional package availability flags ─────────────────────────────────────
try:
    from langchain_ollama import ChatOllama  # noqa: F401
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

try:
    from web3 import Web3  # noqa: F401
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CATERYA Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": "https://github.com/caterya-tech",
        "About": "CATERYA Agentic Enterprise v1.0 — Offline-First AI Workforce",
    }
)

# ─── Custom CSS (Mobile-First) ────────────────────────────────────────────────

st.markdown("""
<style>
  /* Mobile-first */
  .main { padding: 0.5rem; }
  .block-container { max-width: 100%; padding: 1rem; }

  /* CATERYA Brand */
  :root {
    --primary: #00d4aa;
    --secondary: #1a1a2e;
    --accent: #f72585;
    --bg: #0f0f1a;
    --card: #1a1a2e;
    --text: #e0e0e0;
  }

  body { background-color: var(--bg) !important; color: var(--text) !important; }

  .caterya-header {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    border: 1px solid var(--primary);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    text-align: center;
  }

  .status-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: bold;
    margin: 2px;
  }
  .status-online { background: #00d4aa22; color: #00d4aa; border: 1px solid #00d4aa; }
  .status-offline { background: #f7258522; color: #f72585; border: 1px solid #f72585; }
  .status-warn { background: #ffbe0b22; color: #ffbe0b; border: 1px solid #ffbe0b; }

  .agent-card {
    background: var(--card);
    border: 1px solid #333;
    border-radius: 10px;
    padding: 1rem;
    margin: 0.5rem 0;
    transition: border-color 0.2s;
  }
  .agent-card:hover { border-color: var(--primary); }

  .metric-card {
    background: var(--card);
    border-radius: 8px;
    padding: 0.8rem;
    text-align: center;
    border: 1px solid #333;
  }

  /* Streamlit overrides */
  .stButton > button {
    background: linear-gradient(135deg, #00d4aa, #0099cc);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-weight: bold;
    width: 100%;
  }
  .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }

  .stSelectbox > div { border-color: var(--primary) !important; }
  .stTextArea textarea { background: #1a1a2e; color: #e0e0e0; border-color: #333; }
</style>
""", unsafe_allow_html=True)


# ─── System Status ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_system_status():
    try:
        from src.core.llm_router import get_connectivity
        conn = get_connectivity()
        return {
            "ollama": conn.ollama_available,
            "online": conn.is_online,
            "latency_ms": round(conn.latency_ms or 0, 1),
        }
    except Exception as e:
        import socket
        try:
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            online = True
        except OSError:
            online = False
        return {"ollama": False, "online": online, "latency_ms": 0, "error": str(e)}


@st.cache_data(ttl=60)
def get_ollama_models():
    try:
        from src.core.llm_router import get_router
        return get_router().ollama_models
    except Exception:
        return []


def get_active_llm_provider() -> tuple[bool, str]:
    """
    Check if any LLM is actually usable right now.
    Returns (is_ready, provider_name).
    Checks: Ollama → session keys → Streamlit secrets → env vars.
    """
    # Check Ollama
    try:
        import httpx
        r = httpx.get(
            f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags",
            timeout=1.5
        )
        if r.status_code == 200 and r.json().get("models"):
            return True, "🦙 Ollama (local)"
    except Exception:
        pass

    # Check session keys + env + streamlit secrets
    key_checks = [
        ("GROQ_API_KEY", "⚡ Groq"),
        ("TOGETHER_API_KEY", "🤝 Together.ai"),
        ("FIREWORKS_API_KEY", "🎆 Fireworks"),
        ("HF_TOKEN", "🤗 HuggingFace"),
    ]
    # Pull from session state if set
    session_keys = st.session_state.get("runtime_keys", {})
    for env_key, name in key_checks:
        val = session_keys.get(env_key) or os.environ.get(env_key, "")
        if not val:
            try:
                val = st.secrets.get(env_key, "")
            except Exception:
                pass
        if val and val.strip():
            return True, name

    return False, "none"


# ─── Header ──────────────────────────────────────────────────────────────────

status = get_system_status()
llm_ready, llm_provider = get_active_llm_provider()

st.markdown(f"""
<div class="caterya-header">
  <h1 style="color: #00d4aa; margin: 0; font-size: 1.8rem;">⚡ CATERYA</h1>
  <p style="color: #888; margin: 4px 0; font-size: 0.85rem;">Agentic Enterprise v1.0 — Built for founders, runs from your phone</p>
  <div style="margin-top: 0.8rem;">
    <span class="status-pill {'status-online' if status['ollama'] else 'status-offline'}">
      {'✓ Ollama' if status['ollama'] else '✗ Ollama Offline'}
    </span>
    <span class="status-pill {'status-online' if llm_ready else 'status-offline'}">
      {'✓ LLM: ' + llm_provider if llm_ready else '✗ No LLM — add key in Settings'}
    </span>
    <span class="status-pill {'status-online' if status['online'] else 'status-warn'}">
      {'🌐 Online' if status['online'] else '📡 Offline'}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Navigation ──────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🤖 Agents", "💰 Crypto", "📊 Monitor", "🔗 Pipelines", "📥 Export", "⚙️ Settings"
])


# ─── Tab 1: Agents ───────────────────────────────────────────────────────────

with tab1:
    st.markdown("### Run an Agent")

    from src.agents.agents import AGENT_REGISTRY

    # ── No-LLM Banner ──────────────────────────────────────────────────────────
    if not llm_ready:
        st.markdown("""
        <div style="background:#1a0a00;border:1px solid #ff6b00;border-radius:10px;padding:1rem 1.2rem;margin-bottom:1rem;">
          <div style="color:#ff6b00;font-weight:bold;font-size:1rem;margin-bottom:0.5rem;">
            ⚠️ Belum ada LLM yang aktif — agents tidak bisa dijalankan
          </div>
          <div style="color:#ccc;font-size:0.85rem;line-height:1.6;">
            Pilih salah satu cara:
          </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            **Opsi A — Groq (gratis, paling cepat, 1 menit setup):**
            1. Daftar di [console.groq.com](https://console.groq.com)
            2. Create API key → copy
            3. Buka tab **⚙️ Settings** → Groq → paste key → Save
            4. Kembali ke tab ini → Run Agent ✓
            """)
        with c2:
            st.markdown("""
            **Opsi B — Ollama (offline, laptop):**
            ```bash
            curl -fsSL https://ollama.ai/install.sh | sh
            ollama pull phi4
            ollama serve
            ```
            Pastikan dashboard bisa reach `localhost:11434`

            **Opsi C — Streamlit Cloud Secrets (permanent):**
            App Settings → Secrets → tambah `GROQ_API_KEY = "gsk_..."`
            """)

        # Inline mini-form untuk langsung set Groq key tanpa pindah tab
        st.markdown("---")
        st.markdown("**⚡ Quick-set Groq key di sini:**")
        qcol1, qcol2 = st.columns([4, 1])
        with qcol1:
            quick_groq = st.text_input(
                "Groq API Key",
                type="password",
                placeholder="gsk_...",
                key="quick_groq_key",
                label_visibility="collapsed",
            )
        with qcol2:
            if st.button("✅ Aktivasi", key="quick_activate", use_container_width=True):
                if quick_groq.strip():
                    if "runtime_keys" not in st.session_state:
                        st.session_state.runtime_keys = {}
                    st.session_state.runtime_keys["GROQ_API_KEY"] = quick_groq.strip()
                    os.environ["GROQ_API_KEY"] = quick_groq.strip()
                    st.success("✅ Groq key aktif! Coba Run Agent sekarang.")
                    st.rerun()
                else:
                    st.warning("Masukkan key dulu")
        st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        agent_id = st.selectbox(
            "Select Agent",
            options=list(AGENT_REGISTRY.keys()),
            format_func=lambda x: {
                "lead_gen": "🎯 Lead Gen",
                "content_writer": "✍️ Content Writer",
                "sales_closer": "💼 Sales Closer",
                "support": "🎧 Support",
                "finance": "💳 Finance",
                "code_improver": "💻 Code Improver",
                "crypto_ops": "🔗 Crypto Ops",
                "ethics_guard": "🛡️ Ethics Guard",
                "self_optimizer": "🧬 Self Optimizer",
                "research": "🔬 Research",
                "dashboard_monitor": "📊 Monitor",
                "backup": "💾 Backup",
            }.get(x, x)
        )

        with st.expander("Agent Context (JSON)"):
            context_str = st.text_area(
                "Context",
                value='{}',
                height=120,
                label_visibility="collapsed"
            )

    with col2:
        task = st.text_area(
            "Task / Prompt",
            placeholder="Describe what you need this agent to do...",
            height=120,
        )

        run_disabled = not llm_ready
        run_label = "🚀 Run Agent" if llm_ready else "🔒 Run Agent (set API key first)"

        if st.button(run_label, use_container_width=True, disabled=run_disabled):
            if task:
                with st.spinner(f"Running {agent_id} via {llm_provider}..."):
                    t0 = time.time()
                    try:
                        context = json.loads(context_str) if context_str.strip() else {}
                    except json.JSONDecodeError:
                        context = {}

                    from src.teams.orchestrator import run_agent
                    result = run_agent(agent_id, task, context)
                    duration = time.time() - t0

                verdict_color = {
                    "pass": "#00d4aa",
                    "warn": "#ffbe0b",
                    "block": "#f72585",
                    "error": "#f72585",
                }.get(result.get("ethics_verdict", "pass"), "#888")

                if result["success"]:
                    # ── Save to history for Export tab ──────────────────────
                    if "agent_history" not in st.session_state:
                        st.session_state.agent_history = []
                    st.session_state.agent_history.insert(0, {
                        "timestamp": time.strftime("%H:%M:%S"),
                        "agent_id": result["agent_id"],
                        "task": task,
                        "result": result["result"],
                        "ethics_verdict": result.get("ethics_verdict", "pass"),
                        "metadata": result.get("metadata", {}),
                    })
                    # Keep max 20 in history
                    st.session_state.agent_history = st.session_state.agent_history[:20]

                    st.markdown(f"""
                    <div class="agent-card">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                        <strong style="color:#00d4aa;">Agent: {result['agent_id']}</strong>
                        <span style="color:{verdict_color};font-size:0.8rem;">
                          Ethics: {result['ethics_verdict'].upper()}
                        </span>
                      </div>
                      <p style="color:#888;font-size:0.75rem;margin-bottom:0.5rem;">
                        ⏱ {duration:.2f}s | ✓ Success via {llm_provider}
                      </p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("**Output:**")
                    st.markdown(result["result"])

                    # ── Quick Export buttons ─────────────────────────────────
                    st.markdown("**📥 Export hasil ini:**")
                    from src.tools.export_manager import ExportPayload, export as do_export
                    from datetime import datetime as _dt
                    _payload = ExportPayload(
                        title=f"{result['agent_id']} — {task[:50]}",
                        agent_id=result["agent_id"],
                        task=task,
                        content=result["result"],
                        metadata=result.get("metadata", {}),
                    )
                    qcols = st.columns(6)
                    for _qi, (_fmt, _icon) in enumerate([
                        ("pdf","📄"), ("xlsx","📊"), ("csv","📋"),
                        ("json","🔧"), ("markdown","📝"), ("txt","📃")
                    ]):
                        with qcols[_qi]:
                            try:
                                _fb, _mime, _fn = do_export(_payload, _fmt)
                                st.download_button(
                                    label=_icon + " " + _fmt.upper(),
                                    data=_fb,
                                    file_name=_fn,
                                    mime=_mime,
                                    use_container_width=True,
                                    key=f"quick_export_{_fmt}_{time.time()}",
                                )
                            except Exception as _e:
                                st.caption(f"{_icon} {_fmt}: {str(_e)[:30]}")

                    with st.expander("Metadata"):
                        st.json(result.get("metadata", {}))
                else:
                    # Friendly error with fix guidance
                    err_msg = result.get("result", "Unknown error")
                    st.error(f"**Agent failed:** {err_msg}")

                    if "No LLM available" in err_msg or "connection" in err_msg.lower():
                        st.info(
                            "💡 **Fix:** Buka tab **⚙️ Settings** dan set salah satu API key. "
                            "Groq paling mudah — gratis di [console.groq.com](https://console.groq.com)"
                        )
            else:
                st.warning("Please enter a task")


# ─── Tab 2: Crypto ───────────────────────────────────────────────────────────

with tab2:
    st.markdown("### 💰 Crypto Operations")

    from src.core.crypto_manager import get_crypto, Chain

    crypto = get_crypto()
    addresses = crypto.get_all_addresses()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 1.5rem;">₿</div>
          <div style="color: #f7931a; font-weight: bold; font-size: 0.9rem;">Bitcoin</div>
          <div style="color: #888; font-size: 0.65rem; word-break: break-all; margin-top: 4px;">
            {addresses['bitcoin']}
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 1.5rem;">Ξ</div>
          <div style="color: #627eea; font-weight: bold; font-size: 0.9rem;">Ethereum / EVM</div>
          <div style="color: #888; font-size: 0.65rem; word-break: break-all; margin-top: 4px;">
            {addresses['ethereum_evm']}
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 1.5rem;">◎</div>
          <div style="color: #9945ff; font-weight: bold; font-size: 0.9rem;">Solana</div>
          <div style="color: #888; font-size: 0.65rem; word-break: break-all; margin-top: 4px;">
            {addresses['solana']}
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Generate Invoice")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        invoice_chain = st.selectbox("Chain", ["ethereum", "bitcoin", "solana", "polygon"])
    with col2:
        invoice_amount = st.number_input("Amount", min_value=0.0001, value=0.01, step=0.001, format="%.4f")
    with col3:
        invoice_memo = st.text_input("Memo / Description", placeholder="Service payment...")

    if st.button("📄 Generate Invoice"):
        try:
            chain_enum = Chain(invoice_chain)
            invoice = crypto.generate_invoice(chain_enum, invoice_amount, invoice_memo)
            st.success("Invoice generated!")
            st.code(json.dumps(invoice, indent=2), language="json")

            # QR code placeholder
            st.info(f"💡 Payment URI: `{invoice.get('payment_uri', '')}`")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("#### Verify Payment")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        verify_chain = st.selectbox("Chain ", ["ethereum", "bitcoin", "solana"])
    with col2:
        verify_amount = st.number_input("Expected Amount", min_value=0.0, value=0.01, format="%.4f")
    with col3:
        verify_tx = st.text_input("Transaction Hash / Signature", placeholder="0x...")

    if st.button("✅ Verify Payment"):
        if verify_tx:
            with st.spinner("Checking blockchain..."):
                try:
                    chain_enum = Chain(verify_chain)
                    verified = crypto.verify_payment(chain_enum, verify_tx, verify_amount)
                    if verified:
                        st.success(f"✅ Payment VERIFIED! {verify_amount} on {verify_chain}")
                    else:
                        st.error(f"❌ Payment NOT found or insufficient amount")
                except Exception as e:
                    st.error(f"Verification error: {e}")
        else:
            st.warning("Enter a transaction hash")


# ─── Tab 3: Monitor ──────────────────────────────────────────────────────────

with tab3:
    st.markdown("### 📊 System Monitor")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 2rem;">{'🟢' if status['ollama'] else '🔴'}</div>
          <div style="font-weight: bold;">Ollama</div>
          <div style="color: #888; font-size: 0.8rem;">{'Running' if status['ollama'] else 'Stopped'}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 2rem;">{'🌐' if status['online'] else '📡'}</div>
          <div style="font-weight: bold;">Network</div>
          <div style="color: #888; font-size: 0.8rem;">{'Online' if status['online'] else 'Offline'}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 2rem;">⚡</div>
          <div style="font-weight: bold;">Latency</div>
          <div style="color: #888; font-size: 0.8rem;">{status['latency_ms']}ms</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        models = get_ollama_models()
        st.markdown(f"""
        <div class="metric-card">
          <div style="font-size: 2rem;">🤖</div>
          <div style="font-weight: bold;">Models</div>
          <div style="color: #888; font-size: 0.8rem;">{len(models)} loaded</div>
        </div>""", unsafe_allow_html=True)

    if models:
        st.markdown("#### Available Ollama Models")
        for m in models:
            st.markdown(f"- `{m}`")

    st.markdown("---")
    if st.button("🔄 Refresh Status"):
        st.cache_data.clear()
        st.rerun()

    # Audit log viewer
    st.markdown("#### Recent Audit Log")
    audit_path = os.getenv("AUDIT_LOG_PATH", "./data/audit.log")
    if os.path.exists(audit_path):
        with open(audit_path) as f:
            lines = f.readlines()[-20:]
        entries = []
        for line in reversed(lines):
            try:
                entries.append(json.loads(line.strip()))
            except Exception:
                pass
        if entries:
            st.dataframe(entries, use_container_width=True)
        else:
            st.info("No audit entries yet")
    else:
        st.info("Audit log will appear here after running agents")


# ─── Tab 4: Pipelines ────────────────────────────────────────────────────────

with tab4:
    st.markdown("### 🔗 Multi-Agent Pipelines")

    st.markdown("""
    <div class="agent-card">
      <strong style="color: #00d4aa;">🎯 Sales Pipeline</strong>
      <p style="color: #888; margin: 0.5rem 0 0;">Research → LeadGen → ContentWriter → SalesCloser → EthicsCheck</p>
    </div>
    """, unsafe_allow_html=True)

    pipeline_task = st.text_area(
        "Pipeline Task",
        placeholder="E.g.: Find and approach B2B SaaS companies in Southeast Asia needing AI automation...",
        height=100,
    )

    if st.button("🚀 Run Sales Pipeline", use_container_width=True):
        if pipeline_task:
            with st.spinner("Running multi-agent pipeline... (this may take a few minutes)"):
                from src.teams.orchestrator import run_sales_pipeline
                result = run_sales_pipeline(pipeline_task)

            if result.get("ethics_approved"):
                st.success("✅ Pipeline completed — Ethics Approved")
            else:
                st.warning("⚠️ Pipeline completed — Ethics review flagged content")

            st.markdown("#### Final Output")
            st.markdown(result.get("final_output", "No output"))

            with st.expander("Pipeline Steps"):
                for step in result.get("steps", []):
                    st.markdown(f"**{step.get('agent')}:**")
                    st.markdown(step.get("output", ""))
                    st.markdown("---")
        else:
            st.warning("Enter a pipeline task")



# ─── Tab 5: Export ───────────────────────────────────────────────────────────

with tab5:
    st.markdown("### 📥 Export Reports")
    st.caption("Convert any agent output ke PDF, Excel, CSV, JSON, Markdown, atau TXT")

    from src.tools.export_manager import ExportPayload, export, EXPORT_FORMATS
    from datetime import datetime

    # ── History store ─────────────────────────────────────────────────────────
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []

    # ── Input: Paste or use history ───────────────────────────────────────────
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 1️⃣ Pilih Sumber Konten")

        source_mode = st.radio(
            "Sumber",
            ["✍️ Ketik / Paste manual", "🕐 Dari riwayat agent (tab Agents)"],
            label_visibility="collapsed"
        )

        if source_mode == "🕐 Dari riwayat agent (tab Agents)":
            history = st.session_state.get("agent_history", [])
            if not history:
                st.info("Belum ada riwayat. Jalankan agent di tab 🤖 Agents dulu, lalu kembali ke sini.")
                selected_result = None
            else:
                options = [
                    f"[{h['timestamp']}] {h['agent_id']} — {h['task'][:50]}..."
                    for h in history
                ]
                chosen_idx = st.selectbox("Pilih hasil agent:", range(len(options)),
                                          format_func=lambda i: options[i])
                selected_result = history[chosen_idx]

                st.markdown(f"""
                <div class="agent-card" style="font-size:0.8rem;">
                  <b>Agent:</b> {selected_result['agent_id']}<br>
                  <b>Task:</b> {selected_result['task'][:80]}<br>
                  <b>Ethics:</b> {selected_result['ethics_verdict']}
                </div>
                """, unsafe_allow_html=True)

                export_title = st.text_input(
                    "Judul Laporan",
                    value=f"Report {selected_result['agent_id']} — {selected_result['task'][:40]}"
                )
                export_content = selected_result["result"]
                export_task = selected_result["task"]
                export_agent = selected_result["agent_id"]
                export_meta = selected_result.get("metadata", {})

        else:
            selected_result = None
            export_title = st.text_input("Judul Laporan", value="CATERYA Report")
            export_task = st.text_input("Deskripsi Task", value="Manual export")
            export_agent = st.selectbox(
                "Agent ID",
                ["research", "content_writer", "finance", "lead_gen", "custom"],
                index=0
            )
            export_content = st.text_area(
                "Konten (markdown/teks/JSON)",
                height=250,
                placeholder=(
                    "Paste hasil analisa, laporan, atau data di sini...\n\n"
                    "Bisa berupa:\n"
                    "• Teks biasa\n"
                    "• Markdown dengan heading (# ## ###)\n"
                    "• JSON array atau object\n"
                    "• Hasil copy-paste dari agent"
                )
            )
            export_meta = {}

    with col_right:
        st.markdown("#### 2️⃣ Pilih Format & Download")

        # Format selection grid
        fmt_cols = st.columns(3)
        format_info = {
            "pdf":      ("📄", "PDF",      "Laporan branded, siap print/share"),
            "xlsx":     ("📊", "Excel",    "Multi-sheet, bisa diedit"),
            "csv":      ("📋", "CSV",      "Data tabular, buka di Sheets/Excel"),
            "json":     ("🔧", "JSON",     "Structured data untuk developer"),
            "markdown": ("📝", "Markdown", "Format dokumen universal"),
            "txt":      ("📃", "TXT",      "Plain text, universal"),
        }

        selected_format = st.radio(
            "Format output:",
            list(format_info.keys()),
            format_func=lambda f: f"{format_info[f][0]} {format_info[f][1]}",
            horizontal=True,
        )

        # Show format description
        icon, fname, fdesc = format_info[selected_format]
        st.markdown(f"""
        <div style="background:#1a1a2e;border-left:3px solid #00d4aa;
                    padding:0.6rem 1rem;border-radius:4px;margin:0.5rem 0;
                    font-size:0.85rem;color:#ccc;">
          {icon} <b>{fname}</b> — {fdesc}
        </div>
        """, unsafe_allow_html=True)

        # Preview panel
        content_ready = bool(
            (selected_result and export_content) or
            (source_mode != "🕐 Dari riwayat agent (tab Agents)" and export_content)
        )

        if content_ready:
            with st.expander("👁 Preview konten (50 baris pertama)", expanded=False):
                preview_lines = export_content.split('\n')[:50]
                st.code('\n'.join(preview_lines), language="markdown")
                if len(export_content.split('\n')) > 50:
                    st.caption(f"... +{len(export_content.split(chr(10))) - 50} baris lagi")

        st.markdown("---")

        # ── Generate & Download ────────────────────────────────────────────────
        if st.button(f"{icon} Generate & Download {fname}", use_container_width=True,
                     type="primary", disabled=not content_ready):
            if not content_ready:
                st.warning("Isi konten dulu di panel kiri")
            else:
                with st.spinner(f"Generating {fname}..."):
                    try:
                        payload = ExportPayload(
                            title=export_title or "CATERYA Report",
                            agent_id=export_agent if not selected_result else selected_result["agent_id"],
                            task=export_task if not selected_result else selected_result["task"],
                            content=export_content,
                            metadata=export_meta,
                            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        )
                        file_bytes, mime, filename = export(payload, selected_format)

                        st.success(f"✅ {fname} siap! ({len(file_bytes):,} bytes)")
                        st.download_button(
                            label=f"⬇️ Download {filename}",
                            data=file_bytes,
                            file_name=filename,
                            mime=mime,
                            use_container_width=True,
                        )

                    except ImportError as e:
                        st.error(f"Library belum terinstall: {e}")
                        st.info("Push update ke Streamlit Cloud — `reportlab` dan `openpyxl` sudah ditambahkan ke requirements.txt")
                    except Exception as e:
                        st.error(f"Export gagal: {type(e).__name__}: {e}")

    # ── Batch Export ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📦 Batch Export — Download Semua Format Sekaligus")

    history = st.session_state.get("agent_history", [])
    if not history:
        st.info("Jalankan beberapa agent dulu, lalu batch export semua hasilnya sekaligus.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            batch_formats = st.multiselect(
                "Format yang mau di-export:",
                list(format_info.keys()),
                default=["pdf", "xlsx", "json"],
                format_func=lambda f: f"{format_info[f][0]} {format_info[f][1]}"
            )
        with col2:
            batch_idx_options = [
                f"[{h['timestamp']}] {h['agent_id']}" for h in history
            ]
            st.caption(f"{len(history)} hasil tersedia")

        if st.button("📦 Batch Export (ZIP)", use_container_width=True) and batch_formats:
            import zipfile
            with st.spinner(f"Generating {len(history) * len(batch_formats)} files..."):
                try:
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for h in history:
                            p = ExportPayload(
                                title=f"{h['agent_id']} — {h['task'][:40]}",
                                agent_id=h["agent_id"],
                                task=h["task"],
                                content=h["result"],
                                metadata=h.get("metadata", {}),
                                timestamp=h.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                            )
                            for fmt in batch_formats:
                                try:
                                    fb, _, fn = export(p, fmt)
                                    zf.writestr(fn, fb)
                                except Exception:
                                    pass

                    ts = datetime.now().strftime('%Y%m%d_%H%M')
                    zip_bytes = zip_buf.getvalue()
                    st.success(f"✅ ZIP siap! {len(batch_formats) * len(history)} files, {len(zip_bytes):,} bytes")
                    st.download_button(
                        label=f"⬇️ Download CATERYA_Reports_{ts}.zip",
                        data=zip_bytes,
                        file_name=f"CATERYA_Reports_{ts}.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Batch export gagal: {e}")

# ─── Tab 6: Settings ─────────────────────────────────────────────────────────

with tab6:
    st.markdown("### ⚙️ Settings & API Keys")

    # ── Runtime key store (session-scoped, never written to disk) ──────────────
    if "runtime_keys" not in st.session_state:
        st.session_state.runtime_keys = {}

    def _set_key(env_key: str, value: str):
        """Set key in both session state and os.environ for this session."""
        if value and value.strip():
            st.session_state.runtime_keys[env_key] = value.strip()
            os.environ[env_key] = value.strip()

    def _get_key(env_key: str) -> str:
        """Get key — check session state, then env, then Streamlit secrets."""
        if env_key in st.session_state.runtime_keys:
            return st.session_state.runtime_keys[env_key]
        val = os.environ.get(env_key, "")
        if not val:
            try:
                import streamlit as _st
                val = _st.secrets.get(env_key, "")
            except Exception:
                pass
        return val or ""

    def _mask(key: str) -> str:
        """Show only first 8 chars + *** for display."""
        if not key:
            return ""
        return key[:8] + "•" * min(12, max(4, len(key) - 8))

    def _status_badge(key: str) -> str:
        if key:
            return "🟢 **Set**"
        return "🔴 Not set"

    # ── Section 1: Ollama (Local / Self-hosted) ────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🦙 Ollama — Local LLM (Primary, 100% Offline)")

    # Detect if running on Streamlit Cloud
    is_cloud = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit" or \
               os.path.exists("/mount/src")

    if is_cloud:
        st.info("""
        **Kamu sedang di Streamlit Cloud** — Ollama tidak bisa diinstall di sini.

        Untuk pakai Ollama dari cloud, kamu perlu **expose Ollama dari laptop/server kamu**:

        **Cara 1 — Tailscale (Recommended):**
        ```
        # Di laptop kamu
        tailscale up
        OLLAMA_HOST=0.0.0.0 ollama serve
        ```
        Lalu set URL: `http://[tailscale-ip]:11434`

        **Cara 2 — ngrok:**
        ```
        # Di laptop kamu (terminal 1)
        OLLAMA_HOST=0.0.0.0 ollama serve
        # Terminal 2
        ngrok http 11434
        ```
        Copy URL dari ngrok (misal `https://abc123.ngrok-free.app`) → paste di field URL di bawah.

        **Atau gunakan Free Cloud APIs di bawah** — tidak perlu laptop online.
        """)

    col1, col2 = st.columns([3, 1])
    with col1:
        current_url = _get_key("OLLAMA_BASE_URL") or "http://localhost:11434"
        ollama_url_input = st.text_input(
            "Ollama API URL",
            value=current_url,
            placeholder="http://localhost:11434",
            help=(
                "Format yang benar:\n"
                "• Lokal: http://localhost:11434\n"
                "• Tailscale: http://100.64.x.x:11434\n"
                "• ngrok: https://abc123.ngrok-free.app\n\n"
                "❌ BUKAN: ollama.com/username (itu halaman profil, bukan API)"
            )
        )
        # Validate URL format
        if ollama_url_input and not ollama_url_input.startswith("http"):
            st.warning("⚠️ URL harus dimulai dengan `http://` atau `https://` — bukan `ollama.com/...`")
        if "ollama.com" in ollama_url_input and "/api" not in ollama_url_input:
            st.error(
                "❌ `ollama.com/username` adalah halaman profil publik, bukan endpoint API.\n\n"
                "Ollama tidak punya public cloud API. Kamu perlu:\n"
                "- Jalankan Ollama di laptop sendiri, lalu expose via Tailscale/ngrok\n"
                "- Atau gunakan Groq/Together di bawah (gratis, tidak butuh Ollama)"
            )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save URL", key="save_ollama_url"):
            _set_key("OLLAMA_BASE_URL", ollama_url_input)
            st.success("Saved!")

    # Ollama API key (ngrok/tunnel auth or future Ollama Cloud)
    col1, col2 = st.columns([3, 1])
    with col1:
        ollama_key_input = st.text_input(
            "Ollama Auth Token (opsional — hanya jika Ollama kamu pakai autentikasi)",
            type="password",
            placeholder="Kosongkan untuk Ollama lokal biasa",
            help="Biasanya kosong. Isi hanya jika kamu set OLLAMA_AUTH_TOKEN di server."
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save", key="save_ollama_key"):
            _set_key("OLLAMA_API_KEY", ollama_key_input)
            st.success("Saved!")

    existing_ollama_key = _get_key("OLLAMA_API_KEY")
    if existing_ollama_key:
        st.caption(f"Auth token aktif: `{_mask(existing_ollama_key)}`")

    col1, col2 = st.columns(2)
    with col1:
        default_model_input = st.text_input(
            "Default Model",
            value=_get_key("OLLAMA_DEFAULT_MODEL") or "llama3.3",
            help="Nama model sesuai output: ollama list"
        )
        if st.button("💾 Save Model", key="save_model"):
            _set_key("OLLAMA_DEFAULT_MODEL", default_model_input)
            st.success("Saved!")

    with col2:
        if st.button("🔌 Test Ollama Connection", key="test_ollama", use_container_width=True):
            test_url = _get_key("OLLAMA_BASE_URL") or ollama_url_input or "http://localhost:11434"

            # Validate URL format first
            if not test_url.startswith("http"):
                st.error(
                    f"❌ URL tidak valid: `{test_url}`\n\n"
                    "URL harus format: `http://localhost:11434` atau `https://abc123.ngrok-free.app`"
                )
            elif "ollama.com" in test_url and "/api" not in test_url:
                st.error(
                    "❌ `ollama.com/username` bukan API endpoint.\n"
                    "Ollama tidak punya cloud API publik. Gunakan Groq/Together di bawah."
                )
            else:
                with st.spinner(f"Testing {test_url}..."):
                    try:
                        import httpx
                        # Try /api/tags endpoint
                        r = httpx.get(f"{test_url.rstrip('/')}/api/tags", timeout=5)
                        r.raise_for_status()
                        data = r.json()
                        models = [m["name"] for m in data.get("models", [])]
                        _set_key("OLLAMA_BASE_URL", test_url)
                        if models:
                            st.success(f"✅ Terhubung! Models tersedia: {', '.join(models[:5])}")
                        else:
                            st.success("✅ Terhubung! Belum ada model. Jalankan: `ollama pull phi4`")
                    except httpx.ConnectError:
                        st.error(
                            f"❌ Tidak bisa reach `{test_url}`\n\n"
                            "**Checklist:**\n"
                            "- Ollama running? → `ollama serve`\n"
                            "- Exposed ke network? → `OLLAMA_HOST=0.0.0.0 ollama serve`\n"
                            "- Tailscale/ngrok aktif dan URL benar?"
                        )
                    except httpx.HTTPStatusError as e:
                        st.error(f"❌ HTTP {e.response.status_code} — server ada tapi error")
                    except Exception as e:
                        st.error(f"❌ Error: {type(e).__name__}: {e}")

    # ── Section 2: Free Cloud API Keys ───────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ☁️ Free Cloud LLM APIs (Fallback when Ollama unavailable)")
    st.caption("All free tier — no credit card required. Used only if Ollama is unreachable.")

    providers = [
        {
            "name": "Groq",
            "env": "GROQ_API_KEY",
            "icon": "⚡",
            "desc": "Fastest free tier — 14,400 req/day, llama-3.3-70b",
            "signup": "https://console.groq.com",
            "placeholder": "gsk_...",
        },
        {
            "name": "Together.ai",
            "env": "TOGETHER_API_KEY",
            "icon": "🤝",
            "desc": "Free $25 credits on signup, Llama-3.3-70b",
            "signup": "https://api.together.xyz",
            "placeholder": "...",
        },
        {
            "name": "Fireworks.ai",
            "env": "FIREWORKS_API_KEY",
            "icon": "🎆",
            "desc": "Free tier — DeepSeek-Coder, fast inference",
            "signup": "https://fireworks.ai",
            "placeholder": "fw_...",
        },
        {
            "name": "HuggingFace",
            "env": "HF_TOKEN",
            "icon": "🤗",
            "desc": "Free inference API — Qwen2.5, Llama, etc.",
            "signup": "https://huggingface.co/settings/tokens",
            "placeholder": "hf_...",
        },
    ]

    for p in providers:
        existing = _get_key(p["env"])
        status = _status_badge(existing)
        with st.expander(f"{p['icon']} **{p['name']}** — {status}", expanded=not bool(existing)):
            st.caption(f"{p['desc']} | [Sign up free →]({p['signup']})")
            col1, col2 = st.columns([4, 1])
            with col1:
                new_key = st.text_input(
                    f"{p['name']} API Key",
                    type="password",
                    placeholder=p["placeholder"],
                    key=f"key_input_{p['env']}",
                    label_visibility="collapsed",
                )
            with col2:
                if st.button("💾 Save", key=f"save_{p['env']}"):
                    if new_key.strip():
                        _set_key(p["env"], new_key)
                        st.success("Saved for this session!")
                        st.rerun()
                    else:
                        st.warning("Enter a key first")

            if existing:
                st.caption(f"Active key: `{_mask(existing)}`")
                if st.button(f"🗑 Clear {p['name']} key", key=f"clear_{p['env']}"):
                    st.session_state.runtime_keys.pop(p["env"], None)
                    os.environ.pop(p["env"], None)
                    st.rerun()

    # ── Section 3: Persist to .env ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💾 Save Keys to .env File")
    st.caption("Keys entered above are session-only (lost on restart). Save to .env for persistence.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Export keys to .env", use_container_width=True):
            env_path = ".env"
            try:
                # Read existing .env
                existing_lines = []
                if os.path.exists(env_path):
                    with open(env_path) as f:
                        existing_lines = f.readlines()

                # Update or append keys
                runtime = st.session_state.runtime_keys
                updated_keys = set()
                new_lines = []
                for line in existing_lines:
                    key = line.split("=")[0].strip()
                    if key in runtime:
                        new_lines.append(f"{key}={runtime[key]}\n")
                        updated_keys.add(key)
                    else:
                        new_lines.append(line)

                # Add new keys not already in file
                for key, val in runtime.items():
                    if key not in updated_keys:
                        new_lines.append(f"{key}={val}\n")

                with open(env_path, "w") as f:
                    f.writelines(new_lines)

                st.success(f"✅ Saved {len(runtime)} keys to .env")
                st.caption("Restart dashboard to apply. Never commit .env to git!")
            except Exception as e:
                st.error(f"Cannot write .env: {e}")
                st.caption("On Streamlit Cloud, use Settings → Secrets instead.")

    with col2:
        if st.button("📋 Show .env template", use_container_width=True):
            runtime = st.session_state.runtime_keys
            if runtime:
                lines = [f"{k}=YOUR_VALUE_HERE" for k in runtime.keys()]
                st.code("\n".join(lines), language="bash")
                st.caption("Copy these to Streamlit Cloud → Settings → Secrets")
            else:
                st.info("No keys set in this session yet")

    # ── Section 4: Streamlit Cloud Secrets Guide ──────────────────────────────
    with st.expander("☁️ How to add keys on Streamlit Cloud (permanent)"):
        st.markdown("""
        Keys entered in this UI are **session-only** on Streamlit Cloud (cleared on restart).

        **For permanent keys on Streamlit Cloud:**
        1. Go to your app at **share.streamlit.io**
        2. Click **⋮ menu → Settings → Secrets**
        3. Add in TOML format:
        ```toml
        GROQ_API_KEY = "gsk_your_key_here"
        TOGETHER_API_KEY = "your_key"
        OLLAMA_BASE_URL = "http://100.64.x.x:11434"
        OLLAMA_API_KEY = "your_ollama_cloud_key"
        ```
        4. Save — app restarts with keys loaded

        **For local .env (laptop/Docker):**
        Edit `.env` file directly, or use "Export keys to .env" button above.
        """)

    # ── Section 5: LLM Priority & Security ───────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔒 Security & Behavior")

    col1, col2 = st.columns(2)
    with col1:
        ethics_enabled = st.toggle("Ethics Guard", value=True)
        if ethics_enabled != (os.getenv("ETHICS_GUARD_ENABLED", "true") == "true"):
            os.environ["ETHICS_GUARD_ENABLED"] = str(ethics_enabled).lower()
        st.caption("Blocks harmful agent outputs")

    with col2:
        st.markdown("**LLM Priority Order:**")
        st.markdown("""
        1. 🦙 Ollama (local, offline-first)
        2. ⚡ Groq (free, fastest cloud)
        3. 🤝 Together.ai (free)
        4. 🎆 Fireworks.ai (free)
        5. 🤗 HuggingFace (free)
        """)

    # ── Section 6: Ollama Model Management ────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📦 Ollama Model Management")

    if is_cloud:
        st.info(
            "Model management hanya bisa dilakukan di laptop/server tempat Ollama running.\n\n"
            "**Di laptop kamu:**\n"
            "```bash\n"
            "ollama pull phi4          # ~4GB, fast\n"
            "ollama pull llama3.3      # ~4GB, general\n"
            "ollama pull qwen2.5:7b   # ~4GB, multilingual\n"
            "ollama pull deepseek-coder  # coding\n"
            "```"
        )
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 List Installed Models", use_container_width=True):
                try:
                    from src.core.llm_router import get_router
                    models = get_router().ollama_models
                    if models:
                        for m in models:
                            st.markdown(f"- `{m}`")
                    else:
                        st.info("No models installed yet.")
                except Exception as e:
                    st.error(f"Cannot reach Ollama: {e}")
        with col2:
            if st.button("📥 Pull All Required Models", use_container_width=True):
                with st.spinner("Pulling models..."):
                    try:
                        from src.core.llm_router import get_router
                        get_router().pull_required_models()
                        st.success("Models pulled!")
                    except Exception as e:
                        st.error(f"Error: {e}")

        model_to_pull = st.text_input("Pull specific model:", placeholder="e.g. qwen2.5:7b")
        if st.button("⬇️ Pull Model") and model_to_pull:
            import subprocess
            import shutil
            if not shutil.which("ollama"):
                st.error("❌ `ollama` binary not found. Install Ollama first: https://ollama.ai")
            else:
                with st.spinner(f"Pulling {model_to_pull}..."):
                    r = subprocess.run(
                        ["ollama", "pull", model_to_pull],
                        capture_output=True, text=True
                    )
                    if r.returncode == 0:
                        st.success(f"✅ Pulled {model_to_pull}")
                    else:
                        st.error(f"Failed: {r.stderr[:300]}")

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #444; font-size: 0.75rem; padding: 1rem;">
      CATERYA Agentic Enterprise v1.0<br>
      © 2026 Caterya Tech — All Rights Reserved<br>
      Keys are stored in session memory only — never logged or sent anywhere
    </div>
    """, unsafe_allow_html=True)
