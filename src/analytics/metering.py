"""
CATERYA Agentic Enterprise — Usage Analytics & Metering
Track token usage, latency, cost per tenant untuk billing akurat.
© 2026 Caterya Tech. All Rights Reserved.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# Cost per 1000 tokens (approximate USD) per model
MODEL_COSTS = {
    "ollama/local": 0.0,           # Free (your hardware)
    "groq/llama-3.3-70b": 0.0,    # Free tier
    "openai/gpt-4o": 0.005,
    "anthropic/claude-3-5": 0.003,
    "together/llama-3": 0.0,      # Free tier
}

# Cost per agent task (base, for AaaS pricing)
AGENT_TASK_COST = {
    "free": 0.0,
    "starter": 0.01,     # $0.01 per task for overages
    "growth": 0.005,
    "enterprise": 0.002,
}


@dataclass
class UsageEvent:
    event_id: str
    tenant_id: str
    agent_id: str
    model_used: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    cost_usd: float
    timestamp: str
    success: bool
    task_preview: str = ""

    @classmethod
    def record(
        cls,
        tenant_id: str,
        agent_id: str,
        model_used: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: float,
        success: bool,
        task_preview: str = "",
    ) -> "UsageEvent":
        total_tokens = tokens_input + tokens_output
        cost_per_1k = MODEL_COSTS.get(model_used, 0.001)
        cost_usd = (total_tokens / 1000) * cost_per_1k

        return cls(
            event_id=uuid.uuid4().hex,
            tenant_id=tenant_id,
            agent_id=agent_id,
            model_used=model_used,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            timestamp=datetime.utcnow().isoformat(),
            success=success,
            task_preview=task_preview[:200],
        )


class AnalyticsDB:
    def __init__(self, db_path: str = "data/analytics.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS usage_events (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                model_used TEXT,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                latency_ms REAL DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                timestamp TEXT NOT NULL,
                success INTEGER DEFAULT 1,
                task_preview TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_tenant ON usage_events(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_events(timestamp);
            CREATE TABLE IF NOT EXISTS daily_summaries (
                summary_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_tasks INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,
                success_rate REAL DEFAULT 0,
                top_agent TEXT DEFAULT '',
                UNIQUE(tenant_id, date)
            );
        """)
        self.conn.commit()

    def record(self, event: UsageEvent):
        self.conn.execute("""
            INSERT OR IGNORE INTO usage_events VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            event.event_id, event.tenant_id, event.agent_id, event.model_used,
            event.tokens_input, event.tokens_output, event.latency_ms,
            event.cost_usd, event.timestamp, int(event.success), event.task_preview,
        ))
        self.conn.commit()
        self._update_daily_summary(event)

    def _update_daily_summary(self, event: UsageEvent):
        date = event.timestamp[:10]
        existing = self.conn.execute(
            "SELECT * FROM daily_summaries WHERE tenant_id = ? AND date = ?",
            (event.tenant_id, date)
        ).fetchone()

        if existing:
            self.conn.execute("""
                UPDATE daily_summaries
                SET total_tasks = total_tasks + 1,
                    total_tokens = total_tokens + ?,
                    total_cost_usd = total_cost_usd + ?
                WHERE tenant_id = ? AND date = ?
            """, (event.tokens_input + event.tokens_output, event.cost_usd, event.tenant_id, date))
        else:
            self.conn.execute("""
                INSERT OR IGNORE INTO daily_summaries VALUES (?,?,?,1,?,?,0,1,'')
            """, (
                uuid.uuid4().hex, event.tenant_id, date,
                event.tokens_input + event.tokens_output, event.cost_usd,
            ))
        self.conn.commit()

    def get_tenant_stats(self, tenant_id: str, days: int = 30) -> dict:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = self.conn.execute("""
            SELECT agent_id, COUNT(*) as calls, SUM(tokens_input+tokens_output) as tokens,
                   SUM(cost_usd) as cost, AVG(latency_ms) as avg_latency,
                   SUM(success) * 100.0 / COUNT(*) as success_rate
            FROM usage_events
            WHERE tenant_id = ? AND timestamp >= ?
            GROUP BY agent_id
            ORDER BY calls DESC
        """, (tenant_id, since)).fetchall()

        total = self.conn.execute("""
            SELECT COUNT(*), SUM(tokens_input+tokens_output), SUM(cost_usd)
            FROM usage_events WHERE tenant_id = ? AND timestamp >= ?
        """, (tenant_id, since)).fetchone()

        return {
            "period_days": days,
            "total_tasks": total[0] or 0,
            "total_tokens": total[1] or 0,
            "total_cost_usd": round(total[2] or 0, 4),
            "by_agent": [
                {
                    "agent_id": r[0],
                    "calls": r[1],
                    "tokens": r[2] or 0,
                    "cost_usd": round(r[3] or 0, 4),
                    "avg_latency_ms": round(r[4] or 0, 1),
                    "success_rate": round(r[5] or 0, 1),
                }
                for r in rows
            ],
        }

    def get_daily_timeseries(self, tenant_id: str, days: int = 30) -> list[dict]:
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.conn.execute("""
            SELECT date, total_tasks, total_tokens, total_cost_usd
            FROM daily_summaries
            WHERE tenant_id = ? AND date >= ?
            ORDER BY date ASC
        """, (tenant_id, since)).fetchall()
        return [
            {"date": r[0], "tasks": r[1], "tokens": r[2], "cost_usd": r[3]}
            for r in rows
        ]

    def get_admin_overview(self) -> dict:
        """Cross-tenant overview for admin."""
        rows = self.conn.execute("""
            SELECT tenant_id, COUNT(*) as tasks, SUM(cost_usd) as revenue
            FROM usage_events
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY tenant_id
            ORDER BY tasks DESC
            LIMIT 20
        """).fetchall()

        total = self.conn.execute("""
            SELECT COUNT(*), SUM(cost_usd)
            FROM usage_events
            WHERE timestamp >= date('now', '-30 days')
        """).fetchone()

        return {
            "last_30_days": {
                "total_tasks": total[0] or 0,
                "total_cost_usd": round(total[1] or 0, 4),
            },
            "top_tenants": [
                {"tenant_id": r[0], "tasks": r[1], "cost_usd": round(r[2] or 0, 4)}
                for r in rows
            ],
        }
