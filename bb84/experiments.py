"""Six reproducible BB84 experiments with raw CSVs and publication-ready plots.

The exported seeds reconstruct individual runs, independently of sweep order.
No raw bit strings are exported. Experiments 1--5 use the same BB84 pipeline
as the interactive demo; experiment 6 is explicitly a theoretical reference.
The simulator produces candidate bits, not an extracted or certified secret key.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict
from numbers import Integral
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable

# The cache is disposable; keep it in the OS temporary directory so read-only
# user profile folders do not produce cache warnings. Honor an explicit choice.
if "MPLCONFIGDIR" not in os.environ:
    _cache_directory = Path(tempfile.gettempdir()) / "bb84-matplotlib"
    _cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(_cache_directory))

import matplotlib

# Batch generation also works on a machine without a graphical desktop.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .core import BB84Config, simulate
from .theory import (
    asymptotic_secret_fraction,
    expected_qber,
    expected_sift_fraction,
    probability_detect_error,
    wilson_interval,
)


PRESETS = {
    "quick": {"n_signals": 5_000, "repetitions": 30, "detection_repetitions": 500},
    "standard": {"n_signals": 20_000, "repetitions": 150, "detection_repetitions": 2_000},
}
COLORS = ("#176B9A", "#D06A20", "#16876F", "#835BA5")


def _run_seed(base_seed: int, experiment: str, config: dict[str, Any], repeat: int) -> int:
    """Deterministic 128-bit seed; no process-randomized Python hash().

    A configuration gets the same seed even if other configurations are added,
    sweep order changes, or more repetitions are requested. The entire config
    and this seed are saved in the corresponding raw CSV row.
    """
    payload = json.dumps(
        [int(base_seed), experiment, config, int(repeat)], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Use UTF-8 with BOM for convenient direct opening in Windows Excel."""
    if not rows:
        raise ValueError(f"No data to export: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: "" if isinstance(value, float) and not math.isfinite(value) else value
                for key, value in row.items()
            })


def _statistics(values: Iterable[float]) -> dict[str, float | int]:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    count = int(array.size)
    mean = float(np.mean(array)) if count else float("nan")
    sd = float(np.std(array, ddof=1)) if count > 1 else float("nan")
    return {"count": count, "mean": mean, "sd": sd, "sem": sd / math.sqrt(count) if count > 1 else float("nan")}


def _group_summary(rows: list[dict[str, Any]], keys: tuple[str, ...], metrics: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[key] for key in keys), []).append(row)
    result = []
    for values, members in groups.items():
        item = dict(zip(keys, values))
        item["repetitions"] = len(members)
        item["expected_qber"] = members[0]["expected_qber"]
        for metric in metrics:
            for suffix, value in _statistics(member[metric] for member in members).items():
                item[f"{metric}_{suffix}"] = value
        result.append(item)
    return result


def _simulate_rows(
    experiment: str, configs: Iterable[BB84Config], repetitions: int, seed: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for config in configs:
        config_dict = asdict(config)
        theory_q = float(expected_qber(config.eve_fraction, config.noise_probability, config.noise_model))
        for repeat in range(repetitions):
            run_seed = _run_seed(seed, experiment, config_dict, repeat)
            result = simulate(config, seed=run_seed)
            n_sifted, n_test, n_remaining = result.n_sifted, result.n_test, result.n_remaining
            test_errors, actual_errors = result.test_errors, result.actual_errors
            lo, hi = wilson_interval(test_errors, n_test, config.confidence)
            rows.append({
                "experiment": experiment,
                "repeat": repeat,
                "seed": run_seed,
                **config_dict,
                "n_detected": result.n_detected,
                "n_sifted": n_sifted,
                "n_test": n_test,
                "n_remaining": n_remaining,
                "actual_errors": actual_errors,
                "test_errors": test_errors,
                "qber_actual": actual_errors / n_sifted if n_sifted else float("nan"),
                "qber_estimate": test_errors / n_test if n_test else float("nan"),
                "qber_ci_low": lo,
                "qber_ci_high": hi,
                "qber_ci_width": hi - lo,
                "detected_fraction": result.n_detected / config.n_signals,
                "sifted_fraction": n_sifted / config.n_signals,
                "candidate_fraction": n_remaining / config.n_signals,
                "has_error": int(test_errors > 0),
                "full_sample": int(n_test == config.sample_size) if config.sample_size is not None else 1,
                "expected_qber": theory_q,
            })
    return rows


def _style(ax: Any, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.22)
    ax.spines[["top", "right"]].set_visible(False)


def _save_figure(figure: Any, output: Path, name: str, caption: str) -> tuple[str, str]:
    relative_png, relative_pdf = f"figures/{name}.png", f"figures/{name}.pdf"
    (output / "figures").mkdir(parents=True, exist_ok=True)
    figure.text(0.5, 0.012, caption, ha="center", va="bottom", fontsize=8, color="#465565")
    figure.tight_layout(rect=(0, 0.052, 1, 0.98))
    figure.savefig(output / relative_png, dpi=180, facecolor="white")
    figure.savefig(output / relative_pdf, facecolor="white")
    plt.close(figure)
    return relative_png, relative_pdf


def _export(
    output: Path, name: str, title: str, description: str,
    raw: list[dict[str, Any]] | None, summary: list[dict[str, Any]],
    figure: Any, caption: str, findings: list[str],
) -> dict[str, Any]:
    raw_csv = f"data/{name}_raw.csv" if raw is not None else None
    summary_csv = f"data/{name}_{'summary' if raw is not None else 'theory'}.csv"
    if raw_csv is not None:
        _write_csv(output / raw_csv, raw)
    _write_csv(output / summary_csv, summary)
    png, pdf = _save_figure(figure, output, name, caption)
    return {
        "id": name, "title": title, "description": description,
        "figure": png, "pdf": pdf, "raw_csv": raw_csv, "summary_csv": summary_csv,
        "findings": findings, "error_semantics": caption,
        "run_count": len(raw) if raw is not None else 0,
    }


def _eve_sweep(output: Path, n: int, repeats: int, seed: int) -> dict[str, Any]:
    name = "01_eve_sweep"
    noise_levels = (0.0, 0.02, 0.06)
    fractions = np.linspace(0, 1, 11)
    raw = _simulate_rows(name, (
        BB84Config(n_signals=n, eve_fraction=float(f), noise_probability=p)
        for p in noise_levels for f in fractions
    ), repeats, seed)
    summary = _group_summary(raw, ("noise_probability", "eve_fraction"), ("qber_estimate", "qber_actual"))
    fig, ax = plt.subplots(figsize=(9.5, 5.7))
    for color, p in zip(COLORS, noise_levels):
        group = [row for row in summary if row["noise_probability"] == p]
        ax.errorbar(
            fractions, [row["qber_estimate_mean"] for row in group],
            yerr=[row["qber_estimate_sem"] for row in group], fmt="o", capsize=3,
            color=color, label=f"MC sampled QBER; depolarizing p={p:.2f}", markersize=4,
        )
        ax.plot(fractions, expected_qber(fractions, p), "--", color=color, alpha=0.9)
    _style(ax, "Intercept-resend probability f", "Sampled QBER (fraction)")
    ax.set_title("01 | Intercept-resend Eve and background noise", loc="left", fontweight="bold")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(bottom=-0.005)
    ax.legend(fontsize=9, loc="upper left")
    end = next(row for row in summary if row["noise_probability"] == 0 and row["eve_fraction"] == 1)
    max_error = max(abs(row["qber_estimate_mean"] - row["expected_qber"]) for row in summary)
    return _export(output, name, "QBER theo tỷ lệ Eve", "Eve chặn–đo–gửi lại với ba mức nhiễu depolarizing.", raw, summary, fig,
        f"N={n:,}; R={repeats}; mean +/- 1 SEM across runs; dashed = theory; sample fraction=0.20; pZ=0.50.", [
            f"Eve chặn toàn bộ, không nhiễu: QBER mẫu trung bình {end['qber_estimate_mean']:.4%}; kỳ vọng 25%.",
            f"Sai lệch tuyệt đối lớn nhất giữa trung bình mẫu và lý thuyết trên lưới: {100 * max_error:.4f} điểm phần trăm.",
            "Nhiễu và tấn công kết hợp theo e+c−2ec; QBER không xác định danh tính tác nhân gây lỗi.",
        ])


def _noise_sweep(output: Path, n: int, repeats: int, seed: int) -> dict[str, Any]:
    name = "02_noise_sweep"
    probabilities = np.linspace(0, 0.2, 11)
    raw = _simulate_rows(name, (
        BB84Config(n_signals=n, noise_probability=float(p), noise_model=model)
        for model in ("depolarizing", "readout_flip") for p in probabilities
    ), repeats, seed)
    summary = _group_summary(raw, ("noise_model", "noise_probability"), ("qber_estimate", "qber_actual"))
    fig, ax = plt.subplots(figsize=(9.5, 5.7))
    for color, model in zip(COLORS, ("depolarizing", "readout_flip")):
        group = [row for row in summary if row["noise_model"] == model]
        ax.errorbar(probabilities, [row["qber_estimate_mean"] for row in group],
            yerr=[row["qber_estimate_sem"] for row in group], fmt="o", capsize=3,
            color=color, markersize=4, label=f"MC: {model}")
        ax.plot(probabilities, expected_qber(0, probabilities, model), "--", color=color,
            label="Theory: p/2" if model == "depolarizing" else "Theory: p")
    _style(ax, "Noise parameter p (model-specific)", "Sampled QBER (fraction)")
    ax.set_title("02 | Noise models have different parameter meanings", loc="left", fontweight="bold")
    ax.set_ylim(bottom=-0.004)
    ax.legend(fontsize=9)
    last = {model: next(row for row in reversed(summary) if row["noise_model"] == model) for model in ("depolarizing", "readout_flip")}
    return _export(output, name, "QBER theo mô hình nhiễu", "Phân biệt depolarizing rho → (1−p)rho+pI/2 với lật bit đầu ra Bob.", raw, summary, fig,
        f"N={n:,}; R={repeats}; mean +/- 1 SEM; no Eve, no loss; sample fraction=0.20; pZ=0.50.", [
            f"Tại p=0.20: depolarizing cho QBER mẫu {last['depolarizing']['qber_estimate_mean']:.3%}, readout_flip {last['readout_flip']['qber_estimate_mean']:.3%}.",
            "Lý thuyết tương ứng là p/2 và p. Không dùng cùng p để tuyên bố hai kênh có cùng mức lỗi.",
        ])


def _uncertainty(output: Path, n: int, repeats: int, seed: int) -> dict[str, Any]:
    name = "03_sample_uncertainty"
    maximum = n // 4
    sizes = sorted(set([size for size in (10, 25, 50, 100, 250, 500, 1_000, 2_500) if size <= maximum] + [maximum]))
    q = 0.05
    raw = _simulate_rows(name, (
        BB84Config(n_signals=n, eve_fraction=4 * q, sample_size=m) for m in sizes
    ), repeats, seed)
    summary = _group_summary(raw, ("sample_size",), ("qber_estimate", "qber_ci_width", "candidate_fraction"))
    for row in summary:
        row["theory_qber_sd"] = math.sqrt(q * (1 - q) / row["sample_size"])
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2))
    axes[0].errorbar(sizes, [row["qber_estimate_mean"] for row in summary],
        yerr=[row["qber_estimate_sd"] for row in summary], color=COLORS[0], fmt="o-", capsize=4, label="Mean +/- 1 SD")
    axes[0].axhline(q, color=COLORS[1], linestyle="--", label="True ensemble Q=0.05")
    _style(axes[0], "Disclosed sample size m", "Sampled QBER (fraction)")
    axes[0].set_title("Estimate spread across runs", fontsize=11)
    axes[0].legend(fontsize=8)
    axes[1].plot(sizes, [row["qber_ci_width_mean"] for row in summary], "o-", color=COLORS[0], label="Mean Wilson width")
    _style(axes[1], "Disclosed sample size m", "Width of a 95% Wilson interval")
    axes[1].set_title("Per-run statistical uncertainty", fontsize=11)
    axes[2].plot(sizes, [row["candidate_fraction_mean"] for row in summary], "o-", color=COLORS[2])
    axes[2].plot(sizes, 0.5 - np.asarray(sizes) / n, "--", color=COLORS[1], label="Approx. 0.5 - m/N")
    _style(axes[2], "Disclosed sample size m", "Undisclosed candidate bits / sent")
    axes[2].set_title("Public testing consumes bits", fontsize=11)
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.set_xscale("log")
    fig.suptitle("03 | Larger samples reduce uncertainty and leave fewer candidate bits", fontsize=13, fontweight="bold", y=1.02)
    first, last = summary[0], summary[-1]
    return _export(output, name, "Bất định QBER và chi phí lấy mẫu", "Lấy mẫu công khai từ đầu ra BB84; Eve f=0.20, không nhiễu/mất, Q kỳ vọng 0.05.", raw, summary, fig,
        f"N={n:,}; R={repeats}; LEFT bars = 1 SD (not SEM); CENTER = mean per-run Wilson width; no finite-key security claim.", [
            f"Khi m tăng từ {first['sample_size']} lên {last['sample_size']}, độ rộng Wilson trung bình đổi từ {first['qber_ci_width_mean']:.4f} thành {last['qber_ci_width_mean']:.4f}.",
            f"Ở m={last['sample_size']}, phần ứng viên chưa công bố trung bình bằng {last['candidate_fraction_mean']:.2%} số tín hiệu phát.",
            "Độ lệch chuẩn giữa các lần chạy khác với sai số chuẩn của trung bình; Wilson 95% không phải bảo đảm finite-key QKD.",
        ])


def _error_detection(output: Path, repeats: int, seed: int) -> dict[str, Any]:
    name = "04_error_detection"
    sizes = (1, 2, 5, 10, 20, 50, 100, 200)
    q_values = (0.025, 0.10, 0.25)
    # Independent BB84 blocks are cheap here: only enough signals to obtain
    # the specified sample are needed. No binomial outcomes are substituted.
    raw = _simulate_rows(name, (
        BB84Config(n_signals=max(512, 8 * m), eve_fraction=4 * q, sample_size=m)
        for q in q_values for m in sizes
    ), repeats, seed)
    summary = []
    for q in q_values:
        for m in sizes:
            group = [row for row in raw if row["expected_qber"] == q and row["sample_size"] == m]
            complete = [row for row in group if row["full_sample"]]
            successes = sum(row["has_error"] for row in complete)
            lo, hi = wilson_interval(successes, len(complete))
            summary.append({
                "expected_qber": q, "sample_size": m, "n_signals": max(512, 8 * m),
                "repetitions_requested": repeats, "complete_runs": len(complete),
                "incomplete_runs": len(group) - len(complete), "runs_with_error": successes,
                "probability_estimate": successes / len(complete) if complete else float("nan"),
                "probability_ci_low": lo, "probability_ci_high": hi,
                "theory_probability": float(probability_detect_error(q, m)),
            })
    fig, ax = plt.subplots(figsize=(9.5, 5.7))
    dense = np.arange(1, 201)
    for color, q in zip(COLORS, q_values):
        group = [row for row in summary if row["expected_qber"] == q]
        values = np.array([row["probability_estimate"] for row in group])
        lower = np.array([row["probability_ci_low"] for row in group])
        upper = np.array([row["probability_ci_high"] for row in group])
        ax.errorbar(sizes, values, yerr=np.maximum(0, np.vstack([values - lower, upper - values])),
            fmt="o", capsize=3, markersize=4, color=color, label=f"BB84 runs: Q={q:.3f}, Eve f={4*q:.2f}")
        ax.plot(dense, probability_detect_error(q, dense), "--", color=color)
    _style(ax, "Disclosed sample size m", "P(at least one observed error)")
    ax.set_xscale("log")
    ax.set_ylim(-0.03, 1.04)
    ax.set_title("04 | Finding an error is not identifying an eavesdropper", loc="left", fontweight="bold")
    ax.legend(fontsize=9, loc="lower right")
    incomplete = sum(row["incomplete_runs"] for row in summary)
    example = next(row for row in summary if row["expected_qber"] == 0.025 and row["sample_size"] == 20)
    return _export(output, name, "Xác suất thấy ít nhất một lỗi", "Mỗi điểm chạy giao thức BB84 nhiều lần; so sánh với 1−(1−Q)^m trong ensemble i.i.d.", raw, summary, fig,
        f"R={repeats} per point; N=max(512,8m); bars = 95% Wilson across complete runs; dashed = theory; no noise/loss.", [
            f"Q=2.5%, m=20: xác suất thấy lỗi mô phỏng {example['probability_estimate']:.2%}; lý thuyết {example['theory_probability']:.2%}.",
            f"Có {incomplete} lần không đủ cỡ mẫu; các lần đó được lưu dữ liệu và loại khỏi mẫu số ước lượng xác suất.",
            "Đây là xác suất tìm thấy lỗi, không phải xác suất chứng minh Eve hiện diện; mẫu nhỏ có thể bỏ sót lỗi.",
        ])


def _loss_sweep(output: Path, n: int, repeats: int, seed: int) -> dict[str, Any]:
    name = "05_loss_retention"
    losses = np.linspace(0, 1, 11)
    raw = _simulate_rows(name, (
        BB84Config(n_signals=n, loss_probability=float(loss), noise_probability=0.04)
        for loss in losses
    ), repeats, seed)
    summary = _group_summary(raw, ("loss_probability",), ("detected_fraction", "sifted_fraction", "candidate_fraction", "qber_estimate"))
    for row in summary:
        row["theory_detected_fraction"] = 1 - row["loss_probability"]
        row["theory_sifted_fraction"] = float(expected_sift_fraction(0.5, row["loss_probability"]))
        row["theory_candidate_fraction_approx"] = 0.8 * row["theory_sifted_fraction"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    for metric, theory, label, color in (
        ("detected_fraction", "theory_detected_fraction", "Detected / sent", COLORS[0]),
        ("sifted_fraction", "theory_sifted_fraction", "Sifted / sent", COLORS[1]),
        ("candidate_fraction", "theory_candidate_fraction_approx", "Candidate / sent", COLORS[2]),
    ):
        axes[0].errorbar(losses, [row[f"{metric}_mean"] for row in summary],
            yerr=[row[f"{metric}_sem"] for row in summary], fmt="o", capsize=3, color=color, label=label, markersize=4)
        axes[0].plot(losses, [row[theory] for row in summary], "--", color=color)
    _style(axes[0], "Independent loss probability L", "Count / number of signals sent")
    axes[0].legend(fontsize=9)
    axes[0].set_title("Production falls with loss", fontsize=11)
    valid = [row for row in summary if row["qber_estimate_count"] > 0]
    axes[1].errorbar([row["loss_probability"] for row in valid], [row["qber_estimate_mean"] for row in valid],
        yerr=[row["qber_estimate_sem"] for row in valid], fmt="o-", capsize=4, color=COLORS[0])
    axes[1].axhline(0.02, linestyle="--", color=COLORS[1], label="Expected Q=p/2=0.02")
    _style(axes[1], "Independent loss probability L", "Sampled QBER (fraction)")
    axes[1].set_title("Loss does not itself flip a bit", fontsize=11)
    axes[1].legend(fontsize=9)
    axes[1].set_xlim(-0.03, 1.03)
    axes[1].text(0.97, 0.03, "L=1: QBER undefined", transform=axes[1].transAxes, ha="right", fontsize=9)
    fig.suptitle("05 | Independent erasures: retention and QBER", fontweight="bold", y=1.01)
    return _export(output, name, "Mất tín hiệu và tỷ lệ giữ lại", "Mất tín hiệu độc lập; nhiễu nền depolarizing p=0.04 giữ cố định; không Eve.", raw, summary, fig,
        f"N={n:,}; R={repeats}; mean +/- 1 SEM; dashed = theory; candidate curve approximate due to floor(0.2*sifted).", [
            "Tỷ lệ sifted/phát kỳ vọng bằng (1−L)/2; phần ứng viên còn lại xấp xỉ 0.4(1−L).",
            "Nhiễu nền cho QBER kỳ vọng 2% dù xác suất mất thay đổi; ít tín hiệu sống sót làm ước lượng dao động hơn.",
            "Tại L=1 không có bit được phát hiện; QBER là không xác định, không được thay bằng 0.",
        ])


def _secret_fraction(output: Path) -> dict[str, Any]:
    name = "06_secret_fraction"
    q_values = np.linspace(0, 0.16, 321)
    efficiencies = (1.0, 1.1, 1.2)
    summary = [
        {"qber": float(q), "f_ec": efficiency, "secret_fraction_reference": float(asymptotic_secret_fraction(q, f_ec=efficiency)),
         "model": "asymptotic_ideal_single_photon_symmetric_qz_equals_qx", "source": "theory_only"}
        for efficiency in efficiencies for q in q_values
    ]
    fig, ax = plt.subplots(figsize=(9.5, 5.7))
    for color, efficiency in zip(COLORS, efficiencies):
        ax.plot(q_values, asymptotic_secret_fraction(q_values, f_ec=efficiency), color=color, lw=2, label=f"f_EC={efficiency:.1f}")
    ax.axvline(0.110028, linestyle=":", color="#7C8793", alpha=0.8)
    ax.text(0.112, 0.42, "~11% only for f_EC=1\nand this reference model", color="#596672", fontsize=9)
    _style(ax, "Symmetric QBER Q = qZ = qX", "Asymptotic secret fraction per Z-key sifted bit")
    ax.set_title("06 | Theoretical reference, not an extracted secret key", loc="left", fontweight="bold")
    ax.set_xlim(0, 0.16)
    ax.set_ylim(-0.03, 1.04)
    ax.legend(fontsize=10)
    return _export(output, name, "Tỷ lệ khóa tiệm cận tham chiếu", "r∞ = max(0, 1−h2(Q)−fEC h2(Q)); mô hình lý tưởng, sai số bit/pha đối xứng.", None, summary, fig,
        "THEORY ONLY: no Monte Carlo, no error bars. Excludes finite-size, sifting, test, verification and authentication costs.", [
            "Khi hiệu suất sửa lỗi kém hơn (fEC tăng), phần khóa tiệm cận tham chiếu giảm.",
            "Mốc xấp xỉ 11% chỉ thuộc trường hợp fEC=1 với giả định đang nêu; không là ngưỡng chứng nhận phổ quát.",
            "Chương trình chưa sửa lỗi/khuếch đại riêng tư; các đường này không phải khóa bí mật thực tế được sinh ra.",
        ])


def run_experiments(
    output: str | Path,
    preset: str = "quick",
    seed: int = 84,
    n_signals: int | None = None,
    repetitions: int | None = None,
    progress: Callable[[str], Any] | None = print,
) -> dict[str, Any]:
    """Run all six experiments and return a JSON-safe report manifest.

    Overrides change the main Monte Carlo sample sizes, not experiment 4:
    the detection curve uses 500/2000 independent runs per point and small
    dedicated signal blocks. Require N>=64 and R>=2 to permit sample-size
    comparisons and an empirical SD/SEM. Outputs are overwritten on rerun.
    A fixed NumPy version is needed for strict byte-level reproducibility;
    figures and run duration need not be byte-identical across environments.
    """
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of {tuple(PRESETS)}.")
    parameters = PRESETS[preset]
    n = parameters["n_signals"] if n_signals is None else n_signals
    repeats = parameters["repetitions"] if repetitions is None else repetitions
    for label, value, minimum in (("n_signals", n, 64), ("repetitions", repeats, 2), ("seed", seed, 0)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < minimum:
            raise ValueError(f"{label} must be an integer >= {minimum}.")
    n, repeats, seed = int(n), int(repeats), int(seed)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    jobs = (
        ("1/6: QBER theo Eve và nhiễu nền", lambda: _eve_sweep(output, n, repeats, seed)),
        ("2/6: So sánh mô hình nhiễu", lambda: _noise_sweep(output, n, repeats, seed)),
        ("3/6: Bất định theo cỡ mẫu", lambda: _uncertainty(output, n, repeats, seed)),
        ("4/6: Xác suất thấy lỗi qua nhiều lần chạy BB84", lambda: _error_detection(output, parameters["detection_repetitions"], seed)),
        ("5/6: Mất tín hiệu và tỷ lệ giữ lại", lambda: _loss_sweep(output, n, repeats, seed)),
        ("6/6: Tỷ lệ khóa tiệm cận tham chiếu", lambda: _secret_fraction(output)),
    )
    experiments = []
    with plt.rc_context({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelcolor": "#273849", "axes.titlecolor": "#18324A",
        "figure.facecolor": "white", "axes.facecolor": "#FBFCFE",
        "savefig.bbox": "tight", "pdf.fonttype": 42,
    }):
        for message, function in jobs:
            if progress is not None:
                progress(message)
            experiments.append(function())
    return {
        "preset": preset, "seed": seed, "n_signals": n, "repetitions": repeats,
        "duration_seconds": round(perf_counter() - started, 3),
        "config": {
            "preset": preset, "n_signals": n, "repetitions": repeats,
            "seed": seed, "detection_repetitions": parameters["detection_repetitions"],
            "detection_signal_rule": "max(512, 8 * sample_size)",
            "sample_fraction_default": 0.2, "basis_probability_z": 0.5,
            "confidence": 0.95, "seed_derivation": "first 128 bits SHA-256([base_seed, experiment_id, sorted_config, repeat])",
        },
        "experiments": experiments,
        "highlights": [experiment["findings"][0] for experiment in experiments],
        "error_semantics": {
            "01_02_05": "Mean +/- 1 standard error of the mean (SEM) across independent runs; not a 95% interval.",
            "03": "QBER mean +/- 1 sample standard deviation (SD); Wilson widths are mean per-run 95% interval widths.",
            "04": "95% Wilson interval for probability of observing at least one error across complete independent runs.",
            "06": "Theoretical curves only, without Monte Carlo errors or finite-key security certification.",
        },
        "data_notes": [
            "Raw CSV contains each run's complete configuration, deterministic integer seed and aggregate counts, never raw bits.",
            "qber_actual is simulator-only ground truth; qber_estimate uses the publicly disclosed sample.",
            "Empty CSV cells denote undefined values (e.g. QBER with no detections); never interpret as zero.",
            "Seeds have up to 39 decimal digits: import the seed column as TEXT in Excel to avoid numeric rounding.",
            "CSV uses UTF-8 with BOM. Reproduce a run by constructing BB84Config from its config columns and simulate(config, int(seed)).",
            "Candidate bits are not secret keys; no information reconciliation or privacy amplification is implemented.",
        ],
    }
