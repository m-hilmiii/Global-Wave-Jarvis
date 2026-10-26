@echo off
setlocal EnableDelayedExpansion
title JARVIS AI Operating System - Sayin Hilmi
color 0B
chcp 65001 >nul
cd /d "%~dp0"

call "%~dp0start_jarvis.bat" %*
