"""
CATERYA Agentic Enterprise — Pipeline Studio (Streamlit UI)
===========================================================
Halaman Streamlit lengkap untuk:
  - Browse & clone template pipeline
  - Build pipeline baru secara visual (drag-drop emulation)
  - Run pipeline dengan live step-by-step progress
  - Review history & output runs
  - Export pipeline sebagai JSON

Tambahkan ke app.py:
    from src.pipeline.pipeline_page import render_pipeline_page
    # di routing:
    elif selected == "🔀 Pipeline Studio":
        render_pipeline_page()

© 2026 Caterya Tech. All Rights Reserved.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Optional

import streamlit as st

# ── Safe imports ──────────────────────────────────────────────────────────────
try:
    from .engine import (
        Pipeline, NodeConfig, Edge, EdgeType, PassMode,
        PipelineRun, StepResult, NodeStatus, RunStatus,
        get_pipeline_db, get_pipeline_runner,
    )
    from .templates import get_all_templates, seed_templates, ALL_TEMPLATES
    _ENGINE_OK = True
except ImportError:
    _ENGINE_OK = False

# ── Constants ─────────────────────────────────────────────────────────────────
AGENT_OPTIONS = {
    "lead_gen":      "🎯 Lead Generation",
    "content_writer":"✍️ Content Writer",
    "sales_closer":  "💼 Sales Closer",
    "support":       "💬 Customer Support",
    "finance":       "💰 Finance Analyst",
    "code_improver": "🔧 Code Improver / Generator",
    "research":      "🔬 Research Analyst",
    "ethics_guard":  "🛡️ Ethics Guard",
    "copywriter":    "🖊️ Copywriter",
    "seo_analyst":   "🔍 SEO Analyst",
    "email_writer":  "📧 Email Writer",
    "social_media":  "📱 Social Media",
    "data_analyst":  "📊 Data Analyst",
    "translator":    "🌐 Translator",
    "summarizer":    "📋 Summarizer",
    "self_optimizer":"⚙️ Self Optimizer",
    "product_manager":"📦 Product Manager",   # NEW
}

CATEGORY_OPTIONS = {
    "sales":       "💼 Sales",
    "content":     "📝 Content",
    "research":    "🔬 Research",
    "marketing":   "📣 Marketing",
    "support":     "💬 Support",
    "finance":     "💰 Finance",
    "development": "🔧 Development",
    "hr":          "👥 HR",
    "custom":      "⚙️ Custom",
}

PASS_MODE_LABELS = {
    "full":    "Full — teruskan seluruh output",
    "summary": "Summary — ringkas dulu",
    "append":  "Append — gabungkan semua output sebelumnya",
    "field":   "Field — ambil field JSON tertentu",
    "none":    "None — mulai fresh (hanya input awal)",
}

STATUS_ICON = {
    "pending":   "⏳",
    "running":   "🔄",
    "completed": "✅",
    "failed":    "❌",
    "blocked":   "⛔",
    "skipped":   "⏭️",
}

CATEGORY_ICON = {
    "sales":       "💼",
    "content":     "📝",
    "research":    "🔬",
    "marketing":   "📣",
    "support":     "💬",
    "finance":     "💰",
    "development": "🔧",
    "hr":          "👥",
    "custom":      "⚙️",
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def render_pipeline_page():
    """Main entry point — panggil dari app.py."""
    _inject_css()

    if not _ENGINE_OK:
        st.error("⚠️ Pipeline engine tidak bisa diload. Pastikan `src/pipeline/engine.py` ada.")
        st.code("from src.pipeline.engine import get_pipeline_db")
        return

    db = get_pipeline_db()
    seed_templates(db)

    # Init session state
    if "pipeline_view" not in st.session_state:
        st.session_state.pipeline_view = "browse"
    if "selected_pipeline_id" not in st.session_state:
        st.session_state.selected_pipeline_id = None
    if "edit_pipeline" not in st.session_state:
        st.session_state.edit_pipeline = None
    if "active_run" not in st.session_state:
        st.session_state.active_run = None

    view = st.session_state.pipeline_view

    if view == "browse":
        _render_browse(db)
    elif view == "build":
        _render_builder(db)
    elif view == "run":
        _render_run_page(db)
    elif view == "history":
        _render_history(db)


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: BROWSE TEMPLATES & MY PIPELINES
# ══════════════════════════════════════════════════════════════════════════════

def _render_browse(db):
    tenant_id = _get_tenant_id()

    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.title("🔀 Pipeline Studio")
        st.caption("Buat, kelola, dan jalankan multi-agent pipeline yang sepenuhnya bisa dikustomisasi.")
    with col_btn:
        st.write("")
        if st.button("➕ Buat Baru", type="primary", use_container_width=True):
            st.session_state.pipeline_view = "build"
            st.session_state.edit_pipeline = None
            st.rerun()

    # Stats bar
    stats = db.get_tenant_run_stats(tenant_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Runs", stats["total_runs"])
    c2.metric("Success Rate", f"{stats['success_rate']}%")
    c3.metric("Total Tokens", f"{stats['total_tokens']:,}")
    c4.metric("Total Cost", f"${stats['total_cost_usd']:.3f}")

    st.divider()

    # Filter bar
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        search = st.text_input("🔍 Cari pipeline...", placeholder="nama, deskripsi, tag")
    with col2:
        cat_filter = st.selectbox(
            "Kategori", ["Semua"] + list(CATEGORY_OPTIONS.keys()),
            format_func=lambda x: "Semua Kategori" if x == "Semua" else CATEGORY_OPTIONS.get(x, x)
        )
    with col3:
        show_templates = st.checkbox("Tampilkan Templates", value=True)

    # Load pipelines
    all_pipes = db.list_pipelines(
        tenant_id,
        category=cat_filter if cat_filter != "Semua" else None,
        include_templates=show_templates,
    )

    # Filter by search
    if search:
        sl = search.lower()
        all_pipes = [p for p in all_pipes if (
            sl in p.name.lower() or
            sl in p.description.lower() or
            any(sl in t for t in p.tags)
        )]

    # Separate templates vs mine
    templates = [p for p in all_pipes if p.is_template]
    mine      = [p for p in all_pipes if not p.is_template and p.tenant_id == tenant_id]

    # My Pipelines
    if mine:
        st.subheader("📂 Pipeline Saya")
        _render_pipeline_grid(mine, db, tenant_id, is_template=False)

    # Templates
    if show_templates and templates:
        st.subheader("📚 Template Library")
        st.caption("Clone template untuk memulai — lalu kustomisasi sesuai kebutuhan.")
        _render_pipeline_grid(templates, db, tenant_id, is_template=True)

    if not all_pipes:
        st.info("Belum ada pipeline. Klik **➕ Buat Baru** atau aktifkan **Tampilkan Templates**.")


def _render_pipeline_grid(pipelines: list, db, tenant_id: str, is_template: bool):
    cols = st.columns(2)
    for i, pipe in enumerate(pipelines):
        with cols[i % 2]:
            _render_pipeline_card(pipe, db, tenant_id, is_template)


def _render_pipeline_card(pipe: "Pipeline", db, tenant_id: str, is_template: bool):
    cat_icon = CATEGORY_ICON.get(pipe.category, "⚙️")
    badge = "📚 Template" if pipe.is_template else "👤 Mine"

    with st.container(border=True):
        st.markdown(f"### {pipe.name}")
        col_meta, col_badge = st.columns([3, 1])
        with col_meta:
            st.caption(f"{cat_icon} {pipe.category.title()} · {len(pipe.nodes)} nodes · {pipe.run_count} runs")
        with col_badge:
            st.caption(badge)

        st.write(pipe.description[:120] + ("..." if len(pipe.description) > 120 else ""))

        # Tags
        if pipe.tags:
            st.markdown(" ".join(f"`{t}`" for t in pipe.tags[:4]))

        # Stats
        if pipe.run_count > 0:
            st.caption(f"Avg duration: {pipe.avg_duration_sec:.1f}s")

        # Node preview
        with st.expander("👁️ Lihat nodes"):
            for j, node in enumerate(pipe.nodes):
                connector = "→" if j < len(pipe.nodes) - 1 else "⊙"
                agent_label = AGENT_OPTIONS.get(node.agent_id, node.agent_id)
                st.write(f"**{j+1}.** {agent_label} — _{node.label}_")

        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶ Run", key=f"run_{pipe.pipeline_id}", use_container_width=True, type="primary"):
                st.session_state.selected_pipeline_id = pipe.pipeline_id
                st.session_state.pipeline_view = "run"
                st.rerun()
        with col2:
            btn_label = "📋 Clone" if is_template else "✏️ Edit"
            if st.button(btn_label, key=f"edit_{pipe.pipeline_id}", use_container_width=True):
                if is_template:
                    cloned = _clone_pipeline(pipe, tenant_id)
                    db.save_pipeline(cloned)
                    st.success(f"✅ Cloned ke: **{cloned.name}**")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.session_state.edit_pipeline = pipe
                    st.session_state.pipeline_view = "build"
                    st.rerun()
        with col3:
            if st.button("📜 History", key=f"hist_{pipe.pipeline_id}", use_container_width=True):
                st.session_state.selected_pipeline_id = pipe.pipeline_id
                st.session_state.pipeline_view = "history"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: PIPELINE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _render_builder(db):
    tenant_id = _get_tenant_id()
    editing   = st.session_state.get("edit_pipeline")
    is_edit   = editing is not None

    col_back, col_title = st.columns([1, 5])
    with col_back:
        st.write("")
        if st.button("← Kembali"):
            st.session_state.pipeline_view = "browse"
            st.session_state.edit_pipeline = None
            st.rerun()
    with col_title:
        st.title("✏️ Edit Pipeline" if is_edit else "➕ Buat Pipeline Baru")

    # ── Init builder session state ───────────────────────────────────────────
    if "builder_nodes" not in st.session_state or not is_edit:
        if is_edit:
            st.session_state.builder_nodes = [_node_to_dict(n) for n in editing.nodes]
            st.session_state.builder_edges = [_edge_to_dict(e) for e in editing.edges]
            st.session_state.builder_meta  = {
                "name": editing.name, "description": editing.description,
                "category": editing.category, "tags": ", ".join(editing.tags),
                "input_label": editing.input_label, "input_hint": editing.input_hint,
            }
        else:
            if "builder_nodes" not in st.session_state:
                st.session_state.builder_nodes = []
                st.session_state.builder_edges = []
                st.session_state.builder_meta  = {
                    "name": "", "description": "", "category": "custom",
                    "tags": "", "input_label": "Input", "input_hint": "Masukkan instruksi...",
                }

    tab_meta, tab_nodes, tab_edges, tab_preview = st.tabs([
        "📋 Info Pipeline", "🤖 Nodes / Agents", "🔗 Edges / Alur", "👁️ Preview & Simpan"
    ])

    with tab_meta:
        _render_builder_meta()

    with tab_nodes:
        _render_builder_nodes()

    with tab_edges:
        _render_builder_edges()

    with tab_preview:
        _render_builder_preview(db, tenant_id, editing)


def _render_builder_meta():
    meta = st.session_state.builder_meta

    col1, col2 = st.columns(2)
    with col1:
        meta["name"] = st.text_input("Nama Pipeline *", value=meta.get("name", ""),
            placeholder="e.g. Sales Pipeline Tokopedia")
        meta["category"] = st.selectbox(
            "Kategori", list(CATEGORY_OPTIONS.keys()),
            index=list(CATEGORY_OPTIONS.keys()).index(meta.get("category", "custom")),
            format_func=lambda x: CATEGORY_OPTIONS[x]
        )
        meta["tags"] = st.text_input("Tags (pisah koma)", value=meta.get("tags", ""),
            placeholder="sales, indonesia, b2b")
    with col2:
        meta["description"] = st.text_area("Deskripsi", value=meta.get("description", ""),
            height=100, placeholder="Apa yang dilakukan pipeline ini?")
        meta["input_label"] = st.text_input("Label Input", value=meta.get("input_label", "Input"),
            help="Teks label yang muncul di atas field input saat Run")
        meta["input_hint"] = st.text_input("Hint Input", value=meta.get("input_hint", ""),
            help="Placeholder text di field input")

    st.session_state.builder_meta = meta


def _render_builder_nodes():
    st.subheader("🤖 Kelola Nodes")
    st.caption(
        "Setiap node adalah satu agent dengan konfigurasi. "
        "Urutan node di sini tidak menentukan alur — alur ditentukan di tab **Edges**."
    )

    nodes = st.session_state.builder_nodes

    # Add node button
    if st.button("➕ Tambah Node", type="primary"):
        new_id = f"node_{uuid.uuid4().hex[:6]}"
        nodes.append({
            "node_id":       new_id,
            "agent_id":      "content_writer",
            "label":         f"Node {len(nodes)+1}",
            "task_template": "{prev}",
            "system_prompt_override": "",
            "model_override": "",
            "temperature":   0.7,
            "max_tokens":    2048,
            "timeout_sec":   120,
            "retry_max":     2,
            "pass_mode":     "full",
            "pass_field":    "",
            "ethics_check":  True,
        })
        st.session_state.builder_nodes = nodes
        st.rerun()

    if not nodes:
        st.info("Belum ada node. Klik **➕ Tambah Node** untuk mulai.")
        return

    for i, node in enumerate(nodes):
        nid = node["node_id"]
        agent_label = AGENT_OPTIONS.get(node["agent_id"], node["agent_id"])

        with st.expander(f"**Node {i+1}: {node['label']}** — {agent_label}", expanded=False):
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                node["node_id"] = st.text_input("Node ID (unik)", value=nid,
                    key=f"nid_{i}", help="ID unik, dipakai di edges")
                node["agent_id"] = st.selectbox("Agent", list(AGENT_OPTIONS.keys()),
                    index=list(AGENT_OPTIONS.keys()).index(node.get("agent_id", "content_writer")),
                    format_func=lambda x: AGENT_OPTIONS[x], key=f"agent_{i}")
                node["label"] = st.text_input("Label", value=node.get("label", f"Node {i+1}"),
                    key=f"label_{i}")

            with col2:
                node["task_template"] = st.text_area(
                    "Task Template",
                    value=node.get("task_template", "{prev}"),
                    height=120, key=f"task_{i}",
                    help=(
                        "Gunakan placeholder:\n"
                        "{input} = input awal user\n"
                        "{prev} = output node sebelumnya (sesuai pass_mode)\n"
                        "{last} = output node langsung sebelumnya"
                    )
                )
                node["system_prompt_override"] = st.text_area(
                    "System Prompt Override (opsional)",
                    value=node.get("system_prompt_override", ""),
                    height=60, key=f"sys_{i}",
                    help="Kosongkan untuk pakai default system prompt agent"
                )

            with col3:
                node["pass_mode"] = st.selectbox(
                    "Pass Mode",
                    list(PASS_MODE_LABELS.keys()),
                    index=list(PASS_MODE_LABELS.keys()).index(node.get("pass_mode", "full")),
                    format_func=lambda x: PASS_MODE_LABELS[x],
                    key=f"pm_{i}"
                )
                if node["pass_mode"] == "field":
                    node["pass_field"] = st.text_input("Field Name (JSON)",
                        value=node.get("pass_field", ""), key=f"pf_{i}")
                node["temperature"] = st.slider("Temperature", 0.0, 1.0,
                    value=float(node.get("temperature", 0.7)), step=0.1, key=f"temp_{i}")
                node["max_tokens"] = st.number_input("Max Tokens", 256, 8192,
                    value=int(node.get("max_tokens", 2048)), step=256, key=f"tok_{i}")
                node["retry_max"] = st.number_input("Retry Max", 0, 5,
                    value=int(node.get("retry_max", 2)), key=f"ret_{i}")
                node["ethics_check"] = st.checkbox("Ethics Check",
                    value=bool(node.get("ethics_check", True)), key=f"eth_{i}")

            col_del, _ = st.columns([1, 4])
            with col_del:
                if st.button("🗑️ Hapus Node", key=f"del_{i}",
                             help="Hapus node ini"):
                    nodes.pop(i)
                    st.session_state.builder_nodes = nodes
                    st.rerun()

    st.session_state.builder_nodes = nodes


def _render_builder_edges():
    st.subheader("🔗 Kelola Edges (Alur)")
    st.caption(
        "Edge menentukan **urutan** dan **kondisi** eksekusi antar nodes. "
        "Node tanpa incoming edge = titik awal. Multiple outgoing edge = eksekusi paralel."
    )

    nodes   = st.session_state.builder_nodes
    edges   = st.session_state.builder_edges
    node_ids = [n["node_id"] for n in nodes]

    if not node_ids:
        st.warning("Tambahkan minimal 2 nodes dulu sebelum bisa membuat edges.")
        return

    # Quick Template Edges
    if len(node_ids) >= 2:
        with st.expander("⚡ Quick Connect: Sambungkan semua nodes secara linear"):
            if st.button("🔗 Linear Connect (1→2→3→...)", use_container_width=True):
                new_edges = []
                for k in range(len(node_ids) - 1):
                    new_edges.append({
                        "from_node": node_ids[k],
                        "to_node":   node_ids[k+1],
                        "edge_type": "on_success",
                        "label":     "",
                    })
                st.session_state.builder_edges = new_edges
                st.success(f"✅ {len(new_edges)} edges dibuat!")
                st.rerun()

    # Add edge form
    with st.form("add_edge_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        with col1:
            from_node = st.selectbox("Dari Node", node_ids,
                format_func=lambda x: f"{x} ({next((n['label'] for n in nodes if n['node_id']==x), x)})")
        with col2:
            edge_type = st.selectbox("Kondisi", ["on_success", "on_failure", "always"],
                format_func=lambda x: {"on_success":"✅ Jika sukses","on_failure":"❌ Jika gagal","always":"→ Selalu"}[x])
        with col3:
            to_node = st.selectbox("Ke Node", node_ids,
                format_func=lambda x: f"{x} ({next((n['label'] for n in nodes if n['node_id']==x), x)})")
        with col4:
            edge_label = st.text_input("Label (opsional)")

        if st.form_submit_button("➕ Tambah Edge", type="primary", use_container_width=True):
            if from_node == to_node:
                st.error("from_node dan to_node tidak boleh sama.")
            else:
                edges.append({
                    "from_node": from_node, "to_node": to_node,
                    "edge_type": edge_type, "label": edge_label,
                })
                st.session_state.builder_edges = edges
                st.rerun()

    # List edges
    if not edges:
        st.info("Belum ada edges. Tambahkan edge di atas, atau pakai **Quick Connect**.")
    else:
        st.markdown(f"**{len(edges)} Edges:**")
        for i, edge in enumerate(edges):
            from_label = next((n["label"] for n in nodes if n["node_id"] == edge["from_node"]), edge["from_node"])
            to_label   = next((n["label"] for n in nodes if n["node_id"] == edge["to_node"]),   edge["to_node"])
            type_icon  = {"on_success":"✅","on_failure":"❌","always":"→"}.get(edge["edge_type"],"→")

            col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
            col1.write(f"**{from_label}**")
            col2.write(f"{type_icon}")
            col3.write(f"**{to_label}**")
            col4.write(f"_{edge.get('label','')}_")
            with col5:
                if st.button("🗑️", key=f"del_edge_{i}"):
                    edges.pop(i)
                    st.session_state.builder_edges = edges
                    st.rerun()

    st.session_state.builder_edges = edges


def _render_builder_preview(db, tenant_id: str, editing):
    st.subheader("👁️ Preview Pipeline")

    meta  = st.session_state.builder_meta
    nodes = st.session_state.builder_nodes
    edges = st.session_state.builder_edges

    # Render visual flow
    if nodes:
        st.markdown("**Alur Pipeline:**")
        # Build adjacency for topological display
        node_map = {n["node_id"]: n for n in nodes}
        incoming  = {n["node_id"]: [] for n in nodes}
        for e in edges:
            if e["to_node"] in incoming:
                incoming[e["to_node"]].append(e["from_node"])

        starts = [n for n in nodes if not incoming[n["node_id"]]]

        cols = st.columns(max(len(nodes), 1))
        for i, node in enumerate(nodes):
            with cols[i % len(cols)]:
                agent_lbl = AGENT_OPTIONS.get(node["agent_id"], node["agent_id"])
                st.markdown(f"""
<div style="background:#1e1e2e;border:1px solid #6366f1;border-radius:8px;
            padding:0.7rem;text-align:center;font-size:0.85rem;">
  <b>{node['label']}</b><br/>
  <span style="color:#6366f1;">{agent_lbl}</span><br/>
  <small style="color:#888;">pass: {node.get('pass_mode','full')}</small>
</div>
""", unsafe_allow_html=True)
                # Show outgoing arrows
                out_edges = [e for e in edges if e["from_node"] == node["node_id"]]
                for oe in out_edges:
                    to_label = next((n["label"] for n in nodes if n["node_id"] == oe["to_node"]), oe["to_node"])
                    type_icon = {"on_success":"✅","on_failure":"❌","always":"→"}.get(oe["edge_type"],"→")
                    st.caption(f"{type_icon} → {to_label}")

    st.divider()

    # Validation
    errors = []
    if not meta.get("name"):
        errors.append("Nama pipeline kosong")
    if not nodes:
        errors.append("Minimal 1 node diperlukan")
    if len(nodes) > 1 and not edges:
        errors.append("Pipeline dengan 2+ nodes harus punya minimal 1 edge")

    # Duplicate node IDs
    nids = [n["node_id"] for n in nodes]
    if len(nids) != len(set(nids)):
        errors.append("Ada Node ID yang duplikat")

    if errors:
        st.error("**Errors yang perlu diperbaiki:**\n" + "\n".join(f"- {e}" for e in errors))
        return

    st.success("✅ Validasi OK! Pipeline siap disimpan.")

    # JSON Export preview
    with st.expander("📄 Lihat JSON"):
        preview_dict = {
            "name": meta["name"],
            "category": meta["category"],
            "nodes": nodes,
            "edges": edges,
        }
        st.json(preview_dict)

    col_save, col_export, col_pdf_spec = st.columns([1, 1, 1])

    with col_save:
        save_label = "💾 Update Pipeline" if editing else "💾 Simpan Pipeline"
        if st.button(save_label, type="primary", use_container_width=True):
            pipe = _build_pipeline_from_state(tenant_id, editing)
            db.save_pipeline(pipe)
            st.success(f"✅ Pipeline **{pipe.name}** disimpan!")
            time.sleep(1)
            st.session_state.pipeline_view = "browse"
            st.session_state.edit_pipeline = None
            st.session_state.builder_nodes = []
            st.session_state.builder_edges = []
            st.rerun()

    with col_export:
        pipe_dict = _build_pipeline_from_state(tenant_id, editing).to_dict()
        st.download_button(
            "⬇️ Export JSON",
            data=json.dumps(pipe_dict, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=f"{meta.get('name','pipeline').replace(' ','_')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_pdf_spec:
        try:
            from .pdf_exporter import generate_pipeline_spec_pdf
            spec_pipe = _build_pipeline_from_state(tenant_id, editing)
            pdf_bytes = generate_pipeline_spec_pdf(spec_pipe)
            st.download_button(
                "⬇️ Export Spec PDF",
                data=pdf_bytes,
                file_name=f"{meta.get('name','pipeline').replace(' ','_')}_spec.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"PDF spec error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: RUN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def _render_run_page(db):
    tenant_id   = _get_tenant_id()
    pipeline_id = st.session_state.get("selected_pipeline_id")

    if not pipeline_id:
        st.error("Tidak ada pipeline yang dipilih.")
        return

    pipe = db.get_pipeline(pipeline_id)
    if not pipe:
        st.error(f"Pipeline `{pipeline_id}` tidak ditemukan.")
        return

    col_back, col_title = st.columns([1, 5])
    with col_back:
        st.write("")
        if st.button("← Kembali"):
            st.session_state.pipeline_view = "browse"
            st.rerun()
    with col_title:
        st.title(f"▶ Run: {pipe.name}")
        st.caption(f"{CATEGORY_ICON.get(pipe.category,'')} {pipe.category.title()} · {len(pipe.nodes)} nodes")

    # Node overview
    with st.expander("📋 Lihat Pipeline Nodes", expanded=False):
        for i, node in enumerate(pipe.nodes):
            agent_lbl = AGENT_OPTIONS.get(node.agent_id, node.agent_id)
            st.write(f"**{i+1}. {node.label}** — {agent_lbl} _(pass_mode: {node.pass_mode.value})_")
            if node.task_template:
                st.code(node.task_template[:200], language=None)

    st.divider()

    # Input
    st.subheader(f"📥 {pipe.input_label}")

    initial_input = st.text_area(
        pipe.input_label,
        height=150,
        placeholder=pipe.input_hint,
        label_visibility="collapsed",
    )

    col_run, col_opts = st.columns([1, 2])
    with col_run:
        run_btn = st.button("▶ Jalankan Pipeline", type="primary",
                            use_container_width=True, disabled=not initial_input.strip())
    with col_opts:
        trigger = st.selectbox("Triggered by", ["manual", "api", "webhook", "schedule"],
                               label_visibility="collapsed")

    if not run_btn or not initial_input.strip():
        return

    # ── Execute pipeline with live progress ────────────────────────────────
    st.divider()
    st.subheader("🔄 Eksekusi Pipeline")

    # Progress containers
    progress_bar = st.progress(0, text="Memulai pipeline...")
    step_containers = {}
    for node in pipe.nodes:
        agent_lbl = AGENT_OPTIONS.get(node.agent_id, node.agent_id)
        step_containers[node.node_id] = st.container(border=True)
        with step_containers[node.node_id]:
            st.markdown(f"**⏳ {node.label}** — {agent_lbl}")

    total_nodes     = len(pipe.nodes)
    completed_count = [0]

    def step_callback(step: "StepResult"):
        completed_count[0] += 1
        # FIX: progress() butuh float 0.0-1.0, bukan string
        prog = float(completed_count[0]) / float(max(total_nodes, 1))
        prog = min(max(prog, 0.0), 1.0)  # clamp
        progress_bar.progress(prog, text=f"Selesai {completed_count[0]}/{total_nodes} nodes")

        container = step_containers.get(step.node_id)
        if container:
            with container:
                icon  = STATUS_ICON.get(step.status.value, "❓")
                node_obj = pipe.get_node(step.node_id)
                node_lbl = node_obj.label if node_obj else step.node_id
                agent_lbl = AGENT_OPTIONS.get(step.agent_id, step.agent_id)
                st.markdown(f"**{icon} {node_lbl}** — {agent_lbl}")
                col_s, col_t, col_l = st.columns(3)
                col_s.caption(f"Status: **{step.status.value}**")
                col_t.caption(f"Tokens: {step.tokens_in + step.tokens_out:,}")
                col_l.caption(f"Latency: {step.latency_ms:.0f}ms")
                if step.error:
                    st.error(step.error)
                if step.output_text:
                    with st.expander("📄 Output"):
                        st.write(step.output_text)

    runner = get_pipeline_runner()

    with st.spinner("Pipeline berjalan..."):
        run = runner.run(
            pipeline=pipe,
            initial_input=initial_input,
            tenant_id=tenant_id,
            triggered_by=trigger,
            step_callback=step_callback,
        )

    # FIX: gunakan float literal bukan 1.0 yang bisa diinterpretasi berbeda
    progress_bar.progress(1.0, text="Pipeline selesai!")

    # Final result
    st.divider()
    if run.status == RunStatus.COMPLETED:
        st.success(f"✅ Pipeline selesai dalam **{run.duration_sec:.1f}s**!")
    else:
        st.error(f"❌ Pipeline gagal: {run.error}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Duration", f"{run.duration_sec:.1f}s")
    col2.metric("Total Tokens", f"{run.total_tokens:,}")
    col3.metric("Steps", str(len(run.steps)))
    col4.metric("Cost", f"${run.total_cost_usd:.4f}")

    if run.final_output:
        st.subheader("📋 Output Akhir")
        with st.container(border=True):
            st.write(run.final_output)

        # Export buttons
        col_txt, col_pdf, col_json = st.columns(3)

        with col_txt:
            st.download_button(
                "⬇️ Download TXT",
                data=run.final_output.encode("utf-8"),
                file_name=f"pipeline_output_{run.run_id}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with col_pdf:
            try:
                from .pdf_exporter import generate_run_pdf
                pdf_bytes = generate_run_pdf(run, pipe)
                st.download_button(
                    "⬇️ Export PDF",
                    data=pdf_bytes,
                    file_name=f"pipeline_report_{run.run_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except ImportError:
                st.warning("reportlab belum terinstall. Jalankan: `pip install reportlab`")
            except Exception as e:
                st.error(f"PDF error: {e}")

        with col_json:
            # Full run data as JSON
            import dataclasses
            run_dict = {
                "run_id":       run.run_id,
                "pipeline":     pipe.name,
                "status":       run.status.value,
                "duration_sec": run.duration_sec,
                "total_tokens": run.total_tokens,
                "final_output": run.final_output,
                "steps": [
                    {
                        "node_id":      s.node_id,
                        "agent_id":     s.agent_id,
                        "status":       s.status.value,
                        "output":       s.output_text,
                        "tokens":       s.tokens_in + s.tokens_out,
                        "latency_ms":   s.latency_ms,
                        "ethics_passed":s.ethics_passed,
                    }
                    for s in run.steps
                ],
            }
            st.download_button(
                "⬇️ Export JSON",
                data=json.dumps(run_dict, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name=f"pipeline_run_{run.run_id}.json",
                mime="application/json",
                use_container_width=True,
            )

    # Save to session for reference
    st.session_state.active_run = run


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: RUN HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def _render_history(db):
    pipeline_id = st.session_state.get("selected_pipeline_id")
    pipe = db.get_pipeline(pipeline_id) if pipeline_id else None

    col_back, col_title = st.columns([1, 5])
    with col_back:
        st.write("")
        if st.button("← Kembali"):
            st.session_state.pipeline_view = "browse"
            st.rerun()
    with col_title:
        st.title(f"📜 History: {pipe.name if pipe else 'All'}")

    runs = db.list_runs(pipeline_id, limit=30) if pipeline_id else []

    if not runs:
        st.info("Belum ada run history untuk pipeline ini.")
        return

    st.caption(f"{len(runs)} run terakhir")

    for run_data in runs:
        status    = run_data.get("status", "unknown")
        icon      = {"completed":"✅","failed":"❌","running":"🔄","cancelled":"⛔"}.get(status,"❓")
        started   = run_data.get("started_at","")[:16].replace("T"," ")
        finished  = run_data.get("finished_at","")[:16].replace("T"," ")
        run_id    = run_data["run_id"]

        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 1, 1])
            col1.write(f"{icon} `{status}`")
            col2.write(f"🕐 {started}")
            col3.write(f"Tokens: {run_data.get('total_tokens',0):,}")
            col4.write(f"By: {run_data.get('triggered_by','manual')}")
            with col5:
                if st.button("Detail", key=f"detail_{run_id}"):
                    full_run = db.get_run(run_id)
                    if full_run:
                        st.session_state[f"expand_{run_id}"] = True

            # Expanded detail
            if st.session_state.get(f"expand_{run_id}"):
                full_run = db.get_run(run_id)
                if full_run:
                    st.markdown(f"**Input:** {full_run.initial_input[:200]}")
                    st.markdown(f"**Steps:** {len(full_run.steps)}")
                    for step in full_run.steps:
                        step_icon = STATUS_ICON.get(step.status.value, "❓")
                        agent_lbl = AGENT_OPTIONS.get(step.agent_id, step.agent_id)
                        with st.expander(f"{step_icon} {step.node_id} — {agent_lbl}"):
                            st.write(f"**Output:** {step.output_text[:500]}")
                            if step.error:
                                st.error(step.error)
                    if full_run.final_output:
                        col_dl_txt, col_dl_pdf = st.columns(2)
                        with col_dl_txt:
                            st.download_button(
                                "⬇️ Download TXT",
                                data=full_run.final_output.encode("utf-8"),
                                file_name=f"run_{run_id}_output.txt",
                                use_container_width=True,
                            )
                        with col_dl_pdf:
                            try:
                                from .pdf_exporter import generate_run_pdf
                                hist_pipe = db.get_pipeline(full_run.pipeline_id)
                                if hist_pipe:
                                    pdf_bytes = generate_run_pdf(full_run, hist_pipe)
                                    st.download_button(
                                        "⬇️ Export PDF",
                                        data=pdf_bytes,
                                        file_name=f"run_{run_id}_report.pdf",
                                        mime="application/pdf",
                                        use_container_width=True,
                                    )
                            except Exception as e:
                                st.caption(f"PDF: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_tenant_id() -> str:
    return st.session_state.get("tenant_id", "demo_tenant")


def _clone_pipeline(pipe: "Pipeline", tenant_id: str) -> "Pipeline":
    import copy, dataclasses
    cloned = copy.deepcopy(pipe)
    cloned.pipeline_id = f"pipe_{uuid.uuid4().hex[:12]}"
    cloned.name        = f"{pipe.name} (Copy)"
    cloned.tenant_id   = tenant_id
    cloned.is_template = False
    cloned.run_count   = 0
    cloned.avg_duration_sec = 0.0
    cloned.created_at  = datetime.utcnow().isoformat()
    cloned.updated_at  = datetime.utcnow().isoformat()
    return cloned


def _node_to_dict(n: "NodeConfig") -> dict:
    import dataclasses
    d = dataclasses.asdict(n)
    d["pass_mode"] = d["pass_mode"] if isinstance(d["pass_mode"], str) else d["pass_mode"].value
    return d


def _edge_to_dict(e: "Edge") -> dict:
    import dataclasses
    d = dataclasses.asdict(e)
    d["edge_type"] = d["edge_type"] if isinstance(d["edge_type"], str) else d["edge_type"].value
    return d


def _build_pipeline_from_state(tenant_id: str, editing) -> "Pipeline":
    meta  = st.session_state.builder_meta
    nodes_raw = st.session_state.builder_nodes
    edges_raw = st.session_state.builder_edges

    nodes = [NodeConfig(
        node_id=n["node_id"], agent_id=n["agent_id"], label=n["label"],
        task_template=n.get("task_template", "{prev}"),
        system_prompt_override=n.get("system_prompt_override", ""),
        model_override=n.get("model_override", ""),
        temperature=float(n.get("temperature", 0.7)),
        max_tokens=int(n.get("max_tokens", 2048)),
        timeout_sec=int(n.get("timeout_sec", 120)),
        retry_max=int(n.get("retry_max", 2)),
        pass_mode=PassMode(n.get("pass_mode", "full")),
        pass_field=n.get("pass_field", ""),
        ethics_check=bool(n.get("ethics_check", True)),
    ) for n in nodes_raw]

    edges = [Edge(
        from_node=e["from_node"], to_node=e["to_node"],
        edge_type=EdgeType(e.get("edge_type", "on_success")),
        label=e.get("label", ""),
    ) for e in edges_raw]

    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]

    if editing:
        editing.name        = meta["name"]
        editing.description = meta.get("description", "")
        editing.category    = meta.get("category", "custom")
        editing.tags        = tags
        editing.nodes       = nodes
        editing.edges       = edges
        editing.input_label = meta.get("input_label", "Input")
        editing.input_hint  = meta.get("input_hint", "")
        editing.updated_at  = datetime.utcnow().isoformat()
        return editing

    return Pipeline.create(
        name=meta["name"],
        description=meta.get("description", ""),
        category=meta.get("category", "custom"),
        tenant_id=tenant_id,
        nodes=nodes,
        edges=edges,
        tags=tags,
        input_label=meta.get("input_label", "Input"),
        input_hint=meta.get("input_hint", ""),
        is_template=False,
    )


def _inject_css():
    st.markdown("""
<style>
/* Pipeline cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    transition: box-shadow 0.2s;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 0 0 1px #6366f1;
}
/* Node preview boxes */
.node-box {
    background: #1e1e2e;
    border: 1px solid #6366f1;
    border-radius: 8px;
    padding: 0.7rem;
    text-align: center;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)
