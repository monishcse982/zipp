import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "build-load-report-site.py"
SPEC = importlib.util.spec_from_file_location("build_load_report_site", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT_PATH}")
REPORT_SITE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT_SITE)


class BuildLoadReportSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()
        self.metadata = {
            "commit_sha": "abcdef0123456789",
            "environment": "test",
            "github_run_url": "https://github.com/example/zipp/actions/runs/123",
            "preset": "mixed_redirect_constant_user_100user_5minutes",
            "recorded_at_utc": "2026-11-10T10:05:30+00:00",
            "run_key": "123-1-abcdef0",
            "run_note": "Verify <report> escaping",
            "test_ended_at_utc": "2026-11-10T10:05:00+00:00",
            "test_started_at_utc": "2026-11-10T10:00:00+00:00",
        }
        (self.run_dir / "metadata.json").write_text(
            json.dumps(self.metadata), encoding="utf-8"
        )
        (self.run_dir / "report.html").write_text(
            "<html>Locust</html>", encoding="utf-8"
        )
        for filename in (
            "grafana-application.png",
            "grafana-infrastructure.png",
        ):
            (self.run_dir / filename).write_bytes(b"\x89PNG\r\n\x1a\nfixture")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_bundle_and_merge_create_history_and_latest_pages(self) -> None:
        bundle_dir = self.root / "bundle"
        site_dir = self.root / "site"
        site_dir.mkdir()

        REPORT_SITE.build_bundle(self.run_dir, bundle_dir)
        REPORT_SITE.merge_bundle(bundle_dir, site_dir)

        run_page = site_dir / "runs" / self.metadata["run_key"] / "index.html"
        latest_page = site_dir / "latest" / self.metadata["preset"] / "index.html"
        catalogue = (site_dir / "index.html").read_text(encoding="utf-8")
        self.assertTrue(run_page.is_file())
        self.assertTrue(latest_page.is_file())
        self.assertTrue((site_dir / ".nojekyll").is_file())
        self.assertIn("Verify &lt;report&gt; escaping", catalogue)

    def test_merge_rejects_duplicate_run(self) -> None:
        bundle_dir = self.root / "bundle"
        site_dir = self.root / "site"
        site_dir.mkdir()
        REPORT_SITE.build_bundle(self.run_dir, bundle_dir)
        REPORT_SITE.merge_bundle(bundle_dir, site_dir)

        with self.assertRaises(FileExistsError):
            REPORT_SITE.merge_bundle(bundle_dir, site_dir)

    def test_metadata_rejects_unsafe_run_key(self) -> None:
        metadata_path = self.run_dir / "metadata.json"
        self.metadata["run_key"] = "../../unsafe"
        metadata_path.write_text(json.dumps(self.metadata), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "Invalid run_key"):
            REPORT_SITE.load_metadata(metadata_path)


if __name__ == "__main__":
    unittest.main()
