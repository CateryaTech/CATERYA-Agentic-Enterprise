"""
CATERYA Agentic Enterprise — Webhook & Integration Hub
Zapier-style automation: trigger agent runs dari event external.
© 2026 Caterya Tech. All Rights Reserved.
"""

import hashlib
import hmac
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


# ─── Event Types ─────────────────────────────────────────────────────────────

EVENTS = {
    # Agent events
    "agent.started": "Agent mulai berjalan",
    "agent.completed": "Agent selesai dengan sukses",
    "agent.failed": "Agent gagal",
    "agent.ethics_blocked": "Agent diblokir ethics guard",
    # Payment events
    "payment.invoice_created": "Invoice baru dibuat",
    "payment.confirmed": "Pembayaran dikonfirmasi",
    "payment.failed": "Pembayaran gagal",
    # Tenant events
    "tenant.created": "Tenant baru registrasi",
    "tenant.upgraded": "Tenant upgrade plan",
    "tenant.quota_warning": "Penggunaan mendekati limit (80%)",
    "tenant.quota_exceeded": "Quota habis",
    # System events
    "system.backup_completed": "Backup selesai",
    "system.error": "Error sistem",
}

# ─── Trigger Types (Inbound) ──────────────────────────────────────────────────

TRIGGER_TYPES = {
    "http_post": "HTTP POST ke URL CATERYA",
    "schedule_cron": "Jadwal cron (e.g. setiap hari jam 9)",
    "email_received": "Email masuk ke inbox agent",
    "form_submitted": "Form submission (Tally, Typeform, dll)",
    "payment_received": "Konfirmasi pembayaran",
    "file_uploaded": "File diunggah ke sistem",
}


@dataclass
class WebhookSubscription:
    webhook_id: str
    tenant_id: str
    url: str
    events: list[str]
    secret: str
    is_active: bool = True
    created_at: str = ""
    last_triggered: Optional[str] = None
    success_count: int = 0
    fail_count: int = 0

    @classmethod
    def create(cls, tenant_id: str, url: str, events: list[str], secret: str = "") -> "WebhookSubscription":
        if not secret:
            secret = "whs_" + uuid.uuid4().hex
        return cls(
            webhook_id="wh_" + uuid.uuid4().hex[:10],
            tenant_id=tenant_id,
            url=url,
            events=events,
            secret=secret,
            created_at=datetime.utcnow().isoformat(),
        )


@dataclass
class Automation:
    """Zapier-style automation rule."""
    automation_id: str
    tenant_id: str
    name: str
    trigger_type: str
    trigger_config: dict
    action_agent_id: str
    action_task_template: str
    is_active: bool = True
    created_at: str = ""
    run_count: int = 0

    @classmethod
    def create(
        cls,
        tenant_id: str,
        name: str,
        trigger_type: str,
        trigger_config: dict,
        action_agent_id: str,
        action_task_template: str,
    ) -> "Automation":
        return cls(
            automation_id="auto_" + uuid.uuid4().hex[:10],
            tenant_id=tenant_id,
            name=name,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            action_agent_id=action_agent_id,
            action_task_template=action_task_template,
            created_at=datetime.utcnow().isoformat(),
        )


class WebhookHub:
    """Manages webhook subscriptions and dispatches events."""

    def __init__(self, db_path: str = "data/webhooks.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS webhooks (
                webhook_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                url TEXT NOT NULL,
                events TEXT NOT NULL,
                secret TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                last_triggered TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS automations (
                automation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                action_agent_id TEXT NOT NULL,
                action_task_template TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                run_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS webhook_logs (
                log_id TEXT PRIMARY KEY,
                webhook_id TEXT,
                event_type TEXT,
                payload TEXT,
                response_status INTEGER,
                sent_at TEXT,
                success INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()

    def subscribe(self, sub: WebhookSubscription):
        self.conn.execute("""
            INSERT OR REPLACE INTO webhooks VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            sub.webhook_id, sub.tenant_id, sub.url, json.dumps(sub.events),
            sub.secret, int(sub.is_active), sub.created_at,
            sub.last_triggered, sub.success_count, sub.fail_count,
        ))
        self.conn.commit()

    def get_subscribers(self, event_type: str, tenant_id: Optional[str] = None) -> list[WebhookSubscription]:
        query = "SELECT * FROM webhooks WHERE is_active = 1"
        params = []
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        rows = self.conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            events = json.loads(row[3])
            if event_type in events or "*" in events:
                result.append(WebhookSubscription(
                    webhook_id=row[0], tenant_id=row[1], url=row[2],
                    events=events, secret=row[4], is_active=bool(row[5]),
                    created_at=row[6] or "", last_triggered=row[7],
                    success_count=row[8] or 0, fail_count=row[9] or 0,
                ))
        return result

    def sign_payload(self, secret: str, payload: str) -> str:
        """HMAC-SHA256 signature for webhook verification."""
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def dispatch(self, event_type: str, payload: dict, tenant_id: Optional[str] = None):
        """Dispatch event to all matching webhook subscribers."""
        import httpx
        subscribers = self.get_subscribers(event_type, tenant_id)
        payload_str = json.dumps({
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        })

        for sub in subscribers:
            signature = self.sign_payload(sub.secret, payload_str)
            headers = {
                "Content-Type": "application/json",
                "X-CATERYA-Event": event_type,
                "X-CATERYA-Signature": f"sha256={signature}",
            }
            log_id = uuid.uuid4().hex
            success = False
            status_code = 0

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(sub.url, content=payload_str, headers=headers)
                    status_code = resp.status_code
                    success = 200 <= status_code < 300
            except Exception as e:
                status_code = 0

            # Log attempt
            self.conn.execute("""
                INSERT INTO webhook_logs VALUES (?,?,?,?,?,?,?)
            """, (log_id, sub.webhook_id, event_type, payload_str,
                  status_code, datetime.utcnow().isoformat(), int(success)))

            # Update counters
            if success:
                self.conn.execute(
                    "UPDATE webhooks SET success_count = success_count + 1, last_triggered = ? WHERE webhook_id = ?",
                    (datetime.utcnow().isoformat(), sub.webhook_id)
                )
            else:
                self.conn.execute(
                    "UPDATE webhooks SET fail_count = fail_count + 1 WHERE webhook_id = ?",
                    (sub.webhook_id,)
                )
            self.conn.commit()

    def save_automation(self, auto: Automation):
        self.conn.execute("""
            INSERT OR REPLACE INTO automations VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            auto.automation_id, auto.tenant_id, auto.name, auto.trigger_type,
            json.dumps(auto.trigger_config), auto.action_agent_id,
            auto.action_task_template, int(auto.is_active), auto.created_at, auto.run_count,
        ))
        self.conn.commit()

    def list_automations(self, tenant_id: str) -> list[Automation]:
        rows = self.conn.execute(
            "SELECT * FROM automations WHERE tenant_id = ?", (tenant_id,)
        ).fetchall()
        result = []
        for row in rows:
            result.append(Automation(
                automation_id=row[0], tenant_id=row[1], name=row[2],
                trigger_type=row[3], trigger_config=json.loads(row[4]),
                action_agent_id=row[5], action_task_template=row[6],
                is_active=bool(row[7]), created_at=row[8] or "", run_count=row[9] or 0,
            ))
        return result

    def get_webhook_logs(self, webhook_id: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute("""
            SELECT log_id, event_type, response_status, sent_at, success
            FROM webhook_logs WHERE webhook_id = ?
            ORDER BY sent_at DESC LIMIT ?
        """, (webhook_id, limit)).fetchall()
        return [
            {"log_id": r[0], "event": r[1], "status": r[2], "sent_at": r[3], "success": bool(r[4])}
            for r in rows
        ]


# ─── Example Automation Templates ─────────────────────────────────────────────

AUTOMATION_TEMPLATES = [
    {
        "name": "New Lead → Qualify dengan Lead Gen Agent",
        "trigger_type": "http_post",
        "trigger_config": {"endpoint": "/triggers/new-lead"},
        "action_agent_id": "lead_gen",
        "action_task_template": "Qualify this lead: {name}, {email}, {company}. Score them 1-10 and recommend next action.",
    },
    {
        "name": "Email Masuk → Support Agent Auto-Reply",
        "trigger_type": "email_received",
        "trigger_config": {"inbox": "support@yourcompany.com"},
        "action_agent_id": "support",
        "action_task_template": "Reply to this customer email professionally: {email_body}",
    },
    {
        "name": "Form Submit → Content Writer",
        "trigger_type": "form_submitted",
        "trigger_config": {"form_id": "content_brief"},
        "action_agent_id": "content_writer",
        "action_task_template": "Write a blog post about: {topic} for audience: {audience}",
    },
    {
        "name": "Setiap Hari 09:00 → Research Market",
        "trigger_type": "schedule_cron",
        "trigger_config": {"cron": "0 9 * * *", "timezone": "Asia/Jakarta"},
        "action_agent_id": "research",
        "action_task_template": "Buat daily market intelligence report untuk industri: {industry}",
    },
]
