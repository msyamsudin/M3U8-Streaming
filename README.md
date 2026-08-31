# 🎬 M3U8 Streaming Player

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-green)
![UI](https://img.shields.io/badge/UI-PySide6%20(Qt)-9b59b6)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange)](https://github.com/msyamsudin/M3U8-Streaming/blob/main/LICENSE)

Pemutar streaming berbasis **HLS (.m3u8)** dengan dukungan **Referer/User-Agent custom** dan dibangun menggunakan **Python (PySide6) + MPV**.

> UI default sekarang adalah **PySide6/Qt** dengan fokus pada animasi halus dan look modern (mirip MPC-HC / IINA).

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 🎬 **Pemutaran Stream** | Mendukung HLS (.m3u8) via libmpv |
| 🕒 **Riwayat URL** | Menyimpan URL dan posisi terakhir |
| ⏯️ **Continue Watching** | Menawarkan resume dari posisi terakhir |
| 🚀 **Cache Tuning** | Input forward/back cache dan refresh threshold |
| 🔄 **Pause Refresh** | Reload stream saat lanjut setelah pause melebihi threshold |
| 📊 **Speed Indicator** | Network speed & buffered time real-time |
| 🛠️ **Debug Overlay** | State, posisi, buffer, cache, speed, codec, URL aktif (F12/Ctrl+D) |
| 🕵️ **Request Headers** | Custom Referer dan User-Agent |
| 🎚️ **Quality Selector** | Pilih track video (1080p/720p/dll) |
| 🔊 **Volume Slider** | 0–130% boost |
| 🌑 **Fullscreen Auto-Hide** | Chrome & cursor hide setelah 3 detik idle |
| 🪟 **Frameless Window** | Custom title bar, drag, min/max/close dengan hover state |
| ⌨️ **Keyboard Shortcuts** | Space, arrow keys, F, H, M, Ctrl+L/Ctrl+O, F1 |
| 🔔 **Toast Notifications** | Feedback ringkas untuk aksi penting |

---

## 🖥️ Persyaratan Sistem

| Komponen | Spesifikasi Minimum |
|----------|---------------------|
| Sistem Operasi | Windows 10 / Windows 11 |
| Python | Versi 3.10 atau lebih baru |
| Library Python | `python-mpv`, `PySide6>=6.6` |
| Library Eksternal | `libmpv-2.dll` (**wajib**) |

📌 **Catatan:** `libmpv-2.dll` harus berada di folder utama aplikasi atau di subfolder `mpv/`.

---

## 📦 Instalasi

### 1️⃣ Clone repositori
```bash
git clone https://github.com/msyamsudin/M3U8-Streaming.git
cd M3U8-Streaming
```

### 2️⃣ Install library Python

```bash
pip install -r requirements.txt
```

### 3️⃣ Download `libmpv-2.dll`

Unduh dari:
🔗 [https://sourceforge.net/projects/mpv-player-windows/files/libmpv/](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/)

Lalu letakkan di:
```
./ (root folder)
atau
./mpv/
```

---

## ▶️ Cara Menjalankan Aplikasi

### Mode Development
```bash
python main.py
```

Shortcut Windows:
```bash
run.bat
```

## ⌨️ Shortcut Keyboard (PySide6 build)

| Tombol | Fungsi |
|--------|--------|
| `Spasi` | Play / Pause |
| `S` | Stop |
| `←` / `→` | Seek -10s / +10s |
| `Shift + ←/→` | Seek -30s / +30s |
| `↑` / `↓` | Volume +5 / -5 |
| `F` atau **Double Click** title bar | Fullscreen toggle |
| `Esc` | Keluar dari fullscreen |
| `H` | Toggle History panel |
| `M` | Mute / Unmute |
| `Ctrl + L` / `Ctrl + O` | Focus URL input |
| `F12` / `Ctrl + D` | Toggle Debug Overlay |
| `F1` | Show keyboard shortcuts |

> Shortcut otomatis di-block saat text input sedang fokus.

---

## 🎬 Tombol Title Bar (kiri ke kanan)

| Tombol | Fungsi |
|--------|--------|
| ⚙ (gear) | Toggle Settings panel |
| ⏳ (clock) | Toggle History panel |
| – (min) | Minimize |
| □ (max) / ⷠ (restore) | Maximize / Restore |
| ✕ (close) | Close (hover merah) |

## 🎚️ Control Bar (bawah)

| Tombol | Fungsi |
|--------|--------|
| ⏮ / ⏭ | Seek -10s / +10s |
| ▶ / ⏸ | Play / Pause |
| – | Seek slider dengan buffered highlight |
| 🔊 | Volume (klik untuk expand slider 0–130) |
| – | Quality dropdown (Auto + detected tracks) |
| ⛶ / ✕ | Fullscreen |
| ⏐ | Debug overlay (juga F12) |

---

## 🏗️ Arsitektur PySide6

```
src/app/
├── main_window.py            # QMainWindow orchestration
├── theme/
│   ├── colors.py              # Palet warna (MPC-HC dark)
│   ├── animations.py         # Anim helper: fade, slide, expand
│   └── styles.qss            # Global QSS (dark theme)
├── controllers/
│   └── player_controller.py   # QObject wrapper MpvPlayer + signals
├── widgets/
│   ├── video_surface.py      # QWidget hosting libmpv HWND
│   ├── custom_title_bar.py   # Frameless title bar
│   ├── control_bar.py        # Seek/play/pause/volume/quality/debug
│   ├── seek_slider.py        # Custom QSlider + buffered region
│   ├── history_panel.py      # QListWidget + custom delegate
│   ├── debug_overlay.py      # Real-time stats
│   └── toast.py              # Slide-in notifications
```

### Logika Inti (tidak berubah)
- `src/player_core.py` — wrapper libmpv
- `src/config.py` — MPV paths + palet lama (kompatibilitas mundur)
- `src/utils.py` — JSON load/save (history + settings)

---

## 🎨 Animasi yang Diimplementasi

| Komponen | Animasi |
|----------|---------|
| Video placeholder | Fade in/out saat idle/loading/play |
| History panel | Slide horizontal 400ms `EASE_OUT` |
| Config bar | Collapse/expand dari title bar |
| Toast in/out | Slide vertical + fade 250ms |
| Fullscreen auto-hide | Title + control bar hide setelah idle |
| Mouse activity | Reset 3-detik idle timer |

---

## 🔗 URL Contoh untuk Uji Coba

```
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
```

---

## ❗ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Video tidak tampil | Pastikan `libmpv-2.dll` sudah ditempatkan dengan benar |
| `ModuleNotFoundError: PySide6` | `pip install -r requirements.txt` |
| `Cannot find mpv-1.dll, mpv-2.dll or libmpv-2.dll` | PATH belum diset — `player_core.py` auto-set di awal import |
| Streaming lag/stutter | Gunakan **Cache Tuning**, naikkan forward cache |
| Stream mati setelah pause | **Pause Refresh** akan reload saat playback dilanjutkan setelah threshold (default 60s) |

---

## 🔒 Keamanan Data

> ⚠️ **`history.json` menyimpan URL stream lengkap, termasuk token akses signed**
> (bisa berumur panjang) dalam teks polos. File ini **tidak** di-upload ke git
> (sudah di `.gitignore`), tapi jangan dibagikan atau di-backup ke tempat publik.
>
> `settings.json` berisi konfigurasi lokal (referer, user-agent, volume, geometri
> jendela) dan saat ini ikut ter-track di repo. Jika ingin menjaga privasi
> konfigurasi per-mesin, tambahkan `settings.json` ke `.gitignore`.

---

## 📝 Status UI

Proyek ini sudah memakai **PySide6/Qt** sebagai UI default.

- `main.py` → entrypoint resmi aplikasi Qt
- `run.bat` → menjalankan `main.py`
Lihat `history.json` dan `settings.json` — schema tidak berubah, jadi migrasi data otomatis.
