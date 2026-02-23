# CATERYA — Multi-Agent Pipeline System
**Dokumentasi Lengkap: Arsitektur, Penggunaan, dan API**
© 2026 Caterya Tech. All Rights Reserved.

---

## 📐 Konsep Dasar

### Apa itu Pipeline?
Pipeline adalah **rangkaian agent AI yang bekerja berurutan atau paralel**, di mana output satu agent menjadi input agent berikutnya. Berbeda dengan menjalankan satu agent, pipeline memungkinkan workflow multi-langkah yang kompleks.

```
Input Awal
    │
    ▼
[Lead Gen Agent] ──────────────────────────────────────────────────────────────
    │ output: daftar 5 prospek
    ▼
[Research Agent] ──────────────────────────────────────────────────────────────
    │ output: pain points + skor tiap prospek
    ▼
[Content Writer] ──┬─────────────────────────────────────────────────────────
    │              │
    │ email outreach   [Sales Closer] → objection guide
    ▼              │
[Email Writer]     │ ← (paralel, kedua node jalan bersamaan)
    │
    ▼
[Summarizer] → Final Sales Brief
```

### Empat Konsep Kunci

| Konsep | Penjelasan |
|--------|-----------|
| **Node** | Satu agent dengan konfigurasinya (task template, model, dll) |
| **Edge** | Koneksi antara nodes; menentukan kondisi kapan node berikutnya jalan |
| **PassMode** | Bagaimana output diteruskan ke node berikutnya |
| **Run** | Satu eksekusi pipeline dengan input tertentu |

---

## 🔀 PassMode — Cara Meneruskan Output

| Mode | Deskripsi | Kapan Dipakai |
|------|-----------|--------------|
| `full` | Teruskan **seluruh** output node sebelumnya | Default; node panjang dengan konteks penuh |
| `summary` | Ringkas dulu (500 char) sebelum diteruskan | Output sangat panjang, konteks terbatas |
| `append` | Gabungkan **semua** output dari semua node sebelumnya | Node summary/aggregator di akhir |
| `field` | Ambil field JSON tertentu | Node sebelumnya output JSON terstruktur |
| `none` | Mulai fresh, hanya pakai input awal | Node independen, tidak butuh konteks sebelumnya |

### Task Template Variables
Dalam `task_template`, gunakan placeholder ini:

```
{input}  → input awal yang dimasukkan user/API
{prev}   → output yang diteruskan (sesuai pass_mode)
{last}   → output raw dari node terakhir yang dieksekusi
```

Contoh:
```python
# Node: Email Writer
task_template = """
Buat email outreach berdasarkan kualifikasi prospek ini:

{prev}

Email harus: personal, 200 kata, CTA jelas.
"""
```

---

## 🔗 Edge Types — Kondisi Eksekusi

| Edge Type | Kondisi | Use Case |
|-----------|---------|----------|
| `on_success` | Node berikutnya jalan hanya jika sebelumnya **sukses** | Default; alur normal |
| `on_failure` | Node berikutnya jalan hanya jika sebelumnya **gagal** | Error handling / fallback |
| `always` | Selalu jalan terlepas dari status sebelumnya | Logging, notification |

### Paralel Execution
Multiple edge dari satu node = nodes berikutnya jalan **paralel** (BFS):

```
[Research] ──on_success──▶ [Email Writer]
    │
    └──on_success──────────▶ [Social Media]  ← kedua ini jalan setelah Research selesai
```

---

## 📚 Template Library

8 template built-in siap pakai:

| Template | Nodes | Kategori | Use Case |
|----------|-------|----------|----------|
| 🎯 Full Sales Pipeline | 6 | Sales | Prospecting hingga closing |
| 📝 Content Marketing Pipeline | 6 | Content | Blog → SEO → Social → Email |
| 🔬 Market Research Pipeline | 6 | Research | Kompetitor → SWOT → Strategy |
| 💬 Support Triage Pipeline | 5 | Support | Classify → Response → Escalate |
| 🚀 Product Launch Pipeline | 5 | Marketing | Positioning → Landing → Email |
| 💰 Financial Analysis Pipeline | 5 | Finance | Data → Analisis → Rekomendasi |
| 🔧 Code Review Pipeline | 5 | Dev | Bug → Security → Refactor → Docs |
| ⚡ Quick Lead Qualify | 3 | Sales | Qualify → Pitch → Outreach |

---

## 🖥️ Penggunaan via Streamlit UI (Pipeline Studio)

### 1. Browse & Clone Template
```
Pipeline Studio → Template Library → Clone → Kustomisasi → Run
```

### 2. Buat Pipeline Baru
1. Klik **➕ Buat Baru**
2. **Tab "Info Pipeline"**: isi nama, kategori, deskripsi
3. **Tab "Nodes / Agents"**: tambah dan konfigurasi nodes
4. **Tab "Edges / Alur"**: sambungkan nodes (atau pakai Quick Connect)
5. **Tab "Preview & Simpan"**: validasi, preview, simpan/export

### 3. Run Pipeline
1. Pilih pipeline → klik **▶ Run**
2. Masukkan input di field yang muncul
3. Lihat progress live step-by-step
4. Download output akhir

---

## 🔌 API Reference

Base URL: `http://localhost:8000`

### Authentication
Semua endpoint butuh header `X-API-Key`:
```bash
-H "X-API-Key: cae_your_api_key"
```

---

### `GET /api/pipelines/`
List semua pipeline tenant + templates.

**Query params:**
- `category` — filter by kategori (sales, content, research, dll)
- `templates` — sertakan templates? (default: true)

**Response:**
```json
{
  "total": 10,
  "pipelines": [
    {
      "pipeline_id": "pipe_abc123",
      "name": "Full Sales Pipeline",
      "category": "sales",
      "nodes": 6,
      "is_template": true,
      "run_count": 0
    }
  ]
}
```

---

### `GET /api/pipelines/templates`
List semua built-in templates.

---

### `POST /api/pipelines/`
Buat pipeline baru.

**Body:**
```json
{
  "name": "My Sales Pipeline",
  "description": "Custom sales workflow",
  "category": "sales",
  "nodes": [
    {
      "node_id": "qualify",
      "agent_id": "lead_gen",
      "label": "Qualify Prospect",
      "task_template": "Kualifikasi prospek ini: {input}",
      "pass_mode": "full",
      "temperature": 0.7,
      "max_tokens": 2048,
      "retry_max": 2,
      "ethics_check": true
    },
    {
      "node_id": "outreach",
      "agent_id": "email_writer",
      "label": "Write Outreach Email",
      "task_template": "Buat email berdasarkan kualifikasi:\n{prev}",
      "pass_mode": "full"
    }
  ],
  "edges": [
    {
      "from_node": "qualify",
      "to_node": "outreach",
      "edge_type": "on_success"
    }
  ],
  "input_label": "Nama Prospek",
  "input_hint": "e.g. PT Maju Jaya, bergerak di retail fashion"
}
```

---

### `POST /api/pipelines/{pipeline_id}/clone`
Clone pipeline (biasanya dari template).

```json
{ "new_name": "My Custom Sales Pipeline" }
```

---

### `POST /api/pipelines/{pipeline_id}/run`
Jalankan pipeline secara **async** (langsung return `run_id`).

```json
{
  "initial_input": "PT Startup Indonesia, industri edtech, 50 karyawan",
  "triggered_by": "api"
}
```

**Response:**
```json
{
  "run_id": "run_xyz789",
  "status": "queued",
  "message": "Poll /api/pipelines/{id}/runs/{run_id} untuk status"
}
```

---

### `POST /api/pipelines/{pipeline_id}/run/sync`
Jalankan pipeline secara **synchronous** (tunggu sampai selesai).

**Response:**
```json
{
  "run_id": "run_xyz789",
  "status": "completed",
  "duration_sec": 45.3,
  "total_tokens": 3420,
  "final_output": "Sales brief final...",
  "steps": [
    {
      "node_id": "qualify",
      "agent_id": "lead_gen",
      "status": "completed",
      "output": "Prospek kualifikasi: skor 8/10...",
      "tokens": 840,
      "latency_ms": 1230.5,
      "ethics_passed": true
    }
  ]
}
```

---

### `GET /api/pipelines/{pipeline_id}/runs/{run_id}`
Get status run (untuk polling async run).

---

### `DELETE /api/pipelines/{pipeline_id}`
Soft delete pipeline.

---

## 🐍 Python SDK Example

```python
import requests

API_KEY  = "cae_your_api_key"
BASE_URL = "http://localhost:8000"
HEADERS  = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


# 1. List templates
templates = requests.get(f"{BASE_URL}/api/pipelines/templates", headers=HEADERS).json()
print(templates["templates"])


# 2. Clone template
clone_resp = requests.post(
    f"{BASE_URL}/api/pipelines/pipe_template_id/clone",
    headers=HEADERS,
    json={"new_name": "My Sales Pipeline"}
).json()
pipeline_id = clone_resp["pipeline_id"]


# 3. Run pipeline (sync)
run_resp = requests.post(
    f"{BASE_URL}/api/pipelines/{pipeline_id}/run/sync",
    headers=HEADERS,
    json={
        "initial_input": "PT Maju Digital, startup SaaS HR, 30 karyawan, Jakarta",
        "triggered_by": "api",
    }
).json()

print("Status:", run_resp["status"])
print("Duration:", run_resp["duration_sec"], "s")
print("Tokens:", run_resp["total_tokens"])
print("\nFinal Output:")
print(run_resp["final_output"])


# 4. Create custom pipeline from scratch
custom_pipe = requests.post(
    f"{BASE_URL}/api/pipelines/",
    headers=HEADERS,
    json={
        "name": "Quick Research + Blog",
        "category": "content",
        "nodes": [
            {
                "node_id": "research",
                "agent_id": "research",
                "label": "Topic Research",
                "task_template": "Riset mendalam tentang: {input}",
                "pass_mode": "full",
            },
            {
                "node_id": "article",
                "agent_id": "content_writer",
                "label": "Write Article",
                "task_template": "Tulis artikel 1000 kata berdasarkan riset ini:\n{prev}",
                "pass_mode": "full",
                "max_tokens": 4096,
            },
        ],
        "edges": [
            {"from_node": "research", "to_node": "article", "edge_type": "on_success"}
        ],
        "input_label": "Topik",
        "input_hint": "e.g. Tren AI untuk UMKM 2026",
    }
).json()
print("Pipeline dibuat:", custom_pipe["pipeline_id"])
```

---

## 📁 Struktur File

```
src/pipeline/
├── __init__.py          ← Exports utama
├── engine.py            ← Core: Pipeline, Node, Edge, Runner, DB
├── templates.py         ← 8 built-in pipeline templates
├── pipeline_page.py     ← Streamlit UI: Pipeline Studio
└── api_router.py        ← FastAPI router: /api/pipelines/...
```

---

## ⚙️ Konfigurasi

Tidak ada env var tambahan untuk pipeline. Pipeline engine otomatis menggunakan:
- `OLLAMA_BASE_URL` — untuk LLM calls
- `OLLAMA_DEFAULT_MODEL` — model default
- `GROQ_API_KEY` — fallback jika Ollama tidak tersedia
- `data/pipelines.db` — SQLite database (auto-created)

---

## 🧪 Test Pipeline

```bash
# 1. Start server
uvicorn src.api.main:app --reload --port 8000

# 2. List templates
curl http://localhost:8000/api/pipelines/templates \
  -H "X-API-Key: cae_test_key_demo"

# 3. Clone dan run template
PIPE_ID=$(curl -s -X POST http://localhost:8000/api/pipelines/pipe_TEMPLATE_ID/clone \
  -H "X-API-Key: cae_test_key_demo" \
  -H "Content-Type: application/json" \
  -d '{"new_name": "Test Pipeline"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['pipeline_id'])")

curl -X POST http://localhost:8000/api/pipelines/$PIPE_ID/run/sync \
  -H "X-API-Key: cae_test_key_demo" \
  -H "Content-Type: application/json" \
  -d '{"initial_input": "PT Demo Tech, startup B2B SaaS"}'

# 4. Streamlit: run Pipeline Studio
streamlit run src/dashboard/app_updated.py
# Buka: http://localhost:8501
# Navigasi ke: 🔀 Pipeline Studio
```

---

## 🔒 Ethics Guard

Setiap node (jika `ethics_check: true`) akan diperiksa sebelum output diteruskan:
- Node dengan output yang melanggar → status `blocked`
- Edge `on_failure` dari node tersebut akan tetap dieksekusi (untuk fallback)
- Run tetap berlanjut ke node lain yang tidak bergantung pada node yang blocked

Custom ethics rules bisa ditambahkan di `engine.py` → class `EthicsGuard`.

---

## 📊 Monitoring & Analytics

Setiap run tersimpan di `data/pipelines.db` dengan:
- Token usage per step
- Latency per step
- Model yang dipakai
- Ethics check result
- Cost estimation (USD)

Akses via API:
```
GET /api/pipelines/stats/overview   ← Ringkasan semua pipeline tenant
GET /api/pipelines/{id}/runs        ← History runs
GET /api/pipelines/{id}/runs/{rid}  ← Detail satu run
```

---

*Pipeline System v1.0.0 — Bagian dari CATERYA Agentic Enterprise*
