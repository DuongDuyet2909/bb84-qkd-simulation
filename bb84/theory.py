"""Analytic reference curves for the educational BB84 simulator.

These functions do not constitute a composable finite-key security proof.
In particular, a binomial Wilson interval for an observed QBER is not an
upper bound on Eve's information or on the phase error of a general attack.
"""

from __future__ import annotations

from numbers import Integral, Real
from statistics import NormalDist

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _probability(value: ArrayLike, name: str) -> NDArray[np.float64]:
    """Validate a scalar or array of finite probabilities, including endpoints."""
    result = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(result)) or np.any((result < 0) | (result > 1)):
        raise ValueError(f"{name} must contain finite probabilities in [0, 1].")
    return result


def _scalar_or_array(value: NDArray[np.float64]) -> float | NDArray[np.float64]:
    return float(value) if value.ndim == 0 else value


def binary_entropy(q: ArrayLike) -> float | NDArray[np.float64]:
    """Return binary Shannon entropy h2(q), with h2(0)=h2(1)=0.

    The logarithm is base two, so the result is measured in bits. Inputs may
    be scalars or NumPy-compatible arrays; invalid probabilities raise an
    error instead of being silently clipped.
    """
    probability = _probability(q, "q")
    result = np.zeros_like(probability)
    interior = (probability > 0) & (probability < 1)
    p = probability[interior]
    result[interior] = -p * np.log2(p) - (1 - p) * np.log2(1 - p)
    return _scalar_or_array(result)


def asymptotic_secret_fraction(
    qz: ArrayLike, qx: ArrayLike | None = None, f_ec: float = 1.0
) -> float | NDArray[np.float64]:
    """Return max(0, 1 - f_ec*h2(qz) - h2(qx)).

    This is an illustrative asymptotic secret fraction per *Z-key* sifted
    bit under an ideal single-photon BB84 security model: qz is its bit
    error and qx estimates its phase error in the asymptotic limit. Omit
    qx only to assume symmetric errors qx=qz. It does not include sifting,
    disclosed tests, finite-size penalties, verification or authentication.
    f_ec >= 1 describes error-correction inefficiency; 1 is ideal Shannon
    efficiency. This helper does not certify any simulated output as secret.
    """
    if (
        not isinstance(f_ec, Real)
        or isinstance(f_ec, (bool, np.bool_))
        or not np.isfinite(f_ec)
        or f_ec < 1
    ):
        raise ValueError("f_ec must be a finite real number >= 1.")
    z = _probability(qz, "qz")
    x = z if qx is None else _probability(qx, "qx")
    result = np.asarray(np.maximum(0.0, 1.0 - f_ec * binary_entropy(z) - binary_entropy(x)))
    return _scalar_or_array(result)


def expected_qber(
    eve_fraction: ArrayLike = 0.0,
    noise_probability: ArrayLike = 0.0,
    noise_model: str = "depolarizing",
) -> float | NDArray[np.float64]:
    """Expected QBER after sifting for the exact implemented attack/channel.

    Eve intercepts each signal independently with probability f and measures
    in an unbiased Z/X basis, yielding attack error e=f/4. Depolarization is
    rho -> (1-p)rho + p*I/2 and gives a matched-basis flip probability p/2.
    The readout_flip model flips Bob's classical output with probability p.
    Independent channel/attack errors combine as e+c-2*e*c, not e+c.
    Independent loss and Alice/Bob basis bias do not change this conditional
    QBER when Eve remains unbiased.
    """
    attack = _probability(eve_fraction, "eve_fraction") / 4.0
    noise = _probability(noise_probability, "noise_probability")
    if noise_model == "depolarizing":
        channel = noise / 2.0
    elif noise_model == "readout_flip":
        channel = noise
    else:
        raise ValueError("noise_model must be 'depolarizing' or 'readout_flip'.")
    return _scalar_or_array(np.asarray(attack + channel - 2.0 * attack * channel))


def expected_sift_fraction(
    p_z: ArrayLike = 0.5, loss_probability: ArrayLike = 0.0
) -> float | NDArray[np.float64]:
    """Expected sifted count divided by sent count, before public testing.

    Both parties independently select Z with the same probability p_z.
    For independent loss L, the fraction is (1-L)*(p_z**2+(1-p_z)**2).
    An endpoint basis bias is simulatable but cannot establish BB84 security
    because it leaves the complementary basis untested.
    """
    basis = _probability(p_z, "p_z")
    loss = _probability(loss_probability, "loss_probability")
    return _scalar_or_array(np.asarray((1 - loss) * (basis**2 + (1 - basis)**2)))


def wilson_interval(errors: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Two-sided Wilson score interval for a binomial error probability.

    Return (NaN, NaN) for zero trials. This is an approximate binomial
    interval, not an exact hypergeometric interval conditional on the full
    finite sifted block, and is not a finite-key security bound.
    """
    for name, value in (("errors", errors), ("trials", trials)):
        if not isinstance(value, Integral) or isinstance(value, (bool, np.bool_)) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer.")
    if errors > trials:
        raise ValueError("errors cannot exceed trials.")
    # NumPy integer scalars satisfy Integral but their fixed-width powers
    # can overflow (for example np.int32(100000)**2). Normalize before any
    # arithmetic so callers with counts from arrays get the same interval
    # as callers with ordinary Python integers.
    errors, trials = int(errors), int(trials)
    if (
        not isinstance(confidence, Real)
        or isinstance(confidence, (bool, np.bool_))
        or not np.isfinite(confidence)
        or not 0 < confidence < 1
    ):
        raise ValueError("confidence must be a finite real number in (0, 1).")
    if trials == 0:
        return float("nan"), float("nan")
    # This expression avoids rounding (1+confidence)/2 to 1 for confidence
    # extremely close to 1; the lower-tail argument remains representable.
    z = -NormalDist().inv_cdf((1.0 - float(confidence)) / 2.0)
    q = errors / trials
    z2 = z * z
    denominator = 1.0 + z2 / trials
    center = (q + z2 / (2.0 * trials)) / denominator
    radius = z * np.sqrt(q * (1.0 - q) / trials + z2 / (4.0 * trials**2)) / denominator
    return max(0.0, float(center - radius)), min(1.0, float(center + radius))


def probability_detect_error(q: ArrayLike, m: ArrayLike) -> float | NDArray[np.float64]:
    """Return P(at least one error)=1-(1-q)**m for independent sampled errors.

    q and nonnegative integer m may be scalar or broadcast-compatible arrays.
    The event detects an error, not the identity or existence of an attacker.
    For a fixed finite population with a fixed error count, a sample without
    replacement instead follows a hypergeometric distribution. The present
    formula applies to the simulator's ensemble of independent signal errors.
    """
    probability = _probability(q, "q")
    sizes = np.asarray(m)
    if sizes.dtype.kind not in "iu" or np.any(sizes < 0):
        raise ValueError("m must contain nonnegative integers.")
    probability, sizes = np.broadcast_arrays(probability, sizes)
    result = np.zeros(probability.shape, dtype=float)
    positive = sizes > 0
    certain = positive & (probability == 1)
    interior = positive & (probability < 1)
    result[certain] = 1.0
    result[interior] = -np.expm1(sizes[interior] * np.log1p(-probability[interior]))
    return _scalar_or_array(result)
