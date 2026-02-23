"""
CATERYA Agentic Enterprise — Tenant Manager
SaaS multi-tenancy: isolasi data, quota, dan konfigurasi per tenant.
© 2026 Caterya Tech. All Rights Reserved.
"""

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"       # $29/mo
    GROWTH = "growth"         # $99/mo
    ENTERPRISE = "enterprise" # custom
    WHITE_LABEL = "white_label"


PLAN_LIMITS = {
    PlanType.FREE: {
        "agents_per_month": 100,
        "max_agents": 3,
        "storage_mb": 100,
        "api_calls_per_day": 50,
        "team_members": 1,
        "crypto_enabled": False,
        "white_label": False,
    },
    PlanType.STARTER: {
        "agents_per_month": 2000,
        "max_agents": 6,
        "storage_mb": 1000,
        "api_calls_per_day": 500,
        "team_members": 3,
        "crypto_enabled": True,
        "white_label": False,
    },
    PlanType.GROWTH: {
        "agents_per_month": 10000,
        "max_agents": 12,
        "storage_mb": 5000,
        "api_calls_per_day": 5000,
        "team_members": 10,
        "crypto_enabled": True,
        "white_label": False,
    },
    PlanType.ENTERPRISE: {
        "agents_per_month": -1,  # unlimited
        "max_agents": -1,
        "storage_mb": -1,
        "api_calls_per_day": -1,
        "team_members": -1,
        "crypto_enabled": True,
        "white_label": True,
    },
    PlanType.WHITE_LABEL: {
        "agents_per_month": -1,
        "max_agents": -1,
        "storage_mb": -1,
        "api_calls_per_day": -1,
        "team_members": -1,
        "crypto_enabled": True,
        "white_label": True,
    },
}


@dataclass
class Tenant:
    tenant_id: str
    name: str
    email: str
    plan: PlanType
    created_at: str
    api_key: str
    is_active: bool = True
    custom_domain: Optional[str] = None
    branding: dict = field(default_factory=dict)
    usage_this_month: dict = field(default_factory=dict)
    subscription_expires: Optional[str] = None

    @classmethod
    def create(cls, name: str, email: str, plan: PlanType = PlanType.FREE) -> "Tenant":
        tenant_id = str(uuid.uuid4())
        api_key = "cae_" + hashlib.sha256(f"{tenant_id}{email}".encode()).hexdigest()[:32]
        return cls(
            tenant_id=tenant_id,
            name=name,
            email=email,
            plan=plan,
            created_at=datetime.utcnow().isoformat(),
            api_key=api_key,
            usage_this_month={"agent_calls": 0, "api_calls": 0, "storage_mb": 0},
        )

    def get_limits(self) -> dict:
        return PLAN_LIMITS[self.plan]

    def check_quota(self, resource: str) -> tuple[bool, str]:
        limits = self.get_limits()
        limit_key = {
            "agent_call": "agents_per_month",
            "api_call": "api_calls_per_day",
            "storage": "storage_mb",
        }.get(resource, resource)

        limit = limits.get(limit_key, 0)
        if limit == -1:
            return True, "unlimited"

        usage_key = {"agent_call": "agent_calls", "api_call": "api_calls"}.get(resource, resource)
        current = self.usage_this_month.get(usage_key, 0)

        if current >= limit:
            return False, f"Quota exceeded: {current}/{limit} {resource}s this period"
        return True, f"{current}/{limit} used"

    def increment_usage(self, resource: str, amount: int = 1):
        key = {"agent_call": "agent_calls", "api_call": "api_calls"}.get(resource, resource)
        self.usage_this_month[key] = self.usage_this_month.get(key, 0) + amount


class TenantDB:
    """SQLite-based tenant store (swap to PostgreSQL in prod via env var)."""

    def __init__(self, db_path: str = "data/tenants.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL,
                created_at TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 1,
                custom_domain TEXT,
                branding TEXT DEFAULT '{}',
                usage_this_month TEXT DEFAULT '{}',
                subscription_expires TEXT
            )
        """)
        self.conn.commit()

    def save(self, tenant: Tenant):
        import json
        self.conn.execute("""
            INSERT OR REPLACE INTO tenants VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            tenant.tenant_id, tenant.name, tenant.email, tenant.plan.value,
            tenant.created_at, tenant.api_key, int(tenant.is_active),
            tenant.custom_domain,
            json.dumps(tenant.branding),
            json.dumps(tenant.usage_this_month),
            tenant.subscription_expires,
        ))
        self.conn.commit()

    def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        import json
        row = self.conn.execute(
            "SELECT * FROM tenants WHERE api_key = ? AND is_active = 1", (api_key,)
        ).fetchone()
        if not row:
            return None
        return Tenant(
            tenant_id=row[0], name=row[1], email=row[2],
            plan=PlanType(row[3]), created_at=row[4], api_key=row[5],
            is_active=bool(row[6]), custom_domain=row[7],
            branding=json.loads(row[8]), usage_this_month=json.loads(row[9]),
            subscription_expires=row[10],
        )

    def get_by_email(self, email: str) -> Optional[Tenant]:
        import json
        row = self.conn.execute(
            "SELECT * FROM tenants WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return None
        return Tenant(
            tenant_id=row[0], name=row[1], email=row[2],
            plan=PlanType(row[3]), created_at=row[4], api_key=row[5],
            is_active=bool(row[6]), custom_domain=row[7],
            branding=json.loads(row[8]), usage_this_month=json.loads(row[9]),
            subscription_expires=row[10],
        )

    def list_all(self) -> list[Tenant]:
        import json
        rows = self.conn.execute("SELECT * FROM tenants").fetchall()
        result = []
        for row in rows:
            result.append(Tenant(
                tenant_id=row[0], name=row[1], email=row[2],
                plan=PlanType(row[3]), created_at=row[4], api_key=row[5],
                is_active=bool(row[6]), custom_domain=row[7],
                branding=json.loads(row[8]), usage_this_month=json.loads(row[9]),
                subscription_expires=row[10],
            ))
        return result

    def reset_monthly_usage(self):
        self.conn.execute("UPDATE tenants SET usage_this_month = '{}'")
        self.conn.commit()


# Singleton instance
_db: Optional[TenantDB] = None


def get_tenant_db() -> TenantDB:
    global _db
    if _db is None:
        _db = TenantDB()
    return _db
