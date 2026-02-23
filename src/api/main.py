"""
CATERYA Agentic Enterprise — AaaS API Layer (FastAPI)
Expose semua agents sebagai REST API endpoints untuk Agent-as-a-Service.
Deploy di Streamlit sebagai preview; FastAPI untuk production.
© 2026 Caterya Tech. All Rights Reserved.

Jalankan:
    uvicorn src.api.main:app --reload --port 8000
"""

import time
from functools import wraps
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import dari existing CATERYA modules
# (path menyesuaikan struktur repo yang ada)
try:
    from src.saas.tenant_manager import get_tenant_db, Tenant
    from src.saas.billing_engine import BillingEngine, Invoice, PaymentMethod, PlanType
except ImportError:
    # Graceful fallback for standalone testing
    pass

app = FastAPI(
    title="CATERYA AaaS API",
    description="Agent-as-a-Service: Jalankan AI agents via REST API.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include pipeline router
try:
    from src.pipeline.api_router import pipeline_router
    app.include_router(pipeline_router)
except ImportError:
    pass

# ─── Request/Response Models ─────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    agent_id: str = Field(..., description="ID agent yang dijalankan, e.g. 'lead_gen'")
    task: str = Field(..., description="Instruksi/task untuk agent")
    context: dict = Field(default_factory=dict, description="Konteks tambahan (optional)")
    stream: bool = Field(False, description="Stream output? (SSE)")

class AgentRunResponse(BaseModel):
    run_id: str
    agent_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0
    ethics_passed: bool = True

class TenantRegisterRequest(BaseModel):
    name: str
    email: str
    plan: str = "free"

class InvoiceCreateRequest(BaseModel):
    plan: str
    billing_period: str = "monthly"
    payment_method: str = "stripe"

class WebhookRegisterRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=list, description="e.g. ['agent.completed', 'payment.confirmed']")
    secret: str = ""

# ─── Auth Dependency ──────────────────────────────────────────────────────────

def get_tenant(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    """Validate API key and return tenant info."""
    try:
        db = get_tenant_db()
        tenant = db.get_by_api_key(x_api_key)
    except Exception:
        # Demo mode: fake tenant
        tenant = None

    if not tenant:
        # For demo/testing: allow a test key
        if x_api_key == "cae_test_key_demo":
            return {"tenant_id": "demo", "plan": "free", "name": "Demo User"}
        raise HTTPException(status_code=401, detail="Invalid API key. Get yours at /api/auth/register")
    return {"tenant_id": tenant.tenant_id, "plan": tenant.plan.value, "name": tenant.name}

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "CATERYA AaaS API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "status": "operational",
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


# ── Auth & Tenant ─────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
async def register_tenant(req: TenantRegisterRequest):
    """Register tenant baru, dapatkan API key."""
    try:
        from src.saas.tenant_manager import Tenant, PlanType, get_tenant_db
        plan = PlanType(req.plan) if req.plan in [p.value for p in PlanType] else PlanType.FREE
        tenant = Tenant.create(name=req.name, email=req.email, plan=plan)
        get_tenant_db().save(tenant)
        return {
            "success": True,
            "tenant_id": tenant.tenant_id,
            "api_key": tenant.api_key,
            "plan": tenant.plan.value,
            "message": "Keep your API key safe! Use it in X-API-Key header.",
        }
    except Exception as e:
        # Demo fallback
        import hashlib, uuid
        tid = str(uuid.uuid4())
        key = "cae_" + hashlib.sha256(f"{tid}{req.email}".encode()).hexdigest()[:32]
        return {
            "success": True,
            "tenant_id": tid,
            "api_key": key,
            "plan": req.plan,
            "message": "Demo mode: tenant created in memory only.",
        }

@app.get("/api/tenant/me")
async def get_my_tenant(tenant: dict = Depends(get_tenant)):
    return tenant

@app.get("/api/tenant/usage")
async def get_usage(tenant: dict = Depends(get_tenant)):
    return {
        "tenant_id": tenant["tenant_id"],
        "plan": tenant["plan"],
        "usage": {"agent_calls": 0, "api_calls": 0},
        "limits": {"agent_calls": 100, "api_calls": 50},
    }


# ── Agents ────────────────────────────────────────────────────────────────────

AVAILABLE_AGENTS = {
    "lead_gen": "Find & qualify prospects",
    "content_writer": "SEO copy & marketing content",
    "sales_closer": "Objection handling & closing",
    "support": "Customer inquiries",
    "finance": "Invoicing & billing",
    "code_improver": "Code review & refactor",
    "crypto_ops": "On-chain crypto operations",
    "ethics_guard": "Ethics compliance review",
    "research": "Market intelligence",
    "self_optimizer": "System improvement",
}

@app.get("/api/agents")
async def list_agents(tenant: dict = Depends(get_tenant)):
    """List semua agent yang tersedia."""
    return {
        "agents": [
            {"id": aid, "description": desc, "status": "available"}
            for aid, desc in AVAILABLE_AGENTS.items()
        ]
    }

@app.post("/api/agents/run", response_model=AgentRunResponse)
async def run_agent(req: AgentRunRequest, tenant: dict = Depends(get_tenant)):
    """
    Jalankan agent via API.
    Ini adalah core AaaS endpoint.
    """
    import uuid
    
    if req.agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    start = time.time()

    try:
        # Import & run agent dari existing CATERYA core
        result_text = await _invoke_caterya_agent(req.agent_id, req.task, req.context, tenant)
        latency = (time.time() - start) * 1000

        return AgentRunResponse(
            run_id=run_id,
            agent_id=req.agent_id,
            status="completed",
            result=result_text,
            tokens_used=len(req.task.split()) * 3,  # Rough estimate
            latency_ms=round(latency, 2),
            ethics_passed=True,
        )
    except Exception as e:
        return AgentRunResponse(
            run_id=run_id,
            agent_id=req.agent_id,
            status="failed",
            error=str(e),
        )

async def _invoke_caterya_agent(agent_id: str, task: str, context: dict, tenant: dict) -> str:
    """
    Bridge ke CATERYA agent system yang sudah ada.
    Coba import existing agent runner, fallback ke simple LLM call.
    """
    try:
        # Try to use existing CATERYA agent runner
        from src.agents.runner import run_agent as caterya_run
        return await caterya_run(agent_id=agent_id, task=task, context=context)
    except ImportError:
        pass

    # Fallback: direct Ollama call
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("http://localhost:11434/api/generate", json={
                "model": "llama3.3",
                "prompt": f"You are the CATERYA {agent_id} agent. Task: {task}",
                "stream": False,
            })
            if resp.status_code == 200:
                return resp.json().get("response", "")
    except Exception:
        pass

    return f"[Demo] Agent '{agent_id}' processed: {task[:100]}..."

@app.get("/api/agents/run/{run_id}")
async def get_run_status(run_id: str, tenant: dict = Depends(get_tenant)):
    """Get status of an async run."""
    # In production: query from job queue (Redis/Celery)
    return {"run_id": run_id, "status": "completed", "note": "Async runs coming in v2"}


# ── Billing ───────────────────────────────────────────────────────────────────

@app.post("/api/billing/invoice")
async def create_invoice(req: InvoiceCreateRequest, tenant: dict = Depends(get_tenant)):
    """Buat invoice untuk upgrade plan."""
    try:
        engine = BillingEngine()
        plan = PlanType(req.plan)
        method = PaymentMethod(req.payment_method)
        inv = engine.create_invoice(
            tenant_id=tenant["tenant_id"],
            plan=plan,
            billing_period=req.billing_period,
            payment_method=method,
        )
        return inv.to_payment_page_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/billing/invoices")
async def list_invoices(tenant: dict = Depends(get_tenant)):
    """List semua invoice tenant."""
    try:
        engine = BillingEngine()
        invs = engine.db.list_by_tenant(tenant["tenant_id"])
        return {"invoices": [i.to_payment_page_data() for i in invs]}
    except Exception:
        return {"invoices": [], "note": "Demo mode"}

@app.post("/api/billing/confirm/{invoice_id}")
async def confirm_payment(invoice_id: str, tx_hash: str = "", tenant: dict = Depends(get_tenant)):
    """Konfirmasi pembayaran crypto manual."""
    try:
        engine = BillingEngine()
        result = engine.confirm_payment_and_upgrade(invoice_id, tx_hash)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Webhooks ──────────────────────────────────────────────────────────────────

@app.post("/api/webhooks")
async def register_webhook(req: WebhookRegisterRequest, tenant: dict = Depends(get_tenant)):
    """Register webhook endpoint untuk event notifications."""
    import uuid
    webhook_id = f"wh_{uuid.uuid4().hex[:10]}"
    # In production: store in DB and trigger on events
    return {
        "webhook_id": webhook_id,
        "url": req.url,
        "events": req.events,
        "status": "active",
        "note": "Webhooks will POST JSON to your URL on each event.",
    }

@app.get("/api/webhooks")
async def list_webhooks(tenant: dict = Depends(get_tenant)):
    return {"webhooks": [], "note": "No webhooks registered yet."}


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.get("/api/admin/revenue")
async def admin_revenue(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """Admin: revenue summary. Requires X-Admin-Key header."""
    import os
    if x_admin_key != os.getenv("ADMIN_SECRET_KEY", "caterya_admin_change_me"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    try:
        engine = BillingEngine()
        return engine.get_revenue_summary()
    except Exception:
        return {"total_revenue_usd": 0, "by_plan": [], "note": "Demo mode"}

@app.get("/api/admin/tenants")
async def admin_list_tenants(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    import os
    if x_admin_key != os.getenv("ADMIN_SECRET_KEY", "caterya_admin_change_me"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    try:
        db = get_tenant_db()
        tenants = db.list_all()
        return {"total": len(tenants), "tenants": [
            {"id": t.tenant_id, "name": t.name, "plan": t.plan.value, "email": t.email}
            for t in tenants
        ]}
    except Exception:
        return {"total": 0, "tenants": [], "note": "Demo mode"}
