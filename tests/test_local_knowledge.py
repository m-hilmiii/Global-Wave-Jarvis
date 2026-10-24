"""
Unit Tests for Local Knowledge & Documentation RAG Engine (Stage 3)
Verifies:
1. Tokenization and linguistic preprocessing
2. Sensitive credential file exclusion
3. Heading & code-aware chunking
4. BM25 lexical ranking and search relevance
5. Document structural summarization
6. Orchestrator intent routing for local docs
7. FastAPI REST endpoints (/api/jarvis/knowledge/*)
"""

import os
import unittest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from core_jarvis.tools.knowledge_indexer import (
    KnowledgeIndexer, tokenize, knowledge_indexer
)
from core_jarvis.orchestrator import orchestrator
from web.server import app, LOCAL_SESSION_TOKEN


class TestLocalKnowledgeEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.indexer = KnowledgeIndexer(workspace_path=self.temp_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tokenization(self):
        text = "JARVIS v5.6: Otonom AI ve RAG mimarisi, 100% güvenli!"
        tokens = tokenize(text)
        self.assertIn("jarvis", tokens)
        self.assertIn("otonom", tokens)
        self.assertIn("rag", tokens)
        self.assertIn("mimarisi", tokens)
        self.assertIn("güvenli", tokens)

    def test_sensitive_file_blacklist(self):
        sensitive_samples = [
            Path("secrets.env"),
            Path(".env.production"),
            Path("session_token.key"),
            Path("client_secret_xyz.json"),
            Path("id_rsa_private.pem"),
            Path("google_credentials.json")
        ]
        for f in sensitive_samples:
            self.assertTrue(self.indexer._is_sensitive_file(f), f"Failed for {f.name}")

        safe_samples = [
            Path("README.md"),
            Path("main.py"),
            Path("system_tool.py"),
            Path("settings.json")
        ]
        for f in safe_samples:
            self.assertFalse(self.indexer._is_sensitive_file(f), f"Failed for {f.name}")

    def test_heading_and_code_chunking(self):
        sample_doc = """# Başlık 1: Jarvis Giriş
Bu bölüm sistemin genel mimarisini açıklar.

## Alt Başlık: İzin Sistemi
Burada dört seviyeli güvenlik kalkanı bulunur.
Seviye 1, Seviye 2, Seviye 3, Seviye 4.

class SecurityGuard:
    def evaluate(self):
        return True
"""
        chunks = self.indexer.chunk_content(sample_doc, "sample.md")
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]["file_name"], "sample.md")
        self.assertIn("start_line", chunks[0])
        self.assertIn("end_line", chunks[0])

    def test_bm25_indexing_and_search(self):
        # Create test files in temp directory
        file1 = self.temp_path / "architecture.md"
        file1.write_text(
            "# Global Wave Architecture\n\nBu doküman video üretim hattını ve FFmpeg donanım hızlandırıcısını içerir.",
            encoding="utf-8"
        )

        file2 = self.temp_path / "telemetry.py"
        file2.write_text(
            "def get_system_telemetry():\n    return {'cpu': 15.2, 'ram': 45.0, 'gpu': 'AMD Radeon RX 9060 XT'}",
            encoding="utf-8"
        )

        # Index
        index_res = self.indexer.index_workspace(force=True)
        self.assertTrue(index_res["success"])
        self.assertEqual(index_res["files_indexed"], 2)
        self.assertGreater(index_res["total_chunks"], 0)

        # Search query 1
        res1 = self.indexer.search("FFmpeg donanım hızlandırıcı", top_k=3)
        self.assertGreater(res1["total_matches"], 0)
        self.assertEqual(res1["results"][0]["file_name"], "architecture.md")
        self.assertIn("Sayın Hilmi", res1["executive_summary"])

        # Search query 2
        res2 = self.indexer.search("AMD Radeon RX", top_k=3)
        self.assertGreater(res2["total_matches"], 0)
        self.assertEqual(res2["results"][0]["file_name"], "telemetry.py")

    def test_document_summarization(self):
        # Create a Python file
        test_py = self.temp_path / "agent_mesh.py"
        test_py.write_text(
            "# Agent Mesh Module\n\nclass SystemSpecialist:\n    pass\n\nclass CodeSpecialist:\n    pass\n\ndef run_diagnostics():\n    return True\n",
            encoding="utf-8"
        )
        summary = self.indexer.summarize_document(str(test_py))
        self.assertTrue(summary["success"])
        self.assertEqual(summary["file_name"], "agent_mesh.py")
        self.assertEqual(summary["classes_count"], 2)
        self.assertEqual(summary["functions_count"], 1)
        self.assertIn("SystemSpecialist", summary["structure_summary"])

    def test_orchestrator_local_knowledge_intents(self):
        # 1. Search local docs intent
        search_intent = orchestrator.handle_intent("yerel dokümanlarda ara: permission guard")
        self.assertEqual(search_intent["specialist"], "ResearchSpecialist")
        self.assertEqual(search_intent["intent"], "search_local_docs")
        self.assertIn("query", search_intent)
        self.assertIn("Sayın Hilmi", search_intent["speak_text"])

        # 2. Summarize document intent
        doc_intent = orchestrator.handle_intent("doküman özetle: JARVIS_CAPABILITIES_MASTER.md")
        self.assertEqual(doc_intent["specialist"], "ResearchSpecialist")
        self.assertEqual(doc_intent["intent"], "summarize_file")
        self.assertIn("JARVIS_CAPABILITIES_MASTER.md", doc_intent["speak_text"])

    def test_fastapi_knowledge_endpoints(self):
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {LOCAL_SESSION_TOKEN}"}

        # 1. GET /api/jarvis/knowledge/stats
        stats_resp = client.get("/api/jarvis/knowledge/stats", headers=headers)
        self.assertEqual(stats_resp.status_code, 200)
        self.assertEqual(stats_resp.json()["status"], "success")

        # 2. POST /api/jarvis/knowledge/search
        s_resp = client.post(
            "/api/jarvis/knowledge/search",
            json={"query": "permission guard security level", "top_k": 3},
            headers=headers
        )
        self.assertEqual(s_resp.status_code, 200)
        s_data = s_resp.json()
        self.assertEqual(s_data["status"], "success")
        self.assertIn("results", s_data)

        # 3. POST /api/jarvis/knowledge/summarize
        sum_resp = client.post(
            "/api/jarvis/knowledge/summarize",
            json={"file_path": "JARVIS_CAPABILITIES_MASTER.md"},
            headers=headers
        )
        self.assertEqual(sum_resp.status_code, 200)
        sum_data = sum_resp.json()
        self.assertEqual(sum_data["status"], "success")
        self.assertEqual(sum_data["document"]["file_name"], "JARVIS_CAPABILITIES_MASTER.md")


if __name__ == "__main__":
    unittest.main()
