# -*- coding: utf-8 -*-
"""
==============================================================================
 UPDATER — Resi Auto-Merger BigSeller
==============================================================================

Update aplikasi langsung dari GitHub (branch main), tanpa dependency tambahan
(hanya stdlib urllib). Bisa dipanggil dari GUI (tombol "Cek Update") atau
dijalankan sendiri: `python updater.py`.

CARA KERJA:
  1. Ambil version.py dari GitHub raw, baca __version__ remote.
  2. Bandingkan dengan versi lokal (version.py).
  3. Kalau remote lebih baru: download tiap file di FILES_TO_UPDATE,
     backup file lama ke *.bak, lalu timpa.
  4. config.py TIDAK PERNAH ditimpa — pengaturan operator aman.

Setelah update, aplikasi perlu di-restart (tutup & buka lagi start.bat).
==============================================================================
"""

import os
import re
import urllib.request

import config

# File yang ikut di-update. SENGAJA TIDAK memasukkan config.py.
FILES_TO_UPDATE = [
	"version.py",
	"resi_merger_core.py",
	"resi_merger.py",
	"resi_merger_gui.py",
	"updater.py",
	"start.bat",
	"README.md",
]

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_TIMEOUT = 15  # detik


def _raw_url(filename):
	return (
		f"https://raw.githubusercontent.com/{config.GITHUB_OWNER}/"
		f"{config.GITHUB_REPO}/{config.GITHUB_BRANCH}/{filename}"
	)


def _fetch(url):
	"""Ambil isi URL sebagai bytes. Lempar exception kalau gagal."""
	req = urllib.request.Request(url, headers={"User-Agent": "resi-merger-updater"})
	with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
		return resp.read()


def _parse_version(text):
	"""Ambil string versi dari isi version.py."""
	m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
	return m.group(1) if m else None


def _version_tuple(v):
	"""'1.2.3' -> (1, 2, 3) untuk perbandingan numerik."""
	parts = []
	for p in str(v).split("."):
		num = re.sub(r"[^0-9]", "", p)
		parts.append(int(num) if num else 0)
	return tuple(parts)


def local_version():
	from version import __version__
	return __version__


def remote_version():
	"""Versi terbaru di GitHub, atau None kalau gagal mengambil."""
	try:
		text = _fetch(_raw_url("version.py")).decode("utf-8", "replace")
		return _parse_version(text)
	except Exception:
		return None


def check_for_update():
	"""
	Return dict:
      {'ok': bool, 'has_update': bool, 'local': str, 'remote': str|None, 'error': str|None}
	"""
	loc = local_version()
	rem = remote_version()
	if rem is None:
		return {
			"ok": False,
			"has_update": False,
			"local": loc,
			"remote": None,
			"error": "Tidak bisa menghubungi GitHub (cek koneksi internet).",
		}
	has = _version_tuple(rem) > _version_tuple(loc)
	return {"ok": True, "has_update": has, "local": loc, "remote": rem, "error": None}


def apply_update(on_log=print):
	"""
	Download & timpa file aplikasi. Return dict {'ok': bool, 'updated': [...], 'error': str|None}.
	File lama dibackup ke *.bak sebelum ditimpa.
	"""
	updated = []
	try:
		for filename in FILES_TO_UPDATE:
			url = _raw_url(filename)
			try:
				data = _fetch(url)
			except Exception as e:
				# File mungkin belum ada di repo (mis. start.bat opsional) — lewati.
				on_log(f"   • lewati {filename} ({e})")
				continue

			dest = os.path.join(_APP_DIR, filename)
			# Backup file lama
			if os.path.exists(dest):
				try:
					bak = dest + ".bak"
					if os.path.exists(bak):
						os.remove(bak)
					os.replace(dest, bak)
				except Exception:
					pass
			with open(dest, "wb") as fh:
				fh.write(data)
			updated.append(filename)
			on_log(f"   ✓ {filename}")
		return {"ok": True, "updated": updated, "error": None}
	except Exception as e:
		return {"ok": False, "updated": updated, "error": str(e)}


def main():
	print("Mengecek update dari GitHub...")
	info = check_for_update()
	if not info["ok"]:
		print("Gagal cek update:", info["error"])
		return
	print(f"Versi lokal : {info['local']}")
	print(f"Versi remote: {info['remote']}")
	if not info["has_update"]:
		print("Sudah versi terbaru. Tidak ada yang perlu di-update.")
		return
	print("Update tersedia. Mengunduh...")
	res = apply_update()
	if res["ok"]:
		print(f"Selesai. {len(res['updated'])} file di-update.")
		print("Silakan tutup & buka ulang aplikasi (start.bat).")
	else:
		print("Update gagal:", res["error"])


if __name__ == "__main__":
	main()
