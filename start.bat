@echo off
chcp 65001 >nul
title Resi Auto-Merger - BigSeller (PT Heavy Object Group)
cd /d "%~dp0"

echo ============================================================
echo   RESI AUTO-MERGER - BigSeller
echo ============================================================
echo.

rem --- Cek Python terpasang -------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python tidak ditemukan di PATH.
    echo     Install Python 3 dari https://www.python.org/downloads/
    echo     dan centang "Add Python to PATH" saat install.
    echo.
    pause
    exit /b 1
)

rem --- Cek dependency, install kalau belum ada ------------------------------
python -c "import pypdf, watchdog" >nul 2>&1
if errorlevel 1 (
    echo [..] Memasang dependency pertama kali: pypdf + watchdog
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install pypdf watchdog
    if errorlevel 1 (
        echo.
        echo [X] Gagal memasang dependency. Cek koneksi internet lalu coba lagi.
        pause
        exit /b 1
    )
)

rem --- Jalankan aplikasi GUI ------------------------------------------------
echo [OK] Menjalankan aplikasi...
echo.
python resi_merger_gui.py
if errorlevel 1 (
    echo.
    echo [X] Aplikasi berhenti dengan error. Salin pesan di atas kalau perlu bantuan.
    pause
)
