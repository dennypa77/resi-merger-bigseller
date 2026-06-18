#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 RESI AUTO-MERGER untuk BigSeller — PT Heavy Object Group (Stickitup & Ganci)
 Versi CONSOLE (tanpa GUI). Untuk versi GUI, jalankan: python resi_merger_gui.py
==============================================================================

Folder watcher lokal berbasis SESI BATCH MANUAL untuk menggabungkan resi PDF
yang di-download terpisah per ekspedisi dari BigSeller menjadi SATU PDF.

KENAPA ada tool ini:
  BigSeller TIDAK mendukung cross-logistics printing kecuali untuk Shopee.
  Untuk order TikTok Shop, operator harus download resi terpisah per ekspedisi
  lalu merge manual. Tool ini mengotomasi penggabungan tsb.

  CATATAN: Untuk order SHOPEE, BigSeller SUDAH mendukung cross-logistics
  printing (print dari tab "New Orders", sortir per shipping method via filter).
  Jadi tool ini terutama untuk kasus TikTok Shop.

ALUR: ENTER untuk MULAI SESI → download resi → ENTER lagi untuk TUTUP & MERGE.
Konfigurasi ada di config.py.
==============================================================================
"""

import sys

# Pastikan console bisa menampilkan karakter Unicode (✓, →, emoji) tanpa crash
# di Windows (cp1252). start.bat juga sudah set chcp 65001.
try:
	sys.stdout.reconfigure(encoding="utf-8", errors="replace")
	sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
	pass

# --- Cek dependency lebih awal --------------------------------------------
_MISSING = []
try:
	import pypdf  # noqa: F401
except ImportError:
	_MISSING.append("pypdf")
try:
	import watchdog  # noqa: F401
except ImportError:
	_MISSING.append("watchdog")

if _MISSING:
	print("\n" + "=" * 70)
	print(" MODUL PYTHON BELUM TERPASANG: " + ", ".join(_MISSING))
	print("=" * 70)
	print("\n Jalankan perintah berikut lalu buka ulang script ini:\n")
	print("     pip install pypdf watchdog\n")
	print(" (kalau 'pip' tidak dikenali: python -m pip install pypdf watchdog)\n")
	sys.exit(1)

from datetime import datetime

import config
from resi_merger_core import SessionController, ensure_folders
from version import __version__


def log(msg):
	"""Cetak pesan ke console dengan timestamp."""
	stamp = datetime.now().strftime("%H:%M:%S")
	print(f"[{stamp}] {msg}", flush=True)


def print_banner():
	print()
	print("=" * 70)
	print(f"   RESI AUTO-MERGER — BigSeller  |  PT Heavy Object Group  (v{__version__})")
	print("=" * 70)
	print(f"   Pantau   : {config.WATCH_FOLDER}")
	print(f"   Kerja    : {config.WORK_FOLDER}")
	print(f"   Output   : {config.OUTPUT_FOLDER}")
	print(f"   Arsip    : {config.ARCHIVE_FOLDER}")
	if config.RESI_KEYWORDS:
		print(f"   Kata kunci resi : {', '.join(config.RESI_KEYWORDS)}")
	else:
		print("   Kata kunci resi : (kosong → SEMUA PDF dianggap resi)")
	print("=" * 70)
	print()
	print("   Hanya resi yang DI-DOWNLOAD SETELAH sesi dimulai yang akan diproses.")
	print("   File lama di folder Downloads diabaikan total — aman dari tercampur.")
	print()


def _ask_interrupt_choice(count):
	"""Tanya operator saat Ctrl+C di tengah sesi. Return 'merge' atau 'batal'."""
	print(f"   Saat ini ada {count} resi terkumpul di sesi ini.")
	print("   Pilih:")
	print("     [G] Gabungkan resi yang sudah terkumpul sekarang")
	print("     [B] Batalkan sesi (resi tetap disimpan di folder sesi)")
	while True:
		try:
			ans = input("   Pilihan (G/B): ").strip().lower()
		except (KeyboardInterrupt, EOFError):
			return "batal"
		if ans in ("g", "gabung", "merge", "y"):
			return "merge"
		if ans in ("b", "batal", "cancel", "n"):
			return "batal"
		print("   Jawaban tidak dikenali. Ketik G atau B.")


def run_session():
	"""Jalankan satu sesi penuh: mulai → pantau → tutup → merge → arsip."""
	ctrl = SessionController(on_log=log)
	session_dir = ctrl.start()

	log("=" * 60)
	log("🟢 SESI DIMULAI — memantau: " + config.WATCH_FOLDER)
	log(f"   Folder sesi: {session_dir}")
	log("=" * 60)
	print()
	print("   Silakan download semua resi dari BigSeller sekarang.")
	print("   >>> Tekan ENTER lagi kalau SELESAI untuk TUTUP SESI & MERGE.")
	print()

	try:
		input()
	except KeyboardInterrupt:
		print()
		log("⏸  Ctrl+C terdeteksi di tengah sesi.")
		if _ask_interrupt_choice(ctrl.count()) == "batal":
			path = ctrl.cancel()
			log("✗  Sesi DIBATALKAN. Resi yang sudah terkumpul tetap ada di:")
			log(f"   {path}")
			return

	log("=" * 60)
	log(f"🔴 SESI DITUTUP — total {ctrl.count()} resi terkumpul.")
	log("=" * 60)
	ctrl.stop_and_merge()


def main():
	ensure_folders()
	print_banner()
	while True:
		try:
			print("-" * 70)
			ans = input("  Tekan ENTER untuk MULAI SESI baru  (ketik 'q' + ENTER untuk keluar): ")
		except (KeyboardInterrupt, EOFError):
			print()
			log("Keluar. Sampai jumpa.")
			break

		if ans.strip().lower() in ("q", "quit", "exit", "keluar"):
			log("Keluar. Sampai jumpa.")
			break

		try:
			run_session()
		except Exception as e:
			log(f"✗  Terjadi error pada sesi: {e}")
			log("   Kembali ke menu utama.")

		print()
		print("   ✅ Sesi selesai. Siap untuk batch berikutnya.")
		print()


if __name__ == "__main__":
	main()
