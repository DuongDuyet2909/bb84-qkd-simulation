"""Kiểm tra báo cáo có thể mở độc lập và giữ thông tin tái lập kết quả."""

from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

from bb84.report import build_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []
        self.script_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.script_count += 1
        for name, value in attrs:
            if name in ("src", "href") and value:
                self.references.append(value)


class ReportTests(unittest.TestCase):
    def fixture(self, output: Path):
        # The report links existing assets without decoding them; actual
        # PNG/PDF validity is covered by experiment export tests.
        assets = {
            "figure": "figures/example.png",
            "pdf": "figures/example.pdf",
            "raw_csv": "data/example_raw.csv",
            "summary_csv": "data/example_summary.csv",
        }
        for value in assets.values():
            path = output / value
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test fixture asset\n")
        return {
            "preset": "quick", "seed": 84, "n_signals": 128,
            "repetitions": 2, "duration_seconds": 0.01,
            "config": {"preset": "quick", "seed": 84, "n_signals": 128, "repetitions": 2},
            "experiments": [{
                "id": "example", "title": "Ví dụ BB84", "description": "Dữ liệu kiểm tra",
                **assets, "findings": ["QBER mẫu được công bố."],
                "error_semantics": "Mean +/- 1 SEM across independent runs.", "run_count": 2,
            }],
            "highlights": ["Kiểm tra giữ nguyên tham số và kết quả."],
            "error_semantics": {"example": "1 SEM"},
            "data_notes": ["Candidate bits are not secret keys."],
        }

    def test_local_asset_links_exist_and_metadata_preserves_provenance(self):
        with tempfile.TemporaryDirectory(prefix="bb84-report-") as temporary:
            output = Path(temporary)
            manifest = self.fixture(output)
            original = copy.deepcopy(manifest)
            report_path = build_report(output, manifest)
            self.assertEqual(report_path.resolve(), (output / "report.html").resolve())
            self.assertTrue(report_path.is_file())
            parser = AssetReferences()
            parser.feed(report_path.read_text(encoding="utf-8"))
            local_references = []
            for reference in parser.references:
                parsed = urlsplit(reference)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                local_references.append(parsed.path)
                self.assertTrue((output / unquote(parsed.path)).is_file(), reference)
            self.assertIn("figures/example.png", local_references)
            self.assertIn("figures/example.pdf", local_references)
            self.assertIn("data/example_raw.csv", local_references)
            self.assertIn("data/example_summary.csv", local_references)
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            for field in ("config", "experiments", "highlights", "data_notes", "seed", "n_signals", "repetitions"):
                self.assertEqual(metadata[field], original[field])
            source_hashes = metadata["environment"]["source_sha256"]
            self.assertIn("core.py", source_hashes)
            self.assertIn("theory.py", source_hashes)
            self.assertIn("report.py", source_hashes)
            for filename, digest in source_hashes.items():
                source = PROJECT_ROOT / "bb84" / filename
                self.assertEqual(digest, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_custom_titles_and_findings_are_escaped_html_text(self):
        with tempfile.TemporaryDirectory(prefix="bb84-report-") as temporary:
            output = Path(temporary)
            manifest = self.fixture(output)
            title = '<script>alert("title")</script> & QBER'
            finding = '<img src="missing.png" onerror="alert(1)">'
            manifest["experiments"][0]["title"] = title
            manifest["experiments"][0]["findings"] = [finding]
            manifest["highlights"] = [finding]
            path = build_report(output, manifest)
            html = path.read_text(encoding="utf-8")
            self.assertNotIn(title, html)
            self.assertNotIn(finding, html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("&lt;img", html)
            parser = AssetReferences()
            parser.feed(html)
            self.assertEqual(parser.script_count, 0)
            self.assertNotIn("missing.png", parser.references)
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["experiments"][0]["title"], title)

    def test_missing_and_outside_assets_are_rejected_before_report_publication(self):
        with tempfile.TemporaryDirectory(prefix="bb84-report-") as temporary:
            root = Path(temporary)
            outside = root / "outside.png"
            outside.write_bytes(b"outside fixture")
            for index, figure in enumerate(("figures/missing.png", "../outside.png")):
                with self.subTest(figure=figure):
                    output = root / f"case-{index}"
                    manifest = self.fixture(output)
                    manifest["experiments"][0]["figure"] = figure
                    with self.assertRaises((ValueError, OSError)) as raised:
                        build_report(output, manifest)
                    self.assertTrue(str(raised.exception).strip())
                    self.assertFalse((output / "report.html").exists())
            self.assertEqual(outside.read_bytes(), b"outside fixture")


if __name__ == "__main__":
    unittest.main()
