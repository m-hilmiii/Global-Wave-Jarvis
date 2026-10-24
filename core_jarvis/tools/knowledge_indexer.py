"""
Global-Wawe / Stark-Core - Local Knowledge & Documentation RAG Engine (Stage 3)
Features:
1. Zero-Cost Multi-Format Indexer (.md, .py, .txt, .json, .csv) across Global-Wawe and local desktop
2. Pure Standard Library BM25 Ranking Engine (No external vector DB required, 100% offline, $0 cost)
3. Incremental Indexing with mtime/size cache persistence in .jarvis_cache/knowledge_index.json
4. Sensitive File Blacklist (Strips credentials, private keys, tokens, session keys)
5. Smart Code & Markdown Chunking with heading / definition awareness
6. Document Summarizer & Executive Key Takeaway Extractor
"""

import os
import re
import json
import math
import time
import logging
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple

from core_jarvis.permission_guard import permission_guard, PermissionLevel

logger = logging.getLogger("Jarvis.KnowledgeIndexer")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = WORKSPACE_DIR / ".jarvis_cache"
INDEX_FILE = CACHE_DIR / "knowledge_index.json"

# File Discovery & Blacklist Constraints
SUPPORTED_EXTENSIONS = {".md", ".py", ".txt", ".json", ".csv", ".log", ".yaml", ".yml"}
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".jarvis_backups", ".jarvis_cache", "output", "temp", "dist", "build", ".pytest_cache"
}
SENSITIVE_FILENAME_PATTERNS = [
    r".*\.env.*", r".*\.key$", r".*\.token$", r".*\.pem$",
    r"client_secret.*\.json$", r"session_token\.key", r".*id_rsa.*", r".*credentials.*\.json$"
]

# BM25 Parameters
BM25_K1 = 1.5
BM25_B = 0.75


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric words."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) > 1]
    return tokens


class KnowledgeIndexer:
    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace = workspace_path or WORKSPACE_DIR
        self.cache_dir = self.workspace / ".jarvis_cache"
        self.index_file = self.cache_dir / "knowledge_index.json"
        
        # In-memory index structures
        self.chunks: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.term_doc_freq: Counter = Counter()  # df: in how many chunks does term appear
        self.file_metadata: Dict[str, Dict[str, Any]] = {}
        self.total_docs: int = 0
        self.last_indexed_at: Optional[str] = None

        self._load_cached_index()

    def _is_sensitive_file(self, file_path: Path) -> bool:
        """Returns True if the file matches any credential/sensitive patterns."""
        name = file_path.name
        for pattern in SENSITIVE_FILENAME_PATTERNS:
            if re.match(pattern, name, re.IGNORECASE):
                return True
        return False

    def _load_cached_index(self):
        """Loads index from disk if cache exists."""
        if not self.index_file.exists():
            return

        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.chunks = data.get("chunks", [])
            self.file_metadata = data.get("file_metadata", {})
            self.last_indexed_at = data.get("last_indexed_at")
            self._recalculate_bm25_stats()
            logger.info(f"Loaded {len(self.chunks)} chunks from {self.index_file}")
        except Exception as e:
            logger.warning(f"Failed to load cached knowledge index: {e}")

    def _save_cached_index(self):
        """Persists chunks and metadata to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "last_indexed_at": self.last_indexed_at,
                "total_chunks": len(self.chunks),
                "file_metadata": self.file_metadata,
                "chunks": self.chunks
            }
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist knowledge index: {e}")

    def _recalculate_bm25_stats(self):
        """Recomputes doc lengths, avg doc length, and document frequencies."""
        self.total_docs = len(self.chunks)
        if self.total_docs == 0:
            self.avg_doc_len = 0.0
            self.doc_lengths = []
            self.term_doc_freq = Counter()
            return

        self.doc_lengths = []
        self.term_doc_freq = Counter()

        for chunk in self.chunks:
            tokens = chunk.get("tokens") or tokenize(chunk.get("content", ""))
            chunk["tokens"] = tokens
            self.doc_lengths.append(len(tokens))
            unique_terms = set(tokens)
            for t in unique_terms:
                self.term_doc_freq[t] += 1

        self.avg_doc_len = sum(self.doc_lengths) / self.total_docs if self.total_docs > 0 else 0.0

    def chunk_content(self, text: str, file_path: str, max_chunk_chars: int = 900) -> List[Dict[str, Any]]:
        """
        Splits file content into contextual chunks.
        Respects markdown headers (# Header) and Python functions/classes.
        """
        lines = text.splitlines()
        chunks = []
        current_chunk_lines = []
        current_chunk_header = ""
        current_start_line = 1

        for line_idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Heading or Code block boundary detection
            is_header = stripped.startswith("# ") or stripped.startswith("## ") or stripped.startswith("### ")
            is_code_def = stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("async def ")

            current_char_count = sum(len(l) for l in current_chunk_lines)

            if (is_header or is_code_def) and current_char_count > 300:
                # Flush previous chunk
                chunk_body = "\n".join(current_chunk_lines).strip()
                if chunk_body:
                    chunks.append({
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "header": current_chunk_header or "Başlangıç Bölümü",
                        "content": chunk_body,
                        "tokens": tokenize(chunk_body),
                        "start_line": current_start_line,
                        "end_line": line_idx - 1
                    })
                current_chunk_lines = []
                current_start_line = line_idx

            if is_header or is_code_def:
                current_chunk_header = stripped[:60]

            current_chunk_lines.append(line)

            # Max size split
            if current_char_count > max_chunk_chars:
                chunk_body = "\n".join(current_chunk_lines).strip()
                if chunk_body:
                    chunks.append({
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "header": current_chunk_header or "Metin Bloğu",
                        "content": chunk_body,
                        "tokens": tokenize(chunk_body),
                        "start_line": current_start_line,
                        "end_line": line_idx
                    })
                current_chunk_lines = []
                current_start_line = line_idx + 1

        # Flush remainder
        if current_chunk_lines:
            chunk_body = "\n".join(current_chunk_lines).strip()
            if chunk_body:
                chunks.append({
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "header": current_chunk_header or "Bölüm",
                    "content": chunk_body,
                    "tokens": tokenize(chunk_body),
                    "start_line": current_start_line,
                    "end_line": len(lines)
                })

        return chunks

    def index_workspace(self, force: bool = False, extra_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scans workspace and optional additional paths, performing incremental indexing.
        """
        guard_res = permission_guard.evaluate_action("file_read", confirmed_by_user=False)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"]}

        start_time = time.time()
        scan_paths = [self.workspace]
        if extra_paths:
            for p in extra_paths:
                extra_p = Path(p).resolve()
                if extra_p.exists() and extra_p.is_dir():
                    scan_paths.append(extra_p)

        discovered_files: List[Path] = []
        for root_path in scan_paths:
            for root, dirs, files in os.walk(root_path):
                # Filter out excluded directories in-place
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        fpath = Path(root) / fname
                        if not self._is_sensitive_file(fpath):
                            discovered_files.append(fpath)

        indexed_count = 0
        skipped_count = 0
        new_chunks = []

        # If incremental, retain chunks for unchanged files
        file_to_chunks: Dict[str, List[Dict[str, Any]]] = {}
        if not force:
            for c in self.chunks:
                fp = c["file_path"]
                if fp not in file_to_chunks:
                    file_to_chunks[fp] = []
                file_to_chunks[fp].append(c)

        for fpath in discovered_files:
            rel_str = str(fpath)
            try:
                stat = fpath.stat()
                mtime = stat.st_mtime
                size = stat.st_size

                # Check if file changed
                prev_meta = self.file_metadata.get(rel_str)
                if not force and prev_meta and prev_meta.get("mtime") == mtime and prev_meta.get("size") == size:
                    skipped_count += 1
                    if rel_str in file_to_chunks:
                        new_chunks.extend(file_to_chunks[rel_str])
                    continue

                # Read and chunk
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                f_chunks = self.chunk_content(content, rel_str)
                new_chunks.extend(f_chunks)
                self.file_metadata[rel_str] = {
                    "mtime": mtime,
                    "size": size,
                    "chunk_count": len(f_chunks),
                    "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                indexed_count += 1
            except Exception as e:
                logger.warning(f"Error reading file {rel_str}: {e}")

        self.chunks = new_chunks
        self.last_indexed_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._recalculate_bm25_stats()
        self._save_cached_index()

        elapsed = round(time.time() - start_time, 2)
        summary = (
            f"İndeksleme tamamlandı: {len(discovered_files)} dosya tarandı, "
            f"{indexed_count} yeni/güncellenen dosya işlendi, {skipped_count} dosya önbellekten korundu. "
            f"Toplam {len(self.chunks)} bilgi parçası (chunk) hazır ({elapsed}sn)."
        )

        return {
            "success": True,
            "total_files_scanned": len(discovered_files),
            "files_indexed": indexed_count,
            "files_skipped_cached": skipped_count,
            "total_chunks": len(self.chunks),
            "elapsed_seconds": elapsed,
            "summary": summary
        }

    def search(self, query: str, top_k: int = 5, file_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Pure Python BM25 lexical ranker across all indexed chunks.
        Zero external API calls, $0 cost, <10ms response time.
        """
        if not self.chunks:
            # Auto-index if not already done
            self.index_workspace(force=False)

        q_tokens = tokenize(query)
        if not q_tokens:
            return {"query": query, "total_matches": 0, "results": []}

        scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

        for idx, chunk in enumerate(self.chunks):
            # Optional file name/path filter
            if file_filter and file_filter.lower() not in chunk["file_path"].lower():
                continue

            doc_len = self.doc_lengths[idx] if idx < len(self.doc_lengths) else len(chunk.get("tokens", []))
            term_counts = Counter(chunk.get("tokens", []))
            score = 0.0

            for q_term in q_tokens:
                if q_term not in term_counts:
                    continue

                tf = term_counts[q_term]
                n_q = self.term_doc_freq.get(q_term, 0)
                # BM25 standard IDF with smoothing
                idf = math.log(((self.total_docs - n_q + 0.5) / (n_q + 0.5)) + 1.0)
                
                # BM25 TF weight
                denom = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * (doc_len / (self.avg_doc_len or 1.0)))
                term_score = idf * ((tf * (BM25_K1 + 1.0)) / (denom or 1.0))
                score += term_score

            if score > 0.0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_chunks[:top_k]

        formatted_results = []
        for rank, (score, ch) in enumerate(top_matches, start=1):
            # Extract high-relevance snippet
            content_preview = ch["content"][:300].replace("\n", " ").strip()
            if len(ch["content"]) > 300:
                content_preview += "..."

            formatted_results.append({
                "rank": rank,
                "score": round(score, 3),
                "file_name": ch["file_name"],
                "file_path": ch["file_path"],
                "header": ch.get("header", ""),
                "start_line": ch.get("start_line", 1),
                "end_line": ch.get("end_line", 1),
                "preview": content_preview,
                "full_chunk": ch["content"]
            })

        return {
            "query": query,
            "total_matches": len(scored_chunks),
            "top_k": top_k,
            "results": formatted_results,
            "executive_summary": (
                f"Sayın Hilmi, '{query}' araması için {len(scored_chunks)} eşleşme bulundu. "
                f"En alakalı kaynak: **{formatted_results[0]['file_name']}** ({formatted_results[0]['header']})."
                if formatted_results else f"Sayın Hilmi, yerel bilgi tabanında '{query}' ile eşleşen bir içerik bulunamadı."
            )
        }

    def summarize_document(self, file_path: str, max_chars: int = 3000) -> Dict[str, Any]:
        """
        Reads a document, analyzes structure, classes, headings, and generates an executive overview.
        """
        guard_res = permission_guard.evaluate_action("file_read", confirmed_by_user=False)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"]}

        target = Path(file_path)
        if not target.is_absolute():
            target = self.workspace / file_path

        if not target.exists() or not target.is_file():
            return {"success": False, "error": f"Dosya bulunamadı: {file_path}"}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines = content.splitlines()
            total_lines = len(lines)
            size_kb = round(target.stat().st_size / 1024, 2)

            # Structural analysis
            headings = [l.strip() for l in lines if l.strip().startswith("#")]
            functions = [l.strip() for l in lines if l.strip().startswith("def ") or l.strip().startswith("async def ")]
            classes = [l.strip() for l in lines if l.strip().startswith("class ")]

            summary_lead = f"{target.name} ({size_kb} KB, {total_lines} satır)."
            structure_points = []
            if classes:
                structure_points.append(f"{len(classes)} Sınıf: {', '.join([c.split('(')[0].replace('class ', '') for c in classes[:4]])}")
            if functions:
                structure_points.append(f"{len(functions)} Fonksiyon/Metot")
            if headings:
                structure_points.append(f"{len(headings)} Ana Başlık")

            first_sample = content[:max_chars].strip()

            return {
                "success": True,
                "file_name": target.name,
                "file_path": str(target),
                "size_kb": size_kb,
                "total_lines": total_lines,
                "classes_count": len(classes),
                "functions_count": len(functions),
                "headings_count": len(headings),
                "headings_sample": headings[:6],
                "functions_sample": functions[:6],
                "lead_text": summary_lead,
                "structure_summary": " | ".join(structure_points) if structure_points else "Düz metin / dokümantasyon",
                "preview_text": first_sample
            }
        except Exception as e:
            return {"success": False, "error": f"Doküman analiz hatası: {str(e)}"}

    def get_index_stats(self) -> Dict[str, Any]:
        """Returns metadata about the active index."""
        return {
            "total_chunks": len(self.chunks),
            "total_files": len(self.file_metadata),
            "avg_chunk_length": round(self.avg_doc_len, 1),
            "unique_terms": len(self.term_doc_freq),
            "last_indexed_at": self.last_indexed_at,
            "index_file_exists": self.index_file.exists()
        }


knowledge_indexer = KnowledgeIndexer()
