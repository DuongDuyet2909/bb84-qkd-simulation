"""Mốc giải tích độc lập cho entropy, nhiễu và ước lượng thống kê."""

from __future__ import annotations

import math
import unittest

import numpy as np

from bb84.theory import (
    asymptotic_secret_fraction,
    binary_entropy,
    expected_qber,
    expected_sift_fraction,
    probability_detect_error,
    wilson_interval,
)


class TheoryTests(unittest.TestCase):
    def test_binary_entropy_endpoints_and_symmetry(self):
        self.assertEqual(binary_entropy(0), 0)
        self.assertEqual(binary_entropy(1), 0)
        self.assertAlmostEqual(binary_entropy(0.5), 1)
        self.assertAlmostEqual(binary_entropy(0.1), 0.4689955935892812)
        for q in (0.01, 0.1, 0.23, 0.4):
            self.assertAlmostEqual(binary_entropy(q), binary_entropy(1 - q))

    def test_vectorized_theory_preserves_array_shape_and_values(self):
        np.testing.assert_allclose(binary_entropy([0, 0.5, 1]), [0, 1, 0])
        np.testing.assert_allclose(expected_qber(np.array([[0], [1]]), [0, 0.2], "depolarizing"), [[0, 0.1], [0.25, 0.3]])
        np.testing.assert_allclose(probability_detect_error([0, 0.25, 1], [5, 2, 5]), [0, 0.4375, 1])

    def test_asymptotic_fraction_and_ec_cost(self):
        self.assertEqual(asymptotic_secret_fraction(0), 1)
        self.assertEqual(asymptotic_secret_fraction(0.5), 0)
        self.assertGreater(asymptotic_secret_fraction(0.10), 0)
        self.assertEqual(asymptotic_secret_fraction(0.12), 0)
        self.assertAlmostEqual(asymptotic_secret_fraction(0.11002786443836), 0, delta=1e-12)
        expected = 1 - 1.16 * binary_entropy(0.02) - binary_entropy(0.06)
        self.assertAlmostEqual(asymptotic_secret_fraction(0.02, 0.06, f_ec=1.16), expected)
        self.assertLess(asymptotic_secret_fraction(0.04, f_ec=1.16), asymptotic_secret_fraction(0.04))

    def test_independent_errors_cancel_when_both_occur(self):
        self.assertEqual(expected_qber(0, 0, "depolarizing"), 0)
        self.assertEqual(expected_qber(1, 0, "depolarizing"), 0.25)
        self.assertAlmostEqual(expected_qber(0.4, 0.2, "readout_flip"), 0.26)
        self.assertAlmostEqual(expected_qber(0.4, 0.4, "depolarizing"), 0.26)
        self.assertEqual(expected_qber(0, 1, "depolarizing"), 0.5)
        self.assertEqual(expected_qber(0, 1, "readout_flip"), 1)
        self.assertEqual(expected_qber(1, 1, "readout_flip"), 0.75)

    def test_sift_fraction_includes_independent_loss(self):
        self.assertEqual(expected_sift_fraction(), 0.5)
        self.assertAlmostEqual(expected_sift_fraction(0.8), 0.68)
        self.assertAlmostEqual(expected_sift_fraction(0.8, 0.25), 0.51)
        self.assertEqual(expected_sift_fraction(0.5, 1), 0)
        for p_z in (0.01, 0.2, 0.4):
            self.assertAlmostEqual(expected_sift_fraction(p_z), expected_sift_fraction(1 - p_z))

    def test_wilson_interval_known_reference(self):
        low, high = wilson_interval(50, 100, 0.95)
        self.assertAlmostEqual(low, 0.4038315303659956, places=12)
        self.assertAlmostEqual(high, 0.5961684696340044, places=12)

    def test_numpy_integer_counts_do_not_overflow_wilson_arithmetic(self):
        for integer_type, count in ((np.int32, 100_000), (np.int64, 5_000_000_000)):
            for errors in (0, count // 2, count):
                with self.subTest(integer_type=integer_type, count=count, errors=errors):
                    actual = wilson_interval(integer_type(errors), integer_type(count))
                    expected = wilson_interval(errors, count)
                    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-15)

    def test_wilson_interval_bounds_and_extreme_confidence(self):
        for errors in (0, 1, 50, 99, 100):
            for confidence in (0.5, 0.95, np.nextafter(1.0, 0.0)):
                with self.subTest(errors=errors, confidence=confidence):
                    low, high = wilson_interval(errors, 100, confidence)
                    self.assertTrue(math.isfinite(low) and math.isfinite(high))
                    self.assertLessEqual(0, low)
                    self.assertLessEqual(low, errors / 100)
                    self.assertLessEqual(errors / 100, high)
                    self.assertLessEqual(high, 1)

    def test_no_observations_does_not_imply_zero_error(self):
        low, high = wilson_interval(0, 0)
        self.assertTrue(math.isnan(low))
        self.assertTrue(math.isnan(high))

    def test_zero_errors_still_has_positive_upper_bound(self):
        low, high = wilson_interval(0, 100, 0.95)
        self.assertAlmostEqual(low, 0, places=14)
        self.assertAlmostEqual(high, 0.03699349820698568, places=12)
        other_low, other_high = wilson_interval(100, 100, 0.95)
        self.assertAlmostEqual(other_high, 1, places=14)
        self.assertAlmostEqual(other_low, 1 - high, places=12)

    def test_larger_sample_narrows_interval(self):
        small = wilson_interval(5, 100, 0.95)
        large = wilson_interval(50, 1000, 0.95)
        self.assertLess(large[1] - large[0], small[1] - small[0])
        more_confident = wilson_interval(5, 100, 0.99)
        self.assertGreater(more_confident[1] - more_confident[0], small[1] - small[0])

    def test_error_detection_probability(self):
        self.assertEqual(probability_detect_error(0.25, 0), 0)
        self.assertEqual(probability_detect_error(0, 100), 0)
        self.assertEqual(probability_detect_error(1, 1), 1)
        self.assertAlmostEqual(probability_detect_error(0.25, 10), 1 - (3 / 4) ** 10)
        # Stable calculation avoids cancellation for very small QBER.
        self.assertAlmostEqual(probability_detect_error(1e-12, 1000), -math.expm1(1000 * math.log1p(-1e-12)), delta=1e-18)

    def test_invalid_theory_parameters_are_rejected(self):
        bad_calls = [
            lambda: binary_entropy(-0.01),
            lambda: binary_entropy(1.01),
            lambda: binary_entropy(float("nan")),
            lambda: expected_qber(-0.1, 0, "depolarizing"),
            lambda: expected_qber(0, 1.1, "depolarizing"),
            lambda: expected_qber(0, 0, "unknown"),
            lambda: expected_sift_fraction(-0.1),
            lambda: expected_sift_fraction(0.5, 1.1),
            lambda: asymptotic_secret_fraction(0.01, f_ec=0.9),
            lambda: wilson_interval(-1, 10),
            lambda: wilson_interval(11, 10),
            lambda: wilson_interval(1.5, 10),
            lambda: wilson_interval(1, 10, confidence=1),
            lambda: probability_detect_error(-0.01, 10),
            lambda: probability_detect_error(0.25, -1),
            lambda: probability_detect_error(0.25, 1.5),
        ]
        for call in bad_calls:
            with self.subTest(call=call), self.assertRaises((ValueError, TypeError)):
                call()


if __name__ == "__main__":
    unittest.main()
