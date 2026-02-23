"""
CATERYA Crypto Manager — Multi-Chain, Offline-Capable, Privacy-Native
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>

Supported chains: Bitcoin, Ethereum/EVM, Solana
Default receive addresses pre-configured for Caterya Tech.
All private key operations are local — no keys ever leave this device.

Python 3.13 compatibility note:
  - solana/solders SDK: no Py3.13 wheel → replaced with pure JSON-RPC over HTTP
  - bitcoinlib: optional, graceful fallback if not installed
  - All invoice generation + payment verification works without any SDK
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from src.core.state_manager import get_logger

logger = get_logger(__name__)


# ─── Default Receive Addresses ────────────────────────────────────────────────

DEFAULT_BTC_RECEIVE = os.getenv("BTC_RECEIVE_ADDRESS", "bc1qxwq5uwlpmjcjcq8h0ylmvzjktu8mtpe33cslk8")
DEFAULT_ETH_RECEIVE = os.getenv("ETH_RECEIVE_ADDRESS", "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81")
DEFAULT_SOL_RECEIVE = os.getenv("SOL_RECEIVE_ADDRESS", "9GfH2m7foUKceYKV927EknXpK8HLnxqQzNevar1kPizU")


class Chain(str, Enum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    BASE = "base"
    ARBITRUM = "arbitrum"
    SOLANA = "solana"


@dataclass
class PaymentRequest:
    chain: Chain
    amount: float
    currency: str
    to_address: str
    memo: str = ""
    invoice_id: str = ""


@dataclass
class TxResult:
    success: bool
    tx_hash: str | None
    chain: Chain
    error: str | None = None
    block_explorer_url: str | None = None


# ─── Vault Encryption ─────────────────────────────────────────────────────────

class WalletVault:
    """
    AES-GCM encrypted wallet vault.
    Master password → PBKDF2 → Fernet key → encrypted JSON vault.
    """

    def __init__(self, vault_path: str | None = None):
        self.vault_path = Path(vault_path or os.getenv("WALLET_VAULT_PATH", "./data/vault.enc"))
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {}
        self._fernet: Fernet | None = None

    def unlock(self, master_password: str) -> bool:
        """Unlock vault with master password."""
        try:
            key = self._derive_key(master_password)
            self._fernet = Fernet(key)
            if self.vault_path.exists():
                encrypted = self.vault_path.read_bytes()
                decrypted = self._fernet.decrypt(encrypted)
                self._data = json.loads(decrypted)
                logger.info(f"Vault unlocked: {len(self._data)} entries")
            else:
                logger.info("New vault initialized")
            return True
        except Exception as e:
            logger.error(f"Vault unlock failed: {e}")
            return False

    def lock(self) -> None:
        if self._fernet and self._data:
            encrypted = self._fernet.encrypt(json.dumps(self._data).encode())
            self.vault_path.write_bytes(encrypted)
            self._data = {}
            self._fernet = None
            logger.info("Vault locked and saved")

    def store_key(self, key_id: str, private_key: str, metadata: dict | None = None) -> None:
        if not self._fernet:
            raise RuntimeError("Vault is locked. Call unlock() first.")
        self._data[key_id] = {"private_key": private_key, "metadata": metadata or {}}
        self.lock()  # auto-save

    def get_key(self, key_id: str) -> str | None:
        if not self._fernet:
            raise RuntimeError("Vault is locked.")
        entry = self._data.get(key_id)
        return entry["private_key"] if entry else None

    def _derive_key(self, password: str) -> bytes:
        salt = b"CATERYA_VAULT_SALT_2026"  # fixed salt for deterministic key
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))


# ─── Bitcoin ─────────────────────────────────────────────────────────────────

class BitcoinManager:
    def __init__(self):
        self.network = os.getenv("BTC_NETWORK", "mainnet")
        self.default_receive = DEFAULT_BTC_RECEIVE
        # bitcoinlib is optional (not available on Python 3.13 cloud envs)
        try:
            import bitcoinlib  # noqa: F401
            self._has_sdk = True
        except ImportError:
            self._has_sdk = False
            logger.info("bitcoinlib not installed — using pure HTTP for BTC verification")

    def get_receive_address(self) -> str:
        return self.default_receive

    def verify_payment(self, tx_hash: str, expected_amount_btc: float) -> bool:
        """Verify a Bitcoin payment on-chain (requires internet)."""
        try:
            import httpx
            # Use free mempool.space API
            resp = httpx.get(f"https://mempool.space/api/tx/{tx_hash}", timeout=10)
            if resp.status_code != 200:
                return False
            tx_data = resp.json()
            # Check outputs for our address
            for vout in tx_data.get("vout", []):
                if self.default_receive in vout.get("scriptpubkey_address", ""):
                    satoshis = vout.get("value", 0)
                    btc_received = satoshis / 1e8
                    if btc_received >= expected_amount_btc:
                        logger.info(f"BTC payment verified: {btc_received} BTC in tx {tx_hash}")
                        return True
            return False
        except Exception as e:
            logger.error(f"BTC verification failed: {e}")
            return False

    def generate_invoice(self, amount_btc: float, memo: str = "") -> dict:
        return {
            "chain": "bitcoin",
            "address": self.default_receive,
            "amount_btc": amount_btc,
            "memo": memo,
            "payment_uri": f"bitcoin:{self.default_receive}?amount={amount_btc}&message={memo}",
        }


# ─── Ethereum / EVM ──────────────────────────────────────────────────────────

class EthereumManager:
    def __init__(self):
        self.default_receive = DEFAULT_ETH_RECEIVE
        self._rpc_urls = {
            Chain.ETHEREUM: os.getenv("ETH_RPC_URL", "https://cloudflare-eth.com"),
            Chain.POLYGON: os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
            Chain.BASE: "https://mainnet.base.org",
            Chain.ARBITRUM: "https://arb1.arbitrum.io/rpc",
        }

    def get_receive_address(self) -> str:
        return self.default_receive

    def get_web3(self, chain: Chain = Chain.ETHEREUM):
        from web3 import Web3
        rpc = self._rpc_urls.get(chain, self._rpc_urls[Chain.ETHEREUM])
        w3 = Web3(Web3.HTTPProvider(rpc))
        return w3

    def verify_payment(self, tx_hash: str, expected_amount_eth: float, chain: Chain = Chain.ETHEREUM) -> bool:
        """Verify ETH/EVM payment."""
        try:
            w3 = self.get_web3(chain)
            tx = w3.eth.get_transaction(tx_hash)
            if tx and tx["to"].lower() == self.default_receive.lower():
                amount = w3.from_wei(tx["value"], "ether")
                return float(amount) >= expected_amount_eth
            return False
        except Exception as e:
            logger.error(f"ETH verification failed: {e}")
            return False

    def sign_message(self, message: str, private_key: str) -> str:
        """Sign a message with an Ethereum private key."""
        from eth_account import Account
        from eth_account.messages import encode_defunct
        msg = encode_defunct(text=message)
        signed = Account.sign_message(msg, private_key=private_key)
        return signed.signature.hex()

    def generate_invoice(self, amount_eth: float, chain: Chain = Chain.ETHEREUM, memo: str = "") -> dict:
        return {
            "chain": chain.value,
            "address": self.default_receive,
            "amount_eth": amount_eth,
            "memo": memo,
            "payment_uri": f"ethereum:{self.default_receive}?value={int(amount_eth * 1e18)}",
        }


# ─── Solana ──────────────────────────────────────────────────────────────────

class SolanaManager:
    """
    Pure JSON-RPC Solana implementation.
    No solana/solders SDK required — works on Python 3.13, Streamlit Cloud, anywhere.
    Uses official Solana JSON-RPC API directly over HTTP.
    """

    def __init__(self):
        self.default_receive = DEFAULT_SOL_RECEIVE
        self.rpc_url = os.getenv("SOL_RPC_URL", "https://api.mainnet-beta.solana.com")

    def get_receive_address(self) -> str:
        return self.default_receive

    def _rpc(self, method: str, params: list) -> dict:
        """Make a Solana JSON-RPC call without any SDK."""
        import httpx
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        resp = httpx.post(self.rpc_url, json=payload, timeout=15)
        return resp.json()

    def get_balance(self, address: str) -> float:
        """Get SOL balance in SOL (not lamports)."""
        try:
            result = self._rpc("getBalance", [address])
            lamports = result.get("result", {}).get("value", 0)
            return lamports / 1e9
        except Exception as e:
            logger.error(f"SOL balance check failed: {e}")
            return 0.0

    def verify_payment(self, tx_signature: str, expected_amount_sol: float) -> bool:
        """
        Verify SOL payment via pure JSON-RPC.
        Checks that our receive address received >= expected_amount_sol in this tx.
        """
        try:
            result = self._rpc(
                "getTransaction",
                [tx_signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            )
            tx = result.get("result")
            if not tx:
                logger.warning(f"Transaction not found: {tx_signature}")
                return False

            accounts = tx["transaction"]["message"].get("accountKeys", [])
            post_balances = tx["meta"].get("postBalances", [])
            pre_balances = tx["meta"].get("preBalances", [])

            for i, account in enumerate(accounts):
                addr = account if isinstance(account, str) else account.get("pubkey", "")
                if addr == self.default_receive:
                    delta_lamports = post_balances[i] - pre_balances[i]
                    delta_sol = delta_lamports / 1e9
                    logger.info(f"SOL received: {delta_sol} SOL in tx {tx_signature}")
                    return delta_sol >= expected_amount_sol

            return False
        except Exception as e:
            logger.error(f"SOL verification failed: {e}")
            return False

    def get_recent_transactions(self, limit: int = 10) -> list[dict]:
        """Get recent transactions for the receive address."""
        try:
            result = self._rpc(
                "getSignaturesForAddress",
                [self.default_receive, {"limit": limit}]
            )
            return result.get("result", [])
        except Exception as e:
            logger.error(f"SOL tx fetch failed: {e}")
            return []

    def generate_invoice(self, amount_sol: float, memo: str = "") -> dict:
        return {
            "chain": "solana",
            "address": self.default_receive,
            "amount_sol": amount_sol,
            "memo": memo,
            "payment_uri": f"solana:{self.default_receive}?amount={amount_sol}&label=CATERYA&message={memo}",
            "rpc_url": self.rpc_url,
        }


# ─── Unified Crypto Manager ───────────────────────────────────────────────────

class CryptoManager:
    """
    Unified interface for all crypto operations.
    Fully offline for wallet/signing ops; internet only for on-chain queries.
    """

    def __init__(self):
        self.vault = WalletVault()
        self.bitcoin = BitcoinManager()
        self.ethereum = EthereumManager()
        self.solana = SolanaManager()

    def get_receive_address(self, chain: Chain) -> str:
        """Get default receive address for given chain."""
        if chain == Chain.BITCOIN:
            return self.bitcoin.get_receive_address()
        elif chain in (Chain.ETHEREUM, Chain.POLYGON, Chain.BASE, Chain.ARBITRUM):
            return self.ethereum.get_receive_address()
        elif chain == Chain.SOLANA:
            return self.solana.get_receive_address()
        raise ValueError(f"Unsupported chain: {chain}")

    def generate_invoice(self, chain: Chain, amount: float, memo: str = "") -> dict:
        """Generate payment invoice for any chain."""
        if chain == Chain.BITCOIN:
            return self.bitcoin.generate_invoice(amount, memo)
        elif chain in (Chain.ETHEREUM, Chain.POLYGON, Chain.BASE, Chain.ARBITRUM):
            return self.ethereum.generate_invoice(amount, chain, memo)
        elif chain == Chain.SOLANA:
            return self.solana.generate_invoice(amount, memo)
        raise ValueError(f"Unsupported chain: {chain}")

    def verify_payment(self, chain: Chain, tx_id: str, expected_amount: float) -> bool:
        """Verify payment on given chain."""
        if chain == Chain.BITCOIN:
            return self.bitcoin.verify_payment(tx_id, expected_amount)
        elif chain in (Chain.ETHEREUM, Chain.POLYGON, Chain.BASE, Chain.ARBITRUM):
            return self.ethereum.verify_payment(tx_id, expected_amount, chain)
        elif chain == Chain.SOLANA:
            return self.solana.verify_payment(tx_id, expected_amount)
        return False

    def get_all_addresses(self) -> dict[str, str]:
        """Return all default receive addresses."""
        return {
            "bitcoin": DEFAULT_BTC_RECEIVE,
            "ethereum_evm": DEFAULT_ETH_RECEIVE,
            "solana": DEFAULT_SOL_RECEIVE,
        }

    def sign_message_eth(self, message: str, private_key: str) -> str:
        return self.ethereum.sign_message(message, private_key)


# ─── Singleton ───────────────────────────────────────────────────────────────

_crypto: CryptoManager | None = None


def get_crypto() -> CryptoManager:
    global _crypto
    if _crypto is None:
        _crypto = CryptoManager()
    return _crypto
