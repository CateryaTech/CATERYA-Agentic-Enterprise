"""
CATERYA Agentic Enterprise — Billing Engine
Mendukung pembayaran Stripe (kartu) dan Crypto (BTC/ETH/SOL).
© 2026 Caterya Tech. All Rights Reserved.
"""

import hashlib
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from .tenant_manager import PlanType, Tenant, get_tenant_db

# Plan pricing in USD
PLAN_PRICING = {
    PlanType.FREE: {"monthly": 0, "annual": 0},
    PlanType.STARTER: {"monthly": 29, "annual": 290},      # ~17% discount annual
    PlanType.GROWTH: {"monthly": 99, "annual": 990},
    PlanType.ENTERPRISE: {"monthly": 499, "annual": 4990},
    PlanType.WHITE_LABEL: {"monthly": 999, "annual": 9990},
}

# Crypto receive addresses (from env or defaults)
CRYPTO_ADDRESSES = {
    "BTC": os.getenv("BTC_RECEIVE_ADDRESS", "bc1qxwq5uwlpmjcjcq8h0ylmvzjktu8mtpe33cslk8"),
    "ETH": os.getenv("ETH_RECEIVE_ADDRESS", "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81"),
    "SOL": os.getenv("SOL_RECEIVE_ADDRESS", "9GfH2m7foUKceYKV927EknXpK8HLnxqQzNevar1kPizU"),
    "USDT_ETH": os.getenv("ETH_RECEIVE_ADDRESS", "0x44a0fc77b271d75dfc8a6f9a3320154a176b1e81"),
}


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class PaymentMethod(str, Enum):
    STRIPE = "stripe"
    CRYPTO_BTC = "crypto_btc"
    CRYPTO_ETH = "crypto_eth"
    CRYPTO_SOL = "crypto_sol"
    CRYPTO_USDT = "crypto_usdt"
    MANUAL = "manual"


@dataclass
class Invoice:
    invoice_id: str
    tenant_id: str
    plan: PlanType
    amount_usd: float
    payment_method: PaymentMethod
    status: PaymentStatus
    created_at: str
    expires_at: str
    crypto_address: Optional[str] = None
    crypto_amount: Optional[float] = None
    crypto_currency: Optional[str] = None
    stripe_payment_intent: Optional[str] = None
    paid_at: Optional[str] = None
    notes: str = ""

    @classmethod
    def create(
        cls,
        tenant_id: str,
        plan: PlanType,
        billing_period: str = "monthly",
        payment_method: PaymentMethod = PaymentMethod.STRIPE,
    ) -> "Invoice":
        pricing = PLAN_PRICING[plan]
        amount_usd = pricing[billing_period]
        invoice_id = "inv_" + str(uuid.uuid4())[:12]
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=24)

        invoice = cls(
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            plan=plan,
            amount_usd=amount_usd,
            payment_method=payment_method,
            status=PaymentStatus.PENDING,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat(),
        )

        # Populate crypto info
        if payment_method in (
            PaymentMethod.CRYPTO_BTC,
            PaymentMethod.CRYPTO_ETH,
            PaymentMethod.CRYPTO_SOL,
            PaymentMethod.CRYPTO_USDT,
        ):
            crypto_map = {
                PaymentMethod.CRYPTO_BTC: "BTC",
                PaymentMethod.CRYPTO_ETH: "ETH",
                PaymentMethod.CRYPTO_SOL: "SOL",
                PaymentMethod.CRYPTO_USDT: "USDT_ETH",
            }
            currency = crypto_map[payment_method]
            invoice.crypto_currency = currency
            invoice.crypto_address = CRYPTO_ADDRESSES[currency]
            # In production, fetch live rates from CoinGecko/etc.
            # Here we use approximate static rates for demo
            approx_rates = {"BTC": 95000, "ETH": 3200, "SOL": 180, "USDT_ETH": 1}
            rate = approx_rates.get(currency, 1)
            invoice.crypto_amount = round(amount_usd / rate, 8)

        return invoice

    def to_payment_page_data(self) -> dict:
        """Data to display on payment page."""
        return {
            "invoice_id": self.invoice_id,
            "amount_usd": self.amount_usd,
            "plan": self.plan.value,
            "method": self.payment_method.value,
            "crypto_address": self.crypto_address,
            "crypto_amount": self.crypto_amount,
            "crypto_currency": self.crypto_currency,
            "expires_at": self.expires_at,
            "status": self.status.value,
        }


class BillingDB:
    def __init__(self, db_path: str = "data/billing.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                plan TEXT NOT NULL,
                amount_usd REAL NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                crypto_address TEXT,
                crypto_amount REAL,
                crypto_currency TEXT,
                stripe_payment_intent TEXT,
                paid_at TEXT,
                notes TEXT DEFAULT ''
            )
        """)
        self.conn.commit()

    def save_invoice(self, inv: Invoice):
        self.conn.execute("""
            INSERT OR REPLACE INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            inv.invoice_id, inv.tenant_id, inv.plan.value, inv.amount_usd,
            inv.payment_method.value, inv.status.value, inv.created_at,
            inv.expires_at, inv.crypto_address, inv.crypto_amount,
            inv.crypto_currency, inv.stripe_payment_intent, inv.paid_at, inv.notes,
        ))
        self.conn.commit()

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        row = self.conn.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
        ).fetchone()
        if not row:
            return None
        return Invoice(
            invoice_id=row[0], tenant_id=row[1], plan=PlanType(row[2]),
            amount_usd=row[3], payment_method=PaymentMethod(row[4]),
            status=PaymentStatus(row[5]), created_at=row[6], expires_at=row[7],
            crypto_address=row[8], crypto_amount=row[9], crypto_currency=row[10],
            stripe_payment_intent=row[11], paid_at=row[12], notes=row[13] or "",
        )

    def list_by_tenant(self, tenant_id: str) -> list[Invoice]:
        rows = self.conn.execute(
            "SELECT * FROM invoices WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,)
        ).fetchall()
        result = []
        for row in rows:
            result.append(Invoice(
                invoice_id=row[0], tenant_id=row[1], plan=PlanType(row[2]),
                amount_usd=row[3], payment_method=PaymentMethod(row[4]),
                status=PaymentStatus(row[5]), created_at=row[6], expires_at=row[7],
                crypto_address=row[8], crypto_amount=row[9], crypto_currency=row[10],
                stripe_payment_intent=row[11], paid_at=row[12], notes=row[13] or "",
            ))
        return result

    def mark_paid(self, invoice_id: str):
        self.conn.execute(
            "UPDATE invoices SET status = ?, paid_at = ? WHERE invoice_id = ?",
            (PaymentStatus.CONFIRMED.value, datetime.utcnow().isoformat(), invoice_id)
        )
        self.conn.commit()


class BillingEngine:
    """Main billing controller."""

    def __init__(self):
        self.db = BillingDB()
        self.tenant_db = get_tenant_db()

    def create_invoice(
        self,
        tenant_id: str,
        plan: PlanType,
        billing_period: str = "monthly",
        payment_method: PaymentMethod = PaymentMethod.STRIPE,
    ) -> Invoice:
        inv = Invoice.create(tenant_id, plan, billing_period, payment_method)
        self.db.save_invoice(inv)
        return inv

    def process_stripe_webhook(self, payload: dict) -> bool:
        """Handle Stripe webhook events."""
        event_type = payload.get("type")
        if event_type == "payment_intent.succeeded":
            pi_id = payload["data"]["object"]["id"]
            # Find invoice by stripe PI
            # In production: query by stripe_payment_intent
            return True
        return False

    def verify_crypto_payment_manual(self, invoice_id: str) -> dict:
        """
        Returns payment verification info.
        In production: auto-verify via blockchain APIs (Blockstream, Etherscan, Solscan).
        For offline use: manual verification with instructions.
        """
        inv = self.db.get_invoice(invoice_id)
        if not inv:
            return {"error": "Invoice not found"}

        return {
            "invoice_id": invoice_id,
            "status": inv.status.value,
            "send_to": inv.crypto_address,
            "amount": inv.crypto_amount,
            "currency": inv.crypto_currency,
            "amount_usd": inv.amount_usd,
            "expires_at": inv.expires_at,
            "verify_url": {
                "BTC": f"https://blockstream.info/address/{inv.crypto_address}",
                "ETH": f"https://etherscan.io/address/{inv.crypto_address}",
                "SOL": f"https://solscan.io/account/{inv.crypto_address}",
            }.get(inv.crypto_currency or "", ""),
            "note": "After sending, click 'Confirm Payment' and paste your TX hash.",
        }

    def confirm_payment_and_upgrade(self, invoice_id: str, tx_hash: str = "") -> dict:
        """Manually confirm payment and upgrade tenant plan."""
        inv = self.db.get_invoice(invoice_id)
        if not inv:
            return {"success": False, "error": "Invoice not found"}

        self.db.mark_paid(invoice_id)

        # Upgrade tenant plan
        tenant = self.tenant_db.get_by_api_key("")  # Would lookup by tenant_id
        # Update subscription expiry (30 days from now)
        sub_expires = (datetime.utcnow() + timedelta(days=30)).isoformat()

        return {
            "success": True,
            "invoice_id": invoice_id,
            "new_plan": inv.plan.value,
            "subscription_expires": sub_expires,
            "tx_hash": tx_hash,
        }

    def get_revenue_summary(self) -> dict:
        """Admin: get revenue summary across all tenants."""
        conn = self.db.conn
        rows = conn.execute("""
            SELECT plan, COUNT(*) as count, SUM(amount_usd) as total
            FROM invoices
            WHERE status = 'confirmed'
            GROUP BY plan
        """).fetchall()

        total_revenue = sum(r[2] for r in rows if r[2])
        return {
            "total_revenue_usd": total_revenue,
            "by_plan": [
                {"plan": r[0], "customers": r[1], "revenue": r[2]} for r in rows
            ],
        }
