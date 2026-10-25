@echo off
setlocal EnableDelayedExpansion
title JARVIS God Mode v3.0 - Nokta Atisi 5'li Uzman Model Kurulumu
color 0B
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\unalm\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

set "OLLAMA_EXE=C:\Users\unalm\AppData\Local\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" set "OLLAMA_EXE=ollama"

echo ======================================================================
echo    JARVIS GOD MODE v3.0 - NOKTA ATISI 5'LI UZMAN MODEL CEPHANELIGI
echo    Donanim: AMD Radeon RX 9060 XT (16GB VRAM) + Intel i5-14400F
echo    Hat: 1000 Mbps Fiber ^| Maliyet: $0 (100%% Yerel Acik Kaynak)
echo ======================================================================
echo.
echo [1/6] Cok Dilli Anlamsal Vektor RAG Motoru indiriliyor (bge-m3 ~1.2 GB)...
"%OLLAMA_EXE%" pull bge-m3
echo.
echo [2/6] Gorsel Zeka ve Ekran/Fatura Okuma Modeli indiriliyor (qwen2.5vl:7b ~5.2 GB)...
"%OLLAMA_EXE%" pull qwen2.5vl:7b
echo.
echo [3/6] Ana Beyin ve Turkce Ajan Orkestratoru kontrol ediliyor (qwen3:14b ~9.0 GB)...
"%OLLAMA_EXE%" pull qwen3:14b
echo.
echo [4/6] Uzman Yazilim Muhendisi ve Kod Doktoru indiriliyor (qwen2.5-coder:14b ~9.0 GB)...
"%OLLAMA_EXE%" pull qwen2.5-coder:14b
echo.
echo [5/6] Derin Muhakeme (Chain-of-Thought) ve Strateji Beyni indiriliyor (deepseek-r1:14b ~9.0 GB)...
"%OLLAMA_EXE%" pull deepseek-r1:14b
echo.
echo [6/6] Proje Kod Tabani ve Transkript/ YouTube Egitim Arsivi RAG indeksine isleniyor...
"%PYTHON_EXE%" -c "from core_jarvis.tools.knowledge_indexer import knowledge_indexer; res = knowledge_indexer.index_workspace(force=True); print(res.get('summary'))"
echo.
echo ======================================================================
echo    TUM UZMAN MODELLER VE BILGI TABANI BASARIYLA HAZIRLANDI!
echo ======================================================================
pause
