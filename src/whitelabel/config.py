"""
CATERYA Agentic Enterprise — White Label System
Jual CATERYA sebagai produk branded milik client enterprise.
© 2026 Caterya Tech. All Rights Reserved.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WhiteLabel:
    """White label configuration for an enterprise client."""
    wl_id: str
    tenant_id: str
    # Branding
    brand_name: str           # e.g. "AcmeCorp AI Assistant"
    logo_url: str             # URL or base64
    primary_color: str        # e.g. "#FF5733"
    secondary_color: str      # e.g. "#333333"
    favicon_url: str
    # Domain
    custom_domain: str        # e.g. "ai.acmecorp.com"
    app_title: str            # Browser tab title
    # Content
    welcome_message: str
    footer_text: str
    support_email: str
    # Features (what to show/hide)
    enabled_agents: list[str]
    show_crypto: bool
    show_api_docs: bool
    show_powered_by: bool     # "Powered by CATERYA" watermark
    # Legal
    terms_url: str
    privacy_url: str
    # Metadata
    created_at: str
    is_active: bool = True

    @classmethod
    def create(
        cls,
        tenant_id: str,
        brand_name: str,
        primary_color: str = "#6366f1",
        custom_domain: str = "",
    ) -> "WhiteLabel":
        return cls(
            wl_id="wl_" + uuid.uuid4().hex[:10],
            tenant_id=tenant_id,
            brand_name=brand_name,
            logo_url="",
            primary_color=primary_color,
            secondary_color="#1e1e2e",
            favicon_url="",
            custom_domain=custom_domain,
            app_title=f"{brand_name} — AI Platform",
            welcome_message=f"Selamat datang di {brand_name}. AI Agent siap membantu bisnis Anda.",
            footer_text=f"© {datetime.utcnow().year} {brand_name}. All rights reserved.",
            support_email=f"support@{custom_domain}" if custom_domain else "",
            enabled_agents=[
                "lead_gen", "content_writer", "sales_closer",
                "support", "finance", "research",
            ],
            show_crypto=False,
            show_api_docs=True,
            show_powered_by=True,
            terms_url="",
            privacy_url="",
            created_at=datetime.utcnow().isoformat(),
        )

    def to_streamlit_theme(self) -> dict:
        """Generate Streamlit config.toml theme block."""
        return {
            "primaryColor": self.primary_color,
            "backgroundColor": self.secondary_color,
            "secondaryBackgroundColor": self._darken(self.secondary_color),
            "textColor": "#ffffff",
            "font": "sans serif",
        }

    def generate_config_toml(self) -> str:
        """Generate .streamlit/config.toml for this white label."""
        t = self.to_streamlit_theme()
        return f"""[theme]
primaryColor = "{t['primaryColor']}"
backgroundColor = "{t['backgroundColor']}"
secondaryBackgroundColor = "{t['secondaryBackgroundColor']}"
textColor = "{t['textColor']}"
font = "{t['font']}"

[server]
headless = true
enableCORS = false
port = 8501
"""

    def generate_env_overrides(self) -> str:
        """Generate .env overrides for white label deploy."""
        return f"""# White Label: {self.brand_name}
WL_ID={self.wl_id}
WL_BRAND_NAME={self.brand_name}
WL_PRIMARY_COLOR={self.primary_color}
WL_CUSTOM_DOMAIN={self.custom_domain}
WL_SHOW_CRYPTO={str(self.show_crypto).lower()}
WL_SHOW_POWERED_BY={str(self.show_powered_by).lower()}
WL_SUPPORT_EMAIL={self.support_email}
WL_ENABLED_AGENTS={','.join(self.enabled_agents)}
"""

    def _darken(self, hex_color: str) -> str:
        """Darken a hex color by 20%."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = int(r * 0.8), int(g * 0.8), int(b * 0.8)
        return f"#{r:02x}{g:02x}{b:02x}"


class WhiteLabelDB:
    def __init__(self, db_path: str = "data/whitelabel.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS whitelabels (
                wl_id TEXT PRIMARY KEY,
                tenant_id TEXT UNIQUE NOT NULL,
                config TEXT NOT NULL,
                created_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        self.conn.commit()

    def save(self, wl: WhiteLabel):
        import dataclasses
        self.conn.execute("""
            INSERT OR REPLACE INTO whitelabels VALUES (?,?,?,?,?)
        """, (
            wl.wl_id, wl.tenant_id, json.dumps(dataclasses.asdict(wl)),
            wl.created_at, int(wl.is_active),
        ))
        self.conn.commit()

    def get_by_tenant(self, tenant_id: str) -> Optional[WhiteLabel]:
        row = self.conn.execute(
            "SELECT config FROM whitelabels WHERE tenant_id = ? AND is_active = 1",
            (tenant_id,)
        ).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        return WhiteLabel(**data)

    def get_by_domain(self, domain: str) -> Optional[WhiteLabel]:
        rows = self.conn.execute(
            "SELECT config FROM whitelabels WHERE is_active = 1"
        ).fetchall()
        for row in rows:
            data = json.loads(row[0])
            if data.get("custom_domain") == domain:
                return WhiteLabel(**data)
        return None


def load_white_label_from_env() -> Optional[WhiteLabel]:
    """
    Load white label config from environment variables.
    Used at runtime in deployed white-label instances.
    """
    import os
    wl_id = os.getenv("WL_ID")
    if not wl_id:
        return None

    return WhiteLabel(
        wl_id=wl_id,
        tenant_id=os.getenv("WL_TENANT_ID", ""),
        brand_name=os.getenv("WL_BRAND_NAME", "CATERYA"),
        logo_url=os.getenv("WL_LOGO_URL", ""),
        primary_color=os.getenv("WL_PRIMARY_COLOR", "#6366f1"),
        secondary_color=os.getenv("WL_SECONDARY_COLOR", "#1e1e2e"),
        favicon_url=os.getenv("WL_FAVICON_URL", ""),
        custom_domain=os.getenv("WL_CUSTOM_DOMAIN", ""),
        app_title=os.getenv("WL_APP_TITLE", "AI Platform"),
        welcome_message=os.getenv("WL_WELCOME_MESSAGE", "Selamat datang!"),
        footer_text=os.getenv("WL_FOOTER_TEXT", ""),
        support_email=os.getenv("WL_SUPPORT_EMAIL", ""),
        enabled_agents=os.getenv("WL_ENABLED_AGENTS", "lead_gen,content_writer,support").split(","),
        show_crypto=os.getenv("WL_SHOW_CRYPTO", "false").lower() == "true",
        show_api_docs=os.getenv("WL_SHOW_API_DOCS", "true").lower() == "true",
        show_powered_by=os.getenv("WL_SHOW_POWERED_BY", "true").lower() == "true",
        terms_url=os.getenv("WL_TERMS_URL", ""),
        privacy_url=os.getenv("WL_PRIVACY_URL", ""),
        created_at=datetime.utcnow().isoformat(),
    )
