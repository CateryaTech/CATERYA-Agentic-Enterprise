# ⚡ CATERYA Agentic Enterprise

> **Proprietary. Closed-Source. All Rights Reserved © 2026 Caterya Tech.**  
> Built by Ary HH (Caterya Tech) — `aryhharyanto@proton.me`

---

## 🌍 Jalankan bisnis AI Anda dari mana saja — bahkan dari gunung tanpa internet.

CATERYA Agentic Enterprise adalah AI workforce paling powerful untuk solo founder di 2026:
- **100% offline-first** via Ollama (no internet required)
- **Crypto-native** — Bitcoin, Ethereum, Solana built-in
- **Ethics-first** — setiap output agent melewati CATERYA ethics guard
- **Mobile-first** — PWA dashboard yang bisa di-install di HP
- **Privacy-sovereign** — zero data leaves your device

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CATERYA Dashboard (PWA)               │
│              Streamlit + Mobile-First UI                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   LangGraph Orchestrator                  │
│         Stateful graphs with persistent checkpoints      │
└──────┬─────────────────┬──────────────────┬─────────────┘
       │                 │                  │
┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│ Agent Layer │  │  Ethics Guard│  │ Crypto Layer │
│ 12+ Agents  │  │  All outputs │  │ BTC/ETH/SOL  │
│ Specialized │  │  pass here   │  │ Multi-chain  │
└──────┬──────┘  └──────────────┘  └──────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│                     LLM Router                           │
│  Ollama (offline) → Groq/Together/Fireworks (free tier)  │
│  Smart model selection per task type                     │
└──────┬──────────────────────────────────────────────────┘
       │
┌──────▼──────┐  ┌──────────────┐  ┌──────────────┐
│   Ollama    │  │  PostgreSQL  │  │    Redis     │
│ Local LLMs  │  │  State + DB  │  │   Queues     │
│ 100% offline│  │  SQLite fb   │  │  In-mem fb   │
└─────────────┘  └──────────────┘  └──────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker + Docker Compose
- [Ollama](https://ollama.ai)

### 1. Clone & Setup

```bash
git clone git@github.com:caterya-tech/caterya-agentic-enterprise.git
cd caterya-agentic-enterprise

# Copy environment config
cp .env.example .env
# Edit .env with your settings (never commit .env!)
```

### 2. Install Ollama + Pull Models

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models (one-time, ~20GB)
ollama pull llama3.3
ollama pull qwen2.5:7b
ollama pull phi4
ollama pull deepseek-coder
ollama pull mistral

# Optional: larger models for better reasoning
ollama pull qwen2.5:32b
```

### 3. Run with Docker (Recommended)

```bash
docker-compose up -d

# Dashboard: http://localhost:8501
# Grafana: http://localhost:3000
```

### 4. Run Locally (Development)

```bash
pip install hatch
hatch env create
hatch run streamlit run src/dashboard/app.py
```

---

## 📱 Run from Phone / Tablet

### Option A: Tailscale (Recommended — No port forwarding needed)

```bash
# On your server/laptop
tailscale up

# Get your Tailscale IP
tailscale ip -4

# Access dashboard from phone browser
# http://[your-tailscale-ip]:8501
```

### Option B: ngrok (Quick temporary tunnel)

```bash
# Install ngrok: https://ngrok.com
ngrok http 8501
# Share the HTTPS URL with yourself
```

### Option C: Local Network (Same WiFi)

```bash
# Find your local IP
ip addr show | grep inet

# Access from phone: http://[local-ip]:8501
```

### Install as PWA on Phone:
1. Open dashboard URL in Chrome/Safari
2. Tap "Add to Home Screen"
3. Launch like a native app — even offline!

---

## 🤖 Available Agents

| Agent | ID | Task Type | Description |
|---|---|---|---|
| Lead Gen | `lead_gen` | Reasoning | Find & qualify prospects |
| Content Writer | `content_writer` | Creative | SEO copy & marketing |
| Sales Closer | `sales_closer` | Reasoning | Objection handling & closing |
| Support | `support` | Fast | Customer inquiries |
| Finance | `finance` | Reasoning | Invoicing & billing |
| Code Improver | `code_improver` | Coding | Review & refactor |
| Crypto Ops | `crypto_ops` | Crypto | On-chain operations |
| Ethics Guard | `ethics_guard` | Reasoning | Ethics compliance review |
| Self Optimizer | `self_optimizer` | Analysis | System improvement |
| Research | `research` | Reasoning | Market intelligence |
| Dashboard Monitor | `dashboard_monitor` | Fast | System health |
| Backup | `backup` | Fast | Data backup & recovery |

---

## 💰 Crypto Configuration

Default receive addresses (pre-configured):

```
Bitcoin:  bc1qxwq5uwlpmjcjcq8h0ylmvzjktu8mtpe33cslk8
Ethereum: 0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81
Solana:   9GfH2m7foUKceYKV927EknXpK8HLnxqQzNevar1kPizU
```

Features:
- Generate payment invoices (any chain)
- Verify on-chain payments (no third-party required)
- Encrypted wallet vault (master password + PBKDF2)
- Signed audit trails for all financial operations
- Support for Polygon, Base, Arbitrum (same ETH address)

---

## 🛡️ Security

- **Wallet vault**: AES-256-GCM encrypted, PBKDF2 key derivation (480,000 iterations)
- **Ethics guard**: Every agent output checked before display
- **Audit log**: Immutable, hash-signed trail of all operations
- **Sandboxed tools**: Tools execute in isolated context
- **No telemetry**: Zero data sent to third parties
- **Rate limiting**: Built-in per-endpoint rate limiting
- **Non-root Docker**: Container runs as non-root user

---

## 🧪 Testing

```bash
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

---

## ⚙️ LLM Router Logic

```
Task received
    │
    ▼
Check Ollama (localhost:11434)
    │
    ├── Ollama available? → Use local model (OFFLINE SAFE ✓)
    │       Reasoning → qwen2.5:72b / llama3.3
    │       Coding    → deepseek-coder
    │       Fast      → phi4
    │       Vision    → llama4-vision
    │
    └── Ollama unavailable?
            │
            ├── Internet available? → Free tier fallback
            │       Groq (llama-3.3-70b)
            │       Together.ai
            │       Fireworks.ai
            │
            └── Both unavailable? → Error (user prompted to start Ollama)
```

---

## 🔧 Configuration

Key environment variables (see `.env.example`):

```bash
# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.3

# Databases
POSTGRES_URL=postgresql://...
REDIS_URL=redis://...

# Crypto
BTC_RECEIVE_ADDRESS=bc1q...
ETH_RECEIVE_ADDRESS=0x44...
SOL_RECEIVE_ADDRESS=9GfH...

# Security
WALLET_MASTER_PASSWORD=your_strong_password
ETHICS_GUARD_ENABLED=true
```

---

## 📄 License

**Proprietary — All Rights Reserved © 2026 Caterya Tech**

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, in whole or in part, is strictly prohibited without express written permission from Caterya Tech.

For licensing inquiries: aryhharyanto@proton.me
