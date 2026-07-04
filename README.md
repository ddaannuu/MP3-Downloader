# YouTube MP3 Downloader (CLI)

Tools baris perintah (Command Line Interface) berbasis Python untuk mengunduh
audio dari video YouTube dan mengonversinya menjadi file MP3, tanpa perlu
GUI — cukup jalankan script dan tempelkan URL video.

Dibangun menggunakan **yt-dlp** (pengganti modern `pytube` yang sudah tidak
aktif dikembangkan) dan **FFmpeg** untuk konversi audio.

---

## Fitur

- Validasi otomatis terhadap URL YouTube (`youtube.com`, `youtu.be`,
  `music.youtube.com`, termasuk Shorts & Playlist).
- Menampilkan info video sebelum download: **judul, channel, durasi,
  estimasi ukuran file, bitrate, dan thumbnail**.
- Konfirmasi (`Y/N`) sebelum proses download dimulai.
- Progress bar realtime (persentase & kecepatan) menggunakan `tqdm`.
- Pilihan kualitas audio: **128 / 192 / 256 / 320 kbps**.
- Opsi mengganti nama file sebelum disimpan.
- Pilihan folder penyimpanan (default: `downloads/`).
- Mendukung download **seluruh playlist** YouTube.
- Mendukung download **banyak URL sekaligus** dari file `.txt`
  (`python main.py --file daftar_url.txt`).
- Riwayat download otomatis tersimpan di `logs/history.log`.
- Penanganan error yang informatif untuk berbagai kondisi (lihat bagian
  [Troubleshooting](#troubleshooting)).
- Kompatibel dengan **Windows, Linux, dan macOS**.

---

## Struktur Folder

```
youtube_mp3_downloader/
│
├── main.py              # Entry point CLI, alur interaktif & argumen
├── downloader.py        # Logika download & konversi (yt-dlp + FFmpeg)
├── utils.py              # Validasi URL, formatting, logging, helper lain
├── requirements.txt      # Daftar dependency Python
├── README.md             # Dokumentasi project
├── downloads/            # Folder default hasil MP3 (dibuat otomatis)
└── logs/
    ├── app.log            # Log teknis (error, warning)
    └── history.log        # Riwayat download yang berhasil
```

---

## Instalasi

### 1. Persyaratan

- Python **3.11+**
- FFmpeg (lihat cara instalasi di bawah)

### 2. Clone / salin project

```bash
cd youtube_mp3_downloader
```

### 3. (Opsional) Buat virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 4. Install dependency Python

```bash
pip install -r requirements.txt
```

---

## Cara Menginstal FFmpeg

FFmpeg **wajib terpasang** dan dapat diakses melalui PATH sistem, karena
digunakan yt-dlp untuk mengonversi audio menjadi MP3.

### Windows

1. Unduh build FFmpeg dari <https://www.gyan.dev/ffmpeg/builds/> (pilih
   `ffmpeg-release-essentials.zip`).
2. Ekstrak, misal ke `C:\ffmpeg`.
3. Tambahkan `C:\ffmpeg\bin` ke Environment Variable **PATH**.
4. Verifikasi dengan membuka Command Prompt baru:
   ```bash
   ffmpeg -version
   ```

### macOS (menggunakan Homebrew)

```bash
brew install ffmpeg
```

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install ffmpeg
```

### Linux (Fedora)

```bash
sudo dnf install ffmpeg
```

Verifikasi instalasi di semua OS dengan:

```bash
ffmpeg -version
```

Jika program tidak dapat mendeteksi FFmpeg meski sudah terpasang, pastikan
terminal/Command Prompt sudah dibuka ulang setelah PATH diperbarui.

---

## Cara Menjalankan Program

### Mode interaktif (default)

```bash
python main.py
```

Program akan terus meminta URL baru setelah setiap proses selesai, sampai
Anda memilih untuk berhenti atau menekan `Ctrl+C`.

### Menentukan kualitas audio & folder output lewat argumen

```bash
python main.py --quality 192 --output D:/Musik
```

| Argumen | Alias | Keterangan | Default |
|---|---|---|---|
| `--quality` | `-q` | Kualitas MP3: 128 / 192 / 256 / 320 | `320` |
| `--output` | `-o` | Folder tujuan penyimpanan file | `downloads/` |
| `--file` | `-f` | Path file `.txt` berisi banyak URL (satu per baris) | - |

### Mode batch (banyak URL dari file `.txt`)

Buat file `daftar_url.txt`:

```
# Baris diawali '#' akan diabaikan
https://www.youtube.com/watch?v=xxxxxxxx
https://youtu.be/yyyyyyyy
https://music.youtube.com/watch?v=zzzzzzzz
```

Jalankan:

```bash
python main.py --file daftar_url.txt --quality 256
```

---

## Contoh Penggunaan

```
=====================================
      YouTube MP3 Downloader
=====================================

Masukkan URL YouTube: https://www.youtube.com/watch?v=xxxxxxxx
Mengambil informasi video, mohon tunggu...

-------------------------------------
Judul     : Belajar Python
Channel   : OpenAI
Durasi    : 12 menit 30 detik
Ukuran    : 11.87 MB (estimasi)
Bitrate   : 128 kbps (sumber asli)
Thumbnail : https://i.ytimg.com/vi/xxxxxxxx/maxresdefault.jpg
-------------------------------------

Lanjut download? (Y/N): y
Pilihan kualitas audio: 128, 192, 256, 320 kbps
Kualitas audio [320]: 320
Ubah nama file sebelum disimpan? (kosongkan jika tidak):

Memulai download...
Downloading: 100%|████████████████████| 11.9M/11.9M [00:08<00:00, 1.42MB/s]
Converting ke MP3...

=====================================
Download Berhasil
=====================================

Nama File :
Belajar Python.mp3

Disimpan pada:
downloads/

Terima kasih telah menggunakan program ini.

Unduh video lain? (Y/N): n

Terima kasih telah menggunakan program ini. Sampai jumpa!
```

---

## Troubleshooting

| Masalah | Penyebab | Solusi |
|---|---|---|
| `Error: FFmpeg belum terpasang...` | FFmpeg tidak terdeteksi di PATH | Ikuti langkah [instalasi FFmpeg](#cara-menginstal-ffmpeg), lalu buka terminal baru |
| `URL yang dimasukkan bukan URL YouTube yang valid` | URL bukan dari domain YouTube, atau format salah | Pastikan URL diawali `youtube.com`, `youtu.be`, atau `music.youtube.com` |
| `Video ini bersifat private...` | Video disetel private oleh pemilik | Tidak dapat diunduh; gunakan video lain yang bersifat publik |
| `Video tidak tersedia atau telah dihapus` | Video sudah dihapus / diblokir wilayah | Coba video lain, atau gunakan VPN jika terkena pembatasan wilayah |
| `Tidak ada koneksi internet...` | Jaringan bermasalah | Periksa koneksi Wi-Fi/data, coba lagi setelah tersambung |
| Download gagal di tengah proses | Koneksi putus, video berubah privasi, atau yt-dlp perlu update | Coba lagi; jalankan `pip install -U yt-dlp` untuk memperbarui |
| Program keluar mendadak saat `Ctrl+C` ditekan | Ini perilaku normal (graceful exit) | Tidak perlu tindakan; program berhenti dengan aman |
| Nama file error / tidak tersimpan di Windows | Judul video mengandung karakter terlarang (`: / \ ? *`) | Program otomatis membersihkan nama file (fitur `sanitize_filename`) |

Log teknis (error/warning) tersimpan di `logs/app.log`, dan riwayat download
yang berhasil tersimpan di `logs/history.log` — cek file ini jika mengalami
masalah yang berulang.

---

## Catatan Pengembangan

- Kode dipisah menjadi 3 tanggung jawab jelas: `main.py` (tampilan & alur
  CLI), `downloader.py` (logika download/konversi), `utils.py` (fungsi
  bantu & validasi) — memudahkan pengembangan fitur baru di kemudian hari.
- Semua exception dibuat spesifik (`InvalidURLError`,
  `VideoUnavailableError`, `NoInternetError`, `FFmpegNotFoundError`,
  `DownloadError`) agar pesan error yang ditampilkan ke pengguna selalu
  jelas dan relevan.
