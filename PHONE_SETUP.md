# 📱 CATERYA dari HP — Panduan Lengkap
*Author: Ary HH (Caterya Tech)*

---

## Situasi yang Dicoverage

| Situasi | Solusi | Internet? |
|---|---|---|
| HP + laptop/PC, 1 WiFi | Local IP langsung | WiFi saja |
| HP di lokasi berbeda, laptop di rumah | Tailscale | Internet |
| HP di gunung, laptop offline | Ollama lokal di HP Android | Tidak perlu |
| Cepat share link sementara | ngrok | Internet |
| Production permanent | VPS + Tailscale | Internet |

---

## OPSI 1: Sama WiFi (Paling Simpel)

Laptop dan HP connected ke WiFi yang sama.

```bash
# Di laptop — cari IP lokal
hostname -I          # Linux
ipconfig getifaddr en0   # macOS

# Jalankan dashboard
streamlit run src/dashboard/app.py --server.address=0.0.0.0

# Di HP — buka browser
http://192.168.1.xxx:8501   # ganti dengan IP laptop kamu
```

**Install sebagai PWA di HP:**
1. Buka URL di Chrome/Safari
2. Chrome Android: menu titik tiga → "Add to Home Screen"
3. Safari iOS: Share button → "Add to Home Screen"
4. Muncul icon di home screen — bisa dibuka seperti app biasa
5. Bisa pakai offline jika Ollama dan dashboard masih running di laptop

---

## OPSI 2: Tailscale — Akses dari Mana Saja (Recommended)

Tailscale membuat "private VPN mesh" — HP kamu bisa langsung reach laptop kamu via IP private, menembus router, NAT, bahkan provider berbeda.

### Install Tailscale

```bash
# Laptop/Server (Linux)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Cek IP Tailscale
tailscale ip -4
# Contoh output: 100.64.x.x
```

**HP Android/iOS:**
- Download Tailscale dari Play Store / App Store
- Login dengan akun yang sama
- Connect

### Jalankan Dashboard
```bash
# Di laptop
streamlit run src/dashboard/app.py --server.address=0.0.0.0

# Di HP — buka browser
http://100.64.x.x:8501   # IP Tailscale laptop kamu
```

**Keuntungan Tailscale:**
- Gratis untuk personal (hingga 3 devices — kalau perlu lebih pakai free plan dengan 20 devices)
- End-to-end encrypted (WireGuard)
- Tidak perlu port forwarding di router
- Bekerja meski laptop di balik NAT/CGNAT (provider Indonesia sering CGNAT)
- Koneksi tetap aman di WiFi publik

### Tailscale Funnel (Optional — Share ke internet publik)
```bash
# Buat URL publik dari laptop (HTTPS otomatis)
tailscale funnel 8501
# Output: https://laptop-name.tail1234.ts.net
# Bisa dibuka dari HP manapun tanpa install Tailscale
```

---

## OPSI 3: ngrok — Quick Tunnel Sementara

```bash
# Install ngrok: https://ngrok.com/download
# Atau: brew install ngrok (macOS) / snap install ngrok (Linux)

# Login (gratis)
ngrok config add-authtoken YOUR_TOKEN

# Buat tunnel
ngrok http 8501

# Output:
# Forwarding https://abc123.ngrok-free.app -> http://localhost:8501
# Share URL ini ke HP kamu
```

**Catatan:** URL ngrok berubah setiap restart (kecuali plan berbayar).

---

## OPSI 4: Ollama Langsung di HP Android (Full Offline di HP)

Untuk benar-benar offline di HP tanpa laptop sama sekali:

### Termux (Android)
```bash
# Install Termux dari F-Droid (bukan Play Store — versi Play Store outdated)
# https://f-droid.org/packages/com.termux/

# Di Termux
pkg update && pkg upgrade
pkg install python python-pip curl git

# Install Ollama via script
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model kecil (cocok untuk HP)
ollama pull phi4       # ~4GB, fast, good quality
ollama pull qwen2.5:1b # ~800MB, sangat cepat, RAM rendah

# Clone repo
git clone [repo-url]
cd caterya-agentic-enterprise
pip install streamlit langchain-ollama langgraph cryptography python-dotenv httpx pydantic

# Run
streamlit run src/dashboard/app.py
# Buka di browser HP: http://localhost:8501
```

**Model rekomendasi untuk HP:**
| Model | Size | RAM | Kecepatan |
|---|---|---|---|
| phi4 | 4GB | 6GB+ | Cepat |
| qwen2.5:1b | 800MB | 2GB+ | Sangat cepat |
| gemma3:1b | 800MB | 2GB+ | Cepat |
| llama3.2:1b | 1.3GB | 3GB+ | OK |

---

## OPSI 5: VPS Permanent (Production)

Untuk akses 24/7 dari HP manapun:

```bash
# Di VPS (Contabo/DigitalOcean/Hetzner — harga mulai $4/bulan)
git clone [repo]
cd caterya-agentic-enterprise
docker-compose up -d

# Pasang Tailscale di VPS juga
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Akses dari HP
http://[VPS-tailscale-ip]:8501
```

---

## Checklist Sebelum Pergi ke Gunung 🏔️

```
[ ] Ollama running di laptop/device: ollama serve
[ ] Dashboard running: streamlit run src/dashboard/app.py
[ ] Tailscale connected di laptop DAN HP
[ ] Minimal 1 model sudah di-pull: ollama list
[ ] Test akses dari HP: http://[tailscale-ip]:8501
[ ] PWA installed di home screen HP
[ ] .env sudah dikonfigurasi dengan benar
[ ] Battery + powerbank cukup untuk laptop
```

---

## Troubleshooting

**HP tidak bisa akses dashboard:**
```bash
# Cek firewall (Linux)
sudo ufw allow 8501
sudo ufw allow from 100.64.0.0/10  # Allow Tailscale subnet

# Cek Streamlit sudah listen ke semua interface
# Pastikan ada --server.address=0.0.0.0
```

**Tailscale tidak connect:**
```bash
sudo tailscale status    # Cek status
sudo tailscale up --reset  # Reset jika stuck
```

**Ollama lambat di HP:**
- Gunakan model lebih kecil: `phi4` atau `qwen2.5:1b`
- Pastikan tidak ada app lain yang berat
- Aktifkan "Don't keep activities" di Developer Options OFF
