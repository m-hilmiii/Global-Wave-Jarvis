@echo off
setlocal EnableDelayedExpansion
title VoiceStudio - Local AI Speech & Dubbing Engine (:3900)
color 0A
chcp 65001 >nul

echo ==============================================================
echo    VOICESTUDIO AI SES VE DUBLAJ MOTORU (PORT 3900)
echo    Jarvis & Global Wave Yerel Entegrasyon Servisi
echo ==============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VOICESTUDIO_DIR=%SCRIPT_DIR%..\VoiceStudio-main"
if not exist "%VOICESTUDIO_DIR%\backend\main.py" (
    set "VOICESTUDIO_DIR=%SCRIPT_DIR%VoiceStudio-main"
)
if not exist "%VOICESTUDIO_DIR%\backend\main.py" (
    set "VOICESTUDIO_DIR=C:\Users\unalm\OneDrive\Masaüstü\Jarvis\VoiceStudio-main"
)

if not exist "%VOICESTUDIO_DIR%\backend\main.py" (
    echo [HATA] VoiceStudio-main klasoru bulunamadi: %VOICESTUDIO_DIR%
    pause
    exit /b 1
)

set "PYTHON_EXE=C:\Users\unalm\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo [*] VoiceStudio Klasoru: %VOICESTUDIO_DIR%
echo [*] Python Yolu: %PYTHON_EXE%
echo.

:: Port 3900 Kontrolu
netstat -ano | findstr ":3900" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [BILGI] VoiceStudio servisi zaten 3900 portunda aktif olarak calisiyor!
    echo [BILGI] Jarvis ve Video motoru su an dogrudan baglanabilir.
    echo.
    pause
    exit /b 0
)

cd /d "%VOICESTUDIO_DIR%"

:: UV paket yoneticisi kontrolu
echo [*] Paket yoneticisi (uv) kontrol ediliyor...
"%PYTHON_EXE%" -m uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 'uv' yukleniyor, lutfen bekleyin...
    "%PYTHON_EXE%" -m pip install uv
)

:: Bagimliliklarin senkronizasyonu
echo [*] VoiceStudio bagimliliklari dogrulaniyor...
"%PYTHON_EXE%" -m uv sync --quiet

echo.
echo ==============================================================
echo    VOICESTUDIO SERVISI BASLATILIYOR (http://127.0.0.1:3900)
echo    - OpenAI Uyumlu TTS / STT
echo    - 646 Dilde Yerel Ses Uretimi
echo    - Video Dublaj ve Arka Plan Miksaji
echo ==============================================================
echo.

"%PYTHON_EXE%" -m uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 3900

pause
