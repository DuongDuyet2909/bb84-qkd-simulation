"""Command-line entry points: python -m bb84 demo|simulate|experiments|qiskit-check."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sys
from . import BB84Config, BB84Result, __version__, simulate


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Cần số nguyên dương.")
    return number


def _seed(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("Seed phải không âm.")
    return number


def write_json(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def trace_records(result: BB84Result) -> list[dict]:
    """Teaching view, including simulator-only values; never real secret data."""
    rows = []
    for i in range(result.config.n_signals):
        detected, sifted = bool(result.detected_mask[i]), bool(result.sift_mask[i])
        rows.append({
            "position": i + 1,
            "alice_bit": int(result.alice_bits[i]),
            "alice_basis": "ZX"[result.alice_bases[i]],
            "eve_intercepted": int(result.eve_mask[i]),
            "eve_basis": "ZX"[result.eve_bases[i]] if result.eve_mask[i] else "-",
            "eve_bit": int(result.eve_bits[i]) if result.eve_mask[i] else "-",
            "bob_basis": "ZX"[result.bob_bases[i]],
            "bob_bit": int(result.bob_bits[i]) if detected else "lost",
            "detected": int(detected), "sifted": int(sifted),
            "public_test": int(result.test_mask[i]), "candidate": int(result.key_mask[i]),
            "mismatch_if_sifted": int(result.alice_bits[i] != result.bob_bits[i]) if sifted else "-",
        })
    return rows


def print_trace(result: BB84Result, limit: int = 64) -> None:
    print("\nTrace chỉ dùng để học: bit/mask toàn bộ thuộc góc nhìn của simulator.")
    print("   i  A bit/base  Eve bit/base  B bit/base  Sift  Test  Còn lại")
    for i in range(min(result.config.n_signals, limit)):
        a = f"{result.alice_bits[i]}/{'ZX'[result.alice_bases[i]]}"
        e = f"{result.eve_bits[i]}/{'ZX'[result.eve_bases[i]]}" if result.eve_mask[i] else "-"
        b = f"{result.bob_bits[i]}/{'ZX'[result.bob_bases[i]]}" if result.detected_mask[i] else "lost"
        print(f"{i+1:4}  {a:^10}  {e:^12}  {b:^10}  {int(result.sift_mask[i]):4}  {int(result.test_mask[i]):4}  {int(result.key_mask[i]):7}")
    if result.config.n_signals > limit:
        print(f"Hiển thị {limit}/{result.config.n_signals} tín hiệu; thêm --output để lưu trace.csv đầy đủ.")


def _percent(value: float | None) -> str:
    return "không xác định" if value is None else f"{100 * value:.3f}%"


def print_summary(result: BB84Result, title: str = "Một phiên BB84") -> None:
    data = result.summary()
    print(f"\n{title}")
    print(f"  Phát: {data['n_signals']:,} | Nhận: {data['n_detected']:,} | Sàng lọc: {data['n_sifted']:,}")
    print(f"  Công bố kiểm tra: {data['n_test']:,} | Bit ứng viên còn lại: {data['n_remaining']:,}")
    print(f"  QBER lý thuyết: {_percent(data['theory']['expected_qber'])}")
    print(f"  QBER toàn bộ (simulator biết): {_percent(data['qber_actual'])}")
    print(f"  QBER mẫu (công khai): {_percent(data['qber_estimate'])}")
    low, high = data['qber_interval']
    print(f"  Khoảng Wilson {result.config.confidence:.0%}: [{_percent(low)}, {_percent(high)}]")
    print(f"  Quyết định minh họa: {data['decision']}")
    print("  Chưa tạo khóa bí mật; vẫn cần xác thực, sửa lỗi, xác minh và khuếch đại riêng tư.")


def _base_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--signals", type=_positive, default=10_000, help="Số tín hiệu phát, mặc định 10000")
    parser.add_argument("--seed", type=_seed, default=84)
    parser.add_argument("--trace", action="store_true", help="Hiển thị tối đa 64 tín hiệu; lưu tất cả nếu có --output")
    parser.add_argument("--output", type=Path, help="Thư mục lưu JSON và trace CSV")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BB84: mô phỏng và đối chiếu lý thuyết cho bài tập lớn.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="So sánh 3 tình huống: lý tưởng, nhiễu, Eve")
    _base_options(demo)
    custom = commands.add_parser("simulate", help="Chạy một cấu hình tùy chỉnh")
    _base_options(custom)
    custom.add_argument("--eve", type=float, default=0.0, help="Tỷ lệ chặn độc lập [0,1]")
    custom.add_argument("--noise", type=float, default=0.0, help="Tham số p của kênh được chọn")
    custom.add_argument("--noise-model", choices=["depolarizing", "readout_flip"], default="depolarizing")
    custom.add_argument("--loss", type=float, default=0.0)
    custom.add_argument("--basis-z", type=float, default=0.5)
    custom.add_argument("--sample-fraction", type=float, default=0.2)
    custom.add_argument("--sample-size", type=_positive)
    custom.add_argument("--threshold", type=float, default=0.11, help="Ngưỡng sàng lọc minh họa, không chứng nhận an toàn")
    custom.add_argument("--confidence", type=float, default=0.95)
    experiments = commands.add_parser("experiments", help="Sinh sáu thí nghiệm, CSV, hình và báo cáo HTML")
    experiments.add_argument("--preset", choices=["quick", "standard"], default="quick")
    experiments.add_argument("--signals", type=_positive, help="Ghi đè số tín hiệu của preset, tối thiểu 64")
    experiments.add_argument("--repetitions", type=_positive, help="Ghi đè số lần lặp của preset, tối thiểu 2")
    experiments.add_argument("--seed", type=_seed, default=84)
    experiments.add_argument("--output", type=Path, default=Path("results"))
    quantum = commands.add_parser("qiskit-check", help="Kiểm tra 8 tổ hợp chuẩn bị/đo trên Aer cục bộ")
    quantum.add_argument("--shots", type=_positive, default=4096)
    quantum.add_argument("--seed", type=_seed, default=84)
    quantum.add_argument("--output", type=Path, help="Thư mục lưu qiskit_check.json")
    return parser


def _save_result(result: BB84Result, folder: Path, trace: bool) -> None:
    write_json(folder / "summary.json", result.summary())
    if trace:
        rows = trace_records(result)
        with (folder / "trace.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    else:
        # Remove this exporter's exact generated filename, never a directory.
        # An old trace must not be mistaken for the newly written summary.
        (folder / "trace.csv").unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            cases = [
                ("ideal", "1. Kênh lý tưởng: không Eve, không nhiễu", {}),
                ("noise", "2. Nhiễu đầu ra 3%, không Eve", {"noise_probability": 0.03, "noise_model": "readout_flip"}),
                ("eve", "3. Eve chặn toàn bộ, không nhiễu", {"eve_fraction": 1.0}),
            ]
            records = []
            for identifier, title, overrides in cases:
                result = simulate(BB84Config(n_signals=args.signals, **overrides), seed=args.seed)
                print_summary(result, title)
                if args.trace:
                    print_trace(result)
                if args.output:
                    _save_result(result, args.output / identifier, args.trace)
                records.append({"scenario": identifier, **result.summary()})
            if args.output:
                write_json(args.output / "demo.json", records)
        elif args.command == "simulate":
            result = simulate(BB84Config(
                n_signals=args.signals, eve_fraction=args.eve, noise_probability=args.noise,
                noise_model=args.noise_model, loss_probability=args.loss,
                basis_probability_z=args.basis_z, sample_fraction=args.sample_fraction,
                sample_size=args.sample_size, abort_threshold=args.threshold, confidence=args.confidence,
            ), seed=args.seed)
            print_summary(result)
            if args.trace:
                print_trace(result)
            if args.output:
                _save_result(result, args.output, args.trace)
        elif args.command == "experiments":
            from .experiments import run_experiments
            from .report import build_report
            manifest = run_experiments(
                output=args.output, preset=args.preset, seed=args.seed,
                n_signals=args.signals, repetitions=args.repetitions,
                progress=lambda message: print(message, flush=True),
            )
            path = build_report(args.output, manifest)
            print(f"\nHoàn tất. Báo cáo: {path.resolve()}")
            print(f"Dữ liệu và hình: {args.output.resolve()}")
        elif args.command == "qiskit-check":
            from .qiskit_demo import run_qiskit_check
            rows = run_qiskit_check(args.shots, args.seed)
            print("Chuẩn bị / Đo / P(1) lý thuyết / P(1) thực nghiệm")
            for row in rows:
                print(f"  {row['preparation_basis']}{row['alice_bit']} / {row['measurement_basis']} / "
                      f"{row['expected_p_one']:.3f} / {row['observed_p_one']:.3f}")
            print("AerSimulator cục bộ; đây là kiểm tra phép đo, không phải liên kết QKD vật lý.")
            if args.output:
                write_json(args.output / "qiskit_check.json", rows)
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        parser.exit(2, f"Lỗi: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
