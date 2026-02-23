"""
CATERYA Agentic Enterprise — Multi-Agent Pipeline Engine
=========================================================
Core engine untuk membuat, menyimpan, dan menjalankan pipeline
multi-agent yang sepenuhnya bisa dikonfigurasi (bukan hardcoded).

Konsep:
  - Pipeline  : DAG (Directed Acyclic Graph) dari Node-Node agent
  - Node       : Satu agent + konfigurasinya di dalam pipeline
  - Edge       : Koneksi antar Node (output satu → input berikutnya)
  - Run        : Satu eksekusi sebuah Pipeline dengan input tertentu
  - Step       : Satu eksekusi sebuah Node di dalam sebuah Run

© 2026 Caterya Tech. All Rights Reserved.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class NodeStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    SKIPPED   = "skipped"
    FAILED    = "failed"
    BLOCKED   = "blocked"   # dihentikan oleh ethics guard


class RunStatus(str, Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class EdgeType(str, Enum):
    ALWAYS      = "always"       # selalu lanjut
    ON_SUCCESS  = "on_success"   # lanjut hanya jika node sebelumnya sukses
    ON_FAILURE  = "on_failure"   # lanjut hanya jika node sebelumnya gagal
    CONDITIONAL = "conditional"  # lanjut jika output mengandung kata kunci tertentu


class PassMode(str, Enum):
    """Bagaimana output node sebelumnya diteruskan ke node berikutnya."""
    FULL        = "full"        # teruskan seluruh output mentah
    SUMMARY     = "summary"     # minta LLM meringkas dulu
    FIELD       = "field"       # ambil field JSON tertentu
    APPEND      = "append"      # gabungkan semua output sebelumnya
    NONE        = "none"        # node berikutnya mulai fresh (hanya konteks awal)


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeConfig:
    """Konfigurasi satu node di dalam pipeline."""
    node_id:        str
    agent_id:       str                 # e.g. "lead_gen", "content_writer"
    label:          str                 # nama tampilan, bebas
    system_prompt_override: str = ""    # override system prompt agent (opsional)
    task_template:  str = "{input}"     # template task; {input} = output node sebelumnya
    model_override: str = ""            # paksa pakai model tertentu (opsional)
    temperature:    float = 0.7
    max_tokens:     int   = 2048
    timeout_sec:    int   = 120
    retry_max:      int   = 2
    pass_mode:      PassMode = PassMode.FULL
    pass_field:     str   = ""          # untuk PassMode.FIELD: nama field JSON
    condition_kw:   list[str] = field(default_factory=list)  # untuk EdgeType.CONDITIONAL
    ethics_check:   bool  = True        # apakah output node ini perlu dicek ethics guard
    metadata:       dict  = field(default_factory=dict)


@dataclass
class Edge:
    """Koneksi dari satu node ke node lain."""
    from_node: str
    to_node:   str
    edge_type: EdgeType = EdgeType.ON_SUCCESS
    label:     str = ""


@dataclass
class Pipeline:
    """Definisi sebuah pipeline multi-agent."""
    pipeline_id:  str
    name:         str
    description:  str
    category:     str           # "sales", "content", "research", dst.
    tenant_id:    str
    nodes:        list[NodeConfig]
    edges:        list[Edge]
    input_label:  str = "Input Awal"
    input_hint:   str = "Masukkan data/instruksi untuk pipeline ini..."
    is_active:    bool = True
    is_template:  bool = False  # True = tersedia di template library
    version:      str  = "1.0.0"
    created_at:   str  = ""
    updated_at:   str  = ""
    created_by:   str  = ""
    tags:         list[str] = field(default_factory=list)
    run_count:    int  = 0
    avg_duration_sec: float = 0.0

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        category: str,
        tenant_id: str,
        nodes: list[NodeConfig],
        edges: list[Edge],
        **kwargs,
    ) -> "Pipeline":
        now = datetime.utcnow().isoformat()
        return cls(
            pipeline_id=f"pipe_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            category=category,
            tenant_id=tenant_id,
            nodes=nodes,
            edges=edges,
            created_at=now,
            updated_at=now,
            **kwargs,
        )

    def get_node(self, node_id: str) -> Optional[NodeConfig]:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def get_start_nodes(self) -> list[NodeConfig]:
        """Node yang tidak punya incoming edge = titik awal."""
        has_incoming = {e.to_node for e in self.edges}
        return [n for n in self.nodes if n.node_id not in has_incoming]

    def get_next_nodes(self, from_node_id: str, status: NodeStatus) -> list[NodeConfig]:
        """Cari node-node berikutnya berdasarkan edge type dan status sebelumnya."""
        result = []
        for edge in self.edges:
            if edge.from_node != from_node_id:
                continue
            if edge.edge_type == EdgeType.ALWAYS:
                result.append(self.get_node(edge.to_node))
            elif edge.edge_type == EdgeType.ON_SUCCESS and status == NodeStatus.COMPLETED:
                result.append(self.get_node(edge.to_node))
            elif edge.edge_type == EdgeType.ON_FAILURE and status in (NodeStatus.FAILED, NodeStatus.BLOCKED):
                result.append(self.get_node(edge.to_node))
        return [n for n in result if n is not None]

    def validate(self) -> list[str]:
        """Validasi struktur pipeline. Return list error (kosong = valid)."""
        errors = []
        node_ids = {n.node_id for n in self.nodes}

        if not self.nodes:
            errors.append("Pipeline harus punya minimal 1 node.")

        for edge in self.edges:
            if edge.from_node not in node_ids:
                errors.append(f"Edge dari node tidak dikenal: {edge.from_node}")
            if edge.to_node not in node_ids:
                errors.append(f"Edge ke node tidak dikenal: {edge.to_node}")

        if not self.get_start_nodes():
            errors.append("Tidak ada start node (semua node punya incoming edge = cycle).")

        if not self.name.strip():
            errors.append("Nama pipeline tidak boleh kosong.")

        return errors

    def to_dict(self) -> dict:
        return {
            **{k: v for k, v in asdict(self).items() if k not in ("nodes", "edges")},
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pipeline":
        nodes = [NodeConfig(**{**n, "pass_mode": PassMode(n.get("pass_mode", "full"))})
                 for n in data.pop("nodes", [])]
        edges = [Edge(**{**e, "edge_type": EdgeType(e.get("edge_type", "on_success"))})
                 for e in data.pop("edges", [])]
        return cls(nodes=nodes, edges=edges, **data)


@dataclass
class StepResult:
    """Hasil eksekusi satu Node dalam sebuah Run."""
    step_id:      str
    run_id:       str
    node_id:      str
    agent_id:     str
    status:       NodeStatus
    input_text:   str
    output_text:  str
    error:        str         = ""
    tokens_in:    int         = 0
    tokens_out:   int         = 0
    latency_ms:   float       = 0.0
    model_used:   str         = ""
    ethics_passed: bool       = True
    started_at:   str         = ""
    finished_at:  str         = ""
    retry_count:  int         = 0


@dataclass
class PipelineRun:
    """Satu eksekusi pipeline lengkap."""
    run_id:       str
    pipeline_id:  str
    tenant_id:    str
    status:       RunStatus
    initial_input: str
    steps:        list[StepResult]
    final_output: str         = ""
    error:        str         = ""
    started_at:   str         = ""
    finished_at:  str         = ""
    total_tokens: int         = 0
    total_cost_usd: float     = 0.0
    triggered_by: str         = "manual"   # "manual" | "api" | "webhook" | "schedule"
    metadata:     dict        = field(default_factory=dict)

    @property
    def duration_sec(self) -> float:
        if self.started_at and self.finished_at:
            try:
                s = datetime.fromisoformat(self.started_at)
                e = datetime.fromisoformat(self.finished_at)
                return (e - s).total_seconds()
            except Exception:
                pass
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════

class PipelineDB:
    """SQLite store untuk pipelines dan runs."""

    def __init__(self, db_path: str = "data/pipelines.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS pipelines (
                pipeline_id  TEXT PRIMARY KEY,
                tenant_id    TEXT NOT NULL,
                name         TEXT NOT NULL,
                description  TEXT,
                category     TEXT,
                data         TEXT NOT NULL,      -- JSON blob full pipeline
                is_active    INTEGER DEFAULT 1,
                is_template  INTEGER DEFAULT 0,
                version      TEXT DEFAULT '1.0.0',
                run_count    INTEGER DEFAULT 0,
                avg_duration_sec REAL DEFAULT 0,
                created_at   TEXT,
                updated_at   TEXT,
                created_by   TEXT
            );
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id       TEXT PRIMARY KEY,
                pipeline_id  TEXT NOT NULL,
                tenant_id    TEXT NOT NULL,
                status       TEXT NOT NULL,
                initial_input TEXT,
                final_output TEXT,
                error        TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0,
                triggered_by TEXT DEFAULT 'manual',
                started_at   TEXT,
                finished_at  TEXT,
                metadata     TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS pipeline_steps (
                step_id      TEXT PRIMARY KEY,
                run_id       TEXT NOT NULL,
                node_id      TEXT NOT NULL,
                agent_id     TEXT NOT NULL,
                status       TEXT NOT NULL,
                input_text   TEXT,
                output_text  TEXT,
                error        TEXT DEFAULT '',
                tokens_in    INTEGER DEFAULT 0,
                tokens_out   INTEGER DEFAULT 0,
                latency_ms   REAL DEFAULT 0,
                model_used   TEXT DEFAULT '',
                ethics_passed INTEGER DEFAULT 1,
                retry_count  INTEGER DEFAULT 0,
                started_at   TEXT,
                finished_at  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_runs_pipeline ON pipeline_runs(pipeline_id);
            CREATE INDEX IF NOT EXISTS idx_runs_tenant   ON pipeline_runs(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_steps_run     ON pipeline_steps(run_id);
        """)
        self.conn.commit()

    # ── Pipelines ──────────────────────────────────────────────

    def save_pipeline(self, p: Pipeline):
        self.conn.execute("""
            INSERT OR REPLACE INTO pipelines
            (pipeline_id,tenant_id,name,description,category,data,
             is_active,is_template,version,run_count,avg_duration_sec,
             created_at,updated_at,created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            p.pipeline_id, p.tenant_id, p.name, p.description, p.category,
            json.dumps(p.to_dict()), int(p.is_active), int(p.is_template),
            p.version, p.run_count, p.avg_duration_sec,
            p.created_at, p.updated_at, p.created_by,
        ))
        self.conn.commit()

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        row = self.conn.execute(
            "SELECT data FROM pipelines WHERE pipeline_id=?", (pipeline_id,)
        ).fetchone()
        if not row:
            return None
        return Pipeline.from_dict(json.loads(row["data"]))

    def list_pipelines(
        self,
        tenant_id: str,
        category: Optional[str] = None,
        include_templates: bool = True,
    ) -> list[Pipeline]:
        q = "SELECT data FROM pipelines WHERE (tenant_id=? OR is_template=1) AND is_active=1"
        params: list = [tenant_id]
        if category:
            q += " AND category=?"
            params.append(category)
        if not include_templates:
            q += " AND is_template=0"
        rows = self.conn.execute(q, params).fetchall()
        return [Pipeline.from_dict(json.loads(r["data"])) for r in rows]

    def delete_pipeline(self, pipeline_id: str):
        self.conn.execute("UPDATE pipelines SET is_active=0 WHERE pipeline_id=?", (pipeline_id,))
        self.conn.commit()

    def update_stats(self, pipeline_id: str, duration_sec: float):
        """Update run_count dan avg_duration_sec setelah run selesai."""
        row = self.conn.execute(
            "SELECT run_count, avg_duration_sec FROM pipelines WHERE pipeline_id=?",
            (pipeline_id,)
        ).fetchone()
        if row:
            n = (row["run_count"] or 0) + 1
            avg = ((row["avg_duration_sec"] or 0) * (n - 1) + duration_sec) / n
            self.conn.execute(
                "UPDATE pipelines SET run_count=?, avg_duration_sec=?, updated_at=? WHERE pipeline_id=?",
                (n, avg, datetime.utcnow().isoformat(), pipeline_id)
            )
            self.conn.commit()

    # ── Runs ───────────────────────────────────────────────────

    def save_run(self, run: PipelineRun):
        self.conn.execute("""
            INSERT OR REPLACE INTO pipeline_runs
            (run_id,pipeline_id,tenant_id,status,initial_input,
             final_output,error,total_tokens,total_cost_usd,
             triggered_by,started_at,finished_at,metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            run.run_id, run.pipeline_id, run.tenant_id, run.status.value,
            run.initial_input, run.final_output, run.error,
            run.total_tokens, run.total_cost_usd, run.triggered_by,
            run.started_at, run.finished_at, json.dumps(run.metadata),
        ))
        self.conn.commit()

    def save_step(self, step: StepResult):
        self.conn.execute("""
            INSERT OR REPLACE INTO pipeline_steps
            (step_id,run_id,node_id,agent_id,status,input_text,output_text,
             error,tokens_in,tokens_out,latency_ms,model_used,
             ethics_passed,retry_count,started_at,finished_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            step.step_id, step.run_id, step.node_id, step.agent_id,
            step.status.value, step.input_text, step.output_text,
            step.error, step.tokens_in, step.tokens_out, step.latency_ms,
            step.model_used, int(step.ethics_passed), step.retry_count,
            step.started_at, step.finished_at,
        ))
        self.conn.commit()

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        row = self.conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row:
            return None
        steps_rows = self.conn.execute(
            "SELECT * FROM pipeline_steps WHERE run_id=? ORDER BY started_at", (run_id,)
        ).fetchall()
        steps = [StepResult(
            step_id=s["step_id"], run_id=s["run_id"], node_id=s["node_id"],
            agent_id=s["agent_id"], status=NodeStatus(s["status"]),
            input_text=s["input_text"] or "", output_text=s["output_text"] or "",
            error=s["error"] or "", tokens_in=s["tokens_in"], tokens_out=s["tokens_out"],
            latency_ms=s["latency_ms"], model_used=s["model_used"] or "",
            ethics_passed=bool(s["ethics_passed"]), retry_count=s["retry_count"],
            started_at=s["started_at"] or "", finished_at=s["finished_at"] or "",
        ) for s in steps_rows]
        return PipelineRun(
            run_id=row["run_id"], pipeline_id=row["pipeline_id"],
            tenant_id=row["tenant_id"], status=RunStatus(row["status"]),
            initial_input=row["initial_input"] or "",
            final_output=row["final_output"] or "", error=row["error"] or "",
            total_tokens=row["total_tokens"], total_cost_usd=row["total_cost_usd"],
            triggered_by=row["triggered_by"] or "manual",
            started_at=row["started_at"] or "", finished_at=row["finished_at"] or "",
            metadata=json.loads(row["metadata"] or "{}"),
            steps=steps,
        )

    def list_runs(self, pipeline_id: str, limit: int = 20) -> list[dict]:
        rows = self.conn.execute("""
            SELECT run_id, status, started_at, finished_at,
                   total_tokens, triggered_by, final_output
            FROM pipeline_runs
            WHERE pipeline_id=?
            ORDER BY started_at DESC LIMIT ?
        """, (pipeline_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_tenant_run_stats(self, tenant_id: str) -> dict:
        row = self.conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as success,
                   SUM(total_tokens) as tokens,
                   SUM(total_cost_usd) as cost
            FROM pipeline_runs WHERE tenant_id=?
        """, (tenant_id,)).fetchone()
        total = row["total"] or 0
        success = row["success"] or 0
        return {
            "total_runs": total,
            "success_runs": success,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "total_tokens": row["tokens"] or 0,
            "total_cost_usd": round(row["cost"] or 0, 4),
        }


# ══════════════════════════════════════════════════════════════════════════════
# LLM EXECUTOR  (bridge ke Ollama / cloud)
# ══════════════════════════════════════════════════════════════════════════════

class LLMExecutor:
    """
    Jalankan satu LLM call. Coba Ollama dulu, fallback ke Groq/Together.
    Dipakai oleh PipelineRunner untuk setiap node.
    """

    def __init__(self):
        import os
        self.ollama_url   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.3")
        self.groq_key     = os.getenv("GROQ_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")

    def _build_system_prompt(self, agent_id: str, override: str) -> str:
        if override:
            return override
        AGENT_PROMPTS = {
            "lead_gen":       "Kamu adalah agen Lead Generation ahli. Temukan, kualifikasi, dan skor prospek bisnis secara sistematis.",
            "content_writer": "Kamu adalah penulis konten profesional. Buat konten yang engaging, SEO-friendly, dan sesuai target audiens.",
            "sales_closer":   "Kamu adalah sales closer berpengalaman. Handle objeksi, bangun urgensi, dan arahkan ke closing.",
            "support":        "Kamu adalah agen customer support ramah dan solutif. Jawab dengan empati dan berikan solusi konkret.",
            "finance":        "Kamu adalah analis keuangan bisnis. Buat laporan, invoice, dan analisis keuangan yang akurat.",
            "code_improver":  (
                "Kamu adalah senior software engineer dengan 10+ tahun pengalaman. "
                "Kamu ahli dalam: menulis kode baru dari requirement, review dan refactor kode existing, "
                "debug, security audit, menulis tests, dan dokumentasi teknis. "
                "Selalu tulis kode yang lengkap, production-ready, dengan type hints, error handling, dan docstrings. "
                "Jangan tulis pseudocode — tulis kode nyata yang bisa langsung dijalankan."
            ),
            "research":       "Kamu adalah analis riset pasar. Lakukan riset mendalam dan sajikan insight yang actionable.",
            "ethics_guard":   "Kamu adalah etika bisnis auditor. Evaluasi apakah konten sesuai standar etika bisnis yang baik.",
            "self_optimizer": "Kamu adalah AI system optimizer. Analisis performa sistem dan rekomendasikan peningkatan.",
            "copywriter":     "Kamu adalah copywriter persuasif. Buat copy yang menggerakkan emosi dan mendorong konversi.",
            "seo_analyst":    "Kamu adalah SEO specialist. Analisis dan optimalkan konten untuk mesin pencari.",
            "email_writer":   "Kamu adalah email marketing specialist. Tulis email yang personal, relevan, dan tinggi open rate.",
            "social_media":   "Kamu adalah social media manager. Buat konten yang viral-worthy dan sesuai platform.",
            "data_analyst":   "Kamu adalah data analyst. Interpretasikan data dan hasilkan insight bisnis yang berguna.",
            "translator":     "Kamu adalah penerjemah profesional. Terjemahkan dengan akurat sambil mempertahankan nuansa.",
            "summarizer":     "Kamu adalah information synthesizer. Ringkas informasi kompleks menjadi poin-poin kunci.",
            "product_manager":(
                "Kamu adalah Product Manager berpengalaman di startup teknologi. "
                "Kamu ahli dalam: validasi ide produk, menulis PRD, mendefinisikan user stories, "
                "memprioritaskan feature backlog, membuat roadmap, dan bridging antara bisnis dan engineering. "
                "Selalu berpikir dari perspektif user dan bisnis, bukan hanya teknis."
            ),
        }
        return AGENT_PROMPTS.get(agent_id, f"Kamu adalah agen AI spesialis {agent_id}. Selesaikan task dengan baik.")

    def run(
        self,
        agent_id: str,
        task: str,
        system_override: str = "",
        model_override: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> tuple[str, str, int, int]:
        """
        Returns: (output_text, model_used, tokens_in, tokens_out)
        """
        system = self._build_system_prompt(agent_id, system_override)
        model  = model_override or self.default_model

        # Try Ollama first
        try:
            import urllib.request
            payload = json.dumps({
                "model": model,
                "prompt": f"{system}\n\nTask:\n{task}",
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }).encode()
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            output = data.get("response", "")
            tokens_in  = data.get("prompt_eval_count", len(task.split()) * 2)
            tokens_out = data.get("eval_count", len(output.split()))
            return output, f"ollama/{model}", tokens_in, tokens_out
        except Exception as ollama_err:
            pass

        # Fallback: Groq
        if self.groq_key:
            try:
                import urllib.request
                payload = json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": task},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }).encode()
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self.groq_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                content = data["choices"][0]["message"]["content"]
                usage   = data.get("usage", {})
                return content, "groq/llama-3.3-70b", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            except Exception:
                pass

        # Demo fallback (no LLM available)
        demo_output = (
            f"[DEMO — Hubungkan Ollama atau isi GROQ_API_KEY]\n\n"
            f"Agent **{agent_id}** menerima task:\n{task[:300]}\n\n"
            f"Output nyata akan muncul setelah LLM terhubung."
        )
        return demo_output, "demo/mock", len(task.split()), 50


# ══════════════════════════════════════════════════════════════════════════════
# ETHICS GUARD
# ══════════════════════════════════════════════════════════════════════════════

class EthicsGuard:
    """
    Cek apakah output sebuah agent lolos ethics check.
    Menggunakan LLM sederhana (atau rule-based jika LLM tidak tersedia).
    """

    BLOCKED_KEYWORDS = [
        "penipuan", "scam", "fraud", "illegal", "money laundering",
        "manipulasi harga", "insider trading", "plagiat", "hate speech",
        "diskriminasi", "harassment", "hoaks", "disinformasi",
    ]

    def check(self, text: str, context: str = "") -> tuple[bool, str]:
        """
        Returns: (passed: bool, reason: str)
        """
        text_lower = text.lower()
        for kw in self.BLOCKED_KEYWORDS:
            if kw in text_lower:
                return False, f"Konten mengandung kata terlarang: '{kw}'"
        return True, "OK"


# ══════════════════════════════════════════════════════════════════════════════
# INPUT TRANSFORMER  (PassMode logic)
# ══════════════════════════════════════════════════════════════════════════════

class InputTransformer:
    """Transformasi output node sebelumnya sebelum dikirim ke node berikutnya."""

    def transform(
        self,
        node: NodeConfig,
        initial_input: str,
        prev_outputs: list[tuple[str, str]],  # [(node_id, output_text)]
        all_step_results: list[StepResult],
    ) -> str:
        """Hasilkan input_text untuk node ini."""

        # Ambil output terakhir (immediate predecessor)
        last_output = prev_outputs[-1][1] if prev_outputs else initial_input

        mode = node.pass_mode

        if mode == PassMode.NONE:
            prev_ctx = ""
        elif mode == PassMode.FULL:
            prev_ctx = last_output
        elif mode == PassMode.APPEND:
            prev_ctx = "\n\n---\n\n".join(f"[{nid}]\n{out}" for nid, out in prev_outputs)
        elif mode == PassMode.FIELD:
            try:
                data = json.loads(last_output)
                prev_ctx = str(data.get(node.pass_field, last_output))
            except Exception:
                prev_ctx = last_output
        elif mode == PassMode.SUMMARY:
            # Untuk produksi, bisa pakai LLM; sini kita ambil 500 char pertama
            prev_ctx = last_output[:500] + ("..." if len(last_output) > 500 else "")
        else:
            prev_ctx = last_output

        # Render task_template
        try:
            task = node.task_template.format(
                input=initial_input,
                prev=prev_ctx,
                last=last_output,
            )
        except KeyError:
            task = node.task_template

        return task


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

class PipelineRunner:
    """
    Eksekutor utama. Jalan secara synchronous (cocok untuk Streamlit).
    Untuk async / queue-based, wrap dengan thread executor.
    """

    def __init__(self, db: Optional[PipelineDB] = None):
        self.db          = db or PipelineDB()
        self.llm         = LLMExecutor()
        self.ethics      = EthicsGuard()
        self.transformer = InputTransformer()

    def run(
        self,
        pipeline: Pipeline,
        initial_input: str,
        tenant_id: str = "default",
        triggered_by: str = "manual",
        step_callback=None,   # callable(StepResult) — untuk live update di UI
    ) -> PipelineRun:
        """
        Eksekusi pipeline secara synchronous.
        step_callback dipanggil setiap kali satu step selesai.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now    = datetime.utcnow().isoformat()

        pipeline_run = PipelineRun(
            run_id=run_id,
            pipeline_id=pipeline.pipeline_id,
            tenant_id=tenant_id,
            status=RunStatus.RUNNING,
            initial_input=initial_input,
            steps=[],
            started_at=now,
            triggered_by=triggered_by,
        )
        self.db.save_run(pipeline_run)

        # BFS execution
        completed_nodes: dict[str, StepResult] = {}  # node_id → StepResult
        queue = list(pipeline.get_start_nodes())

        try:
            while queue:
                node = queue.pop(0)

                # Skip jika sudah dieksekusi (bisa terjadi kalau ada multiple incoming edges)
                if node.node_id in completed_nodes:
                    continue

                # Hitung input untuk node ini
                prev_outputs = [
                    (nid, res.output_text)
                    for nid, res in completed_nodes.items()
                ]
                input_text = self.transformer.transform(
                    node, initial_input, prev_outputs, pipeline_run.steps
                )

                # Eksekusi node (dengan retry)
                step = self._execute_node(
                    node=node,
                    input_text=input_text,
                    run_id=run_id,
                )

                pipeline_run.steps.append(step)
                self.db.save_step(step)
                completed_nodes[node.node_id] = step

                if step_callback:
                    step_callback(step)

                # Tambah next nodes ke queue
                next_nodes = pipeline.get_next_nodes(node.node_id, step.status)
                queue.extend(next_nodes)

                # Akumulasi token
                pipeline_run.total_tokens += step.tokens_in + step.tokens_out

            # Tentukan output akhir = output node terakhir yang sukses
            final_steps = [s for s in pipeline_run.steps if s.status == NodeStatus.COMPLETED]
            pipeline_run.final_output = final_steps[-1].output_text if final_steps else ""
            pipeline_run.status       = RunStatus.COMPLETED

        except Exception as exc:
            pipeline_run.status = RunStatus.FAILED
            pipeline_run.error  = str(exc)

        pipeline_run.finished_at = datetime.utcnow().isoformat()
        self.db.save_run(pipeline_run)
        self.db.update_stats(pipeline.pipeline_id, pipeline_run.duration_sec)

        return pipeline_run

    def _execute_node(
        self,
        node: NodeConfig,
        input_text: str,
        run_id: str,
    ) -> StepResult:
        step = StepResult(
            step_id=f"step_{uuid.uuid4().hex[:10]}",
            run_id=run_id,
            node_id=node.node_id,
            agent_id=node.agent_id,
            status=NodeStatus.RUNNING,
            input_text=input_text,
            output_text="",
            started_at=datetime.utcnow().isoformat(),
        )

        attempt = 0
        while attempt <= node.retry_max:
            t0 = time.time()
            try:
                output, model, tok_in, tok_out = self.llm.run(
                    agent_id=node.agent_id,
                    task=input_text,
                    system_override=node.system_prompt_override,
                    model_override=node.model_override,
                    temperature=node.temperature,
                    max_tokens=node.max_tokens,
                )
                step.latency_ms  = (time.time() - t0) * 1000
                step.model_used  = model
                step.tokens_in   = tok_in
                step.tokens_out  = tok_out
                step.output_text = output
                step.retry_count = attempt

                # Ethics check
                if node.ethics_check:
                    passed, reason = self.ethics.check(output, input_text)
                    step.ethics_passed = passed
                    if not passed:
                        step.status     = NodeStatus.BLOCKED
                        step.error      = f"Ethics guard: {reason}"
                        step.finished_at = datetime.utcnow().isoformat()
                        return step

                step.status      = NodeStatus.COMPLETED
                step.finished_at = datetime.utcnow().isoformat()
                return step

            except Exception as exc:
                attempt += 1
                step.retry_count = attempt
                if attempt > node.retry_max:
                    step.status     = NodeStatus.FAILED
                    step.error      = str(exc)
                    step.latency_ms = (time.time() - t0) * 1000
                    step.finished_at = datetime.utcnow().isoformat()
                    return step
                time.sleep(2 ** attempt)  # exponential backoff

        step.status = NodeStatus.FAILED
        step.finished_at = datetime.utcnow().isoformat()
        return step


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_db: Optional[PipelineDB] = None
_runner: Optional[PipelineRunner] = None


def get_pipeline_db() -> PipelineDB:
    global _db
    if _db is None:
        _db = PipelineDB()
    return _db


def get_pipeline_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(get_pipeline_db())
    return _runner
