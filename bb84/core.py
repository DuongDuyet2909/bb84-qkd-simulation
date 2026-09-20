"""A reproducible, vectorized BB84 prepare-and-measure simulator.

Scope: ideal single-qubit states, unbiased intercept-resend Eve, independent
loss, an explicitly chosen noise channel, basis sifting and public testing.
This module performs neither error correction nor privacy amplification.
The remaining bits are therefore *raw candidate bits*, never a certified
secret key. The classical discussion is assumed authenticated.

State representation: basis=0 means Z, basis=1 means X; bit=0/1 selects the
corresponding eigenstate. This compact representation is exact for BB84
states, projective Z/X measurements and Pauli noise up to irrelevant global
phases. It is not a simulator of arbitrary states, entanglement or attacks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from numbers import Integral, Real
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .theory import expected_qber, expected_sift_fraction, wilson_interval

BitArray = NDArray[np.int8]
MaskArray = NDArray[np.bool_]


@dataclass(frozen=True)
class BB84Config:
    """Validated parameters for one experiment; probabilities include endpoints.

    sample_size, when set, overrides sample_fraction. A requested sample
    larger than the sifted block reveals all available bits and produces
    insufficient_data. A fractional sample is floor(fraction*n_sifted).

    abort_threshold=0.11 is an educational screening parameter inspired by
    the ideal symmetric asymptotic BB84 rate. It is neither a universal
    attack detector nor a finite-key security threshold. confidence controls
    a two-sided Wilson interval, not a composable security parameter epsilon.
    """

    n_signals: int = 10_000
    eve_fraction: float = 0.0
    noise_probability: float = 0.0
    noise_model: str = "depolarizing"
    loss_probability: float = 0.0
    basis_probability_z: float = 0.5
    sample_fraction: float = 0.2
    sample_size: int | None = None
    abort_threshold: float = 0.11
    confidence: float = 0.95

    def __post_init__(self) -> None:
        _validate_integer("n_signals", self.n_signals, minimum=1)
        if self.sample_size is not None:
            _validate_integer("sample_size", self.sample_size, minimum=1)
        for name in ("eve_fraction", "noise_probability", "loss_probability", "basis_probability_z"):
            _validate_real(name, getattr(self, name), 0.0, 1.0)
        _validate_real("sample_fraction", self.sample_fraction, 0.0, 1.0, exclusive=True)
        _validate_real("abort_threshold", self.abort_threshold, 0.0, 0.5)
        _validate_real("confidence", self.confidence, 0.0, 1.0, exclusive=True)
        if self.noise_model not in ("depolarizing", "readout_flip"):
            raise ValueError("noise_model must be 'depolarizing' or 'readout_flip'.")


def _validate_integer(name: str, value: Any, minimum: int) -> None:
    if not isinstance(value, Integral) or isinstance(value, (bool, np.bool_)) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}.")


def _validate_real(name: str, value: Any, low: float, high: float, exclusive: bool = False) -> None:
    interval_ok = low < value < high if isinstance(value, Real) and exclusive else (
        low <= value <= high if isinstance(value, Real) else False
    )
    if (
        not isinstance(value, Real)
        or isinstance(value, (bool, np.bool_))
        or not np.isfinite(value)
        or not interval_ok
    ):
        left, right = ("(", ")") if exclusive else ("[", "]")
        raise ValueError(f"{name} must be a finite real number in {left}{low}, {high}{right}.")


def _json_value(value: Any) -> Any:
    """Recursively normalize NumPy values and replace undefined rates by null."""
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, np.ndarray)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


@dataclass(frozen=True)
class BB84Result:
    """Read-only per-signal simulation arrays and aggregate experiment results.

    All arrays have n_signals entries. Alice/Bob bases are 0=Z or 1=X.
    Eve's bases/bits are -1 on un-intercepted signals. Bob's generated bits
    at lost positions are simulator-only values and must be masked by
    detected_mask. test_mask and key_mask partition sift_mask.

    qber_actual/remaining and eve_known_mask are simulator ground truth;
    Alice and Bob would not obtain them through the public testing protocol.
    key_mask is a short identifier for *undisclosed candidate positions*;
    it does not indicate successful generation of a secret key.
    """

    config: BB84Config
    seed: int | dict[str, Any]
    alice_bits: BitArray = field(repr=False)
    alice_bases: BitArray = field(repr=False)
    bob_bases: BitArray = field(repr=False)
    bob_bits: BitArray = field(repr=False)
    eve_mask: MaskArray = field(repr=False)
    eve_bases: BitArray = field(repr=False)
    eve_bits: BitArray = field(repr=False)
    detected_mask: MaskArray = field(repr=False)
    sift_mask: MaskArray = field(repr=False)
    test_mask: MaskArray = field(repr=False)
    key_mask: MaskArray = field(repr=False)
    eve_known_mask: MaskArray = field(repr=False)
    requested_sample_size: int

    @property
    def n_detected(self) -> int:
        return int(np.count_nonzero(self.detected_mask))

    @property
    def n_sifted(self) -> int:
        return int(np.count_nonzero(self.sift_mask))

    @property
    def n_test(self) -> int:
        return int(np.count_nonzero(self.test_mask))

    @property
    def n_remaining(self) -> int:
        return int(np.count_nonzero(self.key_mask))

    def _error_count(self, mask: MaskArray) -> int:
        return int(np.count_nonzero((self.alice_bits != self.bob_bits) & mask))

    def _qber(self, mask: MaskArray) -> float:
        count = int(np.count_nonzero(mask))
        return self._error_count(mask) / count if count else float("nan")

    @property
    def actual_errors(self) -> int:
        return self._error_count(self.sift_mask)

    @property
    def test_errors(self) -> int:
        return self._error_count(self.test_mask)

    @property
    def remaining_errors(self) -> int:
        return self._error_count(self.key_mask)

    @property
    def qber_actual(self) -> float:
        """Ground-truth QBER over all detected matching-basis positions."""
        return self._qber(self.sift_mask)

    @property
    def qber_estimate(self) -> float:
        """Publicly observed QBER from only the disclosed test positions."""
        return self._qber(self.test_mask)

    @property
    def qber_remaining(self) -> float:
        """Simulator-only QBER in the undisclosed candidate positions."""
        return self._qber(self.key_mask)

    @property
    def qber_interval(self) -> tuple[float, float]:
        return wilson_interval(self.test_errors, self.n_test, self.config.confidence)

    @property
    def qber_ci(self) -> tuple[float, float]:
        """Alias for qber_interval."""
        return self.qber_interval

    @property
    def decision(self) -> str:
        """Educational sample screening; never a security certification."""
        if self.n_test == 0 or self.n_remaining == 0 or self.requested_sample_size > self.n_sifted:
            return "insufficient_data"
        if self.qber_interval[1] > self.config.abort_threshold:
            return "abort"
        return "continue_postprocessing"

    @property
    def decision_reason(self) -> str:
        if self.n_test == 0:
            return "No disclosed test bits: QBER cannot be estimated."
        if self.requested_sample_size > self.n_sifted:
            return "The requested test sample exceeds the available sifted block."
        if self.n_remaining == 0:
            return "All sifted bits were disclosed; no candidate bits remain."
        if self.decision == "abort":
            return "The sample Wilson upper endpoint exceeds the educational screening threshold."
        return "The sample passes educational screening; error correction and privacy amplification are still required."

    @property
    def per_basis(self) -> dict[str, dict[str, Any]]:
        """Per-basis counts and QBERs; absent observations are NaN internally."""
        result: dict[str, dict[str, Any]] = {}
        for label, basis in (("Z", 0), ("X", 1)):
            basis_mask = self.alice_bases == basis
            sift = self.sift_mask & basis_mask
            test = self.test_mask & basis_mask
            remaining = self.key_mask & basis_mask
            test_errors = self._error_count(test)
            n_test = int(np.count_nonzero(test))
            lo, hi = wilson_interval(test_errors, n_test, self.config.confidence)
            result[label] = {
                "n_sifted": int(np.count_nonzero(sift)),
                "n_test": n_test,
                "n_remaining": int(np.count_nonzero(remaining)),
                "actual_errors": self._error_count(sift),
                "test_errors": test_errors,
                "remaining_errors": self._error_count(remaining),
                "qber_actual": self._qber(sift),
                "qber_estimate": self._qber(test),
                "qber_remaining": self._qber(remaining),
                "qber_ci_low": lo,
                "qber_ci_high": hi,
            }
        return result

    def summary(self) -> dict[str, Any]:
        """Return JSON-safe metadata/statistics, deliberately excluding raw bits."""
        lo, hi = self.qber_interval
        known = int(np.count_nonzero(self.eve_known_mask & self.key_mask))
        return _json_value({
            "config": asdict(self.config),
            "seed": self.seed,
            "n_signals": self.config.n_signals,
            "n_detected": self.n_detected,
            "n_sifted": self.n_sifted,
            "requested_sample_size": self.requested_sample_size,
            "n_test": self.n_test,
            "n_remaining": self.n_remaining,
            "detection_fraction": self.n_detected / self.config.n_signals,
            "sift_fraction": self.n_sifted / self.config.n_signals,
            "actual_errors": self.actual_errors,
            "test_errors": self.test_errors,
            "remaining_errors": self.remaining_errors,
            "qber_actual": self.qber_actual,
            "qber_estimate": self.qber_estimate,
            "qber_remaining": self.qber_remaining,
            "qber_interval": [lo, hi],
            "qber_ci_low": lo,
            "qber_ci_high": hi,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "per_basis": self.per_basis,
            "n_eve_intercepted": int(np.count_nonzero(self.eve_mask)),
            "n_eve_known_remaining": known,
            "eve_known_fraction_remaining": known / self.n_remaining if self.n_remaining else float("nan"),
            "eve_knowledge_note": "Simulator-only fraction of remaining Alice bits known exactly from Eve measuring in Alice's basis; not mutual information or a general security bound.",
            "theory": {
                "expected_qber": expected_qber(self.config.eve_fraction, self.config.noise_probability, self.config.noise_model),
                "expected_sift_fraction": expected_sift_fraction(self.config.basis_probability_z, self.config.loss_probability),
                "expected_detection_fraction": 1.0 - self.config.loss_probability,
            },
            "security_note": "Educational sample screening only. No secret key is produced. Wilson intervals and the 0.11 default are not finite-key security proofs.",
        })


def _measure(
    state_bits: BitArray, state_bases: BitArray, measurement_bases: BitArray, rng: np.random.Generator
) -> BitArray:
    """Exact projective Z/X measurement of one of the four BB84 states."""
    random_outcomes = rng.integers(0, 2, size=state_bits.size, dtype=np.int8)
    return np.where(state_bases == measurement_bases, state_bits, random_outcomes).astype(np.int8)


def simulate(config: BB84Config, seed: int | np.random.SeedSequence = 0) -> BB84Result:
    """Run BB84 with a local random generator and no global RNG side effects.

    The operation order is Alice preparation -> optional Eve measurement and
    resend -> channel Pauli noise -> Bob measurement -> optional classical
    readout flips -> independent erasures -> sifting -> public random sample.
    Applying independent loss after generating outcomes is distributionally
    identical to discarding lost signals before detection. Their stored bit
    values are never used in the sifted/test/candidate statistics.

    The pseudorandom generator and explicit seed support reproducibility;
    they are unsuitable as a production source of cryptographic randomness.
    """
    if not isinstance(config, BB84Config):
        raise TypeError("config must be a BB84Config instance.")
    if isinstance(seed, np.random.SeedSequence):
        seed_metadata: int | dict[str, Any] = _json_value({
            "entropy": seed.entropy, "spawn_key": seed.spawn_key, "pool_size": seed.pool_size
        })
    else:
        _validate_integer("seed", seed, minimum=0)
        seed_metadata = int(seed)
    rng = np.random.default_rng(seed)
    n = int(config.n_signals)

    alice_bits = rng.integers(0, 2, size=n, dtype=np.int8)
    alice_bases = (rng.random(n) >= config.basis_probability_z).astype(np.int8)
    bob_bases = (rng.random(n) >= config.basis_probability_z).astype(np.int8)

    eve_mask = rng.random(n) < config.eve_fraction
    eve_bases_all = rng.integers(0, 2, size=n, dtype=np.int8)
    eve_bits_all = _measure(alice_bits, alice_bases, eve_bases_all, rng)
    state_bases = np.where(eve_mask, eve_bases_all, alice_bases).astype(np.int8)
    state_bits = np.where(eve_mask, eve_bits_all, alice_bits).astype(np.int8)
    eve_bases = np.where(eve_mask, eve_bases_all, -1).astype(np.int8)
    eve_bits = np.where(eve_mask, eve_bits_all, -1).astype(np.int8)
    eve_known_mask = eve_mask & (eve_bases_all == alice_bases)

    # Depolarization has Pauli weights P(X)=P(Y)=P(Z)=p/4,
    # P(I)=1-3p/4, which is exactly rho -> (1-p)rho+p*I/2.
    # X flips the label of Z states; Z flips the label of X states;
    # Y flips either label. Global phases do not affect these measurements.
    if config.noise_model == "depolarizing":
        draw = rng.random(n)
        quarter = config.noise_probability / 4.0
        pauli_x = draw < quarter
        pauli_y = (draw >= quarter) & (draw < 2.0 * quarter)
        pauli_z = (draw >= 2.0 * quarter) & (draw < 3.0 * quarter)
        label_flip = pauli_y | (pauli_x & (state_bases == 0)) | (pauli_z & (state_bases == 1))
        state_bits = np.bitwise_xor(state_bits, label_flip.astype(np.int8))

    bob_bits = _measure(state_bits, state_bases, bob_bases, rng)
    if config.noise_model == "readout_flip":
        bob_bits = np.bitwise_xor(bob_bits, (rng.random(n) < config.noise_probability).astype(np.int8))

    detected_mask = rng.random(n) >= config.loss_probability
    sift_mask = detected_mask & (alice_bases == bob_bases)
    sift_positions = np.flatnonzero(sift_mask)
    requested = int(config.sample_size) if config.sample_size is not None else int(
        np.floor(config.sample_fraction * sift_positions.size)
    )
    sample_count = min(requested, sift_positions.size)
    test_mask = np.zeros(n, dtype=bool)
    if sample_count:
        chosen = rng.choice(sift_positions, size=sample_count, replace=False)
        test_mask[chosen] = True
    key_mask = sift_mask & ~test_mask

    arrays = {
        "alice_bits": alice_bits,
        "alice_bases": alice_bases,
        "bob_bases": bob_bases,
        "bob_bits": bob_bits,
        "eve_mask": eve_mask,
        "eve_bases": eve_bases,
        "eve_bits": eve_bits,
        "detected_mask": detected_mask,
        "sift_mask": sift_mask,
        "test_mask": test_mask,
        "key_mask": key_mask,
        "eve_known_mask": eve_known_mask,
    }
    for array in arrays.values():
        array.setflags(write=False)
    return BB84Result(config=config, seed=seed_metadata, requested_sample_size=requested, **arrays)
