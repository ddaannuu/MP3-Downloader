"""
utils.py
--------
Kumpulan fungsi utilitas (helper) untuk YouTube MP3 Downloader (CLI).
Berisi validasi URL, formatting, pengecekan FFmpeg, pengecekan koneksi
internet, serta konfigurasi logging.

Dipisahkan dari main.py & downloader.py agar mudah diuji ulang dan
mengikuti prinsip Single Responsibility (Clean Code).
"""

import os
import re
import shutil
import socket
import subprocess
import logging
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Konstanta lokasi folder
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
LOGS_DIR = BASE_DIR / "logs"

# Regex untuk mengenali URL YouTube: youtube.com, m.youtube.com, youtu.be,
# music.youtube.com, termasuk URL video biasa, shorts, dan playlist (list=)
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|watch\?.*[?&]v=|shorts/|embed/|playlist\?list=)"
    r"|youtu\.be/)"
    r"[\w\-]+",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# VALIDASI & FORMATTING
# ---------------------------------------------------------------------------
def is_valid_youtube_url(url: str) -> bool:
    """
    Memvalidasi apakah string adalah URL YouTube yang sah.
    Mendukung: youtube.com, m.youtube.com, music.youtube.com, youtu.be,
    termasuk video biasa, shorts, dan playlist.
    """
    if not url or not isinstance(url, str):
        return False
    return bool(YOUTUBE_REGEX.match(url.strip()))


def is_playlist_url(url: str) -> bool:
    """Mengecek apakah URL mengarah ke playlist YouTube (mengandung 'list=')."""
    return "list=" in url


def format_duration(seconds) -> str:
    """
    Mengubah durasi dalam detik menjadi format berbahasa Indonesia,
    misal: 750 -> '12 menit 30 detik', 3725 -> '1 jam 2 menit 5 detik'.
    """
    if seconds is None:
        return "Tidak diketahui"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "Tidak diketahui"

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes} menit")
    parts.append(f"{secs} detik")

    return " ".join(parts)


def format_bytes(size) -> str:
    """Mengubah ukuran file (bytes) menjadi format yang mudah dibaca, misal '3.34 MB'."""
    if size is None:
        return "Tidak diketahui"
    try:
        size = float(size)
    except (TypeError, ValueError):
        return "Tidak diketahui"

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def sanitize_filename(filename: str) -> str:
    """
    Membersihkan nama file dari karakter yang tidak valid di Windows/Linux/macOS
    agar tidak terjadi error saat menyimpan file.
    """
    invalid_chars = r'<>:"/\|?*'
    for ch in invalid_chars:
        filename = filename.replace(ch, "_")
    return filename.strip() or "audio"


# ---------------------------------------------------------------------------
# PENGECEKAN SISTEM (FFmpeg & Koneksi Internet)
# ---------------------------------------------------------------------------
def check_ffmpeg_installed() -> bool:
    """Mengecek apakah FFmpeg terpasang dan dapat diakses melalui PATH."""
    if shutil.which("ffmpeg") is not None:
        return True
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def check_internet_connection(host="8.8.8.8", port=53, timeout=3) -> bool:
    """
    Mengecek koneksi internet dengan mencoba membuka socket ke DNS Google
    (8.8.8.8:53). Cepat dan tidak bergantung pada satu website tertentu.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# DIREKTORI & LOGGING
# ---------------------------------------------------------------------------
def ensure_directory(path) -> None:
    """Memastikan direktori tujuan ada; jika belum ada maka dibuat otomatis."""
    os.makedirs(path, exist_ok=True)


def setup_logger(name: str = "yt_mp3_downloader") -> logging.Logger:
    """
    Mengonfigurasi logger yang menulis riwayat & error ke file
    logs/app.log, sekaligus tetap menampilkan pesan penting ke console
    (level WARNING ke atas) tanpa mengganggu tampilan CLI utama.
    """
    ensure_directory(LOGS_DIR)
    logger = logging.getLogger(name)

    if logger.handlers:  # Hindari duplikasi handler jika dipanggil berulang
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)

    logger.addHandler(file_handler)
    return logger


def log_download_history(title: str, file_path: str, quality: str) -> None:
    """
    Menyimpan riwayat download yang berhasil ke file logs/history.log
    dalam format sederhana (satu baris per entri).
    """
    ensure_directory(LOGS_DIR)
    history_file = LOGS_DIR / "history.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {title} | {quality}kbps | {file_path}\n")


def read_urls_from_file(file_path: str) -> list:
    """
    Membaca daftar URL dari sebuah file .txt (satu URL per baris).
    Baris kosong dan baris yang diawali '#' (komentar) akan diabaikan.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls