"""
main.py
-------
Entry point aplikasi YouTube MP3 Downloader (versi CLI).

Jalankan dengan:
    python main.py
    python main.py --file daftar_url.txt
    python main.py --quality 192 --output D:/Musik

Argumen CLI bersifat opsional; jika dijalankan tanpa argumen, program
akan berjalan secara interaktif sesuai skenario pada README.md.
"""

import sys
import argparse
from pathlib import Path

from downloader import (
    YouTubeDownloader,
    InvalidURLError,
    VideoUnavailableError,
    NoInternetError,
    FFmpegNotFoundError,
    DownloadError,
)
from utils import (
    is_valid_youtube_url,
    is_playlist_url,
    format_duration,
    format_bytes,
    check_internet_connection,
    ensure_directory,
    setup_logger,
    log_download_history,
    read_urls_from_file,
    DOWNLOADS_DIR,
)

logger = setup_logger()

BANNER = r"""
=====================================
      YouTube MP3 Downloader
=====================================
"""

VALID_QUALITIES = ["128", "192", "256", "320"]


# ---------------------------------------------------------------------------
# FUNGSI TAMPILAN (CLI OUTPUT)
# ---------------------------------------------------------------------------
def print_banner():
    print(BANNER)


def print_video_info(info: dict):
    """Menampilkan informasi video sebelum konfirmasi download."""
    print("\n-------------------------------------")
    print(f"Judul     : {info.get('title')}")
    print(f"Channel   : {info.get('channel')}")
    print(f"Durasi    : {format_duration(info.get('duration'))}")
    print(f"Ukuran    : {format_bytes(info.get('filesize_approx'))} (estimasi)")
    if info.get("abr"):
        print(f"Bitrate   : {info.get('abr')} kbps (sumber asli)")
    if info.get("thumbnail"):
        print(f"Thumbnail : {info.get('thumbnail')}")
    print("-------------------------------------\n")


def print_success(filename: str, output_folder: str):
    print("\n=====================================")
    print("Download Berhasil")
    print("=====================================\n")
    print(f"Nama File :\n{filename}\n")
    print(f"Disimpan pada:\n{output_folder}\n")
    print("Terima kasih telah menggunakan program ini.")


def ask_yes_no(question: str, default: str = "Y") -> bool:
    """Menampilkan prompt Y/N dan mengembalikan True/False."""
    suffix = "(Y/N)" if default.upper() == "Y" else "(y/N)"
    answer = input(f"{question} {suffix}: ").strip().lower()
    if not answer:
        return default.upper() == "Y"
    return answer in ("y", "yes", "ya")


def ask_quality(default_quality: str) -> str:
    """Meminta pengguna memilih kualitas audio (bonus fitur)."""
    print(f"Pilihan kualitas audio: {', '.join(VALID_QUALITIES)} kbps")
    answer = input(f"Kualitas audio [{default_quality}]: ").strip()
    if not answer:
        return default_quality
    if answer in VALID_QUALITIES:
        return answer
    print(f"Kualitas tidak dikenali, menggunakan default {default_quality} kbps.")
    return default_quality


def ask_custom_filename() -> str:
    """Meminta pengguna mengganti nama file sebelum disimpan (bonus fitur)."""
    answer = input("Ubah nama file sebelum disimpan? (kosongkan jika tidak): ").strip()
    return answer or None


# ---------------------------------------------------------------------------
# LOGIKA UTAMA UNTUK MEMPROSES SATU URL
# ---------------------------------------------------------------------------
def process_single_url(downloader: YouTubeDownloader, url: str, output_folder: str, default_quality: str):
    """
    Memproses satu URL YouTube: validasi -> ambil info -> konfirmasi ->
    download -> tampilkan hasil. Mengembalikan True jika berhasil.
    """
    # 1. Validasi URL kosong
    if not url:
        print("URL tidak boleh kosong. Silakan coba lagi.\n")
        return False

    # 2. Validasi format URL YouTube
    if not is_valid_youtube_url(url):
        print("URL yang dimasukkan bukan URL YouTube yang valid.\n")
        return False

    # 3. Validasi koneksi internet sebelum mengambil info
    if not check_internet_connection():
        raise NoInternetError("Tidak ada koneksi internet. Periksa jaringan Anda dan coba lagi.")

    print("Mengambil informasi video, mohon tunggu...")
    info = downloader.get_video_info(url)

    # 4. Jika URL adalah playlist
    if info.get("is_playlist"):
        return process_playlist(downloader, info, output_folder, default_quality)

    # 5. Tampilkan info & minta konfirmasi
    print_video_info(info)
    if not ask_yes_no("Lanjut download?"):
        print("Download dibatalkan oleh pengguna.\n")
        return False

    # 6. Pilihan kualitas & nama file (bonus fitur)
    quality = ask_quality(default_quality)
    custom_filename = ask_custom_filename()

    print("\nMemulai download...")
    output_path = downloader.download_audio(
        url=url,
        output_folder=output_folder,
        quality=quality,
        custom_filename=custom_filename,
    )

    log_download_history(info.get("title"), output_path, quality)
    print_success(Path(output_path).name, output_folder)
    return True


def process_playlist(downloader: YouTubeDownloader, info: dict, output_folder: str, default_quality: str):
    """Menangani skenario ketika URL yang dimasukkan adalah sebuah playlist."""
    print("\n-------------------------------------")
    print(f"Playlist terdeteksi : {info.get('playlist_title')}")
    print(f"Jumlah video        : {info.get('entries_count')}")
    print("-------------------------------------\n")

    if not ask_yes_no("Unduh seluruh video dalam playlist ini?"):
        print("Download playlist dibatalkan oleh pengguna.\n")
        return False

    quality = ask_quality(default_quality)
    print("\nMemulai download playlist...")

    results = downloader.download_playlist(info.get("entries"), output_folder, quality)

    print("\n=====================================")
    print(f"Playlist selesai: {len(results)}/{info.get('entries_count')} video berhasil diunduh")
    print("=====================================")
    for path in results:
        log_download_history(Path(path).stem, path, quality)
    print(f"\nDisimpan pada:\n{output_folder}\n")
    print("Terima kasih telah menggunakan program ini.")
    return True


# ---------------------------------------------------------------------------
# MODE BATCH: MEMBACA BANYAK URL DARI FILE .txt
# ---------------------------------------------------------------------------
def process_batch_file(downloader: YouTubeDownloader, file_path: str, output_folder: str, default_quality: str):
    """Memproses banyak URL sekaligus yang dibaca dari sebuah file .txt."""
    try:
        urls = read_urls_from_file(file_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if not urls:
        print("File tidak berisi URL yang valid.")
        return

    print(f"Ditemukan {len(urls)} URL pada file '{file_path}'.")
    if not ask_yes_no(f"Lanjutkan mengunduh {len(urls)} URL dengan kualitas {default_quality} kbps?"):
        print("Proses batch dibatalkan.\n")
        return

    success_count = 0
    for index, url in enumerate(urls, start=1):
        print(f"\n[{index}/{len(urls)}] Memproses: {url}")
        try:
            if not is_valid_youtube_url(url):
                print("  -> Dilewati: URL tidak valid.")
                continue

            info = downloader.get_video_info(url)
            if info.get("is_playlist"):
                print("  -> Playlist terdeteksi, mengunduh seluruh video...")
                results = downloader.download_playlist(info.get("entries"), output_folder, default_quality)
                success_count += len(results)
                for path in results:
                    log_download_history(Path(path).stem, path, default_quality)
                continue

            output_path = downloader.download_audio(url, output_folder, default_quality)
            log_download_history(info.get("title"), output_path, default_quality)
            print(f"  -> Berhasil: {Path(output_path).name}")
            success_count += 1

        except (VideoUnavailableError, NoInternetError, DownloadError) as e:
            print(f"  -> Gagal: {e}")
            logger.warning(f"Gagal mengunduh {url}: {e}")
            continue

    print("\n=====================================")
    print(f"Batch selesai: {success_count}/{len(urls)} berhasil diunduh")
    print(f"Disimpan pada: {output_folder}")
    print("=====================================")
    print("Terima kasih telah menggunakan program ini.")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(description="YouTube to MP3 Downloader (CLI)")
    parser.add_argument("--file", "-f", help="Path file .txt berisi daftar URL YouTube")
    parser.add_argument(
        "--quality", "-q", default="320", choices=VALID_QUALITIES,
        help="Kualitas audio default dalam kbps (default: 320)"
    )
    parser.add_argument(
        "--output", "-o", default=str(DOWNLOADS_DIR),
        help="Folder tujuan penyimpanan file MP3 (default: downloads/)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    ensure_directory(args.output)

    print_banner()

    try:
        downloader = YouTubeDownloader()
    except FFmpegNotFoundError as e:
        print(f"Error: {e}")
        logger.error(str(e))
        sys.exit(1)

    try:
        if args.file:
            process_batch_file(downloader, args.file, args.output, args.quality)
            return

        # Mode interaktif (default): terus meminta URL sampai user berhenti (Ctrl+C)
        while True:
            url = input("Masukkan URL YouTube: ").strip()

            try:
                process_single_url(downloader, url, args.output, args.quality)
            except VideoUnavailableError as e:
                print(f"Error: {e}\n")
                logger.warning(str(e))
            except NoInternetError as e:
                print(f"Error: {e}\n")
                logger.error(str(e))
            except DownloadError as e:
                print(f"Error: {e}\n")
                logger.error(str(e))
            except InvalidURLError as e:
                print(f"Error: {e}\n")

            if not ask_yes_no("\nUnduh video lain?"):
                print("\nTerima kasih telah menggunakan program ini. Sampai jumpa!")
                break

    except KeyboardInterrupt:
        print("\n\nProgram dihentikan oleh pengguna (Ctrl+C). Sampai jumpa!")
        sys.exit(0)


if __name__ == "__main__":
    main()