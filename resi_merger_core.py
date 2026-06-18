# -*- coding: utf-8 -*-
"""
==============================================================================
 CORE — Resi Auto-Merger BigSeller (PT Heavy Object Group)
==============================================================================

Logika inti yang dipakai bersama oleh CLI (resi_merger.py) dan GUI
(resi_merger_gui.py). TIDAK ada I/O terminal di sini — semua pesan dikirim
lewat callback `on_log` agar bisa dipakai console maupun GUI.

PRIORITAS DESAIN NOMOR SATU — anti-tercampur batch lama:
  - Tool TIDAK PERNAH men-scan isi folder yang sudah ada.
  - Hanya bereaksi pada event download (on_created / on_moved) SETELAH sesi
    dimulai.
  - Resi yang selesai download LANGSUNG DIPINDAH (move, bukan copy) ke folder
    sesi bertimestamp yang terisolasi.

CATATAN: Untuk order SHOPEE, BigSeller sudah mendukung cross-logistics printing
(print dari tab "New Orders", sortir per shipping method via filter). Tool ini
terutama untuk kasus TikTok Shop yang tidak didukung.
==============================================================================
"""

import os
import time
import shutil
import threading
from datetime import datetime

from pypdf import PdfReader, PdfWriter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import config


def _noop_log(msg):
	pass


def _noop_collect(count, filename):
	pass


def is_resi_file(path):
	"""True kalau file ini PDF dan cocok dengan RESI_KEYWORDS."""
	name = os.path.basename(path).lower()
	# File download sementara browser — abaikan dulu, tunggu rename ke .pdf.
	if name.endswith((".crdownload", ".tmp", ".part")):
		return False
	if not name.endswith(".pdf"):
		return False
	if not config.RESI_KEYWORDS:
		# List kosong → anggap semua PDF sebagai resi.
		return True
	return any(kw.lower() in name for kw in config.RESI_KEYWORDS)


def wait_until_stable(path):
	"""
	Tunggu sampai ukuran file stabil (selesai ter-download).
	Return True kalau stabil, False kalau timeout / file hilang.
	"""
	deadline = time.time() + config.STABLE_TIMEOUT
	last_size = -1
	stable_count = 0
	while time.time() < deadline:
		try:
			size = os.path.getsize(path)
		except OSError:
			# File mungkin sedang di-rename (.crdownload → .pdf) atau hilang.
			return False
		if size > 0 and size == last_size:
			stable_count += 1
			if stable_count >= config.STABLE_CHECKS:
				return True
		else:
			stable_count = 0
			last_size = size
		time.sleep(config.STABLE_INTERVAL)
	return False


def ensure_folders():
	"""Pastikan semua folder kerja ada."""
	for folder in (
		config.WATCH_FOLDER,
		config.WORK_FOLDER,
		config.OUTPUT_FOLDER,
		config.ARCHIVE_FOLDER,
	):
		os.makedirs(folder, exist_ok=True)


class ResiSession:
	"""
	Mewakili satu sesi batch aktif. Menampung resi yang ter-download SELAMA
	sesi, memindahkannya ke folder sesi terisolasi, lalu menggabungkannya.
	"""

	def __init__(self, on_log=_noop_log, on_collect=_noop_collect):
		self.on_log = on_log
		self.on_collect = on_collect
		self.stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		self.session_dir = os.path.join(config.WORK_FOLDER, f"sesi_{self.stamp}")
		os.makedirs(self.session_dir, exist_ok=True)
		# Set path file yang SUDAH/SEDANG diproses — cegah dobel (created+moved).
		self._seen = set()
		self._lock = threading.Lock()
		self.collected = []  # daftar path file di folder sesi

	def claim(self, path):
		"""Tandai path agar tidak diproses dua kali. True kalau kita yang berhak."""
		key = os.path.normcase(os.path.abspath(path))
		with self._lock:
			if key in self._seen:
				return False
			self._seen.add(key)
			return True

	def add_file(self, src_path):
		"""
		Proses satu kandidat resi: tunggu stabil, pindah ke folder sesi.
		Dipanggil dari thread observer.
		"""
		if not is_resi_file(src_path):
			return
		if not self.claim(src_path):
			return
		if not os.path.exists(src_path):
			return

		if not wait_until_stable(src_path):
			self.on_log(f"⚠  Lewati '{os.path.basename(src_path)}' — download tidak selesai / file hilang.")
			return

		base = os.path.basename(src_path)
		dest = os.path.join(self.session_dir, base)
		if os.path.exists(dest):
			root, ext = os.path.splitext(base)
			dest = os.path.join(self.session_dir, f"{root}_{int(time.time()*1000)}{ext}")

		try:
			shutil.move(src_path, dest)
		except Exception as e:
			self.on_log(f"⚠  Gagal memindahkan '{base}': {e}")
			return

		with self._lock:
			self.collected.append(dest)
			count = len(self.collected)
		self.on_log(f"✓  Resi #{count} terkumpul: {os.path.basename(dest)}")
		self.on_collect(count, os.path.basename(dest))

	def count(self):
		with self._lock:
			return len(self.collected)

	def merge(self):
		"""
		Gabungkan semua resi di folder sesi (urut nama file) jadi satu PDF.
		Return path output, atau None kalau tidak ada resi yang berhasil.
		"""
		files = sorted(
			[f for f in self.collected if os.path.exists(f)],
			key=lambda p: os.path.basename(p).lower(),
		)
		if not files:
			self.on_log("Tidak ada resi yang terkumpul di sesi ini — tidak ada yang digabung.")
			return None

		os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
		out_name = f"RESI_GABUNGAN_{self.stamp}.pdf"
		out_path = os.path.join(config.OUTPUT_FOLDER, out_name)

		writer = PdfWriter()
		total_pages = 0
		merged_count = 0
		self.on_log("-" * 50)
		self.on_log("Mulai menggabungkan resi (urut nama file):")
		for f in files:
			name = os.path.basename(f)
			try:
				reader = PdfReader(f)
				n = len(reader.pages)
				if n == 0:
					self.on_log(f"   ⚠  {name} — 0 halaman, dilewati.")
					continue
				for page in reader.pages:
					writer.add_page(page)
				total_pages += n
				merged_count += 1
				self.on_log(f"   • {name} — {n} halaman")
			except Exception as e:
				self.on_log(f"   ⚠  {name} — tidak terbaca, dilewati ({e}).")

		if merged_count == 0:
			self.on_log("Semua file gagal dibaca — output tidak dibuat.")
			return None

		try:
			with open(out_path, "wb") as fh:
				writer.write(fh)
		except Exception as e:
			self.on_log(f"✗  Gagal menulis file gabungan: {e}")
			return None

		self.on_log("-" * 50)
		self.on_log(f"✓  SELESAI: {merged_count} resi → {total_pages} halaman.")
		self.on_log(f"   Output: {out_path}")
		return out_path

	def archive(self):
		"""Pindahkan resi mentah ke ARCHIVE_FOLDER (subfolder bertimestamp)."""
		remaining = [f for f in self.collected if os.path.exists(f)]
		if not remaining:
			self._cleanup_session_dir()
			return
		archive_dir = os.path.join(config.ARCHIVE_FOLDER, f"sesi_{self.stamp}")
		os.makedirs(archive_dir, exist_ok=True)
		moved = 0
		for f in remaining:
			try:
				shutil.move(f, os.path.join(archive_dir, os.path.basename(f)))
				moved += 1
			except Exception as e:
				self.on_log(f"⚠  Gagal mengarsipkan '{os.path.basename(f)}': {e}")
		self.on_log(f"📦  {moved} resi mentah diarsipkan ke: {archive_dir}")
		self._cleanup_session_dir()

	def _cleanup_session_dir(self):
		"""Hapus folder sesi sementara kalau sudah kosong."""
		try:
			if os.path.isdir(self.session_dir) and not os.listdir(self.session_dir):
				os.rmdir(self.session_dir)
		except Exception:
			pass


class _Handler(FileSystemEventHandler):
	"""Jembatan event watchdog → ResiSession.add_file (di thread observer)."""

	def __init__(self, session):
		super().__init__()
		self.session = session

	def on_created(self, event):
		if not event.is_directory:
			# Jalankan di thread terpisah agar wait_until_stable tidak memblok
			# event lain yang datang bersamaan.
			threading.Thread(
				target=self.session.add_file, args=(event.src_path,), daemon=True
			).start()

	def on_moved(self, event):
		# Chrome/Edge download dulu sbg .crdownload lalu RENAME ke .pdf → on_moved.
		if not event.is_directory:
			threading.Thread(
				target=self.session.add_file, args=(event.dest_path,), daemon=True
			).start()


class SessionController:
	"""
	Pengelola siklus hidup satu sesi — dipakai GUI maupun CLI:
	  start() → memantau folder; stop_and_merge() → gabung + arsip; cancel().
	"""

	def __init__(self, on_log=_noop_log, on_collect=_noop_collect):
		self.on_log = on_log
		self.on_collect = on_collect
		self.session = None
		self.observer = None

	def start(self):
		ensure_folders()
		self.session = ResiSession(self.on_log, self.on_collect)
		handler = _Handler(self.session)
		self.observer = Observer()
		self.observer.schedule(handler, config.WATCH_FOLDER, recursive=False)
		self.observer.start()
		return self.session.session_dir

	def _stop_observer(self):
		if self.observer is not None:
			self.observer.stop()
			self.observer.join()
			self.observer = None

	def stop_and_merge(self):
		"""Tutup pemantauan, gabungkan, arsipkan. Return path output / None."""
		self._stop_observer()
		# Beri jeda agar file yang masih dalam proses stabilisasi selesai.
		time.sleep(config.STABLE_INTERVAL * config.STABLE_CHECKS + 0.5)
		merged_path = self.session.merge()
		self.session.archive()
		return merged_path

	def cancel(self):
		"""Batalkan sesi tanpa merge. Resi tetap tersimpan di folder sesi."""
		self._stop_observer()
		return self.session.session_dir if self.session else None

	def count(self):
		return self.session.count() if self.session else 0
