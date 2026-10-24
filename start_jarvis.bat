@echo off
setlocal EnableDelayedExpansion
title JARVIS AI Operating System - Sayin Hilmi
color 0B
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\unalm\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

if "%~1"=="start" goto opt_foreground
if "%~1"=="foreground" goto opt_foreground
if "%~1"=="background" goto opt_background
if "%~1"=="bg" goto opt_background
if "%~1"=="stop" goto opt_stop
if "%~1"=="status" goto opt_status
if "%~1"=="restart" goto opt_restart
if "%~1"=="shortcut" goto opt_shortcut
if "%~1"=="startup" goto opt_startup_install

:menu
cls
echo ==============================================================
echo    JARVIS AI OPERATING SYSTEM - SAYIN HILMI
echo    Local Architecture - RX 9060 XT - i5-14400F 16GB
echo ==============================================================
echo.
echo   [1] Konsol Modunda Baslat (Canli Loglar ve Terminal)
echo   [2] Arka Planda Sessiz Baslat (Gizli Daemon Modu)
echo   [3] JARVIS'i Durdur
echo   [4] Sistem ve Telemetri Durumunu Gor
echo   [5] Masaustu Kisayolu Olustur (Desktop Icon)
echo   [6] Windows Baslangicina Ekle (Acilista Otomatik Baslat)
echo   [7] Windows Baslangicindan Kaldir
echo   [0] Cikis
echo.
echo ==============================================================
set /p choice="Seciminiz [1-7, 0]: "

if "%choice%"=="1" goto opt_foreground
if "%choice%"=="2" goto opt_background
if "%choice%"=="3" goto opt_stop
if "%choice%"=="4" goto opt_status
if "%choice%"=="5" goto opt_shortcut
if "%choice%"=="6" goto opt_startup_install
if "%choice%"=="7" goto opt_startup_uninstall
if "%choice%"=="0" exit /b 0

echo Gecersiz secim.
timeout /t 2 >nul
goto menu

:opt_foreground
cls
echo [JARVIS] Konsol modunda baslatiliyor...
"%PYTHON_EXE%" run_global_wave.py
pause
goto menu

:opt_background
cls
echo [JARVIS] Arka planda sessiz daemon modunda baslatiliyor...
"%PYTHON_EXE%" scripts\jarvis_daemon.py start
echo.
pause
goto menu

:opt_stop
cls
echo [JARVIS] Durduruluyor...
"%PYTHON_EXE%" scripts\jarvis_daemon.py stop
echo.
pause
goto menu

:opt_status
cls
"%PYTHON_EXE%" scripts\jarvis_daemon.py status
echo.
pause
goto menu

:opt_shortcut
cls
echo [JARVIS] Masaustu kisayolu olusturuluyor...
"%PYTHON_EXE%" scripts\jarvis_daemon.py shortcut
echo.
pause
goto menu

:opt_startup_install
cls
echo [JARVIS] Windows Baslangicina ekleniyor...
"%PYTHON_EXE%" scripts\jarvis_daemon.py startup-install
echo.
pause
goto menu

:opt_startup_uninstall
cls
echo [JARVIS] Windows Baslangicindan kaldiriliyor...
"%PYTHON_EXE%" scripts\jarvis_daemon.py startup-uninstall
echo.
pause
goto menu
