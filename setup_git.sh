#!/bin/bash
# CATERYA Git Initialization Script
# Run once after cloning or creating the repo

echo "Setting up CATERYA Agentic Enterprise Git..."

git init

git config user.name "Ary HH (Caterya Tech)"
git config user.email "aryhharyanto@proton.me"

git add -A
git commit -m "feat: initial CATERYA Agentic Enterprise v1.0

- Offline-first LLM router (Ollama primary, free-tier cloud fallback)
- Multi-chain crypto: Bitcoin/Ethereum/Solana built-in
- 12 specialized agents with ethics guard on every output
- LangGraph stateful orchestration with persistent checkpoints
- Mobile-first PWA dashboard (Streamlit)
- Docker Compose: ollama + postgres + redis + chromadb + grafana
- CATERYA ethics wrapper (Conservation/Reciprocity/Integrity/Sovereignty/Resonance)
- Wallet vault (AES-GCM + PBKDF2 480k iterations)
- Full test suite (ethics, crypto, state, router)
- VISION.md: 2026-2028 roadmap (quantum-safe, Web4, on-chain marketplace)

Default receive addresses:
  BTC: bc1qxwq5uwlpmjcjcq8h0ylmvzjktu8mtpe33cslk8
  ETH: 0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81
  SOL: 9GfH2m7foUKceYKV927EknXpK8HLnxqQzNevar1kPizU

Co-authored-by: Ary HH (Caterya Tech) <aryhharyanto@proton.me>"

echo ""
echo "✓ Git initialized with author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>"
echo ""
echo "Next steps:"
echo "  1. Create private repo on GitHub/GitLab"
echo "  2. git remote add origin git@github.com:caterya-tech/caterya-agentic-enterprise.git"
echo "  3. git push -u origin main"
