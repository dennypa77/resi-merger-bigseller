#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 RESI AUTO-MERGER untuk BigSeller — GUI  (PT Heavy Object Group)
==============================================================================

Versi antarmuka grafis (Tkinter) dari resi_merger. Operator cukup klik:
  [MULAI SESI] → download resi dari BigSeller → [TUTUP SESI & MERGE].
Progress & hasil tampil real-time. Ada tombol untuk membuka folder/hasil
output, dan tombol "Cek Update" untuk update dari GitHub.

Konfigurasi ada di config.py. Anti-tercampur batch lama: lihat resi_merger_core.py.
==============================================================================
"""

import sys

# --- Cek dependency lebih awal (tampilkan dialog kalau Tkinter ada) --------
_MISSING = []
try:
	import pypdf  # noqa: F401
except ImportError:
	_MISSING.append("pypdf")
try:
	import watchdog  # noqa: F401
except ImportError:
	_MISSING.append("watchdog")

try:
	import tkinter as tk
	from tkinter import ttk, messagebox, scrolledtext
except ImportError:
	print("Tkinter tidak tersedia di instalasi Python ini.")
	print("Pakai versi console saja: python resi_merger.py")
	sys.exit(1)

if _MISSING:
	# Tkinter ada, tampilkan pesan lewat dialog supaya operator tahu.
	_r = tk.Tk()
	_r.withdraw()
	messagebox.showerror(
		"Dependency belum terpasang",
		"Modul belum terpasang: " + ", ".join(_MISSING) + "\n\n"
		"Jalankan perintah ini lalu buka ulang:\n\n"
		"    pip install pypdf watchdog",
	)
	sys.exit(1)

import os
import queue
import threading
from datetime import datetime

import config
from resi_merger_core import SessionController, ensure_folders
from version import __version__
import updater


def open_path(path):
	"""Buka file/folder di file explorer OS. Aman lintas platform."""
	try:
		if not os.path.exists(path):
			return False
		if sys.platform.startswith("win"):
			os.startfile(path)  # noqa: S606 (Windows-only, sengaja)
		elif sys.platform == "darwin":
			import subprocess
			subprocess.Popen(["open", path])
		else:
			import subprocess
			subprocess.Popen(["xdg-open", path])
		return True
	except Exception:
		return False


class ResiMergerApp:
	def __init__(self, root):
		self.root = root
		self.ctrl = None
		self.active = False
		self.collected = 0
		self.last_output = None
		self.log_queue = queue.Queue()

		ensure_folders()
		self._build_ui()
		self._poll_queue()
		self._log_intro()

	# ---------------------------------------------------------------- UI ---
	def _build_ui(self):
		self.root.title(f"Resi Auto-Merger — BigSeller  (v{__version__})")
		self.root.geometry("760x560")
		self.root.minsize(680, 480)

		# Header
		header = tk.Frame(self.root, bg="#1f2937", height=64)
		header.pack(fill="x")
		header.pack_propagate(False)
		tk.Label(
			header, text="RESI AUTO-MERGER  •  BigSeller", bg="#1f2937", fg="white",
			font=("Segoe UI", 14, "bold"),
		).pack(side="left", padx=16)
		tk.Label(
			header, text="PT Heavy Object Group", bg="#1f2937", fg="#9ca3af",
			font=("Segoe UI", 10),
		).pack(side="right", padx=16)

		# Status bar
		status_row = tk.Frame(self.root)
		status_row.pack(fill="x", padx=16, pady=(12, 4))
		self.status_dot = tk.Label(status_row, text="●", fg="#9ca3af", font=("Segoe UI", 14))
		self.status_dot.pack(side="left")
		self.status_label = tk.Label(status_row, text="Idle — belum ada sesi", font=("Segoe UI", 11, "bold"))
		self.status_label.pack(side="left", padx=(4, 0))
		self.counter_label = tk.Label(status_row, text="Resi terkumpul: 0", font=("Segoe UI", 11), fg="#374151")
		self.counter_label.pack(side="right")

		# Action buttons
		btn_row = tk.Frame(self.root)
		btn_row.pack(fill="x", padx=16, pady=6)
		self.btn_start = tk.Button(
			btn_row, text="▶  MULAI SESI", font=("Segoe UI", 11, "bold"),
			bg="#16a34a", fg="white", activebackground="#15803d", relief="flat",
			padx=16, pady=10, cursor="hand2", command=self.on_start,
		)
		self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 6))
		self.btn_stop = tk.Button(
			btn_row, text="■  TUTUP SESI & MERGE", font=("Segoe UI", 11, "bold"),
			bg="#dc2626", fg="white", activebackground="#b91c1c", relief="flat",
			padx=16, pady=10, cursor="hand2", command=self.on_stop, state="disabled",
		)
		self.btn_stop.pack(side="left", expand=True, fill="x", padx=(6, 0))

		# Log area
		log_frame = tk.LabelFrame(self.root, text=" Progress ", font=("Segoe UI", 9, "bold"))
		log_frame.pack(fill="both", expand=True, padx=16, pady=(8, 4))
		self.log = scrolledtext.ScrolledText(
			log_frame, wrap="word", font=("Consolas", 9), bg="#0f172a", fg="#e2e8f0",
			insertbackground="white", state="disabled",
		)
		self.log.pack(fill="both", expand=True, padx=4, pady=4)

		# Bottom buttons
		bottom = tk.Frame(self.root)
		bottom.pack(fill="x", padx=16, pady=(4, 12))
		tk.Button(
			bottom, text="📂  Buka Folder Output", relief="flat", bg="#e5e7eb",
			cursor="hand2", padx=10, pady=6, command=self.open_output_folder,
		).pack(side="left")
		self.btn_open_result = tk.Button(
			bottom, text="📄  Buka Hasil Terakhir", relief="flat", bg="#e5e7eb",
			cursor="hand2", padx=10, pady=6, command=self.open_last_result, state="disabled",
		)
		self.btn_open_result.pack(side="left", padx=8)
		tk.Button(
			bottom, text="⬆  Cek Update", relief="flat", bg="#dbeafe",
			cursor="hand2", padx=10, pady=6, command=self.on_check_update,
		).pack(side="right")

		self.root.protocol("WM_DELETE_WINDOW", self.on_close)

	# ------------------------------------------------------------- logging --
	def log_msg(self, msg):
		"""Thread-safe: taruh pesan di queue, GUI thread yang menulis."""
		self.log_queue.put(msg)

	def _poll_queue(self):
		try:
			while True:
				msg = self.log_queue.get_nowait()
				self._write_log(msg)
		except queue.Empty:
			pass
		self.root.after(120, self._poll_queue)

	def _write_log(self, msg):
		stamp = datetime.now().strftime("%H:%M:%S")
		self.log.configure(state="normal")
		self.log.insert("end", f"[{stamp}] {msg}\n")
		self.log.see("end")
		self.log.configure(state="disabled")

	def _log_intro(self):
		self.log_msg("Siap. Klik MULAI SESI sebelum mendownload resi dari BigSeller.")
		self.log_msg(f"Pantau : {config.WATCH_FOLDER}")
		self.log_msg(f"Output : {config.OUTPUT_FOLDER}")
		if config.RESI_KEYWORDS:
			self.log_msg("Kata kunci resi: " + ", ".join(config.RESI_KEYWORDS))
		else:
			self.log_msg("Kata kunci resi: (kosong → semua PDF dianggap resi)")
		self.log_msg("Hanya resi yang di-download SETELAH sesi dimulai yang diproses — aman dari batch lama.")

	# -------------------------------------------------- collect callback ----
	def on_collect(self, count, filename):
		# Dipanggil dari thread observer → marshal ke GUI lewat after().
		self.collected = count
		self.root.after(0, lambda: self.counter_label.configure(text=f"Resi terkumpul: {count}"))

	# ------------------------------------------------------------- actions --
	def on_start(self):
		if self.active:
			return
		self.ctrl = SessionController(on_log=self.log_msg, on_collect=self.on_collect)
		try:
			session_dir = self.ctrl.start()
		except Exception as e:
			messagebox.showerror("Gagal memulai sesi", str(e))
			return
		self.active = True
		self.collected = 0
		self.counter_label.configure(text="Resi terkumpul: 0")
		self.status_dot.configure(fg="#16a34a")
		self.status_label.configure(text="SESI AKTIF — sedang memantau folder")
		self.btn_start.configure(state="disabled")
		self.btn_stop.configure(state="normal")
		self.log_msg("=" * 50)
		self.log_msg("🟢 SESI DIMULAI — silakan download semua resi dari BigSeller.")
		self.log_msg(f"   Folder sesi: {session_dir}")

	def on_stop(self):
		if not self.active or self.ctrl is None:
			return
		# Disable tombol selama proses merge (jalan di worker thread).
		self.btn_stop.configure(state="disabled")
		self.status_dot.configure(fg="#f59e0b")
		self.status_label.configure(text="Menggabungkan resi...")
		self.log_msg("=" * 50)
		self.log_msg(f"🔴 SESI DITUTUP — total {self.ctrl.count()} resi. Menggabungkan...")

		def worker():
			try:
				path = self.ctrl.stop_and_merge()
			except Exception as e:
				self.log_msg(f"✗  Error saat merge: {e}")
				path = None
			self.root.after(0, lambda: self._after_merge(path))

		threading.Thread(target=worker, daemon=True).start()

	def _after_merge(self, path):
		self.active = False
		self.ctrl = None
		self.status_dot.configure(fg="#9ca3af")
		self.status_label.configure(text="Idle — sesi selesai, siap batch berikutnya")
		self.btn_start.configure(state="normal")
		self.btn_stop.configure(state="disabled")
		if path:
			self.last_output = path
			self.btn_open_result.configure(state="normal")
			self.log_msg("✅ Selesai. Klik 'Buka Hasil Terakhir' untuk melihat PDF gabungan.")
			if messagebox.askyesno("Merge selesai", f"Resi berhasil digabung:\n\n{os.path.basename(path)}\n\nBuka file sekarang?"):
				open_path(path)
		else:
			self.log_msg("⚠  Tidak ada file gabungan yang dihasilkan.")

	def open_output_folder(self):
		os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
		if not open_path(config.OUTPUT_FOLDER):
			messagebox.showwarning("Tidak bisa membuka", f"Gagal membuka:\n{config.OUTPUT_FOLDER}")

	def open_last_result(self):
		if self.last_output and os.path.exists(self.last_output):
			open_path(self.last_output)
		else:
			messagebox.showinfo("Belum ada hasil", "Belum ada file gabungan dari sesi ini.")

	# -------------------------------------------------------------- update --
	def on_check_update(self):
		self.log_msg("Mengecek update dari GitHub...")

		def worker():
			info = updater.check_for_update()
			self.root.after(0, lambda: self._after_check_update(info))

		threading.Thread(target=worker, daemon=True).start()

	def _after_check_update(self, info):
		if not info["ok"]:
			self.log_msg("⚠  Gagal cek update: " + str(info["error"]))
			messagebox.showwarning("Cek update gagal", info["error"])
			return
		self.log_msg(f"Versi lokal {info['local']} • versi terbaru {info['remote']}")
		if not info["has_update"]:
			messagebox.showinfo("Sudah terbaru", f"Versi {info['local']} sudah yang terbaru.")
			return
		if not messagebox.askyesno(
			"Update tersedia",
			f"Versi baru {info['remote']} tersedia (saat ini {info['local']}).\n\n"
			"Update sekarang? Pengaturan (config.py) Anda tidak akan tersentuh.\n"
			"Setelah update, aplikasi perlu dibuka ulang.",
		):
			return
		self.log_msg("Mengunduh update...")

		def worker():
			res = updater.apply_update(on_log=self.log_msg)
			self.root.after(0, lambda: self._after_apply_update(res))

		threading.Thread(target=worker, daemon=True).start()

	def _after_apply_update(self, res):
		if res["ok"]:
			self.log_msg(f"✅ Update selesai ({len(res['updated'])} file).")
			messagebox.showinfo(
				"Update selesai",
				"Update berhasil. Tutup aplikasi ini lalu buka lagi (start.bat) "
				"untuk memakai versi baru.",
			)
		else:
			self.log_msg("✗  Update gagal: " + str(res["error"]))
			messagebox.showerror("Update gagal", str(res["error"]))

	# --------------------------------------------------------------- close --
	def on_close(self):
		if self.active:
			if not messagebox.askyesno(
				"Sesi masih aktif",
				"Sesi masih berjalan dan resi yang terkumpul BELUM digabung.\n\n"
				"Tetap keluar? (resi yang sudah terkumpul tetap tersimpan di folder sesi)",
			):
				return
			try:
				self.ctrl.cancel()
			except Exception:
				pass
		self.root.destroy()


def main():
	root = tk.Tk()
	ResiMergerApp(root)
	root.mainloop()


if __name__ == "__main__":
	main()
