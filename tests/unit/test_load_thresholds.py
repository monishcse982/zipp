import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-load-thresholds.py"
SPEC = importlib.util.spec_from_file_location("check_load_thresholds", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RedirectThresholdTests(unittest.TestCase):
    def test_unconfigured_thresholds_are_not_evaluated(self):
        self.assertEqual(
            MODULE.evaluate(Path("missing.csv"), "", "", "")["status"],
            "NOT_EVALUATED",
        )
        self.assertIsNone(MODULE.validate_thresholds("", "", ""))

    def test_inputs_can_be_validated_before_running_load(self):
        self.assertEqual(MODULE.validate_thresholds("100", "200", "1")["p95_ms"], 100)
        with self.assertRaises(ValueError):
            MODULE.validate_thresholds("100", "", "1")

    def test_thresholds_use_redirect_row_and_report_failure_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stats.csv"
            path.write_text(
                "Type,Name,Request Count,Failure Count,95%,99%\n"
                "POST,/link/,20,20,9999,9999\n"
                "GET,GET /link/{short_code},200,2,100,200\n",
                encoding="utf-8",
            )
            result = MODULE.evaluate(path, "100", "200", "1")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["observed"]["error_percent"], 1)
            self.assertEqual(MODULE.evaluate(path, "99", "200", "1")["status"], "FAIL")
            self.assertEqual(
                MODULE.evaluate(path, "100", "200", "0.9")["status"], "FAIL"
            )

    def test_partial_invalid_or_missing_data_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stats.csv"
            path.write_text(
                "Type,Name,Request Count,Failure Count,95%,99%\n"
                "GET,GET /link/{short_code},0,0,0,0\n",
                encoding="utf-8",
            )
            cases = (
                ("100", "", "1"),
                ("nan", "100", "1"),
                ("1", "2", "101"),
                ("1", "2", "0"),
            )
            for values in cases:
                with self.subTest(values=values), self.assertRaises(ValueError):
                    MODULE.evaluate(path, *values)
            path.write_text(
                "Type,Name,Request Count,Failure Count,95%,99%\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                MODULE.evaluate(path, "1", "2", "0")


if __name__ == "__main__":
    unittest.main()
