"""
downloader.py
--------------
Berisi seluruh logika pengunduhan & konversi audio dari YouTube untuk
versi CLI. Dipisahkan dari main.py agar logika download mudah diuji,
dipelihara, dan dikembangkan tanpa mengubah tampilan CLI.
"""

import os
import socket
from pathlib import Path

import yt_dlp
from tqdm import tqdm

from utils import sanitize_filename, ensure_directory, check_ffmpeg_installed


# ---------------------------------------------------------------------------
# CUSTOM EXCEPTIONS
# Dibuat khusus agar main.py dapat menampilkan pesan error yang informatif
# sesuai jenis masalah yang terjadi (bukan hanya "Exception" generik).
# ---------------------------------------------------------------------------
class InvalidURLError(Exception):
    """URL kosong atau bukan URL YouTube yang valid."""
    pass


class VideoUnavailableError(Exception):
    """Video tidak tersedia (private, dihapus, region-locked, dll)."""
    pass


class NoInternetError(Exception):
    """Tidak ada koneksi internet saat mencoba mengambil data/mengunduh."""
    pass


class FFmpegNotFoundError(Exception):
    """FFmpeg belum terpasang / tidak terdeteksi di PATH sistem."""
    pass


class DownloadError(Exception):
    """Kegagalan umum saat proses download atau konversi berlangsung."""
    pass


class ProgressPrinter:
    """
    Kelas kecil untuk mengelola progress bar (tqdm) selama proses download.
    Dipisahkan agar downloader.py tetap bersih dan progress bar bisa
    di-reset setiap kali file baru mulai diunduh (berguna untuk playlist
    / download banyak URL sekaligus).
    """

    def __init__(self):
        self.bar = None

    def hook(self, d: dict) -> None:
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)

            if self.bar is None and total:
                self.bar = tqdm(
                    total=total, unit="B", unit_scale=True,
                    desc="Downloading", ncols=80
                )

            if self.bar is not None:
                self.bar.n = downloaded
                self.bar.refresh()

        elif status == "finished":
            if self.bar is not None:
                self.bar.n = self.bar.total
                self.bar.refresh()
                self.bar.close()
                self.bar = None
            print("Converting ke MP3...")

    def close(self):
        if self.bar is not None:
            self.bar.close()
            self.bar = None


class YouTubeDownloader:
    """
    Class utama untuk menangani:
    1. Pengambilan informasi video (judul, channel, durasi, thumbnail,
       estimasi ukuran, bitrate yang tersedia).
    2. Pengunduhan audio terbaik & konversi ke MP3 dengan kualitas pilihan.
    3. Pengunduhan seluruh video dalam sebuah playlist.
    """

    def __init__(self):
        if not check_ffmpeg_installed():
            raise FFmpegNotFoundError(
                "FFmpeg belum terpasang atau tidak terdeteksi di PATH sistem.\n"
                "Silakan install FFmpeg terlebih dahulu (lihat README.md)."
            )

    # ------------------------------------------------------------------
    # AMBIL INFORMASI VIDEO (tanpa mengunduh)
    # ------------------------------------------------------------------
    def get_video_info(self, url: str) -> dict:
        """
        Mengambil metadata video: judul, channel, durasi, thumbnail,
        estimasi ukuran file, dan bitrate audio terbaik yang tersedia.
        Melempar VideoUnavailableError / NoInternetError jika bermasalah.
        """
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except socket.gaierror:
            raise NoInternetError("Tidak dapat terhubung ke internet. Periksa koneksi Anda.")
        except yt_dlp.utils.DownloadError as e:
            message = str(e).lower()
            if "private" in message:
                raise VideoUnavailableError("Video ini bersifat private dan tidak dapat diakses.")
            if "unavailable" in message or "removed" in message or "not exist" in message:
                raise VideoUnavailableError("Video tidak tersedia atau telah dihapus.")
            if "network" in message or "resolve" in message or "getaddrinfo" in message:
                raise NoInternetError("Tidak dapat terhubung ke internet. Periksa koneksi Anda.")
            raise VideoUnavailableError(f"Video tidak dapat diakses: {e}")

        # Jika ini adalah playlist, info akan memiliki key 'entries'
        if info.get("_type") == "playlist" or "entries" in info:
            entries = [e for e in info.get("entries", []) if e is not None]
            return {
                "is_playlist": True,
                "playlist_title": info.get("title", "Playlist Tanpa Nama"),
                "entries_count": len(entries),
                "entries": entries,
            }

        # Cari estimasi ukuran & bitrate dari format audio terbaik
        filesize_approx = None
        abr = None
        for fmt in info.get("formats", []):
            if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                filesize_approx = fmt.get("filesize") or fmt.get("filesize_approx")
                abr = fmt.get("abr")
                if filesize_approx:
                    break

        return {
            "is_playlist": False,
            "title": info.get("title", "Tidak diketahui"),
            "channel": info.get("uploader", "Tidak diketahui"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "filesize_approx": filesize_approx,
            "abr": abr,
        }

    # ------------------------------------------------------------------
    # UNDUH & KONVERSI SATU VIDEO KE MP3
    # ------------------------------------------------------------------
    def download_audio(
        self,
        url: str,
        output_folder: str,
        quality: str = "320",
        custom_filename: str = None,
    ) -> str:
        """
        Mengunduh audio terbaik dari sebuah video YouTube lalu
        mengonversinya menjadi MP3 dengan bitrate sesuai `quality`.

        Returns
        -------
        str: path lengkap file MP3 hasil unduhan.
        """
        ensure_directory(output_folder)

        if custom_filename:
            safe_name = sanitize_filename(custom_filename)
            output_template = os.path.join(output_folder, f"{safe_name}.%(ext)s")
        else:
            output_template = os.path.join(output_folder, "%(title)s.%(ext)s")

        progress = ProgressPrinter()

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress.hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base_filename = ydl.prepare_filename(info)
                mp3_filename = os.path.splitext(base_filename)[0] + ".mp3"
            return mp3_filename

        except socket.gaierror:
            raise NoInternetError("Koneksi internet terputus saat proses download.")
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"Gagal mengunduh video: {e}")
        finally:
            progress.close()

    # ------------------------------------------------------------------
    # UNDUH SELURUH VIDEO DALAM PLAYLIST
    # ------------------------------------------------------------------
    def download_playlist(
        self,
        entries: list,
        output_folder: str,
        quality: str = "320",
    ) -> list:
        """
        Mengunduh setiap video dalam sebuah playlist satu per satu.
        Mengembalikan list path file MP3 yang berhasil diunduh.
        Video yang gagal diunduh akan dilewati (skip) tanpa menghentikan
        keseluruhan proses playlist.
        """
        results = []
        total = len(entries)

        for index, entry in enumerate(entries, start=1):
            video_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
            title = entry.get("title", f"Video {index}")

            print(f"\n[{index}/{total}] Mengunduh: {title}")
            try:
                path = self.download_audio(video_url, output_folder, quality)
                results.append(path)
                print(f"[{index}/{total}] Berhasil: {os.path.basename(path)}")
            except Exception as e:
                print(f"[{index}/{total}] Gagal mengunduh '{title}': {e}")
                continue

        return results