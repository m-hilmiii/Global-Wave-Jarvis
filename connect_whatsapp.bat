@echo off
title JARVIS WhatsApp Bridge - Baglanti ve QR Tarama
cd /d "%~dp0core_jarvis\whatsapp_bridge"
echo ====================================================
echo      JARVIS WHATSAPP BAGLANTI MOTORU BASLATILIYOR
echo ====================================================
echo.
echo Lutfen ekrana QR kodu geldiginde telefonunuzdan:
echo WhatsApp -> Bagli Cihazlar -> Cihaz Bagla
echo secenegi ile kameranizi bu ekrana tutun.
echo.
echo Not: Baglanti kurulduktan ve "TEBRIKLER" yazisini
echo gordukten sonra bu pencereyi kapatabilirsiniz!
echo ====================================================
echo.
node dist/bridge.js --auth-dir "../../data/whatsapp_auth"
pause
