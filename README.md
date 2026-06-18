# Resi Auto-Merger untuk BigSeller — PT Heavy Object Group

Folder watcher lokal berbasis **sesi batch manual** untuk menggabungkan resi PDF
yang di-download terpisah per ekspedisi dari BigSeller menjadi **satu PDF**,
tanpa iLovePDF dan tanpa cari file manual. Tersedia versi **GUI** dan **console**.

> Untuk order **Shopee**, BigSeller sudah mendukung cross-logistics printing
> (print dari tab "New Orders", sortir per shipping method via filter). Tool ini
> terutama untuk **TikTok Shop** yang tidak didukung.

## Cara menjalankan (paling mudah)

Klik dua kali **`start.bat`**. Script ini otomatis:
1. Mengecek Python terpasang.
2. Memasang `pypdf` + `watchdog` kalau belum ada (sekali saja).
3. Membuka aplikasi GUI.

Alternatif manual:
```
pip install pypdf watchdog
python resi_merger_gui.py     # versi GUI
python resi_merger.py         # versi console
```

## Cara pakai (GUI)

1. Klik **▶ MULAI SESI** (tool mulai memantau folder download).
2. Download semua resi tiap ekspedisi dari BigSeller seperti biasa. Tiap resi
   yang masuk otomatis dipindah ke folder sesi & terhitung di "Resi terkumpul".
3. Klik **■ TUTUP SESI & MERGE** → PDF gabungan dibuat di `OUTPUT_FOLDER`.
4. Klik **📂 Buka Folder Output** atau **📄 Buka Hasil Terakhir** untuk melihat hasil.
5. Siap untuk batch berikutnya tanpa restart.

## Update aplikasi

Klik tombol **⬆ Cek Update** di GUI (atau jalankan `python updater.py`). Updater
menarik versi terbaru dari GitHub. **`config.py` tidak akan tersentuh**, jadi
pengaturan Anda aman. Setelah update, tutup & buka ulang aplikasi.

## Pengaman anti-tercampur (prioritas desain utama)

- Tool **tidak pernah men-scan** isi folder yang sudah ada.
- Hanya bereaksi pada event download (`on_created` / `on_moved`) yang terjadi
  **setelah** sesi dimulai.
- Resi yang selesai ter-download langsung **dipindah** (bukan copy) ke folder
  sesi bertimestamp terisolasi → folder download langsung bersih, mustahil
  tergabung dua kali atau tertukar dengan batch lama.

## Yang perlu disesuaikan per lingkungan

Edit **`config.py`** (file ini tidak ditimpa saat update):

| Variabel | Default | Catatan |
|---|---|---|
| `WATCH_FOLDER` | `~/Downloads` | Idealnya arahkan ke folder download khusus browser kerja (mis. `D:\RESI_BIGSELLER`). Tidak wajib. |
| `WORK_FOLDER` | `~/Downloads/RESI_PROSES` | Folder kerja terisolasi (sementara). |
| `OUTPUT_FOLDER` | `~/Downloads/RESI_MERGED` | Bisa diarahkan ke folder Google Drive Stream agar auto-sync. |
| `ARCHIVE_FOLDER` | `~/Downloads/RESI_ARSIP` | Arsip resi mentah per batch (jejak audit). |
| `RESI_KEYWORDS` | `shippinglabel, shipping_label, waybill, awb, resi, label` | Kosongkan (`[]`) untuk anggap **semua** PDF sebagai resi. |

Parameter teknis (`STABLE_CHECKS`, `STABLE_INTERVAL`, `STABLE_TIMEOUT`) mengatur
deteksi "download selesai" sebelum file dipindahkan — jarang perlu diubah.

## Struktur file

| File | Fungsi |
|---|---|
| `start.bat` | Launcher Windows (cek deps + buka GUI). |
| `resi_merger_gui.py` | Aplikasi GUI (Tkinter). |
| `resi_merger.py` | Versi console. |
| `resi_merger_core.py` | Logika inti (sesi, watcher, merge) — dipakai GUI & console. |
| `config.py` | Konfigurasi (aman diedit, tidak ditimpa updater). |
| `updater.py` | Updater dari GitHub. |
| `version.py` | Nomor versi. |
