"""Kiểm tra giao diện dòng lệnh, xuất dữ liệu và thông báo lỗi.

Các kiểm tra subprocess dùng đúng Python hiện đang chạy unittest, nên có
thể chạy trong môi trường .venv mà không phụ thuộc lệnh Python hệ thống.
Không chạy thí nghiệm Monte Carlo đầy đủ hoặc lặp lại kiểm tra mạch Qiskit.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bb84.__main__ import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "bb84", *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )

    def read_json(self, path: Path):
        # Reject JavaScript-style NaN/Infinity even though json.loads allows
        # them by default: exported files must be portable standard JSON.
        def reject_nonfinite(value):
            raise ValueError(f"Non-finite JSON value: {value}")

        return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_nonfinite)

    def test_demo_exports_three_distinct_scenarios_with_matching_summaries(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            folder = Path(temporary) / "demo"
            completed = self.run_cli("demo", "--signals", "2000", "--seed", "84", "--output", str(folder))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Bit ứng viên", completed.stdout)
            records = self.read_json(folder / "demo.json")
            self.assertEqual([row["scenario"] for row in records], ["ideal", "noise", "eve"])
            self.assertEqual(records[0]["qber_actual"], 0)
            self.assertEqual(records[1]["theory"]["expected_qber"], 0.03)
            self.assertEqual(records[2]["theory"]["expected_qber"], 0.25)
            self.assertEqual(records[2]["config"]["eve_fraction"], 1)
            for row in records:
                stored = self.read_json(folder / row["scenario"] / "summary.json")
                self.assertEqual(stored, {key: value for key, value in row.items() if key != "scenario"})
                self.assertFalse((folder / row["scenario"] / "trace.csv").exists())

    def test_simulate_sample_size_overrides_fraction_in_exported_data(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            folder = Path(temporary) / "run with spaces"
            completed = self.run_cli(
                "simulate", "--signals", "2000", "--eve", "0.4",
                "--noise", "0.02", "--noise-model", "readout_flip",
                "--sample-size", "73", "--sample-fraction", "0.9",
                "--seed", "8401", "--trace", "--output", str(folder),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = self.read_json(folder / "summary.json")
            self.assertEqual(summary["n_test"], 73)
            self.assertEqual(summary["requested_sample_size"], 73)
            self.assertEqual(summary["seed"], 8401)
            self.assertEqual(summary["config"]["noise_model"], "readout_flip")
            self.assertAlmostEqual(summary["theory"]["expected_qber"], 0.116)
            self.assertEqual(summary["n_sifted"], summary["n_test"] + summary["n_remaining"])
            with (folder / "trace.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2000)
            self.assertEqual(sum(int(row["public_test"]) for row in rows), 73)
            self.assertEqual(sum(int(row["candidate"]) for row in rows), summary["n_remaining"])
            for row in rows:
                self.assertFalse(row["public_test"] == "1" and row["candidate"] == "1")
                self.assertEqual(int(row["sifted"]), int(row["public_test"]) + int(row["candidate"]))
            self.assertIn("64/2000", completed.stdout)

    def test_lost_trace_hides_simulated_bob_values_and_undefined_qber_is_null(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            folder = Path(temporary)
            completed = self.run_cli(
                "simulate", "--signals", "16", "--loss", "1", "--trace", "--output", str(folder),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("lost", completed.stdout)
            summary = self.read_json(folder / "summary.json")
            self.assertEqual(summary["decision"], "insufficient_data")
            self.assertEqual(summary["n_detected"], 0)
            for field in ("qber_actual", "qber_estimate", "qber_remaining"):
                self.assertIsNone(summary[field])
            self.assertEqual(summary["qber_interval"], [None, None])
            with (folder / "trace.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 16)
            self.assertEqual([int(row["position"]) for row in rows], list(range(1, 17)))
            for row in rows:
                self.assertEqual(row["bob_bit"], "lost")
                self.assertEqual(row["mismatch_if_sifted"], "-")
                self.assertEqual(row["eve_basis"], "-")
                self.assertEqual(row["eve_bit"], "-")
                for flag in ("detected", "sifted", "public_test", "candidate"):
                    self.assertEqual(row[flag], "0")

    def test_same_seed_reproduces_exported_json_and_csv(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            folders = [Path(temporary) / name for name in ("first", "second")]
            for folder in folders:
                completed = self.run_cli(
                    "simulate", "--signals", "100", "--eve", "0.5", "--loss", "0.2",
                    "--noise", "0.1", "--seed", "123", "--trace", "--output", str(folder),
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
            for filename in ("summary.json", "trace.csv"):
                self.assertEqual((folders[0] / filename).read_bytes(), (folders[1] / filename).read_bytes())

    def test_reused_output_without_trace_removes_previous_run_trace(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            folder = Path(temporary)
            first = self.run_cli(
                "simulate", "--signals", "100", "--seed", "123", "--trace", "--output", str(folder),
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((folder / "trace.csv").is_file())
            # This CSV described seed 123. It must not sit next to a new
            # seed-456 summary and falsely appear to be that run's trace.
            second = self.run_cli(
                "simulate", "--signals", "100", "--seed", "456", "--output", str(folder),
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(self.read_json(folder / "summary.json")["seed"], 456)
            self.assertFalse((folder / "trace.csv").exists())

    def test_invalid_parameters_exit_cleanly_before_export(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            invalid_arguments = (
                ("--signals", "0"), ("--signals", "1.5"), ("--seed", "-1"),
                ("--eve", "nan"), ("--noise", "1.1"), ("--sample-size", "0"),
                ("--confidence", "1"), ("--noise-model", "undefined"),
            )
            for index, arguments in enumerate(invalid_arguments):
                with self.subTest(arguments=arguments):
                    folder = Path(temporary) / str(index)
                    completed = self.run_cli("simulate", *arguments, "--output", str(folder))
                    self.assertEqual(completed.returncode, 2)
                    self.assertTrue(completed.stderr.strip())
                    self.assertNotIn("Traceback", completed.stderr)
                    self.assertFalse(folder.exists())

    def test_output_path_error_has_actionable_cli_message_without_traceback(self):
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            file_path = Path(temporary) / "occupied.txt"
            file_path.write_text("This is a file, not a directory.", encoding="utf-8")
            completed = self.run_cli("simulate", "--signals", "16", "--output", str(file_path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("Lỗi:", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertEqual(file_path.read_text(encoding="utf-8"), "This is a file, not a directory.")


class QiskitCommandRoutingTests(unittest.TestCase):
    def test_qiskit_cli_passes_parameters_and_exports_returned_results(self):
        rows = [{
            "preparation_basis": "Z", "alice_bit": 0, "measurement_basis": "X",
            "expected_p_one": 0.5, "observed_p_one": 0.5, "counts": {"0": 16, "1": 16},
        }]
        with tempfile.TemporaryDirectory(prefix="bb84-cli-") as temporary:
            output = io.StringIO()
            with patch("bb84.qiskit_demo.run_qiskit_check", return_value=rows) as quantum_check:
                with redirect_stdout(output):
                    status = main(["qiskit-check", "--shots", "32", "--seed", "123", "--output", temporary])
            self.assertEqual(status, 0)
            quantum_check.assert_called_once_with(32, 123)
            stored = json.loads((Path(temporary) / "qiskit_check.json").read_text(encoding="utf-8"))
            self.assertEqual(stored, rows)
            self.assertIn("AerSimulator", output.getvalue())

    def test_qiskit_missing_dependency_preserves_install_guidance(self):
        output = io.StringIO()
        guidance = "Install optional tools: python -m pip install qiskit qiskit-aer"
        with patch("bb84.qiskit_demo.run_qiskit_check", side_effect=RuntimeError(guidance)):
            with redirect_stderr(output), self.assertRaises(SystemExit) as raised:
                main(["qiskit-check"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn(guidance, output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
