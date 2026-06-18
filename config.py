# -*- coding: utf-8 -*-
"""
==============================================================================
 KONFIGURASI — Resi Auto-Merger BigSeller
==============================================================================
File ini AMAN diedit untuk lingkungan Anda. Updater TIDAK akan menimpa file
ini, jadi pengaturan Anda tetap aman saat aplikasi di-update.
==============================================================================
"""

from pathlib import Path

# Folder yang dipantau untuk download resi baru.
# Default folder Downloads. IDEALNYA diarahkan ke folder download khusus
# browser kerja (mis. r"D:\RESI_BIGSELLER") untuk kebersihan maksimal — tapi
# TIDAK WAJIB, karena desain sesi sudah mengisolasi tiap batch.
WATCH_FOLDER = str(Path.home() / "Downloads")

# Folder kerja terisolasi: tempat resi DIPINDAH saat sesi berjalan.
WORK_FOLDER = str(Path.home() / "Downloads" / "RESI_PROSES")

# Tujuan file gabungan final.
# Bisa diarahkan ke folder Google Drive Stream (mis.
# r"G:\My Drive\RESI_MERGED") agar otomatis ter-sync ke sistem.
OUTPUT_FOLDER = str(Path.home() / "Downloads" / "RESI_MERGED")

# Arsip resi mentah per-ekspedisi setelah digabung (untuk jejak audit / bukti).
ARCHIVE_FOLDER = str(Path.home() / "Downloads" / "RESI_ARSIP")

# Kata kunci nama file untuk mengenali resi (case-insensitive).
# Kalau list ini DIKOSONGKAN ([]), SEMUA file PDF dianggap resi.
RESI_KEYWORDS = [
	"shippinglabel",
	"shipping_label",
	"waybill",
	"awb",
	"resi",
	"label",
]

# --- Parameter teknis (jarang perlu diubah) --------------------------------

# Berapa kali ukuran file harus terbaca SAMA berturut-turut sebelum dianggap
# selesai ter-download (mencegah memproses file yang masih separuh).
STABLE_CHECKS = 3
# Jeda antar pengecekan ukuran file (detik).
STABLE_INTERVAL = 0.6
# Batas maksimum menunggu file stabil (detik) — kalau lewat, file dilewati.
STABLE_TIMEOUT = 30.0

# --- Updater ---------------------------------------------------------------

# Repo GitHub sumber update (branch main).
GITHUB_OWNER = "dennypa77"
GITHUB_REPO = "resi-merger-bigseller"
GITHUB_BRANCH = "main"
