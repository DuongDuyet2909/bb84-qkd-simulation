"""Kiểm tra quy tắc vật lý, bất biến giao thức và mốc thống kê BB84.

Các ngưỡng thống kê dùng sai số chuẩn nhị thức (7 sigma) và seed cố định;
không so sánh kết quả Monte Carlo với một số đếm chính xác tùy ý.
Chạy: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from dataclasses import replace
from unittest.mock import patch

import numpy as np

from bb84.core import BB84Config, simulate
from bb84.qiskit_demo import run_qiskit_check
from bb84.theory import expected_qber, expected_sift_fraction


class BB84ProtocolTests(unittest.TestCase):
    def assert_binomial_rate(self, successes, trials, expected):
        self.assertGreater(trials, 0)
        tolerance = 7 * math.sqrt(expected * (1 - expected) / trials) + 1 / trials
        self.assertAlmostEqual(successes / trials, expected, delta=tolerance)

    def test_ideal_measurements_and_sifting(self):
        result = simulate(BB84Config(n_signals=120_000), seed=8401)
        same_basis = result.alice_bases == result.bob_bases
        errors = result.alice_bits != result.bob_bits
        np.testing.assert_array_equal(result.sift_mask, same_basis)
        self.assertFalse(np.any(errors[same_basis]))
        self.assert_binomial_rate(np.count_nonzero(same_basis), len(same_basis), 0.5)
        # Đây là kiểm tra đo khác cơ sở; các bit này bị bỏ khi sifting.
        self.assert_binomial_rate(np.count_nonzero(errors[~same_basis]), np.count_nonzero(~same_basis), 0.5)
        self.assertEqual(result.qber_actual, 0.0)

    def test_full_intercept_resend_produces_quarter_qber(self):
        result = simulate(BB84Config(n_signals=180_000, eve_fraction=1), seed=8402)
        self.assertTrue(np.all(result.eve_mask))
        self.assert_binomial_rate(
            np.count_nonzero((result.alice_bits != result.bob_bits) & result.sift_mask),
            result.n_sifted,
            0.25,
        )
        # Khi cả Eve và Bob chọn đúng cơ sở Alice, Eve không gây lỗi.
        all_matched = result.sift_mask & (result.eve_bases == result.alice_bases)
        np.testing.assert_array_equal(result.alice_bits[all_matched], result.bob_bits[all_matched])
        np.testing.assert_array_equal(result.alice_bits[all_matched], result.eve_bits[all_matched])
        self.assertEqual(result.decision, "abort")

    def test_born_rule_for_each_preparation_and_measurement_basis(self):
        # Aggregate QBER can hide opposite biases in different states.
        # Check all four BB84 preparations against both measurement bases.
        result = simulate(BB84Config(n_signals=160_000), seed=8420)
        for preparation_basis in (0, 1):
            for bit in (0, 1):
                for measurement_basis in (0, 1):
                    with self.subTest(preparation_basis=preparation_basis, bit=bit, measurement_basis=measurement_basis):
                        mask = (
                            (result.alice_bases == preparation_basis)
                            & (result.alice_bits == bit)
                            & (result.bob_bases == measurement_basis)
                        )
                        outcomes = result.bob_bits[mask]
                        self.assertGreater(outcomes.size, 0)
                        if preparation_basis == measurement_basis:
                            np.testing.assert_array_equal(outcomes, np.full(outcomes.size, bit))
                        else:
                            self.assert_binomial_rate(np.count_nonzero(outcomes), outcomes.size, 0.5)

    def test_partial_eve_and_independent_noise_match_theory(self):
        for model, noise in (("depolarizing", 0.16), ("readout_flip", 0.08)):
            with self.subTest(model=model):
                result = simulate(
                    BB84Config(n_signals=180_000, eve_fraction=0.4, noise_probability=noise, noise_model=model),
                    seed=8403,
                )
                expected = expected_qber(0.4, noise, model)
                self.assert_binomial_rate(
                    np.count_nonzero((result.alice_bits != result.bob_bits) & result.sift_mask),
                    result.n_sifted,
                    expected,
                )

    def test_noise_conventions_have_distinct_endpoints(self):
        depolarized = simulate(
            BB84Config(n_signals=120_000, noise_probability=1, noise_model="depolarizing"), seed=8404
        )
        self.assert_binomial_rate(
            np.count_nonzero((depolarized.alice_bits != depolarized.bob_bits) & depolarized.sift_mask),
            depolarized.n_sifted,
            0.5,
        )
        flipped = simulate(
            BB84Config(n_signals=2000, noise_probability=1, noise_model="readout_flip"), seed=8405
        )
        self.assertEqual(flipped.qber_actual, 1.0)

    def test_biased_bases_and_loss_match_count_model(self):
        p_z, loss = 0.8, 0.3
        result = simulate(
            BB84Config(n_signals=180_000, basis_probability_z=p_z, loss_probability=loss), seed=8406
        )
        np.testing.assert_array_equal(
            result.sift_mask,
            result.detected_mask & (result.alice_bases == result.bob_bases),
        )
        self.assert_binomial_rate(result.n_detected, len(result.detected_mask), 1 - loss)
        self.assert_binomial_rate(result.n_sifted, len(result.sift_mask), expected_sift_fraction(p_z, loss))
        self.assertEqual(result.qber_actual, 0.0)

    def test_samples_are_removed_and_partition_sifted_bits(self):
        result = simulate(BB84Config(n_signals=5000, sample_size=173), seed=8407)
        self.assertEqual(result.n_test, 173)
        self.assertFalse(np.any(result.test_mask & result.key_mask))
        np.testing.assert_array_equal(result.sift_mask, result.test_mask | result.key_mask)
        self.assertEqual(result.n_sifted, result.n_test + result.n_remaining)
        self.assertFalse(np.any(result.test_mask & ~result.detected_mask))
        self.assertFalse(np.any(result.key_mask & ~result.detected_mask))

    def test_public_sample_decision_does_not_read_undisclosed_errors(self):
        result = simulate(BB84Config(n_signals=5000, sample_size=500), seed=8421)
        # Only the simulator can inspect these hidden bits. Replacing every
        # undisclosed Bob bit must not affect Alice/Bob's public decision.
        altered_bits = result.bob_bits.copy()
        altered_bits[result.key_mask] ^= 1
        altered_bits.setflags(write=False)
        altered = replace(result, bob_bits=altered_bits)
        self.assertEqual(result.qber_remaining, 0)
        self.assertEqual(altered.qber_remaining, 1)
        self.assertNotEqual(result.qber_actual, altered.qber_actual)
        self.assertEqual(result.test_errors, altered.test_errors)
        self.assertEqual(result.qber_estimate, altered.qber_estimate)
        self.assertEqual(result.qber_interval, altered.qber_interval)
        self.assertEqual(result.decision, altered.decision)

    def test_sample_size_overrides_fraction_and_summary_omits_raw_bits(self):
        result = simulate(BB84Config(n_signals=3000, sample_size=111, sample_fraction=0.9), seed=8422)
        self.assertEqual(result.requested_sample_size, 111)
        self.assertEqual(result.n_test, 111)
        summary = result.summary()
        for field_name in ("alice_bits", "bob_bits", "eve_bits", "test_mask", "key_mask"):
            self.assertNotIn(field_name, summary)

    def test_eve_knowledge_refers_to_alice_bits_and_unintercepted_entries_are_absent(self):
        result = simulate(
            BB84Config(n_signals=8000, eve_fraction=0.4, noise_probability=1, noise_model="readout_flip"),
            seed=8423,
        )
        known_remaining = result.eve_known_mask & result.key_mask
        self.assertGreater(np.count_nonzero(known_remaining), 0)
        np.testing.assert_array_equal(result.eve_bits[known_remaining], result.alice_bits[known_remaining])
        self.assertTrue(np.all(result.eve_bits[known_remaining] != result.bob_bits[known_remaining]))
        self.assertTrue(np.all(result.eve_bases[~result.eve_mask] == -1))
        self.assertTrue(np.all(result.eve_bits[~result.eve_mask] == -1))
        self.assertFalse(np.any(result.eve_known_mask & ~result.eve_mask))

    def test_all_lost_signals_cannot_be_accepted(self):
        result = simulate(BB84Config(n_signals=1000, loss_probability=1), seed=8408)
        self.assertEqual(result.n_detected, 0)
        self.assertEqual(result.n_sifted, 0)
        self.assertEqual(result.n_test, 0)
        self.assertEqual(result.n_remaining, 0)
        self.assertEqual(result.decision, "insufficient_data")
        self.assertTrue(math.isnan(result.qber_actual))
        self.assertTrue(math.isnan(result.qber_estimate))
        self.assertTrue(math.isnan(result.qber_remaining))
        self.assertIsNone(result.summary()["qber_actual"])

    def test_no_sample_cannot_be_accepted(self):
        # floor(0.2 * 2) = 0: legitimate tiny experiments can lack test bits.
        result = simulate(BB84Config(n_signals=2, basis_probability_z=1, sample_fraction=0.2), seed=8409)
        self.assertGreater(result.n_remaining, 0)
        self.assertEqual(result.n_test, 0)
        self.assertEqual(result.decision, "insufficient_data")

    def test_exhausted_remaining_string_cannot_be_accepted(self):
        result = simulate(BB84Config(n_signals=2000, sample_size=2000), seed=8410)
        self.assertEqual(result.n_test, result.n_sifted)
        self.assertEqual(result.n_remaining, 0)
        self.assertEqual(result.decision, "insufficient_data")

    def test_tiny_clean_sample_does_not_imply_low_underlying_error(self):
        result = simulate(BB84Config(n_signals=2000, sample_size=1, abort_threshold=0.11), seed=8411)
        self.assertEqual(result.qber_estimate, 0.0)
        self.assertGreater(result.qber_interval[1], 0.11)
        self.assertNotEqual(result.decision, "continue_postprocessing")

    def test_large_clean_sample_can_continue_postprocessing(self):
        result = simulate(BB84Config(n_signals=4000, sample_size=1000), seed=8412)
        self.assertLess(result.qber_interval[1], 0.11)
        self.assertEqual(result.decision, "continue_postprocessing")

    def test_deterministic_seed_reproduces_every_protocol_array(self):
        config = BB84Config(n_signals=3000, eve_fraction=0.31, noise_probability=0.04, loss_probability=0.15)
        first, second = simulate(config, seed=8413), simulate(config, seed=8413)
        for name in (
            "alice_bits", "alice_bases", "bob_bases", "bob_bits", "eve_mask", "eve_bases", "eve_bits",
            "detected_mask", "sift_mask", "test_mask", "key_mask",
        ):
            np.testing.assert_array_equal(getattr(first, name), getattr(second, name), err_msg=name)
        self.assertEqual(first.summary(), second.summary())
        third = simulate(config, seed=8414)
        self.assertFalse(np.array_equal(first.alice_bits, third.alice_bits))

    def test_seed_sequence_children_are_replayable_and_distinct(self):
        config = BB84Config(n_signals=3000, eve_fraction=0.3)
        first_child, second_child = np.random.SeedSequence(84).spawn(2)
        first = simulate(config, first_child)
        replay = simulate(config, np.random.SeedSequence(**first.seed))
        second = simulate(config, second_child)
        self.assertEqual(first.summary(), replay.summary())
        np.testing.assert_array_equal(first.bob_bits, replay.bob_bits)
        np.testing.assert_array_equal(first.test_mask, replay.test_mask)
        self.assertFalse(np.array_equal(first.alice_bits, second.alice_bits))

    def test_simulation_leaves_global_numpy_rng_unchanged(self):
        before = np.random.get_state()
        simulate(BB84Config(n_signals=1000, eve_fraction=0.2), seed=8424)
        after = np.random.get_state()
        self.assertEqual(before[0], after[0])
        np.testing.assert_array_equal(before[1], after[1])
        self.assertEqual(before[2:], after[2:])

    def test_protocol_arrays_reject_accidental_mutation(self):
        result = simulate(BB84Config(n_signals=100), seed=8425)
        for name in (
            "alice_bits", "alice_bases", "bob_bases", "bob_bits", "eve_mask", "eve_bases", "eve_bits",
            "detected_mask", "sift_mask", "test_mask", "key_mask", "eve_known_mask",
        ):
            array = getattr(result, name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                array[0] = 0

    def test_endpoint_basis_choice_has_no_complementary_basis_evidence(self):
        for probability_z, absent_basis in ((0, "Z"), (1, "X")):
            with self.subTest(probability_z=probability_z):
                result = simulate(BB84Config(n_signals=1000, basis_probability_z=probability_z), seed=8426)
                self.assertEqual(result.n_sifted, 1000)
                self.assertEqual(result.per_basis[absent_basis]["n_test"], 0)
                self.assertTrue(math.isnan(result.per_basis[absent_basis]["qber_estimate"]))
                self.assertIsNone(result.summary()["per_basis"][absent_basis]["qber_estimate"])

    def test_invalid_seeds_are_rejected(self):
        for seed in (-1, True, np.bool_(False), 1.5, "84", None):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                simulate(BB84Config(n_signals=10), seed=seed)

    def test_json_summary_has_no_nan_even_without_data(self):
        for config in (BB84Config(n_signals=1000), BB84Config(n_signals=1000, loss_probability=1)):
            with self.subTest(config=config):
                summary = simulate(config, seed=8415).summary()
                json.dumps(summary, ensure_ascii=False, allow_nan=False)

    def test_invalid_configuration_is_rejected(self):
        invalid = [
            {"n_signals": 0}, {"n_signals": -1}, {"n_signals": 1.5}, {"n_signals": True},
            {"eve_fraction": -0.01}, {"eve_fraction": 1.01}, {"eve_fraction": float("nan")},
            {"noise_probability": -0.01}, {"noise_probability": float("inf")},
            {"loss_probability": 1.01}, {"basis_probability_z": -0.1},
            {"sample_fraction": 0}, {"sample_fraction": 1}, {"sample_fraction": 1.1},
            {"sample_size": 0}, {"sample_size": -1}, {"sample_size": 2.5},
            {"abort_threshold": -0.1}, {"confidence": 0}, {"confidence": 1},
            {"noise_model": "unspecified_noise"},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises((ValueError, TypeError)):
                    simulate(BB84Config(**overrides), seed=84)


class OptionalQiskitTests(unittest.TestCase):
    def test_missing_dependency_has_actionable_install_message(self):
        with patch.dict("sys.modules", {"qiskit": None}):
            with self.assertRaisesRegex(RuntimeError, "python -m pip install qiskit qiskit-aer"):
                run_qiskit_check()

    def test_arguments_are_validated_without_loading_qiskit(self):
        for kwargs in ({"shots": 0}, {"shots": -1}, {"shots": True}, {"shots": 1.5}, {"seed": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_qiskit_check(**kwargs)

    @unittest.skipUnless(
        importlib.util.find_spec("qiskit") is not None and importlib.util.find_spec("qiskit_aer") is not None,
        "Qiskit/Aer là thư viện tùy chọn; phần NumPy không cần chúng.",
    )
    def test_eight_one_qubit_circuits_agree_with_born_rule(self):
        rows = run_qiskit_check(shots=4096, seed=84)
        self.assertEqual(len(rows), 8)
        combinations = {(row["preparation_basis"], row["alice_bit"], row["measurement_basis"]) for row in rows}
        self.assertEqual(len(combinations), 8)
        for row in rows:
            self.assertEqual(sum(row["counts"].values()), 4096)
            if row["preparation_basis"] == row["measurement_basis"]:
                self.assertEqual(row["observed_p_one"], float(row["alice_bit"]))
            else:
                self.assertAlmostEqual(row["observed_p_one"], 0.5, delta=7 * math.sqrt(0.25 / 4096))
        json.dumps(rows, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
