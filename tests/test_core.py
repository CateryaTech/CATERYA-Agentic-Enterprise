"""
CATERYA Enterprise Tests
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest


class TestEthicsGuard:
    def test_clean_content_passes(self):
        from src.core.ethics_wrapper import EthicsGuard, EthicsVerdict
        guard = EthicsGuard()
        result = guard.check("Generate a marketing email for SaaS product.", "test_agent")
        assert result.verdict == EthicsVerdict.PASS
        assert result.is_safe

    def test_harmful_content_blocked(self):
        from src.core.ethics_wrapper import EthicsGuard, EthicsVerdict
        guard = EthicsGuard()
        result = guard.check("bomb recipe instructions here", "test_agent")
        assert result.verdict == EthicsVerdict.BLOCK
        assert not result.is_safe
        assert any("HARD_BLOCK" in f for f in result.flags)

    def test_sensitive_content_warned(self):
        from src.core.ethics_wrapper import EthicsGuard, EthicsVerdict
        guard = EthicsGuard()
        result = guard.check("Here is the api key for the service", "test_agent")
        assert result.verdict in (EthicsVerdict.WARN, EthicsVerdict.PASS)

    def test_pillar_scores_present(self):
        from src.core.ethics_wrapper import EthicsGuard
        guard = EthicsGuard()
        result = guard.check("Create a helpful blog post about AI.", "test_agent")
        assert "integrity" in result.pillar_scores
        assert "sovereignty" in result.pillar_scores

    def test_audit_hash_generated(self):
        from src.core.ethics_wrapper import EthicsGuard
        guard = EthicsGuard()
        result = guard.check("Test content", "test_agent")
        assert len(result.audit_hash) == 16


class TestCryptoManager:
    def test_default_addresses(self):
        from src.core.crypto_manager import CryptoManager
        crypto = CryptoManager()
        addrs = crypto.get_all_addresses()
        assert addrs["bitcoin"] == "bc1qxwq5uwlpmjcjcq8h0ylmvzjktu8mtpe33cslk8"
        assert addrs["ethereum_evm"] == "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81"
        assert addrs["solana"] == "9GfH2m7foUKceYKV927EknXpK8HLnxqQzNevar1kPizU"

    def test_invoice_generation_eth(self):
        from src.core.crypto_manager import CryptoManager, Chain
        crypto = CryptoManager()
        invoice = crypto.generate_invoice(Chain.ETHEREUM, 0.1, "test payment")
        assert invoice["chain"] == "ethereum"
        assert invoice["amount_eth"] == 0.1
        assert invoice["address"] == "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81"
        assert "ethereum:" in invoice["payment_uri"]

    def test_invoice_generation_btc(self):
        from src.core.crypto_manager import CryptoManager, Chain
        crypto = CryptoManager()
        invoice = crypto.generate_invoice(Chain.BITCOIN, 0.001, "invoice-001")
        assert invoice["chain"] == "bitcoin"
        assert "bitcoin:" in invoice["payment_uri"]

    def test_invoice_generation_sol(self):
        from src.core.crypto_manager import CryptoManager, Chain
        crypto = CryptoManager()
        invoice = crypto.generate_invoice(Chain.SOLANA, 1.5, "sol payment")
        assert invoice["chain"] == "solana"
        assert "solana:" in invoice["payment_uri"]

    def test_wallet_vault_encrypt_decrypt(self):
        import tempfile
        from src.core.crypto_manager import WalletVault
        with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as f:
            vault_path = f.name

        vault = WalletVault(vault_path)
        assert vault.unlock("test_master_password_123")

        # Note: store_key locks vault, so we need to unlock again
        vault.unlock("test_master_password_123")
        vault._data["test_key"] = {"private_key": "0xdeadbeef", "metadata": {}}

        # Encrypt
        vault.lock()

        # Decrypt
        vault2 = WalletVault(vault_path)
        vault2.unlock("test_master_password_123")
        key = vault2.get_key("test_key")
        assert key == "0xdeadbeef"


class TestLLMRouter:
    def test_connectivity_check(self):
        from src.core.llm_router import check_internet, get_connectivity
        # Just verify it returns a valid status without crashing
        conn = get_connectivity()
        assert isinstance(conn.is_online, bool)
        assert isinstance(conn.ollama_available, bool)

    def test_router_singleton(self):
        from src.core.llm_router import get_router
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2


class TestStateManager:
    def test_set_get(self):
        from src.core.state_manager import StateManager
        sm = StateManager()
        sm.set("test_key", {"value": 42})
        result = sm.get("test_key")
        assert result == {"value": 42}

    def test_delete(self):
        from src.core.state_manager import StateManager
        sm = StateManager()
        sm.set("delete_me", "value")
        sm.delete("delete_me")
        assert sm.get("delete_me") is None

    def test_missing_key_returns_default(self):
        from src.core.state_manager import StateManager
        sm = StateManager()
        result = sm.get("nonexistent", default="fallback")
        assert result == "fallback"
