# M3U8 Streaming Player

M3U8 Streaming Player dibangun dengan Python (Tkinter) dan MPV.

<img width="1252" height="815" alt="image" src="https://github.com/user-attachments/assets/4f9476f6-ff30-4e61-950d-28e14b99a66e" />


## Fitur

*   **Pemutaran Stream**: Mendukung HLS (M3U8)
*   **Perekaman**: Rekam siaran langsung langsung ke disk (format `.ts`).
*   **Riwayat**: Menyimpan URL yang baru saja diputar untuk akses cepat.
*   **UI Modern**: Tema gelap yang terinspirasi dari MPC-HC dengan kontrol kustom.

## Persyaratan Sistem

*   Python 3.8+
*   `python-mpv`
*   `requests`
*   `libmpv-2.dll` (Harus diletakkan di folder aplikasi atau subfolder `mpv/`)

## Instalasi

1.  Clone repositori ini:
    ```bash
    git clone https://github.com/msyamsudin/M3U8-Streaming.git
    cd m3u8-streaming-player
    ```

2.  Install library Python yang dibutuhkan:
    ```bash
    pip install python-mpv requests
    ```

3.  **PENTING**: Download `libmpv-2.dll` dari [shinchiro's builds](https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) dan letakkan file tersebut di folder root proyek ini.

## Cara Penggunaan

Jalankan aplikasi dengan perintah:
```bash
python main.py
```

### Shortcut

*   `Spasi`: Play/Pause
*   `F` / `Double Click`: Toggle Fullscreen (Layar Penuh)
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
