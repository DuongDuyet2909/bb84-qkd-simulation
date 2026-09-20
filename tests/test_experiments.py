"""Experiment-level checks: real simulation, saved provenance and plot exports."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import numpy as np

from bb84.core import BB84Config, simulate
from bb84.experiments import _run_seed, _simulate_rows, run_experiments
from bb84.theory import asymptotic_secret_fraction, expected_qber, probability_detect_error


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class SeedAndProvenanceTests(unittest.TestCase):
    def test_runs_reproduce_even_when_configuration_order_changes(self):
        configs = [BB84Config(n_signals=256, eve_fraction=f) for f in (0.0, 0.5)]
        original = _simulate_rows("test", configs, repetitions=2, seed=84)
        reordered = _simulate_rows("test", reversed(configs), repetitions=3, seed=84)
        indexed = {row["seed"]: row for row in reordered}
        for row in original:
            self.assertEqual(row, indexed[row["seed"]])
        self.assertEqual(len(indexed), 6)
        self.assertNotEqual(
            _run_seed(84, "test", asdict(configs[0]), 0),
            _run_seed(85, "test", asdict(configs[0]), 0),
        )
        self.assertNotEqual(
            _run_seed(84, "test", asdict(configs[0]), 0),
            _run_seed(84, "another_experiment", asdict(configs[0]), 0),
        )

    def test_recorded_seed_reconstructs_actual_bb84_counts(self):
        config = BB84Config(n_signals=1024, eve_fraction=0.4, noise_probability=0.1, loss_probability=0.2)
        row = _simulate_rows("test", [config], repetitions=1, seed=7)[0]
        result = simulate(config, seed=row["seed"])
        for column in ("n_detected", "n_sifted", "n_test", "n_remaining", "actual_errors", "test_errors"):
            self.assertEqual(row[column], getattr(result, column))
        for field, value in asdict(config).items():
            self.assertEqual(row[field], value)
        self.assertEqual(row["expected_qber"], expected_qber(0.4, 0.1, "depolarizing"))
        self.assertNotIn("alice_bits", row)
        self.assertNotIn("bob_bits", row)

    def test_invalid_experiment_sizes_fail_before_running(self):
        with tempfile.TemporaryDirectory() as directory:
            for parameters in (
                {"preset": "unknown"}, {"n_signals": 63}, {"n_signals": True},
                {"repetitions": 1}, {"repetitions": 2.5}, {"seed": -1},
            ):
                with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                    run_experiments(directory, **parameters)


class ExperimentExportTests(unittest.TestCase):
    """Run the suite once at a small main N; detection remains at 500 runs."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.output = Path(cls.directory.name)
        cls.progress = []
        cls.manifest = run_experiments(cls.output, n_signals=128, repetitions=2, seed=84, progress=cls.progress.append)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_six_pngs_pdfs_csvs_and_strict_json_manifest(self):
        self.assertEqual(len(self.manifest["experiments"]), 6)
        self.assertEqual(len(self.progress), 6)
        json.dumps(self.manifest, allow_nan=False)
        for experiment in self.manifest["experiments"]:
            with self.subTest(experiment=experiment["id"]):
                png = self.output / experiment["figure"]
                pdf = self.output / experiment["pdf"]
                self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(pdf.read_bytes()[:5], b"%PDF-")
                self.assertGreater(png.stat().st_size, 10_000)
                self.assertGreater(len(read_csv(self.output / experiment["summary_csv"])), 1)
                self.assertTrue(experiment["findings"])
                self.assertTrue(experiment["error_semantics"])

    def test_csv_counts_and_seeds_are_consistent_and_unique(self):
        seen_seeds = set()
        for experiment in self.manifest["experiments"]:
            if experiment["raw_csv"] is None:
                continue
            rows = read_csv(self.output / experiment["raw_csv"])
            for row in rows:
                with self.subTest(experiment=experiment["id"], repeat=row["repeat"]):
                    run_seed = int(row["seed"])
                    self.assertNotIn(run_seed, seen_seeds)
                    seen_seeds.add(run_seed)
                    self.assertEqual(int(row["n_sifted"]), int(row["n_test"]) + int(row["n_remaining"]))
                    self.assertLessEqual(int(row["n_sifted"]), int(row["n_detected"]))
                    self.assertLessEqual(int(row["test_errors"]), int(row["n_test"]))
                    expected = expected_qber(float(row["eve_fraction"]), float(row["noise_probability"]), row["noise_model"])
                    self.assertAlmostEqual(float(row["expected_qber"]), expected, places=14)
                    if int(row["n_test"]):
                        self.assertAlmostEqual(float(row["qber_estimate"]), int(row["test_errors"]) / int(row["n_test"]), places=14)
                    else:
                        self.assertEqual(row["qber_estimate"], "")

    def test_summary_is_computed_from_raw_not_a_theory_placeholder(self):
        experiment = self.manifest["experiments"][0]
        raw = read_csv(self.output / experiment["raw_csv"])
        summary = read_csv(self.output / experiment["summary_csv"])
        for row in summary:
            selected = [float(item["qber_estimate"]) for item in raw
                if item["noise_probability"] == row["noise_probability"] and item["eve_fraction"] == row["eve_fraction"]]
            self.assertAlmostEqual(float(row["qber_estimate_mean"]), np.mean(selected), places=14)
            self.assertAlmostEqual(float(row["qber_estimate_sem"]), np.std(selected, ddof=1) / np.sqrt(len(selected)), places=14)

    def test_detection_uses_full_bb84_and_wilson_bounds(self):
        experiment = self.manifest["experiments"][3]
        summary = read_csv(self.output / experiment["summary_csv"])
        for row in summary:
            self.assertEqual(int(row["repetitions_requested"]), 500)
            self.assertEqual(int(row["complete_runs"]), 500)
            self.assertEqual(int(row["incomplete_runs"]), 0)
            self.assertEqual(int(row["n_signals"]), max(512, 8 * int(row["sample_size"])))
            probability = float(row["probability_estimate"])
            self.assertLessEqual(float(row["probability_ci_low"]), probability + 1e-14)
            self.assertGreaterEqual(float(row["probability_ci_high"]), probability - 1e-14)
            theory = probability_detect_error(float(row["expected_qber"]), int(row["sample_size"]))
            self.assertAlmostEqual(float(row["theory_probability"]), theory, places=14)
            # At R=500 the largest possible SEM is ~0.0224. This deliberately
            # generous deterministic-seed bound catches gross pipeline errors.
            self.assertLess(abs(probability - theory), 0.1)

    def test_theoretical_plot_contains_only_reference_values(self):
        experiment = self.manifest["experiments"][5]
        self.assertIsNone(experiment["raw_csv"])
        self.assertEqual(experiment["run_count"], 0)
        rows = read_csv(self.output / experiment["summary_csv"])
        for row in rows:
            q, f_ec = float(row["qber"]), float(row["f_ec"])
            self.assertEqual(row["source"], "theory_only")
            self.assertAlmostEqual(float(row["secret_fraction_reference"]), asymptotic_secret_fraction(q, f_ec=f_ec), places=14)
            self.assertNotIn("seed", row)


if __name__ == "__main__":
    unittest.main()
