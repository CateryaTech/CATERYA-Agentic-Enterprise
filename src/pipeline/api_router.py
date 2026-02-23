"""
CATERYA Agentic Enterprise — Pipeline API Endpoints
====================================================
FastAPI endpoints untuk mengelola dan menjalankan pipeline via REST API.
Tambahkan ke src/api/main.py dengan: app.include_router(pipeline_router)

© 2026 Caterya Tech. All Rights Reserved.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from pydantic import BaseModel, Field

try:
    from src.pipeline.engine import (
        Pipeline, NodeConfig, Edge, EdgeType, PassMode,
        RunStatus, get_pipeline_db, get_pipeline_runner,
    )
    from src.pipeline.templates import get_all_templates
    _OK = True
except ImportError:
    _OK = False

pipeline_router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])


# ── Auth (reuse from main.py) ─────────────────────────────────────────────────

def _get_tenant(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    try:
        from src.saas.tenant_manager import get_tenant_db
        db = get_tenant_db()
        tenant = db.get_by_api_key(x_api_key)
        if tenant:
            return {"tenant_id": tenant.tenant_id, "plan": tenant.plan.value}
    except Exception:
        pass
    if x_api_key == "cae_test_key_demo":
        return {"tenant_id": "demo", "plan": "free"}
    raise HTTPException(status_code=401, detail="Invalid API key")


# ── Request Models ────────────────────────────────────────────────────────────

class NodeConfigRequest(BaseModel):
    node_id:     str
    agent_id:    str
    label:       str
    task_template: str = "{prev}"
    system_prompt_override: str = ""
    model_override: str = ""
    temperature: float = 0.7
    max_tokens:  int   = 2048
    retry_max:   int   = 2
    pass_mode:   str   = "full"
    pass_field:  str   = ""
    ethics_check: bool = True


class EdgeRequest(BaseModel):
    from_node:  str
    to_node:    str
    edge_type:  str = "on_success"
    label:      str = ""


class CreatePipelineRequest(BaseModel):
    name:        str
    description: str = ""
    category:    str = "custom"
    nodes:       list[NodeConfigRequest]
    edges:       list[EdgeRequest]
    tags:        list[str] = Field(default_factory=list)
    input_label: str = "Input"
    input_hint:  str = ""


class RunPipelineRequest(BaseModel):
    initial_input: str = Field(..., description="Input awal yang dikirim ke pipeline")
    triggered_by:  str = "api"
    metadata:      dict = Field(default_factory=dict)


class ClonePipelineRequest(BaseModel):
    new_name: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@pipeline_router.get("/")
async def list_pipelines(
    category: Optional[str] = None,
    templates: bool = True,
    tenant: dict = Depends(_get_tenant),
):
    """List semua pipeline milik tenant + templates."""
    if not _OK:
        return {"pipelines": [], "error": "Pipeline engine not loaded"}
    db = get_pipeline_db()
    pipes = db.list_pipelines(
        tenant_id=tenant["tenant_id"],
        category=category,
        include_templates=templates,
    )
    return {
        "total": len(pipes),
        "pipelines": [
            {
                "pipeline_id": p.pipeline_id,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "nodes": len(p.nodes),
                "tags": p.tags,
                "is_template": p.is_template,
                "run_count": p.run_count,
                "avg_duration_sec": p.avg_duration_sec,
            }
            for p in pipes
        ],
    }


@pipeline_router.get("/templates")
async def list_templates(tenant: dict = Depends(_get_tenant)):
    """List semua built-in templates."""
    if not _OK:
        return {"templates": []}
    templates = get_all_templates()
    return {
        "total": len(templates),
        "templates": [
            {
                "pipeline_id": t.pipeline_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "nodes": len(t.nodes),
                "tags": t.tags,
            }
            for t in templates
        ],
    }


@pipeline_router.post("/")
async def create_pipeline(
    req: CreatePipelineRequest,
    tenant: dict = Depends(_get_tenant),
):
    """Buat pipeline baru."""
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")

    nodes = [
        NodeConfig(
            node_id=n.node_id, agent_id=n.agent_id, label=n.label,
            task_template=n.task_template,
            system_prompt_override=n.system_prompt_override,
            model_override=n.model_override,
            temperature=n.temperature, max_tokens=n.max_tokens,
            retry_max=n.retry_max, pass_mode=PassMode(n.pass_mode),
            pass_field=n.pass_field, ethics_check=n.ethics_check,
        )
        for n in req.nodes
    ]
    edges = [
        Edge(from_node=e.from_node, to_node=e.to_node,
             edge_type=EdgeType(e.edge_type), label=e.label)
        for e in req.edges
    ]

    pipe = Pipeline.create(
        name=req.name, description=req.description,
        category=req.category, tenant_id=tenant["tenant_id"],
        nodes=nodes, edges=edges, tags=req.tags,
        input_label=req.input_label, input_hint=req.input_hint,
        created_by=tenant["tenant_id"],
    )

    errors = pipe.validate()
    if errors:
        raise HTTPException(400, {"errors": errors})

    db = get_pipeline_db()
    db.save_pipeline(pipe)

    return {
        "success": True,
        "pipeline_id": pipe.pipeline_id,
        "name": pipe.name,
        "nodes": len(pipe.nodes),
    }


@pipeline_router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str, tenant: dict = Depends(_get_tenant)):
    """Get detail pipeline."""
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")
    db = get_pipeline_db()
    pipe = db.get_pipeline(pipeline_id)
    if not pipe:
        raise HTTPException(404, f"Pipeline {pipeline_id} tidak ditemukan")
    return pipe.to_dict()


@pipeline_router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, tenant: dict = Depends(_get_tenant)):
    """Hapus pipeline (soft delete)."""
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")
    db = get_pipeline_db()
    pipe = db.get_pipeline(pipeline_id)
    if not pipe:
        raise HTTPException(404, "Pipeline tidak ditemukan")
    if pipe.tenant_id != tenant["tenant_id"] and not pipe.is_template:
        raise HTTPException(403, "Bukan pipeline milik Anda")
    db.delete_pipeline(pipeline_id)
    return {"success": True, "message": f"Pipeline {pipeline_id} dihapus"}


@pipeline_router.post("/{pipeline_id}/clone")
async def clone_pipeline(
    pipeline_id: str,
    req: ClonePipelineRequest,
    tenant: dict = Depends(_get_tenant),
):
    """Clone pipeline (dari template atau pipeline lain)."""
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")
    db = get_pipeline_db()
    pipe = db.get_pipeline(pipeline_id)
    if not pipe:
        raise HTTPException(404, "Pipeline tidak ditemukan")

    import copy, uuid
    from datetime import datetime

    cloned = copy.deepcopy(pipe)
    cloned.pipeline_id  = f"pipe_{uuid.uuid4().hex[:12]}"
    cloned.name         = req.new_name or f"{pipe.name} (Copy)"
    cloned.tenant_id    = tenant["tenant_id"]
    cloned.is_template  = False
    cloned.run_count    = 0
    cloned.avg_duration_sec = 0.0
    cloned.created_at   = datetime.utcnow().isoformat()
    cloned.updated_at   = datetime.utcnow().isoformat()
    cloned.created_by   = tenant["tenant_id"]

    db.save_pipeline(cloned)
    return {
        "success": True,
        "pipeline_id": cloned.pipeline_id,
        "name": cloned.name,
    }


@pipeline_router.post("/{pipeline_id}/run")
async def run_pipeline(
    pipeline_id: str,
    req: RunPipelineRequest,
    background_tasks: BackgroundTasks,
    tenant: dict = Depends(_get_tenant),
):
    """
    Jalankan pipeline. Returns run_id segera (async).
    Poll GET /{pipeline_id}/runs/{run_id} untuk status.
    """
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")

    db = get_pipeline_db()
    pipe = db.get_pipeline(pipeline_id)
    if not pipe:
        raise HTTPException(404, "Pipeline tidak ditemukan")

    import uuid
    from datetime import datetime
    from src.pipeline.engine import PipelineRun, RunStatus

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    placeholder = PipelineRun(
        run_id=run_id, pipeline_id=pipeline_id,
        tenant_id=tenant["tenant_id"],
        status=RunStatus.QUEUED,
        initial_input=req.initial_input,
        steps=[], started_at=datetime.utcnow().isoformat(),
        triggered_by=req.triggered_by, metadata=req.metadata,
    )
    db.save_run(placeholder)

    def _run_in_background():
        runner = get_pipeline_runner()
        runner.run(
            pipeline=pipe,
            initial_input=req.initial_input,
            tenant_id=tenant["tenant_id"],
            triggered_by=req.triggered_by,
        )

    background_tasks.add_task(_run_in_background)

    return {
        "run_id": run_id,
        "status": "queued",
        "pipeline_id": pipeline_id,
        "message": f"Pipeline queued. Poll /api/pipelines/{pipeline_id}/runs/{run_id} untuk status.",
    }


@pipeline_router.post("/{pipeline_id}/run/sync")
async def run_pipeline_sync(
    pipeline_id: str,
    req: RunPipelineRequest,
    tenant: dict = Depends(_get_tenant),
):
    """
    Jalankan pipeline SYNCHRONOUS. Tunggu sampai selesai, kembalikan full result.
    Cocok untuk pipeline pendek (<60s). Untuk pipeline panjang, pakai /run (async).
    """
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")

    db = get_pipeline_db()
    pipe = db.get_pipeline(pipeline_id)
    if not pipe:
        raise HTTPException(404, "Pipeline tidak ditemukan")

    runner = get_pipeline_runner()
    run = runner.run(
        pipeline=pipe,
        initial_input=req.initial_input,
        tenant_id=tenant["tenant_id"],
        triggered_by=req.triggered_by,
    )

    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "duration_sec": run.duration_sec,
        "total_tokens": run.total_tokens,
        "final_output": run.final_output,
        "error": run.error,
        "steps": [
            {
                "node_id": s.node_id,
                "agent_id": s.agent_id,
                "status": s.status.value,
                "output": s.output_text,
                "tokens": s.tokens_in + s.tokens_out,
                "latency_ms": s.latency_ms,
                "ethics_passed": s.ethics_passed,
            }
            for s in run.steps
        ],
    }


@pipeline_router.get("/{pipeline_id}/runs")
async def list_runs(
    pipeline_id: str,
    limit: int = 20,
    tenant: dict = Depends(_get_tenant),
):
    """List run history untuk pipeline."""
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")
    db = get_pipeline_db()
    runs = db.list_runs(pipeline_id, limit=limit)
    return {"pipeline_id": pipeline_id, "runs": runs}


@pipeline_router.get("/{pipeline_id}/runs/{run_id}")
async def get_run(
    pipeline_id: str,
    run_id: str,
    tenant: dict = Depends(_get_tenant),
):
    """Get status dan detail satu run."""
    if not _OK:
        raise HTTPException(500, "Pipeline engine not loaded")
    db = get_pipeline_db()
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} tidak ditemukan")
    return {
        "run_id": run.run_id,
        "pipeline_id": run.pipeline_id,
        "status": run.status.value,
        "duration_sec": run.duration_sec,
        "total_tokens": run.total_tokens,
        "total_cost_usd": run.total_cost_usd,
        "final_output": run.final_output,
        "error": run.error,
        "steps_count": len(run.steps),
        "steps": [
            {
                "node_id": s.node_id, "agent_id": s.agent_id,
                "status": s.status.value, "latency_ms": s.latency_ms,
                "tokens": s.tokens_in + s.tokens_out,
                "ethics_passed": s.ethics_passed,
            }
            for s in run.steps
        ],
    }


@pipeline_router.get("/stats/overview")
async def pipeline_stats(tenant: dict = Depends(_get_tenant)):
    """Overview statistik semua pipeline tenant."""
    if not _OK:
        return {"error": "Pipeline engine not loaded"}
    db = get_pipeline_db()
    stats = db.get_tenant_run_stats(tenant["tenant_id"])
    return stats
