"""Navigation and verdict presentation must remain accurate and escape source text."""

from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "plugins/oss-gate"), str(ROOT / "tests")]
from core.repo_render import report_body, render_repository
from core.render import verdict_seal
from core.repo_review import collect_repository
from core.snapshot import verify
from test_repository_go_cargo import write
from test_repository_jvm_swift_container import TRIVY


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links = [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs)


class RepositoryDesign(unittest.TestCase):
    def test_bilingual_seal_matches_saved_verdict_and_all_contents_links_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write(root, {"trivy.json": json.dumps(TRIVY)})
            result = collect_repository(root, str(Path(tmp) / "out"))
            folder = Path(result["folder"])
            hashes = verify(folder)
            render_repository(folder, "both")
            self.assertEqual(verify(folder), hashes)
            data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
            for lang in ("ko", "en"):
                html = (folder / f"report.{lang}.html").read_text(encoding="utf-8")
                self.assertIn(verdict_seal("hold", lang, data["generated_at"][:10]), html)
                self.assertIn('class="toc repository-toc"', html)
                elements = Elements(html)
                self.assertEqual(len(elements.ids), len(set(elements.ids)))
                fragments = [a["href"][1:] for a in elements.links if a.get("href", "").startswith("#")]
                self.assertGreater(len(fragments), 5)
                self.assertTrue(set(fragments) <= set(elements.ids))
                self.assertTrue(any(a.get("lang") == lang and a.get("aria-current") == "page" for a in elements.links))
                self.assertIn("CVE-2025-0001", html)
                self.assertIn("컨테이너 검사 가져오기" if lang == "ko" else "Imported container scans", html)
                self.assertNotIn('href="#maintenance"', html)

    def test_heading_destinations_ignore_fenced_text_and_escape_hostile_labels(self):
        body, sections = report_body("## <img src=x onerror=alert(1)>\n\n```\n## not a section\n```\n\n## Evidence")
        self.assertEqual(len(sections), 2)
        self.assertNotIn("<img", body)
        self.assertIn("&lt;img", body)
        self.assertEqual([i for i, _ in sections], ["repository-section-1", "repository-section-2"])
        self.assertEqual(len(Elements(body).ids), 2)

    def test_seal_preserves_grade_language_and_escapes_recorded_date(self):
        for grade, color in (("allow", "good"), ("conditional", "warn"), ("hold", "serious")):
            for lang, label in (("ko", "판정"), ("en", "Verdict")):
                html = verdict_seal(grade, lang, "<script>bad</script>")
                self.assertIn(f'class="seal st-{color}"', html)
                self.assertIn(label, html)
                self.assertNotIn("<script>", html)
                self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
