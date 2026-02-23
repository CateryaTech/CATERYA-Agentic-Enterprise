"""
CATERYA Agentic Enterprise — Onboarding Wizard
Setup pertama kali: konfigurasi model, wallet, agents, dan profil bisnis.
Ini adalah halaman Streamlit yang ditampilkan saat pertama install.
© 2026 Caterya Tech. All Rights Reserved.
"""

import json
import os
from pathlib import Path

import streamlit as st

ONBOARDING_STATE_FILE = "data/onboarding_complete.json"


def is_onboarding_complete() -> bool:
    return Path(ONBOARDING_STATE_FILE).exists()


def mark_onboarding_complete(config: dict):
    Path(ONBOARDING_STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(ONBOARDING_STATE_FILE, "w") as f:
        json.dump({"completed_at": str(__import__("datetime").datetime.utcnow()), **config}, f, indent=2)


def render_onboarding():
    """Main onboarding wizard — call this from app.py if not complete."""

    st.markdown("""
    <style>
    .onboard-header { text-align: center; padding: 2rem 0; }
    .step-card { background: #1e1e2e; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; }
    .step-badge { background: #6366f1; color: white; border-radius: 999px; padding: 0.2rem 0.8rem; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="onboard-header">', unsafe_allow_html=True)
    st.title("⚡ Selamat Datang di CATERYA")
    st.caption("Ayo setup sistem Anda dalam 5 menit. Hanya perlu sekali.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Progress bar
    if "onboard_step" not in st.session_state:
        st.session_state.onboard_step = 1
    if "onboard_data" not in st.session_state:
        st.session_state.onboard_data = {}

    total_steps = 5
    progress = st.session_state.onboard_step / total_steps
    st.progress(progress, text=f"Langkah {st.session_state.onboard_step} dari {total_steps}")

    step = st.session_state.onboard_step

    # ── Step 1: Profil Bisnis ─────────────────────────────────────────────────
    if step == 1:
        st.subheader("🏢 Step 1: Profil Bisnis Anda")
        with st.form("step1"):
            biz_name = st.text_input("Nama Bisnis / Brand", placeholder="e.g. Toko Digital Pak Budi")
            industry = st.selectbox("Industri", [
                "E-commerce", "Jasa Konsultasi", "SaaS / Tech", "Konten & Media",
                "Keuangan", "Kesehatan", "Properti", "Kuliner", "Lainnya"
            ])
            biz_desc = st.text_area(
                "Deskripsikan bisnis Anda (2-3 kalimat)",
                placeholder="Kami menjual produk digital untuk UMKM. Target pasar kami...",
                height=100
            )
            col1, col2 = st.columns(2)
            with col1:
                owner_name = st.text_input("Nama Anda (Owner/Founder)")
            with col2:
                owner_email = st.text_input("Email", placeholder="anda@bisnis.com")

            submitted = st.form_submit_button("Lanjut →", use_container_width=True, type="primary")
            if submitted:
                if not biz_name or not owner_email:
                    st.error("Nama bisnis dan email wajib diisi.")
                else:
                    st.session_state.onboard_data.update({
                        "biz_name": biz_name, "industry": industry,
                        "biz_desc": biz_desc, "owner_name": owner_name,
                        "owner_email": owner_email,
                    })
                    st.session_state.onboard_step = 2
                    st.rerun()

    # ── Step 2: LLM Setup ─────────────────────────────────────────────────────
    elif step == 2:
        st.subheader("🤖 Step 2: Pilih Model AI")
        st.info("CATERYA bisa jalan 100% offline menggunakan Ollama, atau pakai cloud API gratis.")

        with st.form("step2"):
            llm_mode = st.radio("Mode LLM Utama", [
                "🏔️ Offline (Ollama) — 100% private, butuh GPU/CPU kencang",
                "☁️ Cloud Free Tier (Groq/Together) — butuh internet, gratis",
                "🔀 Hybrid — Ollama dulu, fallback ke cloud kalau offline",
            ], index=2)

            if "Ollama" in llm_mode or "Hybrid" in llm_mode:
                st.markdown("**Ollama Settings**")
                ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
                default_model = st.selectbox("Model Default", [
                    "llama3.3", "qwen2.5:7b", "phi4", "mistral", "deepseek-coder", "qwen2.5:32b"
                ])
            else:
                ollama_url = ""
                default_model = ""

            if "Cloud" in llm_mode or "Hybrid" in llm_mode:
                st.markdown("**Cloud API Keys (opsional, bisa diisi nanti)**")
                groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
                together_key = st.text_input("Together.ai Key", type="password", placeholder="...")
            else:
                groq_key = ""
                together_key = ""

            submitted = st.form_submit_button("Lanjut →", use_container_width=True, type="primary")
            if submitted:
                st.session_state.onboard_data.update({
                    "llm_mode": llm_mode, "ollama_url": ollama_url,
                    "default_model": default_model, "groq_key": groq_key,
                    "together_key": together_key,
                })
                st.session_state.onboard_step = 3
                st.rerun()

        if st.button("← Kembali"):
            st.session_state.onboard_step = 1
            st.rerun()

    # ── Step 3: Pilih Agents ──────────────────────────────────────────────────
    elif step == 3:
        st.subheader("🧠 Step 3: Aktifkan Agents")
        st.caption("Pilih agent yang relevan dengan bisnis Anda. Bisa diubah kapan saja.")

        AGENTS = {
            "lead_gen": ("🎯 Lead Generation", "Cari & kualifikasi prospek otomatis"),
            "content_writer": ("✍️ Content Writer", "Buat konten marketing & SEO"),
            "sales_closer": ("💼 Sales Closer", "Handle objeksi & closing otomatis"),
            "support": ("💬 Customer Support", "Auto-reply customer inquiry"),
            "finance": ("💰 Finance", "Invoice, pembayaran, laporan keuangan"),
            "code_improver": ("🔧 Code Improver", "Review & refactor code"),
            "crypto_ops": ("₿ Crypto Ops", "Operasi on-chain BTC/ETH/SOL"),
            "research": ("🔬 Research", "Market intelligence otomatis"),
        }

        selected = []
        cols = st.columns(2)
        for i, (aid, (label, desc)) in enumerate(AGENTS.items()):
            with cols[i % 2]:
                checked = st.checkbox(f"**{label}**\n\n{desc}", value=True, key=f"agent_{aid}")
                if checked:
                    selected.append(aid)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Kembali"):
                st.session_state.onboard_step = 2
                st.rerun()
        with col2:
            if st.button("Lanjut →", use_container_width=True, type="primary"):
                st.session_state.onboard_data["enabled_agents"] = selected
                st.session_state.onboard_step = 4
                st.rerun()

    # ── Step 4: Crypto Wallet ─────────────────────────────────────────────────
    elif step == 4:
        st.subheader("₿ Step 4: Crypto Wallet (Opsional)")
        data = st.session_state.onboard_data

        with st.form("step4"):
            use_crypto = st.checkbox(
                "Aktifkan fitur crypto (terima pembayaran BTC/ETH/SOL)",
                value="crypto_ops" in data.get("enabled_agents", [])
            )

            if use_crypto:
                st.markdown("**Masukkan alamat wallet RECEIVE Anda:**")
                btc_addr = st.text_input("Bitcoin Address", placeholder="bc1q...")
                eth_addr = st.text_input("Ethereum Address", placeholder="0x...")
                sol_addr = st.text_input("Solana Address", placeholder="...")
                wallet_pass = st.text_input(
                    "Master Password Vault (untuk enkripsi lokal)",
                    type="password",
                    help="Digunakan untuk enkripsi AES-256 wallet vault lokal. Jangan sampai lupa!"
                )
            else:
                btc_addr = eth_addr = sol_addr = wallet_pass = ""

            submitted = st.form_submit_button("Lanjut →", use_container_width=True, type="primary")
            if submitted:
                st.session_state.onboard_data.update({
                    "use_crypto": use_crypto, "btc_addr": btc_addr,
                    "eth_addr": eth_addr, "sol_addr": sol_addr,
                })
                st.session_state.onboard_step = 5
                st.rerun()

        if st.button("← Kembali"):
            st.session_state.onboard_step = 3
            st.rerun()

    # ── Step 5: Review & Simpan ───────────────────────────────────────────────
    elif step == 5:
        st.subheader("✅ Step 5: Review & Mulai")
        data = st.session_state.onboard_data

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🏢 Bisnis**")
            st.write(f"- **Nama:** {data.get('biz_name', '-')}")
            st.write(f"- **Industri:** {data.get('industry', '-')}")
            st.write(f"- **Owner:** {data.get('owner_name', '-')}")

            st.markdown("**🤖 LLM**")
            mode = data.get('llm_mode', '')
            st.write(f"- **Mode:** {'Offline' if 'Offline' in mode else 'Cloud' if 'Cloud' in mode else 'Hybrid'}")
            if data.get("default_model"):
                st.write(f"- **Model:** {data.get('default_model')}")

        with col2:
            st.markdown("**🧠 Agents Aktif**")
            for a in data.get("enabled_agents", []):
                st.write(f"- {a}")

            if data.get("use_crypto"):
                st.markdown("**₿ Crypto**")
                if data.get("btc_addr"):
                    st.write(f"- BTC: `{data['btc_addr'][:15]}...`")
                if data.get("eth_addr"):
                    st.write(f"- ETH: `{data['eth_addr'][:15]}...`")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Kembali"):
                st.session_state.onboard_step = 4
                st.rerun()
        with col2:
            if st.button("🚀 Mulai CATERYA!", use_container_width=True, type="primary"):
                _apply_config(data)
                mark_onboarding_complete(data)
                st.success("Setup selesai! Redirecting ke dashboard...")
                st.balloons()
                st.session_state.onboard_step = 1
                st.session_state.onboard_data = {}
                st.rerun()


def _apply_config(data: dict):
    """Write config to .env and data files."""
    env_lines = [
        f"BIZ_NAME={data.get('biz_name', '')}",
        f"BIZ_INDUSTRY={data.get('industry', '')}",
        f"OWNER_EMAIL={data.get('owner_email', '')}",
        f"OLLAMA_BASE_URL={data.get('ollama_url', 'http://localhost:11434')}",
        f"OLLAMA_DEFAULT_MODEL={data.get('default_model', 'llama3.3')}",
        f"GROQ_API_KEY={data.get('groq_key', '')}",
        f"TOGETHER_API_KEY={data.get('together_key', '')}",
        f"ENABLED_AGENTS={','.join(data.get('enabled_agents', []))}",
        f"BTC_RECEIVE_ADDRESS={data.get('btc_addr', '')}",
        f"ETH_RECEIVE_ADDRESS={data.get('eth_addr', '')}",
        f"SOL_RECEIVE_ADDRESS={data.get('sol_addr', '')}",
        f"CRYPTO_ENABLED={str(data.get('use_crypto', False)).lower()}",
    ]
    # Append to .env if not exists
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text("\n".join(env_lines) + "\n")
    else:
        # Don't overwrite existing, just note
        pass


# ─── Entry point for standalone testing ──────────────────────────────────────
if __name__ == "__main__":
    render_onboarding()
