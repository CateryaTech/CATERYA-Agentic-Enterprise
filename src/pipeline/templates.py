"""
CATERYA Agentic Enterprise — Pipeline Templates Library
=======================================================
Koleksi template pipeline siap pakai yang bisa di-clone dan dikustomisasi.
Setiap template bisa langsung dipakai atau dijadikan titik awal pipeline baru.

© 2026 Caterya Tech. All Rights Reserved.
"""

from __future__ import annotations
from .engine import Pipeline, NodeConfig, Edge, EdgeType, PassMode

TEMPLATE_TENANT = "_template_"  # tenant khusus untuk semua template


def _node(node_id: str, agent_id: str, label: str, task_template: str,
          pass_mode: PassMode = PassMode.FULL, **kw) -> NodeConfig:
    return NodeConfig(
        node_id=node_id, agent_id=agent_id, label=label,
        task_template=task_template, pass_mode=pass_mode, **kw
    )


def _edge(f: str, t: str, et: EdgeType = EdgeType.ON_SUCCESS) -> Edge:
    return Edge(from_node=f, to_node=t, edge_type=et)


# ══════════════════════════════════════════════════════════════════════════════
# 1. FULL SALES PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_full_sales_pipeline() -> Pipeline:
    """
    Pipeline penjualan end-to-end:
    Lead Gen → Qualify → Research → Personalized Outreach → Follow-up → Closing
    """
    return Pipeline.create(
        name="🎯 Full Sales Pipeline",
        description=(
            "Pipeline penjualan lengkap dari prospecting hingga closing. "
            "Input: deskripsi target pasar atau nama prospek."
        ),
        category="sales",
        tenant_id=TEMPLATE_TENANT,
        input_label="Target / Prospek",
        input_hint="e.g. 'Startup SaaS B2B di Jakarta dengan 10-50 karyawan' atau nama perusahaan spesifik",
        tags=["sales", "lead gen", "closing", "b2b"],
        is_template=True,
        nodes=[
            _node("lead_gen",    "lead_gen",    "🎯 Lead Generation",
                  "Temukan 5 prospek potensial berdasarkan: {input}\n\n"
                  "Format output: daftar bernomor dengan nama, jabatan, perusahaan, alasan qualified.",
                  pass_mode=PassMode.FULL),

            _node("qualifier",   "research",    "🔍 Deep Qualification",
                  "Lakukan riset mendalam untuk setiap prospek berikut:\n{prev}\n\n"
                  "Untuk setiap prospek: pain points, budget estimate, decision maker, "
                  "dan skor kesiapan beli 1-10.",
                  pass_mode=PassMode.FULL),

            _node("personalize", "content_writer", "✍️ Personalized Outreach",
                  "Buat email outreach yang sangat personal untuk prospek terbaik (skor tertinggi) dari:\n{prev}\n\n"
                  "Email harus: subject line menarik, reference pain point spesifik, "
                  "value prop jelas, dan CTA konkret.",
                  pass_mode=PassMode.FULL),

            _node("followup",    "email_writer", "📧 Follow-up Sequence",
                  "Buat sequence 3 follow-up email (hari 3, 7, 14) berdasarkan outreach ini:\n{prev}\n\n"
                  "Setiap email berbeda angle: value, social proof, urgency.",
                  pass_mode=PassMode.FULL),

            _node("objections",  "sales_closer", "💼 Objection Handler",
                  "Berdasarkan profil prospek dan outreach:\n{prev}\n\n"
                  "Buat panduan handling 5 objeksi paling umum untuk prospek ini, "
                  "lengkap dengan counter-argument dan closing line.",
                  pass_mode=PassMode.FULL),

            _node("summary",     "summarizer",  "📋 Sales Brief",
                  "Buat sales brief ringkas (1 halaman) dari seluruh proses ini:\n{prev}\n\n"
                  "Include: prospek terbaik, strategi outreach, key messages, dan next steps.",
                  pass_mode=PassMode.APPEND),
        ],
        edges=[
            _edge("lead_gen",    "qualifier"),
            _edge("qualifier",   "personalize"),
            _edge("personalize", "followup"),
            _edge("followup",    "objections"),
            _edge("objections",  "summary"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONTENT MARKETING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_content_marketing_pipeline() -> Pipeline:
    """
    Research → Brief → Draft → SEO → Social → Email newsletter
    """
    return Pipeline.create(
        name="📝 Content Marketing Pipeline",
        description=(
            "Buat konten marketing komprehensif dari satu topik: "
            "artikel blog, SEO optimization, social posts, dan email newsletter."
        ),
        category="content",
        tenant_id=TEMPLATE_TENANT,
        input_label="Topik Konten",
        input_hint="e.g. 'Manfaat AI untuk UMKM Indonesia' atau 'Tips investasi crypto 2026'",
        tags=["content", "seo", "social media", "email", "marketing"],
        is_template=True,
        nodes=[
            _node("research",    "research",      "🔬 Topic Research",
                  "Riset mendalam tentang topik: {input}\n\n"
                  "Cari: statistik terkini, perspektif berbeda, pertanyaan yang sering dicari orang, "
                  "dan sudut pandang yang belum banyak dibahas.",
                  pass_mode=PassMode.FULL),

            _node("brief",       "content_writer","📋 Content Brief",
                  "Buat content brief terstruktur dari riset ini:\n{prev}\n\n"
                  "Include: judul utama (5 opsi), outline artikel, target keyword, "
                  "target audiens, dan tone of voice.",
                  pass_mode=PassMode.FULL),

            _node("article",     "content_writer","✍️ Full Article",
                  "Tulis artikel blog lengkap 1500-2000 kata berdasarkan brief ini:\n{prev}\n\n"
                  "Gunakan H2/H3, bullets, dan contoh konkret. "
                  "Bahasa Indonesia yang engaging dan mudah dipahami.",
                  pass_mode=PassMode.FULL,
                  max_tokens=4096),

            _node("seo",         "seo_analyst",   "🔍 SEO Optimization",
                  "Optimalkan artikel ini untuk SEO:\n{prev}\n\n"
                  "Output: meta title, meta description, keyword density analysis, "
                  "internal link suggestions, dan rekomendasi perbaikan.",
                  pass_mode=PassMode.FULL),

            _node("social",      "social_media",  "📱 Social Media Posts",
                  "Buat 5 social media posts dari artikel ini:\n{prev}\n\n"
                  "Format: 2 untuk LinkedIn (profesional), 2 untuk Twitter/X (concise+hook), "
                  "1 untuk Instagram (visual-first). Setiap post include hashtag relevan.",
                  pass_mode=PassMode.FULL),

            _node("newsletter",  "email_writer",  "📧 Email Newsletter",
                  "Buat email newsletter dari artikel ini:\n{prev}\n\n"
                  "Subject line (3 opsi), preview text, isi email (500-700 kata), "
                  "dan CTA yang jelas.",
                  pass_mode=PassMode.FIELD,
                  pass_field="article"),
        ],
        edges=[
            _edge("research",   "brief"),
            _edge("brief",      "article"),
            _edge("article",    "seo"),
            _edge("article",    "social"),
            _edge("article",    "newsletter"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. MARKET RESEARCH PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_market_research_pipeline() -> Pipeline:
    """
    Kompetitor research → SWOT → Opportunity mapping → Strategy
    """
    return Pipeline.create(
        name="🔬 Market Research Pipeline",
        description=(
            "Riset pasar mendalam: analisis kompetitor, SWOT, peluang pasar, "
            "dan rekomendasi strategi bisnis."
        ),
        category="research",
        tenant_id=TEMPLATE_TENANT,
        input_label="Pasar / Industri",
        input_hint="e.g. 'Aplikasi kasir UMKM Indonesia' atau 'Layanan cloud hosting murah Asia Tenggara'",
        tags=["research", "market", "competitor", "strategy", "swot"],
        is_template=True,
        nodes=[
            _node("market_overview", "research",      "🌏 Market Overview",
                  "Lakukan overview pasar untuk: {input}\n\n"
                  "Include: ukuran pasar (TAM/SAM/SOM), tren utama, pemain besar, "
                  "dan dinamika persaingan.",),

            _node("competitor",      "research",      "🆚 Competitor Analysis",
                  "Analisis kompetitor utama di pasar:\n{prev}\n\n"
                  "Untuk setiap kompetitor: produk, harga, kelebihan, kelemahan, "
                  "strategi marketing, dan target segmen.",
                  pass_mode=PassMode.FULL),

            _node("customer",        "research",      "👥 Customer Insights",
                  "Identifikasi dan analisis segmen pelanggan untuk:\n{input}\n\n"
                  "Buat 3 customer persona detail: demografi, psychografi, pain points, "
                  "buying journey, dan willingness to pay.",
                  pass_mode=PassMode.NONE),

            _node("swot",            "data_analyst",  "📊 SWOT Analysis",
                  "Buat SWOT analysis komprehensif berdasarkan:\n"
                  "Market: {prev}\n\nFormat tabel, minimal 5 poin per kuadran.",
                  pass_mode=PassMode.APPEND),

            _node("opportunities",   "research",      "💡 Opportunity Mapping",
                  "Identifikasi 5 peluang bisnis terbesar berdasarkan gap analysis:\n{prev}\n\n"
                  "Untuk setiap peluang: deskripsi, ukuran pasar, tingkat kompetisi, "
                  "dan effort-to-value score.",
                  pass_mode=PassMode.FULL),

            _node("strategy",        "content_writer","🗺️ Strategic Recommendations",
                  "Buat rekomendasi strategi bisnis konkret berdasarkan seluruh riset:\n{prev}\n\n"
                  "Output: 90-day action plan, prioritas investasi, KPI yang harus dicapai, "
                  "dan early warning signs.",
                  pass_mode=PassMode.APPEND),
        ],
        edges=[
            _edge("market_overview", "competitor"),
            _edge("market_overview", "customer"),
            _edge("competitor",      "swot"),
            _edge("customer",        "swot"),
            _edge("swot",            "opportunities"),
            _edge("opportunities",   "strategy"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4. CUSTOMER SUPPORT TRIAGE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_support_triage_pipeline() -> Pipeline:
    """
    Classify → Analyze Sentiment → Draft Response → QA → Escalation Check
    """
    return Pipeline.create(
        name="💬 Support Triage Pipeline",
        description=(
            "Handle tiket customer support: klasifikasi, analisis sentimen, "
            "draft respons, QA, dan cek eskalasi."
        ),
        category="support",
        tenant_id=TEMPLATE_TENANT,
        input_label="Pesan Customer",
        input_hint="Paste isi tiket / pesan customer di sini...",
        tags=["support", "customer service", "triage", "response"],
        is_template=True,
        nodes=[
            _node("classify",  "data_analyst", "🏷️ Classification",
                  "Klasifikasikan tiket support ini:\n{input}\n\n"
                  "Output JSON: {\"category\": \"...\", \"priority\": \"low|medium|high|urgent\", "
                  "\"product_area\": \"...\", \"issue_type\": \"bug|billing|question|complaint|refund\"}",
                  pass_mode=PassMode.FULL),

            _node("sentiment", "data_analyst", "😊 Sentiment Analysis",
                  "Analisis sentimen dari pesan customer:\n{input}\n\n"
                  "Output: sentiment (positif/netral/negatif/frustrated), "
                  "emotion score 1-10, dan summary singkat tone pelanggan.",
                  pass_mode=PassMode.NONE),

            _node("response",  "support",      "✍️ Draft Response",
                  "Tulis respons customer support untuk tiket ini:\n\nPesan: {input}\n\n"
                  "Konteks klasifikasi:\n{prev}\n\n"
                  "Respons harus: empatis, solutif, profesional, dan dalam Bahasa Indonesia.",
                  pass_mode=PassMode.APPEND),

            _node("qa",        "ethics_guard", "✅ QA & Ethics Check",
                  "Review respons support ini sebelum dikirim:\n{prev}\n\n"
                  "Cek: akurasi informasi, tone yang tepat, tidak ada janji berlebihan, "
                  "dan apakah sudah menjawab pertanyaan inti. Berikan skor 1-10 dan feedback.",
                  pass_mode=PassMode.FULL),

            _node("escalate",  "data_analyst", "🚨 Escalation Check",
                  "Tentukan apakah tiket ini perlu eskalasi ke manusia:\n{prev}\n\n"
                  "Output JSON: {\"needs_escalation\": true/false, \"reason\": \"...\", "
                  "\"escalate_to\": \"team_lead|billing|technical|management|none\", "
                  "\"urgency\": \"normal|asap\"}",
                  pass_mode=PassMode.APPEND),
        ],
        edges=[
            _edge("classify",  "response"),
            _edge("sentiment", "response"),
            _edge("response",  "qa"),
            _edge("qa",        "escalate"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5. PRODUCT LAUNCH PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_product_launch_pipeline() -> Pipeline:
    """
    Research → Positioning → Landing Page Copy → Email Sequence → Launch Announcement
    """
    return Pipeline.create(
        name="🚀 Product Launch Pipeline",
        description=(
            "Siapkan semua materi marketing untuk product launch: "
            "positioning, landing page, email sequence, dan announcement."
        ),
        category="marketing",
        tenant_id=TEMPLATE_TENANT,
        input_label="Produk / Fitur",
        input_hint="Deskripsikan produk/fitur yang akan dilaunching, target pasar, dan harga",
        tags=["launch", "product", "marketing", "landing page", "email"],
        is_template=True,
        nodes=[
            _node("research",    "research",      "🔬 Market Fit Research",
                  "Riset market fit untuk produk ini:\n{input}\n\n"
                  "Analisis: siapa yang paling butuh, apa masalah yang dipecahkan, "
                  "kompetitor yang ada, dan unique differentiator.",),

            _node("positioning", "copywriter",    "🎯 Positioning & Messaging",
                  "Buat positioning strategy berdasarkan:\n{prev}\n\n"
                  "Output: tagline (5 opsi), value proposition statement, "
                  "3 key messages utama, dan elevator pitch (30 detik).",
                  pass_mode=PassMode.FULL),

            _node("landing",     "copywriter",    "🌐 Landing Page Copy",
                  "Tulis copy landing page lengkap berdasarkan positioning:\n{prev}\n\n"
                  "Sections: hero (headline+subheadline), problem, solution, features (3), "
                  "social proof template, pricing, FAQ (5), dan CTA.",
                  pass_mode=PassMode.FULL, max_tokens=4096),

            _node("email_seq",   "email_writer",  "📧 Launch Email Sequence",
                  "Buat email launch sequence (5 email) berdasarkan positioning:\n{prev}\n\n"
                  "Email: teaser (D-7), early access (D-3), launch day, benefit reminder (D+2), "
                  "last chance (D+5). Setiap email lengkap dengan subject & body.",
                  pass_mode=PassMode.FIELD,
                  pass_field="positioning",
                  max_tokens=4096),

            _node("announce",    "social_media",  "📣 Launch Announcements",
                  "Buat konten launch announcement:\n{prev}\n\n"
                  "Buat untuk: LinkedIn post (detailed), Twitter/X thread (7 tweets), "
                  "Instagram caption + story text, dan press release singkat.",
                  pass_mode=PassMode.FULL),
        ],
        edges=[
            _edge("research",    "positioning"),
            _edge("positioning", "landing"),
            _edge("positioning", "email_seq"),
            _edge("positioning", "announce"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 6. FINANCIAL ANALYSIS PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_financial_analysis_pipeline() -> Pipeline:
    """
    Input data keuangan → Analisis → Laporan → Rekomendasi
    """
    return Pipeline.create(
        name="💰 Financial Analysis Pipeline",
        description=(
            "Analisis data keuangan bisnis: P&L review, cash flow analysis, "
            "dan rekomendasi finansial."
        ),
        category="finance",
        tenant_id=TEMPLATE_TENANT,
        input_label="Data Keuangan",
        input_hint="Paste data keuangan (revenue, biaya, dll) atau deskripsikan kondisi bisnis Anda",
        tags=["finance", "analysis", "cashflow", "report"],
        is_template=True,
        nodes=[
            _node("parse",      "data_analyst", "📊 Data Parsing",
                  "Parse dan strukturkan data keuangan berikut:\n{input}\n\n"
                  "Output terstruktur: revenue breakdown, cost categories, gross margin, "
                  "operating expenses, net profit/loss.",),

            _node("analysis",   "finance",      "🔍 Financial Analysis",
                  "Lakukan analisis mendalam data keuangan:\n{prev}\n\n"
                  "Include: trend analysis, unit economics, burn rate (jika startup), "
                  "runway, dan financial health score.",
                  pass_mode=PassMode.FULL),

            _node("benchmark",  "research",     "🆚 Industry Benchmark",
                  "Bandingkan metrik keuangan berikut dengan standar industri:\n{prev}\n\n"
                  "Identifikasi mana yang di atas/bawah rata-rata dan apa artinya.",
                  pass_mode=PassMode.FULL),

            _node("report",     "content_writer","📄 Executive Report",
                  "Buat laporan eksekutif ringkas dari analisis ini:\n{prev}\n\n"
                  "Format: executive summary (3 paragraf), key findings (5 poin), "
                  "risks & concerns, dan tabel metrik utama.",
                  pass_mode=PassMode.APPEND),

            _node("recommend",  "finance",      "💡 Recommendations",
                  "Berikan 5 rekomendasi konkret berdasarkan laporan ini:\n{prev}\n\n"
                  "Setiap rekomendasi: action item, expected impact, timeline, "
                  "dan difficulty (easy/medium/hard).",
                  pass_mode=PassMode.FULL),
        ],
        edges=[
            _edge("parse",     "analysis"),
            _edge("analysis",  "benchmark"),
            _edge("benchmark", "report"),
            _edge("report",    "recommend"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 7. CODE REVIEW PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_code_review_pipeline() -> Pipeline:
    """
    Code Review → Bug Detection → Security Audit → Refactor → Documentation
    """
    return Pipeline.create(
        name="🔧 Code Review Pipeline",
        description="Review kode lengkap: bug detection, security audit, refactor suggestions, dan auto-generate docs.",
        category="development",
        tenant_id=TEMPLATE_TENANT,
        input_label="Kode yang Akan Direview",
        input_hint="Paste kode Anda di sini (Python, JavaScript, atau bahasa lain)",
        tags=["code", "review", "security", "refactor", "documentation"],
        is_template=True,
        nodes=[
            _node("review",    "code_improver", "🔍 Code Review",
                  "Lakukan code review komprehensif:\n```\n{input}\n```\n\n"
                  "Cek: code quality, readability, best practices, performance issues.",),

            _node("bugs",      "code_improver", "🐛 Bug Detection",
                  "Identifikasi semua potential bugs dan edge cases dalam kode:\n```\n{input}\n```\n\n"
                  "Untuk setiap bug: lokasi (baris), deskripsi, severity, dan fix.",
                  pass_mode=PassMode.NONE),

            _node("security",  "code_improver", "🔐 Security Audit",
                  "Lakukan security audit untuk kode:\n```\n{input}\n```\n\n"
                  "Cek: SQL injection, XSS, authentication issues, data exposure, "
                  "insecure dependencies. Rate setiap issue: Critical/High/Medium/Low.",
                  pass_mode=PassMode.NONE),

            _node("refactor",  "code_improver", "♻️ Refactor Suggestions",
                  "Berikan refactored version dari kode ini berdasarkan temuan review:\n{prev}\n\n"
                  "Tulis kode yang sudah diperbaiki, lengkap dengan komentar perubahan.",
                  pass_mode=PassMode.APPEND),

            _node("docs",      "content_writer","📚 Auto Documentation",
                  "Generate dokumentasi lengkap untuk kode ini:\n```\n{input}\n```\n\n"
                  "Include: docstrings, README section, API reference, dan usage examples.",
                  pass_mode=PassMode.NONE),
        ],
        edges=[
            _edge("review",   "refactor"),
            _edge("bugs",     "refactor"),
            _edge("security", "refactor"),
            _edge("refactor", "docs"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 8. QUICK LEAD QUALIFY (Pipeline Minimal 3-Node)
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_quick_lead_qualify() -> Pipeline:
    return Pipeline.create(
        name="⚡ Quick Lead Qualify",
        description="Pipeline cepat 3 langkah: qualify prospek, buat pitch, dan draft email outreach.",
        category="sales",
        tenant_id=TEMPLATE_TENANT,
        input_label="Info Prospek",
        input_hint="Nama perusahaan, industri, atau deskripsi singkat prospek",
        tags=["sales", "quick", "lead", "outreach"],
        is_template=True,
        nodes=[
            _node("qualify",  "lead_gen",      "🎯 Qualify",
                  "Kualifikasi prospek ini: {input}\n\n"
                  "Output: ICP fit score 1-10, budget estimate, urgency level, "
                  "dan apakah layak di-pursue (yes/no/maybe) dengan alasan.",),
            _node("pitch",    "sales_closer",  "💼 Craft Pitch",
                  "Buat pitch yang dipersonalisasi berdasarkan kualifikasi ini:\n{prev}\n\n"
                  "30-second elevator pitch + 3 talking points utama.",
                  pass_mode=PassMode.FULL),
            _node("outreach", "email_writer",  "📧 Outreach Email",
                  "Buat email outreach cold yang personal:\n{prev}\n\n"
                  "Subject (3 opsi), body email 200-250 kata, dan CTA jelas.",
                  pass_mode=PassMode.FULL),
        ],
        edges=[_edge("qualify", "pitch"), _edge("pitch", "outreach")],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 9. CODE GENERATOR PIPELINE  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_code_generator_pipeline() -> Pipeline:
    """
    Requirement → Architecture → Generate Code → Test Cases → Docs → README
    Pipeline untuk generate kode lengkap dari deskripsi fitur/produk.
    """
    return Pipeline.create(
        name="💻 Code Generator Pipeline",
        description=(
            "Generate kode lengkap dari deskripsi requirement: "
            "arsitektur, implementasi, test cases, dan dokumentasi — semua otomatis."
        ),
        category="development",
        tenant_id=TEMPLATE_TENANT,
        input_label="Requirement / Fitur",
        input_hint=(
            "Deskripsikan fitur atau produk yang ingin dibuat.\n"
            "Contoh: 'API endpoint Python FastAPI untuk login dengan JWT, "
            "PostgreSQL, rate limiting, dan refresh token support'"
        ),
        tags=["code", "generator", "python", "api", "development", "tdd"],
        is_template=True,
        nodes=[
            _node("analyze",    "code_improver", "🔍 Requirement Analysis",
                  "Analisis requirement berikut dan buat spesifikasi teknis:\n\n{input}\n\n"
                  "Output terstruktur:\n"
                  "1. Functional requirements (list)\n"
                  "2. Non-functional requirements (performance, security, scalability)\n"
                  "3. Assumptions & constraints\n"
                  "4. Input/output specification\n"
                  "5. Edge cases yang perlu ditangani\n"
                  "6. Technology stack yang direkomendasikan",
                  pass_mode=PassMode.FULL),

            _node("architecture","code_improver", "🏗️ System Architecture",
                  "Buat desain arsitektur sistem berdasarkan requirement ini:\n\n{prev}\n\n"
                  "Output:\n"
                  "1. High-level architecture diagram (text-based, ASCII art)\n"
                  "2. Module/class breakdown dengan tanggung jawab masing-masing\n"
                  "3. Data model / schema\n"
                  "4. API contract (endpoints, request/response format)\n"
                  "5. Dependency list\n"
                  "6. File/folder structure yang direkomendasikan",
                  pass_mode=PassMode.FULL),

            _node("codegen",    "code_improver", "⚙️ Code Implementation",
                  "Implementasikan kode lengkap berdasarkan arsitektur ini:\n\n{prev}\n\n"
                  "PENTING:\n"
                  "- Tulis KODE LENGKAP yang bisa langsung dijalankan, bukan pseudocode\n"
                  "- Sertakan semua import, class, function, dan error handling\n"
                  "- Gunakan best practices: type hints, docstrings, logging\n"
                  "- Pisahkan per file dengan header komentar nama file\n"
                  "- Ikuti prinsip SOLID dan DRY\n"
                  "- Tambahkan komentar inline untuk logika kompleks",
                  pass_mode=PassMode.FULL,
                  max_tokens=4096,
                  temperature=0.3),   # suhu rendah = lebih deterministik untuk kode

            _node("tests",      "code_improver", "🧪 Test Cases",
                  "Buat test cases lengkap untuk kode ini:\n\n{prev}\n\n"
                  "Include:\n"
                  "1. Unit tests untuk setiap function/method penting\n"
                  "2. Integration tests untuk alur utama\n"
                  "3. Edge case tests\n"
                  "4. Test untuk error handling\n"
                  "Gunakan pytest. Berikan kode test yang lengkap dan bisa langsung dijalankan.",
                  pass_mode=PassMode.FULL,
                  max_tokens=3000,
                  temperature=0.2),

            _node("security",   "code_improver", "🔐 Security Review",
                  "Lakukan security review untuk kode implementasi:\n\n{prev}\n\n"
                  "Cek dan perbaiki:\n"
                  "1. Input validation & sanitization\n"
                  "2. Authentication & authorization\n"
                  "3. SQL injection / injection attacks\n"
                  "4. Secrets management (jangan hardcode)\n"
                  "5. Rate limiting & abuse prevention\n"
                  "6. Data exposure risks\n"
                  "Berikan versi kode yang sudah diperbaiki untuk setiap issue critical/high.",
                  pass_mode=PassMode.FIELD,
                  pass_field="implementation",
                  temperature=0.3),

            _node("readme",     "content_writer","📄 README & Docs",
                  "Buat README.md lengkap dan dokumentasi untuk proyek ini berdasarkan:\n\n{prev}\n\n"
                  "README harus include:\n"
                  "# Project Name\n"
                  "## Overview & Features\n"
                  "## Requirements & Installation\n"
                  "## Quick Start\n"
                  "## API Reference (jika ada)\n"
                  "## Configuration\n"
                  "## Testing\n"
                  "## Contributing\n"
                  "## License\n\n"
                  "Tulis dalam format Markdown yang rapi dan lengkap.",
                  pass_mode=PassMode.APPEND,
                  max_tokens=3000),
        ],
        edges=[
            _edge("analyze",      "architecture"),
            _edge("architecture", "codegen"),
            _edge("codegen",      "tests"),
            _edge("codegen",      "security"),
            _edge("tests",        "readme"),
            _edge("security",     "readme"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 10. PRODUCT OUTLINE PIPELINE  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_product_outline_pipeline() -> Pipeline:
    """
    Idea → Validation → PRD → Feature Breakdown → Roadmap → Pitch Deck Outline
    Pipeline lengkap dari ide mentah ke product spec yang siap dikerjakan.
    """
    return Pipeline.create(
        name="📦 Product Outline Pipeline",
        description=(
            "Dari ide mentah ke product spec lengkap: validasi, PRD, "
            "feature breakdown, roadmap, dan pitch deck outline — semua dalam satu pipeline."
        ),
        category="development",
        tenant_id=TEMPLATE_TENANT,
        input_label="Ide Produk",
        input_hint=(
            "Deskripsikan ide produk Anda.\n"
            "Contoh: 'Aplikasi mobile untuk manajemen keuangan UMKM Indonesia "
            "dengan fitur invoice otomatis, laporan pajak, dan integrasi marketplace'"
        ),
        tags=["product", "prd", "roadmap", "startup", "outline", "planning"],
        is_template=True,
        nodes=[
            _node("validate",   "research",      "✅ Idea Validation",
                  "Validasi ide produk ini dari perspektif bisnis dan pasar:\n\n{input}\n\n"
                  "Analisis:\n"
                  "1. Problem-Solution Fit: seberapa nyata masalah yang dipecahkan?\n"
                  "2. Target Market: siapa penggunanya? Ukuran pasar?\n"
                  "3. Existing Solutions: kompetitor yang ada, kelemahan mereka\n"
                  "4. Unique Value Proposition: apa bedanya produk ini?\n"
                  "5. Feasibility: teknis, waktu, biaya estimasi awal\n"
                  "6. Risk assessment: 5 risiko terbesar\n"
                  "7. Verdict: Go/No-Go/Pivot dengan alasan",
                  pass_mode=PassMode.FULL),

            _node("persona",    "research",      "👥 User Persona",
                  "Buat 3 user persona detail untuk produk:\n\n{input}\n\n"
                  "Untuk setiap persona:\n"
                  "- Nama, usia, pekerjaan, lokasi\n"
                  "- Goals & motivations\n"
                  "- Pain points & frustrations (yang relevan dengan produk)\n"
                  "- Current behavior (bagaimana mereka solve masalah sekarang)\n"
                  "- Tech savviness & device preference\n"
                  "- Quote representatif\n"
                  "- Jobs-to-be-done (JTBD) utama",
                  pass_mode=PassMode.NONE),

            _node("prd",        "content_writer","📋 Product Requirements Doc (PRD)",
                  "Buat PRD (Product Requirements Document) lengkap berdasarkan:\n\n"
                  "Ide: {input}\n\n"
                  "Validasi & Persona:\n{prev}\n\n"
                  "PRD harus berisi:\n"
                  "## 1. Executive Summary\n"
                  "## 2. Problem Statement\n"
                  "## 3. Goals & Success Metrics (OKR/KPI)\n"
                  "## 4. User Stories (format: As a [persona], I want to [action] so that [benefit])\n"
                  "   - Minimal 10 user stories, prioritized MoSCoW\n"
                  "## 5. Functional Requirements\n"
                  "## 6. Non-Functional Requirements\n"
                  "## 7. Out of Scope\n"
                  "## 8. Assumptions & Dependencies\n"
                  "## 9. Open Questions",
                  pass_mode=PassMode.APPEND,
                  max_tokens=4096),

            _node("features",   "data_analyst",  "🎯 Feature Breakdown",
                  "Breakdown semua fitur dari PRD ini menjadi tasks yang bisa dikerjakan:\n\n{prev}\n\n"
                  "Output dalam format tabel Markdown:\n"
                  "| Feature | Description | Priority | Effort (S/M/L/XL) | Sprint | Dependencies |\n\n"
                  "Kelompokkan per epic/modul. Minimal 15-20 features.\n"
                  "Tambahkan juga:\n"
                  "- MVP Features (yang paling minimal untuk launch)\n"
                  "- Nice-to-have features (post-MVP)\n"
                  "- Technical debt items",
                  pass_mode=PassMode.FULL),

            _node("techstack",  "code_improver", "🔧 Tech Stack Recommendation",
                  "Rekomendasikan tech stack untuk produk ini berdasarkan requirements:\n\n{prev}\n\n"
                  "Berikan rekomendasi untuk:\n"
                  "1. Frontend (web & mobile jika perlu)\n"
                  "2. Backend / API\n"
                  "3. Database (primary + cache)\n"
                  "4. Infrastructure & hosting\n"
                  "5. Third-party services & APIs\n"
                  "6. DevOps & CI/CD\n"
                  "7. Monitoring & analytics\n\n"
                  "Untuk setiap pilihan: alasan, alternatif, dan trade-off.",
                  pass_mode=PassMode.FULL),

            _node("roadmap",    "content_writer","🗺️ Product Roadmap",
                  "Buat product roadmap 12 bulan berdasarkan feature breakdown dan tech stack:\n\n{prev}\n\n"
                  "Format roadmap per quarter:\n\n"
                  "### Q1 (Bulan 1-3): Foundation\n"
                  "### Q2 (Bulan 4-6): Core Features\n"
                  "### Q3 (Bulan 7-9): Growth\n"
                  "### Q4 (Bulan 10-12): Scale\n\n"
                  "Setiap quarter: milestones, deliverables, team size estimasi, dan budget range.\n"
                  "Tambahkan launch strategy dan go-to-market plan singkat.",
                  pass_mode=PassMode.APPEND),

            _node("pitch",      "copywriter",    "🎤 Pitch Deck Outline",
                  "Buat outline pitch deck investor (10-12 slide) berdasarkan seluruh product spec:\n\n{prev}\n\n"
                  "Untuk setiap slide: judul, poin utama (3-5 bullets), dan visual yang disarankan.\n\n"
                  "Slide structure:\n"
                  "1. Cover & Tagline\n"
                  "2. Problem (the pain)\n"
                  "3. Solution (your product)\n"
                  "4. Market Opportunity (TAM/SAM/SOM)\n"
                  "5. Product Demo / Screenshots\n"
                  "6. Business Model\n"
                  "7. Traction (atau roadmap jika pre-launch)\n"
                  "8. Competitive Landscape\n"
                  "9. Team\n"
                  "10. Financial Projections\n"
                  "11. The Ask (funding)\n"
                  "12. Contact & Next Steps",
                  pass_mode=PassMode.APPEND,
                  max_tokens=3000),
        ],
        edges=[
            _edge("validate",  "prd"),
            _edge("persona",   "prd"),
            _edge("prd",       "features"),
            _edge("prd",       "techstack"),
            _edge("features",  "roadmap"),
            _edge("techstack", "roadmap"),
            _edge("roadmap",   "pitch"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 11. QUICK CODE SNIPPET  (NEW — pipeline ringkas 3 node)
# ══════════════════════════════════════════════════════════════════════════════

def tmpl_quick_code_snippet() -> Pipeline:
    """
    Pipeline cepat: Generate → Test → Docs untuk satu fungsi/snippet kode.
    """
    return Pipeline.create(
        name="⚡ Quick Code Snippet",
        description=(
            "Buat satu fungsi/snippet kode: generate implementasi, "
            "unit test, dan docstring — dalam 3 langkah cepat."
        ),
        category="development",
        tenant_id=TEMPLATE_TENANT,
        input_label="Fungsi / Snippet yang Dibutuhkan",
        input_hint=(
            "Deskripsikan fungsi yang ingin dibuat.\n"
            "Contoh: 'Fungsi Python untuk validasi nomor telepon Indonesia "
            "(format +62xxx atau 08xxx) dengan regex'"
        ),
        tags=["code", "snippet", "quick", "python", "function"],
        is_template=True,
        nodes=[
            _node("implement", "code_improver", "⚙️ Implementation",
                  "Tulis implementasi kode Python untuk:\n\n{input}\n\n"
                  "Requirement:\n"
                  "- Kode lengkap dan bisa langsung dijalankan\n"
                  "- Type hints lengkap\n"
                  "- Error handling yang proper\n"
                  "- Contoh penggunaan di bagian bawah\n"
                  "- Tidak ada dependency eksternal kecuali memang dibutuhkan",
                  temperature=0.2, max_tokens=2048),

            _node("test",      "code_improver", "🧪 Unit Tests",
                  "Buat unit tests pytest untuk kode ini:\n\n{prev}\n\n"
                  "Include:\n"
                  "- Test happy path\n"
                  "- Test edge cases\n"
                  "- Test error/exception cases\n"
                  "- Parameterized tests jika relevan\n"
                  "Kode test harus bisa langsung dijalankan dengan `pytest`.",
                  pass_mode=PassMode.FULL, temperature=0.2, max_tokens=1500),

            _node("docs",      "content_writer","📄 Documentation",
                  "Buat dokumentasi lengkap untuk fungsi/kode ini:\n\n{prev}\n\n"
                  "Include:\n"
                  "- Docstring format Google Style\n"
                  "- Usage examples (3-5 contoh berbeda)\n"
                  "- Parameter & return type description\n"
                  "- Known limitations atau edge cases\n"
                  "- Changelog entry singkat",
                  pass_mode=PassMode.FULL),
        ],
        edges=[
            _edge("implement", "test"),
            _edge("implement", "docs"),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

ALL_TEMPLATES: list[tuple[str, callable]] = [
    ("full_sales",         tmpl_full_sales_pipeline),
    ("content_marketing",  tmpl_content_marketing_pipeline),
    ("market_research",    tmpl_market_research_pipeline),
    ("support_triage",     tmpl_support_triage_pipeline),
    ("product_launch",     tmpl_product_launch_pipeline),
    ("financial_analysis", tmpl_financial_analysis_pipeline),
    ("code_review",        tmpl_code_review_pipeline),
    ("quick_lead",         tmpl_quick_lead_qualify),
    ("code_generator",     tmpl_code_generator_pipeline),   # NEW
    ("product_outline",    tmpl_product_outline_pipeline),  # NEW
    ("quick_code_snippet", tmpl_quick_code_snippet),        # NEW
]


def get_all_templates() -> list[Pipeline]:
    return [fn() for _, fn in ALL_TEMPLATES]


def seed_templates(db) -> None:
    """
    Seed semua templates ke database.
    Force-update jika template sudah ada (untuk sinkronisasi perubahan).
    """
    for tmpl in get_all_templates():
        db.save_pipeline(tmpl)  # INSERT OR REPLACE — selalu update template
