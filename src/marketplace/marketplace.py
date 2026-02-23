"""
CATERYA Agentic Enterprise — Agent Marketplace
Beli, jual, dan install custom agents dari marketplace.
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
class MarketplaceAgent:
    """An agent published to the marketplace."""
    agent_id: str
    name: str
    description: str
    author: str
    author_email: str
    category: str
    tags: list[str]
    price_usd: float           # 0 = free
    price_crypto_sol: float
    version: str
    system_prompt: str
    tools: list[str]
    rating: float = 0.0
    downloads: int = 0
    created_at: str = ""
    is_verified: bool = False   # CATERYA-verified badge
    is_active: bool = True

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        author: str,
        author_email: str,
        category: str,
        system_prompt: str,
        price_usd: float = 0.0,
        tags: list[str] = None,
    ) -> "MarketplaceAgent":
        price_sol = round(price_usd / 180, 4) if price_usd > 0 else 0
        return cls(
            agent_id="mkt_" + uuid.uuid4().hex[:10],
            name=name,
            description=description,
            author=author,
            author_email=author_email,
            category=category,
            tags=tags or [],
            price_usd=price_usd,
            price_crypto_sol=price_sol,
            version="1.0.0",
            system_prompt=system_prompt,
            tools=[],
            created_at=datetime.utcnow().isoformat(),
        )


CATEGORIES = [
    "Marketing", "Sales", "Finance", "Operations",
    "Content", "Research", "Development", "Legal",
    "HR", "Customer Service", "E-commerce", "Healthcare",
]

# ─── Built-in Marketplace Agents ─────────────────────────────────────────────

FEATURED_AGENTS = [
    {
        "agent_id": "mkt_instagram_growth",
        "name": "Instagram Growth Agent",
        "description": "Buat caption, hashtag, dan strategi konten Instagram yang viral. Support Bahasa Indonesia.",
        "author": "CateryaTech",
        "category": "Marketing",
        "price_usd": 0.0,
        "rating": 4.8,
        "downloads": 1240,
        "tags": ["instagram", "social media", "indonesia"],
        "is_verified": True,
    },
    {
        "agent_id": "mkt_tokopedia_seller",
        "name": "Tokopedia Seller Agent",
        "description": "Optimasi listing produk Tokopedia, buat deskripsi SEO, dan analisis kompetitor.",
        "author": "CateryaTech",
        "category": "E-commerce",
        "price_usd": 0.0,
        "rating": 4.7,
        "downloads": 987,
        "tags": ["tokopedia", "marketplace", "indonesia"],
        "is_verified": True,
    },
    {
        "agent_id": "mkt_pajak_umkm",
        "name": "Pajak UMKM Agent",
        "description": "Bantu hitung pajak UMKM Indonesia (PPh Final 0.5%), buat laporan, dan reminder deadline.",
        "author": "FinTech Indonesia",
        "category": "Finance",
        "price_usd": 9.99,
        "rating": 4.9,
        "downloads": 2341,
        "tags": ["pajak", "UMKM", "indonesia", "tax"],
        "is_verified": True,
    },
    {
        "agent_id": "mkt_whatsapp_responder",
        "name": "WhatsApp Business Auto-Responder",
        "description": "Template pesan otomatis untuk WhatsApp Business yang terdengar natural dan profesional.",
        "author": "Komunitas CATERYA",
        "category": "Customer Service",
        "price_usd": 0.0,
        "rating": 4.6,
        "downloads": 3210,
        "tags": ["whatsapp", "auto-reply", "indonesia"],
        "is_verified": False,
    },
    {
        "agent_id": "mkt_pitch_deck_writer",
        "name": "Pitch Deck Writer Agent",
        "description": "Buat narasi pitch deck investor yang meyakinkan. Support Bahasa Indonesia & Inggris.",
        "author": "StartupID Community",
        "category": "Sales",
        "price_usd": 4.99,
        "rating": 4.5,
        "downloads": 567,
        "tags": ["pitch", "startup", "investor"],
        "is_verified": False,
    },
    {
        "agent_id": "mkt_seo_writer_id",
        "name": "SEO Content Writer (Bahasa Indonesia)",
        "description": "Tulis artikel SEO berkualitas tinggi dalam Bahasa Indonesia, riset keyword, dan struktur artikel.",
        "author": "CateryaTech",
        "category": "Content",
        "price_usd": 0.0,
        "rating": 4.8,
        "downloads": 4520,
        "tags": ["seo", "content", "bahasa indonesia"],
        "is_verified": True,
    },
    {
        "agent_id": "mkt_legal_contract_id",
        "name": "Contract Drafter (Hukum Indonesia)",
        "description": "Draft kontrak kerja, NDA, dan perjanjian bisnis sesuai hukum Indonesia.",
        "author": "LegalTech ID",
        "category": "Legal",
        "price_usd": 19.99,
        "rating": 4.7,
        "downloads": 234,
        "tags": ["legal", "kontrak", "hukum indonesia"],
        "is_verified": True,
    },
    {
        "agent_id": "mkt_crypto_alpha",
        "name": "Crypto Alpha Research Agent",
        "description": "Analisis DeFi protocols, NFT projects, dan on-chain data untuk alpha research.",
        "author": "Crypto Research DAO",
        "category": "Research",
        "price_usd": 14.99,
        "rating": 4.3,
        "downloads": 892,
        "tags": ["crypto", "defi", "research", "web3"],
        "is_verified": False,
    },
]


class MarketplaceDB:
    def __init__(self, db_path: str = "data/marketplace.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()
        self._seed_featured()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT,
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                price_paid REAL DEFAULT 0,
                payment_method TEXT,
                purchased_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT
            );
        """)
        self.conn.commit()

    def _seed_featured(self):
        for agent_data in FEATURED_AGENTS:
            existing = self.conn.execute(
                "SELECT 1 FROM agents WHERE agent_id = ?", (agent_data["agent_id"],)
            ).fetchone()
            if not existing:
                self.conn.execute(
                    "INSERT INTO agents VALUES (?,?,?,1)",
                    (agent_data["agent_id"], json.dumps(agent_data), datetime.utcnow().isoformat())
                )
        self.conn.commit()

    def list_agents(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        free_only: bool = False,
        verified_only: bool = False,
    ) -> list[dict]:
        rows = self.conn.execute(
            "SELECT data FROM agents WHERE is_active = 1"
        ).fetchall()
        result = []
        for row in rows:
            data = json.loads(row[0])
            if category and data.get("category") != category:
                continue
            if free_only and data.get("price_usd", 0) > 0:
                continue
            if verified_only and not data.get("is_verified", False):
                continue
            if search:
                searchable = f"{data.get('name','')} {data.get('description','')} {' '.join(data.get('tags',[]))}".lower()
                if search.lower() not in searchable:
                    continue
            result.append(data)
        return sorted(result, key=lambda x: x.get("downloads", 0), reverse=True)

    def get_agent(self, agent_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT data FROM agents WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def publish_agent(self, agent: MarketplaceAgent) -> str:
        import dataclasses
        self.conn.execute(
            "INSERT INTO agents VALUES (?,?,?,1)",
            (agent.agent_id, json.dumps(dataclasses.asdict(agent)), agent.created_at)
        )
        self.conn.commit()
        return agent.agent_id

    def purchase(self, tenant_id: str, agent_id: str, price: float, method: str = "free") -> str:
        purchase_id = "pur_" + uuid.uuid4().hex[:10]
        self.conn.execute(
            "INSERT INTO purchases VALUES (?,?,?,?,?,?)",
            (purchase_id, tenant_id, agent_id, price, method, datetime.utcnow().isoformat())
        )
        self.conn.commit()
        return purchase_id

    def is_purchased(self, tenant_id: str, agent_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM purchases WHERE tenant_id = ? AND agent_id = ?",
            (tenant_id, agent_id)
        ).fetchone()
        return row is not None

    def get_purchased_agents(self, tenant_id: str) -> list[dict]:
        rows = self.conn.execute("""
            SELECT a.data FROM agents a
            JOIN purchases p ON a.agent_id = p.agent_id
            WHERE p.tenant_id = ?
        """, (tenant_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]


def render_marketplace_page():
    """Streamlit marketplace page — import and call from app.py"""
    import streamlit as st

    st.title("🛒 Agent Marketplace")
    st.caption("Temukan, beli, dan install custom agents untuk bisnis Anda.")

    db = MarketplaceDB()

    # Search & Filter
    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
    with col1:
        search = st.text_input("🔍 Cari agent...", placeholder="e.g. instagram, pajak, whatsapp")
    with col2:
        category = st.selectbox("Kategori", ["Semua"] + CATEGORIES)
    with col3:
        free_only = st.checkbox("Gratis saja")
    with col4:
        verified_only = st.checkbox("Verified")

    agents = db.list_agents(
        category=category if category != "Semua" else None,
        search=search or None,
        free_only=free_only,
        verified_only=verified_only,
    )

    st.caption(f"Menampilkan {len(agents)} agents")
    st.divider()

    # Agent grid
    cols = st.columns(2)
    for i, agent in enumerate(agents):
        with cols[i % 2]:
            with st.container(border=True):
                name = agent.get("name", "")
                is_verified = agent.get("is_verified", False)
                badge = " ✅" if is_verified else ""
                price = agent.get("price_usd", 0)
                price_str = "🆓 Gratis" if price == 0 else f"💵 ${price}"

                st.markdown(f"**{name}{badge}**")
                st.caption(f"{agent.get('category','')} · ⭐ {agent.get('rating', 0)} · ⬇️ {agent.get('downloads',0):,}")
                st.write(agent.get("description", ""))

                tag_str = " ".join([f"`{t}`" for t in agent.get("tags", [])[:3]])
                if tag_str:
                    st.markdown(tag_str)

                col_a, col_b = st.columns([1, 1])
                col_a.write(price_str)
                btn_label = "Install Gratis" if price == 0 else f"Beli ${price}"
                if col_b.button(btn_label, key=f"install_{agent['agent_id']}", use_container_width=True):
                    if price == 0:
                        db.purchase("demo_tenant", agent["agent_id"], 0, "free")
                        st.success(f"✅ {name} berhasil diinstall!")
                    else:
                        st.info(f"💳 Redirect ke payment untuk {name}...")

    st.divider()

    # Publish your agent
    with st.expander("📤 Publish Agent Anda ke Marketplace"):
        st.write("Monetize custom agent Anda. Revenue split 80% creator / 20% CATERYA.")
        with st.form("publish_agent"):
            name = st.text_input("Nama Agent")
            desc = st.text_area("Deskripsi", height=80)
            category_pub = st.selectbox("Kategori", CATEGORIES, key="pub_cat")
            system_prompt = st.text_area("System Prompt", height=150,
                placeholder="You are an AI agent specialized in...")
            col1, col2 = st.columns(2)
            with col1:
                tags_str = st.text_input("Tags (pisah koma)", placeholder="marketing, indonesia")
                author = st.text_input("Nama Author")
            with col2:
                price = st.number_input("Harga ($)", min_value=0.0, step=0.99, value=0.0)
                author_email = st.text_input("Email")

            if st.form_submit_button("📤 Publish", type="primary"):
                if name and desc and system_prompt:
                    agent = MarketplaceAgent.create(
                        name=name, description=desc, author=author,
                        author_email=author_email, category=category_pub,
                        system_prompt=system_prompt, price_usd=price,
                        tags=[t.strip() for t in tags_str.split(",") if t.strip()],
                    )
                    agent_id = db.publish_agent(agent)
                    st.success(f"✅ Agent dipublish! ID: `{agent_id}`")
                    st.info("Agent Anda akan direview oleh tim CATERYA dalam 1-2 hari kerja sebelum mendapat badge Verified.")
                else:
                    st.error("Lengkapi semua field yang diperlukan.")


if __name__ == "__main__":
    import streamlit as st
    st.set_page_config(page_title="CATERYA Marketplace", page_icon="🛒", layout="wide")
    render_marketplace_page()
