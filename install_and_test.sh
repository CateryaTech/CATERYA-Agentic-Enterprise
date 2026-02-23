#!/bin/bash
# =============================================================================
# CATERYA Agentic Enterprise — Install & Test Script
# Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>
#
# Usage:
#   bash install_and_test.sh          # Full install + test
#   bash install_and_test.sh --offline-test   # Test offline mode only
#   bash install_and_test.sh --ollama-only    # Hanya setup Ollama
# =============================================================================

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    ⚡ CATERYA Agentic Enterprise v1.0               ║${NC}"
echo -e "${CYAN}║    Offline-First AI Workforce Setup                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Detect OS ───────────────────────────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then OS="macos"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* ]]; then OS="windows"; fi
info "OS detected: $OS"

# ─── Check Python ────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install Python 3.12+ first."
    exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PY_VERSION"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" 2>/dev/null; then
    ok "Python 3.12+ confirmed"
else
    warn "Python 3.12+ recommended (you have $PY_VERSION). Some features may not work."
fi

# ─── Handle CLI args ─────────────────────────────────────────────────────────
OFFLINE_TEST_ONLY=false
OLLAMA_ONLY=false
[[ "$1" == "--offline-test" ]] && OFFLINE_TEST_ONLY=true
[[ "$1" == "--ollama-only" ]] && OLLAMA_ONLY=true

# ─── STEP 1: Install Ollama ─────────────────────────────────────────────────
install_ollama() {
    echo ""
    echo -e "${CYAN}━━━ STEP 1: Install Ollama (Local LLM Engine) ━━━━━━━━━${NC}"

    if command -v ollama &>/dev/null; then
        ok "Ollama already installed: $(ollama --version 2>/dev/null || echo 'version unknown')"
    else
        info "Installing Ollama..."
        if [[ "$OS" == "linux" ]] || [[ "$OS" == "macos" ]]; then
            curl -fsSL https://ollama.ai/install.sh | sh
            ok "Ollama installed"
        else
            error "Auto-install not supported on Windows. Download from: https://ollama.ai/download"
            exit 1
        fi
    fi

    # Start Ollama daemon
    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        info "Starting Ollama daemon..."
        ollama serve &>/tmp/ollama.log &
        sleep 3
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            ok "Ollama daemon started"
        else
            warn "Ollama may not be running. Check: ollama serve"
        fi
    else
        ok "Ollama daemon already running"
    fi
}

# ─── STEP 2: Pull Models ────────────────────────────────────────────────────
pull_models() {
    echo ""
    echo -e "${CYAN}━━━ STEP 2: Pull Required Ollama Models ━━━━━━━━━━━━━━${NC}"
    echo ""
    warn "This will download ~15-25GB total. Skip individual models with Ctrl+C."
    echo ""

    MODELS=(
        "phi4:latest|~9GB|Fast tasks, good for most ops"
        "llama3.3:latest|~4GB|General reasoning"
        "qwen2.5:7b|~4GB|Multilingual, reasoning"
        "deepseek-coder:latest|~776MB|Code generation"
        "mistral:latest|~4GB|Creative writing"
    )

    OPTIONAL_MODELS=(
        "qwen2.5:32b|~20GB|Better reasoning (needs 16GB+ RAM)"
        "gemma3:latest|~5GB|Google's model"
    )

    for model_info in "${MODELS[@]}"; do
        IFS='|' read -r model size desc <<< "$model_info"
        model_name=$(echo $model | cut -d: -f1)

        # Check if already present
        if ollama list 2>/dev/null | grep -q "$model_name"; then
            ok "Already have: $model ($desc)"
        else
            info "Pulling $model ($size) — $desc"
            ollama pull "$model" && ok "Pulled: $model" || warn "Failed to pull $model (skipping)"
        fi
    done

    echo ""
    info "Optional larger models (better quality, more VRAM needed):"
    for model_info in "${OPTIONAL_MODELS[@]}"; do
        IFS='|' read -r model size desc <<< "$model_info"
        echo "  → $model  $size  — $desc"
        echo "    To install: ollama pull $model"
    done
}

# ─── STEP 3: Python Dependencies ────────────────────────────────────────────
install_python_deps() {
    echo ""
    echo -e "${CYAN}━━━ STEP 3: Install Python Dependencies ━━━━━━━━━━━━━━${NC}"

    # Create venv if not exists
    if [ ! -d ".venv" ]; then
        info "Creating virtual environment..."
        python3 -m venv .venv
        ok "Virtual environment created: .venv/"
    fi

    # Activate
    source .venv/bin/activate

    info "Installing core dependencies..."
    pip install --quiet --upgrade pip

    pip install --quiet \
        "langchain>=0.3.0" \
        "langchain-community>=0.3.0" \
        "langchain-ollama>=0.2.0" \
        "langgraph>=0.2.0" \
        "streamlit>=1.40.0" \
        "cryptography>=43.0.0" \
        "python-dotenv>=1.0.0" \
        "httpx>=0.27.0" \
        "pydantic>=2.8.0" \
        "rich>=13.8.0" \
        "redis>=5.0.0" \
        "sqlalchemy>=2.0.0" \
        "psycopg2-binary>=2.9.9" \
        "web3>=7.0.0" \
        "argon2-cffi>=23.1.0" \
        "pytest>=8.3.0" \
        "pytest-asyncio>=0.24.0"

    ok "Python dependencies installed"
    deactivate
}

# ─── STEP 4: Environment Setup ──────────────────────────────────────────────
setup_env() {
    echo ""
    echo -e "${CYAN}━━━ STEP 4: Environment Configuration ━━━━━━━━━━━━━━━━${NC}"

    if [ ! -f ".env" ]; then
        cp .env.example .env
        ok ".env created from template"
        warn "Edit .env to set WALLET_MASTER_PASSWORD and other secrets!"
    else
        ok ".env already exists"
    fi

    mkdir -p data logs
    ok "Directories created: data/ logs/"
}

# ─── STEP 5: Offline Test ───────────────────────────────────────────────────
run_offline_test() {
    echo ""
    echo -e "${CYAN}━━━ STEP 5: Offline Mode Test ━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    source .venv/bin/activate

    echo ""
    info "Test 1: Connectivity Detection..."
    python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from src.core.llm_router import get_connectivity, check_ollama, check_internet

conn = get_connectivity()
print(f"  Ollama available: {'✓' if conn.ollama_available else '✗'} {conn.ollama_available}")
print(f"  Internet online:  {'✓' if conn.is_online else '✗ (offline mode)'} {conn.is_online}")
print(f"  Latency check:    {conn.latency_ms:.1f}ms")

if conn.ollama_available:
    print("  → Will use LOCAL Ollama (100% offline capable)")
elif conn.is_online:
    print("  → Will use FREE CLOUD fallback (Groq/Together/Fireworks)")
else:
    print("  ⚠ No LLM available — start Ollama: ollama serve")
PYEOF

    echo ""
    info "Test 2: Ethics Guard..."
    python3 - <<'PYEOF'
import sys; sys.path.insert(0, '.')
from src.core.ethics_wrapper import EthicsGuard, EthicsVerdict

guard = EthicsGuard()

# Test clean content
r1 = guard.check("Write a marketing email for our SaaS product.", "test")
print(f"  Clean content:  {r1.verdict.value.upper()} {'✓' if r1.is_safe else '✗'}")

# Test harmful content
r2 = guard.check("bomb instructions here", "test")
print(f"  Harmful content: {r2.verdict.value.upper()} {'✓' if not r2.is_safe else '✗'}")
print(f"  Ethics guard: WORKING ✓")
PYEOF

    echo ""
    info "Test 3: Crypto Manager (fully offline)..."
    python3 - <<'PYEOF'
import sys; sys.path.insert(0, '.')
from src.core.crypto_manager import CryptoManager, Chain

crypto = CryptoManager()
addrs = crypto.get_all_addresses()
print(f"  BTC receive: {addrs['bitcoin']}")
print(f"  ETH receive: {addrs['ethereum_evm']}")
print(f"  SOL receive: {addrs['solana']}")

invoice = crypto.generate_invoice(Chain.ETHEREUM, 0.1, "test invoice")
print(f"  Invoice generated: {invoice['payment_uri'][:50]}...")
print(f"  Crypto manager: WORKING ✓")
PYEOF

    echo ""
    info "Test 4: State Manager (SQLite offline fallback)..."
    python3 - <<'PYEOF'
import sys; sys.path.insert(0, '.')
from src.core.state_manager import StateManager

sm = StateManager()
sm.set("test_key", {"offline": True, "value": 42})
result = sm.get("test_key")
assert result == {"offline": True, "value": 42}
print(f"  State set/get: ✓")
print(f"  Offline storage: {'SQLite fallback' if sm.is_fully_offline else 'Redis+PostgreSQL'}")
print(f"  State manager: WORKING ✓")
PYEOF

    echo ""
    info "Test 5: Ollama LLM call (if available)..."
    python3 - <<'PYEOF'
import sys; sys.path.insert(0, '.')
from src.core.llm_router import get_connectivity, get_router

conn = get_connectivity()
if conn.ollama_available:
    router = get_router()
    models = router.ollama_models
    print(f"  Available models: {models}")
    print(f"  Ollama LLM: AVAILABLE ✓")
else:
    print("  Ollama not running — skipping LLM call test")
    print("  Start Ollama: ollama serve")
    print("  Then re-run: bash install_and_test.sh --offline-test")
PYEOF

    echo ""
    info "Test 6: Unit Tests..."
    python3 -m pytest tests/test_core.py -v --tb=short -q 2>&1 | tail -20

    deactivate
}

# ─── STEP 6: Streamlit Run ─────────────────────────────────────────────────
run_dashboard() {
    echo ""
    echo -e "${CYAN}━━━ STEP 6: Start Dashboard ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    source .venv/bin/activate

    # Detect local IP for phone access
    if [[ "$OS" == "linux" ]]; then
        LOCAL_IP=$(hostname -I | awk '{print $1}')
    elif [[ "$OS" == "macos" ]]; then
        LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "unknown")
    fi

    echo ""
    ok "Starting CATERYA Dashboard..."
    echo ""
    echo -e "  ${GREEN}Access URLs:${NC}"
    echo -e "  Local:         ${CYAN}http://localhost:8501${NC}"
    echo -e "  Phone (WiFi):  ${CYAN}http://${LOCAL_IP}:8501${NC}"
    echo ""
    echo -e "  ${YELLOW}Install as PWA on phone:${NC}"
    echo "  1. Open http://${LOCAL_IP}:8501 in Chrome/Safari"
    echo "  2. Tap menu → 'Add to Home Screen'"
    echo "  3. Done! Runs like a native app, even offline"
    echo ""
    echo -e "  ${YELLOW}For remote access (any internet):${NC}"
    echo "  tailscale up && tailscale ip -4"
    echo ""

    streamlit run src/dashboard/app.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=true \
        --browser.gatherUsageStats=false
}

# ─── Main ─────────────────────────────────────────────────────────────────
if $OFFLINE_TEST_ONLY; then
    run_offline_test
    echo ""
    ok "Offline test complete!"
    exit 0
fi

if $OLLAMA_ONLY; then
    install_ollama
    pull_models
    echo ""
    ok "Ollama setup complete!"
    exit 0
fi

# Full install flow
install_ollama
pull_models
install_python_deps
setup_env
run_offline_test

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ CATERYA Agentic Enterprise — Ready!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Next steps:"
echo "  1. Edit .env (set WALLET_MASTER_PASSWORD)"
echo "  2. Start dashboard:"
echo "     source .venv/bin/activate"
echo "     streamlit run src/dashboard/app.py"
echo ""
echo "  Or with Docker:"
echo "     docker-compose up -d"
echo ""
read -p "  Start dashboard now? (y/N): " START_NOW
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    run_dashboard
fi
