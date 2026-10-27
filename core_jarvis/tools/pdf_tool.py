"""
Global-Wawe / Stark-Core - Local PDF Extraction & Document Intelligence Tool
Integrated from OpenJarvis / JARVIS capabilities catalog.
Enables JARVIS to read, parse, and summarize incoming WhatsApp invoices, contracts,
specifications, and local PDF files with 100% offline security and zero API cost.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("Jarvis.PDFTool")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
MAX_CHARS_DEFAULT = 40_000
MAX_PAGES_DEFAULT = 50


class PDFTool:
    def __init__(self):
        self._pypdf_available = False
        try:
            import pypdf
            self._pypdf_available = True
        except ImportError:
            self._pypdf_available = False

    def extract_text(
        self,
        file_path: str,
        max_pages: int = MAX_PAGES_DEFAULT,
        max_chars: int = MAX_CHARS_DEFAULT
    ) -> Dict[str, Any]:
        """
        Extracts clean text content and metadata from a local PDF file.
        Safely bounds memory and page counts.
        """
        target = Path(file_path)
        if not target.is_absolute():
            # Check in workspace or common downloads / media folders
            candidates = [
                WORKSPACE_ROOT / target,
                WORKSPACE_ROOT / "output" / "whatsapp_media" / target.name,
                Path("/mnt/c/Users/unalm/Downloads") / target.name,
                Path(os.environ.get("USERPROFILE", "")) / "Downloads" / target.name
            ]
            for cand in candidates:
                if cand.exists() and cand.is_file():
                    target = cand
                    break

        if not target.exists() or not target.is_file():
            return {"success": False, "error": f"PDF dosyası bulunamadı: {file_path}"}

        if target.suffix.lower() != ".pdf":
            return {"success": False, "error": f"Belirtilen dosya bir PDF değil: {target.name}"}

        if not self._pypdf_available:
            try:
                import pypdf
                self._pypdf_available = True
            except ImportError:
                return {
                    "success": False,
                    "error": "pypdf kütüphanesi kurulu değil. Lütfen 'pip install pypdf' çalıştırın."
                }

        try:
            import pypdf
            reader = pypdf.PdfReader(str(target))
            total_pages = len(reader.pages)
            pages_to_read = min(total_pages, max_pages)

            text_chunks = []
            for i in range(pages_to_read):
                try:
                    page_text = reader.pages[i].extract_text() or ""
                    if page_text.strip():
                        text_chunks.append(f"--- Sayfa {i+1} ---\n{page_text.strip()}")
                except Exception as p_err:
                    logger.debug(f"[PDF] Page {i+1} extract error: {p_err}")

            combined_text = "\n\n".join(text_chunks)
            truncated = False
            if len(combined_text) > max_chars:
                combined_text = combined_text[:max_chars] + "\n\n[...Metin karakter sınırından ötürü kısaltıldı...]"
                truncated = True

            meta = reader.metadata or {}
            title = meta.get("/Title") or target.stem

            return {
                "success": True,
                "file_name": target.name,
                "file_path": str(target.resolve()),
                "file_size_kb": round(target.stat().st_size / 1024, 2),
                "total_pages": total_pages,
                "pages_extracted": pages_to_read,
                "title": str(title) if title else target.stem,
                "author": str(meta.get("/Author", "Bilinmiyor")),
                "char_count": len(combined_text),
                "is_truncated": truncated,
                "text": combined_text or "[Bu PDF dosyasında taranabilir metin bulunamadı veya görsel/taranmış sayfalardan oluşuyor.]"
            }
        except Exception as exc:
            logger.error(f"[PDFTool] Extraction failed for {target}: {exc}")
            return {"success": False, "error": f"PDF ayrıştırma hatası: {str(exc)}"}

    def summarize_pdf(
        self,
        file_path: str,
        user_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Extracts PDF text and produces an executive summary for Sayın Hilmi.
        """
        extracted = self.extract_text(file_path)
        if not extracted.get("success"):
            return extracted

        text = extracted.get("text", "")
        file_name = extracted.get("file_name", "Belge")
        pages = extracted.get("total_pages", 0)

        # Quick structural analysis
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first_few_lines = "\n".join(lines[:12]) if lines else "Boş doküman"

        # Look for invoice / financial keywords
        is_financial = any(k in text.lower() for k in ["fatura", "tutar", "toplam", "kdv", "iban", "fiyat", "ödenen", "vergi"])
        doc_type = "Mali / Fatura Belgesi" if is_financial else "Rapor / Genel Doküman"

        summary = (
            f"📄 **{file_name}** ({pages} Sayfa | {extracted.get('file_size_kb')} KB | {doc_type})\n\n"
            f"• **Başlık / Yazar:** {extracted.get('title')} / {extracted.get('author')}\n"
            f"• **İçerik Özeti (İlk Başlıklar):**\n"
            f"```text\n{first_few_lines[:450]}\n```\n\n"
            f"• **Toplam Metin:** {extracted.get('char_count')} karakter çıkarıldı."
        )

        return {
            "success": True,
            "summary": summary,
            "doc_type": doc_type,
            "metadata": extracted
        }

    def find_pdf_files(self, search_term: str = "") -> List[Dict[str, Any]]:
        """Finds PDF files in workspace and downloads directories."""
        found = []
        search_dirs = [
            WORKSPACE_ROOT / "output" / "whatsapp_media",
            WORKSPACE_ROOT,
            Path("/mnt/c/Users/unalm/Downloads"),
            Path(os.environ.get("USERPROFILE", "")) / "Downloads"
        ]
        seen_paths = set()
        for sdir in search_dirs:
            if sdir.exists() and sdir.is_dir():
                try:
                    for f in sdir.glob("*.pdf"):
                        if f.is_file() and str(f.resolve()) not in seen_paths:
                            seen_paths.add(str(f.resolve()))
                            if not search_term or search_term.lower() in f.name.lower():
                                found.append({
                                    "name": f.name,
                                    "path": str(f.resolve()),
                                    "size_kb": round(f.stat().st_size / 1024, 1),
                                    "modified_at": int(f.stat().st_mtime)
                                })
                except Exception:
                    pass
        return sorted(found, key=lambda x: x["modified_at"], reverse=True)


pdf_tool = PDFTool()
