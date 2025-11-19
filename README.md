# M3U8 Streaming Player

M3U8 Streaming Player dibangun dengan Python (Tkinter) dan MPV.

## Fitur

*   **Pemutaran Stream**: Mendukung HLS (M3U8) dan format stream lainnya.
*   **Perekaman**: Rekam siaran langsung langsung ke disk (format `.ts`).
*   **Pilihan Kualitas**: Ganti kualitas/resolusi video yang tersedia secara langsung (on-the-fly).
*   **Riwayat**: Menyimpan URL yang baru saja diputar untuk akses cepat.
*   **UI Modern**: Tema gelap yang terinspirasi dari MPC-HC dengan kontrol kustom.
*   **Selalu di Atas**: Opsi "Always on Top" agar player tetap terlihat saat multitasking.
*   **Layar Penuh**: Mode fullscreen untuk pengalaman menonton yang lebih baik.

## Persyaratan Sistem

*   Python 3.8+
*   `python-mpv`
*   `requests`
*   `libmpv-2.dll` (Harus diletakkan di folder aplikasi atau subfolder `mpv/`)

## Instalasi

1.  Clone repositori ini:
    ```bash
    git clone https://github.com/username-anda/m3u8-streaming-player.git
    cd m3u8-streaming-player
    ```

2.  Install library Python yang dibutuhkan:
    ```bash
    pip install python-mpv requests
    ```

3.  **PENTING**: Download `libmpv-2.dll` (dan `mpv-1.dll` jika diperlukan) dari [shinchiro's builds](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) dan letakkan file tersebut di folder root proyek ini.

## Cara Penggunaan

Jalankan aplikasi dengan perintah:
```bash
python main.py
```

### Pintasan Keyboard (Shortcuts)

*   `Spasi`: Play/Pause
*   `F` / `Klik Ganda`: Toggle Fullscreen (Layar Penuh)
*   `Kiri` / `Kanan`: Mundur/Maju 10 detik
*   `Ctrl+O`: Buka dialog URL
*   `Esc`: Keluar dari Fullscreen

## Cara Merekam

1.  Mulai putar stream.
2.  Klik tombol **Record** di toolbar.
3.  Tombol akan berubah menjadi merah. Stream sekarang sedang disimpan ke folder `downloads/`.
4.  Klik **Stop Rec** untuk selesai dan menyimpan file.

## Lisensi

Open Source