"""Kiểm chứng quy tắc đo BB84 bằng mạch một qubit trên máy mô phỏng cục bộ.

Đây là phần bổ sung tùy chọn: mô phỏng Monte Carlo của dự án không cần Qiskit.
Mạch không dùng tài khoản IBM, token, kết nối mạng hoặc thiết bị lượng tử thật.
"""

from __future__ import annotations

from importlib.metadata import version
from numbers import Integral


def run_qiskit_check(shots: int = 4096, seed: int = 84) -> list[dict]:
    """Đo cả tám tổ hợp (cơ sở chuẩn bị, bit, cơ sở đo).

    X chuẩn bị |1>; H đổi cơ sở Z sang X. H ngay trước phép đo Z
    thực hiện phép đo trong cơ sở X. Đúng cơ sở phải trả lại đúng bit;
    khác cơ sở cho hai kết quả đồng xác suất, trong sai số lấy mẫu.

    Kết quả chứa xác suất lý thuyết/thực nghiệm, số đếm và sơ đồ mạch,
    thuận tiện để lưu JSON hoặc đưa vào phần demo. Không dùng kết quả
    này như một chứng minh an toàn hay một liên kết QKD vật lý.
    """
    if isinstance(shots, bool) or not isinstance(shots, Integral) or shots < 1:
        raise ValueError("shots phải là số nguyên dương.")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed phải là số nguyên không âm.")
    shots, seed = int(shots), int(seed)

    # Nhập thư viện tại đây để phần chính luôn chạy được khi thiếu Qiskit.
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise RuntimeError(
            "Chức năng này cần Qiskit tùy chọn. Cài vào môi trường đang dùng: "
            "python -m pip install qiskit qiskit-aer. "
            "Các mô phỏng BB84 bằng NumPy vẫn chạy mà không cần Qiskit."
        ) from exc

    circuits = []
    specifications = []
    for preparation_basis in ("Z", "X"):
        for bit in (0, 1):
            for measurement_basis in ("Z", "X"):
                circuit = QuantumCircuit(1, 1)
                circuit.name = f"BB84_{preparation_basis}{bit}_measure_{measurement_basis}"
                if bit:
                    circuit.x(0)
                if preparation_basis == "X":
                    circuit.h(0)
                circuit.barrier()
                if measurement_basis == "X":
                    circuit.h(0)
                circuit.measure(0, 0)
                circuits.append(circuit)
                specifications.append((preparation_basis, bit, measurement_basis))

    backend = AerSimulator()
    compiled = transpile(circuits, backend, seed_transpiler=seed)
    result = backend.run(compiled, shots=shots, seed_simulator=seed).result()
    records = []
    for index, ((prep_basis, bit, measure_basis), circuit) in enumerate(
        zip(specifications, circuits)
    ):
        counts = result.get_counts(index)
        expected = float(bit) if prep_basis == measure_basis else 0.5
        observed = counts.get("1", 0) / shots
        standard_error = (expected * (1 - expected) / shots) ** 0.5
        records.append(
            {
                "preparation_basis": prep_basis,
                "alice_bit": bit,
                "measurement_basis": measure_basis,
                "expected_p_one": expected,
                "observed_p_one": observed,
                "absolute_error": abs(observed - expected),
                "theory_standard_error": standard_error,
                "counts": {"0": int(counts.get("0", 0)), "1": int(counts.get("1", 0))},
                "shots": shots,
                "seed": seed,
                "backend": "AerSimulator (local, ideal)",
                "qiskit_version": version("qiskit"),
                "qiskit_aer_version": version("qiskit-aer"),
                "circuit": str(circuit.draw(output="text")),
            }
        )
    return records
