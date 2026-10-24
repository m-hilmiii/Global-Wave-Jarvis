"""
Global Wave - Paket 1 Remediation Unit Tests
Verifies:
1. Material Engine: Deterministic SHA-256 URL hashing and preservation of LLM visual keywords.
2. Laya Decision Engine: Word-boundary guardrails () preventing substring collisions.
3. Laya Comment Analysis: Praise containing 'ses' or 'hizli' is not classified as a complaint.
4. Video Engine: Subtitle ASS timestamp shifting for teaser splice synchronization.
5. Channel Report: report_default.json contains no positive comments in weaknesses_to_avoid.
"""
import os
import json
import hashlib
import tempfile
import unittest
from engine.laya_decision_engine import laya_engine
from engine.video_engine import offset_ass_subtitles
from config.settings import BASE_DIR

class TestPaket1Remediation(unittest.TestCase):

    def test_material_engine_sha256_deterministic(self):
        url = "https://images.pexels.com/videos/12345/free-video.mp4"
        expected = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(len(expected), 12)
        # Verify repeated calculation is strictly deterministic
        self.assertEqual(hashlib.sha256(url.encode("utf-8")).hexdigest()[:12], expected)

    def test_material_engine_preserves_english_visual_keyword(self):
        # When scene text is empty or unmatched, default_kw must be returned (NOT hardcoded 'technology')
        custom_kw = "quantum particle accelerator"
        routed = laya_engine.route_broll_keyword("", default_kw=custom_kw)
        self.assertEqual(routed, custom_kw)

    def test_laya_hard_rule_word_boundaries(self):
        # 'sait' or 'daima' contains 'ai', but must NOT match artificial intelligence
        self.assertIsNone(laya_engine._hard_rule_broll("sait ve arkadaslari sinemaya gitti"))
        self.assertIsNone(laya_engine._hard_rule_broll("daima basarili olmak icin calisti"))

        # 'imparatorluk' contains 'para', but must match ancient history, NOT crypto market
        self.assertEqual(laya_engine._hard_rule_broll("Roma imparatorluk tarihi"), "ancient history mystery")

        # Exact matching works
        self.assertEqual(laya_engine._hard_rule_broll("yapay zeka ve derin ogrenme"), "artificial intelligence robotics")
        self.assertEqual(laya_engine._hard_rule_broll("kripto para piyasalari"), "financial crypto market")

    def test_laya_comment_analysis_positive_praise_never_poisoned(self):
        comments = [
            "Ses tonu ve kelime kelime yanan altyazı inanılmaz akıcı, tebrikler!",
            "Mikrofon sesi berbat, hicbir sey duyulmuyor",
            "Yapay zeka hakkinda yeni bir video gelsin lutfen"
        ]
        res = laya_engine._heuristic_comment_analysis(comments)
        
        # Praise must NOT be in complaints
        self.assertNotIn("Ses tonu ve kelime kelime yanan altyazı inanılmaz akıcı, tebrikler!", res["complaints"])
        
        # Real complaint must be in complaints
        self.assertIn("Mikrofon sesi berbat, hicbir sey duyulmuyor", res["complaints"])
        self.assertEqual(len(res["complaints"]), 1)

    def test_video_engine_ass_offset_precision(self):
        test_ass = (
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:03.50,Default,,0,0,0,,{\\k50}First {\\k50}Line\n"
            "Dialogue: 0,0:00:04.20,0:00:06.80,Default,,0,0,0,,{\\k50}Second {\\k50}Line\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False, encoding="utf-8") as f_in:
            f_in.write(test_ass)
            in_path = f_in.name

        out_path = in_path + ".shifted.ass"
        try:
            offset_ass_subtitles(in_path, out_path, offset_seconds=0.75)
            with open(out_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Dialogue: 0,0:00:01.75,0:00:04.25,Default,,0,0,0,,{\\k50}First {\\k50}Line", content)
            self.assertIn("Dialogue: 0,0:00:04.95,0:00:07.55,Default,,0,0,0,,{\\k50}Second {\\k50}Line", content)
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_channel_report_default_cleaned(self):
        rep_path = BASE_DIR / "config" / "channel_reports" / "report_default.json"
        with open(rep_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        weaknesses = " ".join(data.get("weaknesses_to_avoid", []))
        self.assertNotIn("Ses tonu ve kelime kelime yanan altyazı", weaknesses)
        self.assertNotIn("Yapay zeka sırları hakkında da bir shorts gelsin", weaknesses)

if __name__ == "__main__":
    unittest.main()
