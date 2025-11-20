# 🎬 M3U8 Streaming Player

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-green)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange)](https://github.com/msyamsudin/M3U8-Streaming/blob/main/LICENSE)

Pemutar streaming berbasis **HLS (.m3u8)** dengan dukungan **rekaman siaran langsung**, **riwayat URL**, dan **UI bertema gelap ala MPC-HC**, dibangun menggunakan **Python (Tkinter) + MPV**.

---

## 🖼️ Tampilan Antarmuka

<img width="1252" height="815" alt="image" src="https://github.com/user-attachments/assets/4f9476f6-ff30-4e61-950d-28e14b99a66e" />

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 🎬 **Pemutaran Stream** | Mendukung HLS (.m3u8) |
| 💾 **Perekaman Live** | Rekam streaming ke format `.ts` |
| 🕒 **Riwayat URL** | Menyimpan URL yang baru diputar |
| 🎨 **UI Modern** | Tema gelap mirip MPC-HC |
| ⌨️ **Shortcut Lengkap** | Kontrol cepat layaknya video player profesional |

---

## 🖥️ Persyaratan Sistem

| Komponen | Spesifikasi Minimum |
|----------|---------------------|
| Sistem Operasi | Windows 10 / Windows 11 |
| Python | Versi 3.8 atau lebih baru |
| Library Python | `python-mpv`, `requests` |
| Library Eksternal | `libmpv-2.dll` (**wajib**) |

📌 **Catatan:** `libmpv-2.dll` harus berada di folder utama aplikasi atau di subfolder `mpv/`.

---

## 📦 Instalasi

### 1️⃣ Clone repositori
```bash
git clone https://github.com/msyamsudin/M3U8-Streaming.git
cd M3U8-Streaming
````

### 2️⃣ Install library Python

```bash
pip install python-mpv requests
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

Jalankan perintah berikut:

```bash
python main.py
```

---

## ⌨️ Shortcut Keyboard

| Tombol                    | Fungsi                 |
| ------------------------- | ---------------------- |
| `Spasi`                   | Play / Pause           |
| `F` atau **Double Click** | Fullscreen             |
| `←` / `→`                 | Mundur / Maju 10 detik |
| `Ctrl + O`                | Input URL Stream       |
| `Esc`                     | Keluar dari Fullscreen |

---

## 🎥 Cara Merekam Streaming

1. Putar URL streaming.
2. Tekan tombol **Record** di toolbar.
3. Tombol berubah menjadi merah 🟥 → proses rekam aktif.
4. File akan disimpan otomatis ke folder `downloads/`.
5. Tekan **Stop Rec** untuk menyelesaikan rekaman.

---

## 🔗 URL Contoh untuk Uji Coba

```
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
```

---

## ❗ Troubleshooting

| Masalah                     | Solusi                                                     |
| --------------------------- | ---------------------------------------------------------- |
| Video tidak tampil          | Pastikan `libmpv-2.dll` sudah ditempatkan dengan benar     |
| Tidak bisa merekam          | Pastikan folder `downloads/` tidak diblok/readonly         |
| Error `ModuleNotFoundError` | Install library: `pip install python-mpv requests`         |
| Streaming lag/stutter       | Cek koneksi internet, bitrate tinggi butuh bandwidth lebih |

---

## 📄 Lisensi

Proyek ini menggunakan lisensi **MIT License**.
📌 Lihat berkas [`LICENSE`](https://github.com/msyamsudin/M3U8-Streaming/blob/main/LICENSE)
