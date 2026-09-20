"""Build portable offline HTML/Markdown reports from verified local assets."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
from html import escape
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from . import __version__


def _dump(path: Path, content: object) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def _environment() -> dict:
    packages = {}
    for name in ("numpy", "matplotlib", "qiskit", "qiskit-aer"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    directory = Path(__file__).parent
    sources = sorted([*directory.glob("*.py"), *directory.glob("*.css")])
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "executable": sys.executable, "packages": packages, "project_version": __version__,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    }


def _safe_relative(value: str | None, folder: Path) -> str | None:
    if not value:
        return None
    path = Path(value)
    target = (folder/path).resolve()
    if path.is_absolute() or not target.is_relative_to(folder.resolve()):
        raise ValueError("Report asset must stay inside its output directory.")
    if not target.is_file():
        raise ValueError(f"Missing report asset: {value}")
    return path.as_posix()


def build_report(output: str | Path, manifest: dict) -> Path:
    """Create report.html, RESULTS.md and metadata.json; return HTML path.

    Move or zip the entire output folder to keep figures/CSVs accessible.
    Theoretical experiments have raw_csv=None and are labelled explicitly.
    No user-supplied title, description or finding is inserted as raw HTML.
    """
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    records = manifest["experiments"]
    navigation, cards, sections = [], [], []
    for index, record in enumerate(records, 1):
        identifier = f"experiment-{index}"
        title, description = str(record["title"]), str(record.get("description", ""))
        figure = _safe_relative(record.get("figure"), folder)
        links, md_links = [], []
        for key, label in (("raw_csv", "CSV từng lần chạy"), ("summary_csv", "CSV tổng hợp / lý thuyết"), ("pdf", "Hình PDF")):
            asset = _safe_relative(record.get(key), folder)
            if asset:
                links.append(f'<a class="asset" href="{escape(asset,quote=True)}">{label} ↗</a>')
                md_links.append(f"[{label}]({asset})")
        findings = record.get("findings", [])
        if isinstance(findings, str):
            findings = [findings]
        semantics = record.get("semantics", record.get("error_semantics", record.get("error_bar_semantics", "")))
        if isinstance(semantics, (dict, list)):
            semantics = json.dumps(semantics, ensure_ascii=False)
        navigation.append(f'<a href="#{identifier}"><span>{index:02d}</span>{escape(title)}</a>')
        picture = f'<img src="{escape(figure,quote=True)}" alt="{escape(title,quote=True)}" loading="lazy">' if figure else ""
        finding_items = "".join(f'<li>{escape(str(item))}</li>' for item in findings)
        cards.append(f'''<section class="experiment" id="{identifier}">
<div class="section-title"><span class="number">{index:02d}</span><div><h2>{escape(title)}</h2><p>{escape(description)}</p></div></div>
<div class="figure">{picture}</div><p class="semantics">{escape(str(semantics))}</p>
<div class="findings"><h3>Đọc kết quả</h3><ul>{finding_items}</ul></div><div class="downloads">{"".join(links)}</div></section>''')
        sections.append(f"## {index}. {title}\n\n{description}\n\n"
            + (f"![{title}]({figure})\n\n" if figure else "")
            + "\n".join(f"- {item}" for item in findings)
            + (f"\n\nÝ nghĩa thống kê: {semantics}" if semantics else "")
            + "\n\n"+" · ".join(md_links))
    env = _environment()
    meta_file = folder/"metadata.json"
    prior = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    _dump(meta_file, {**prior, **manifest, "environment": env,
        "report_created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Educational BB84; no actual secret-key extraction or composable finite-key proof."})
    seed, preset = manifest.get("seed",84), str(manifest.get("preset","custom"))
    signals, repetitions = manifest.get("n_signals","—"), manifest.get("repetitions","—")
    duration = manifest.get("duration_seconds")
    duration_text = f"{duration:.1f} giây" if isinstance(duration,(int,float)) else "xem metadata"
    stats = [(str(len(records)),"THÍ NGHIỆM"),
             (f"{signals:,}" if isinstance(signals,int) else str(signals),"TÍN HIỆU / PHIÊN CHÍNH"),
             (str(repetitions),"LẦN LẶP / CẤU HÌNH CHÍNH"), (str(seed),"SEED")]
    stat_html = "".join(f"<div><strong>{escape(value)}</strong><span>{label}</span></div>" for value,label in stats)
    command = f"python -m bb84 experiments --preset {preset} --output results-reproduced --seed {seed}"
    if isinstance(signals,int):
        command += f" --signals {signals}"
    if isinstance(repetitions,int):
        command += f" --repetitions {repetitions}"
    limitations = (
        "Mô hình dùng qubit lý tưởng, Eve chặn–đo–gửi lại với cơ sở đều và mất tín hiệu độc lập. "
        "QBER toàn bộ là thông tin chẩn đoán của simulator; Alice/Bob chỉ công bố mẫu. "
        "Khoảng Wilson minh họa bất định nhị thức, không phải chứng minh an toàn khóa hữu hạn. "
        "Bit ứng viên còn lại chưa trải qua xác thực, sửa lỗi, xác minh và khuếch đại riêng tư. "
        "QBER thấp không chứng minh không có Eve; thấy lỗi không xác định tác nhân gây lỗi.")
    style = (Path(__file__).parent/"report_style.css").read_text(encoding="utf-8")
    page = f'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BB84 · Kết quả mô phỏng</title><style>{style}</style></head><body>
<header><div class="eyebrow">Lý thuyết mật mã · Thí nghiệm có thể tái lập</div>
<h1>BB84: từ phép đo<br>đến phân tích sai số</h1><p>Khảo sát nghe lén, nhiễu, cỡ mẫu và mất tín hiệu. Mỗi kết quả đi kèm dữ liệu, đường đối chiếu và phạm vi diễn giải.</p>
<div class="stats">{stat_html}</div></header><div class="layout"><aside><strong>NỘI DUNG THÍ NGHIỆM</strong>
{"".join(navigation)}<a href="#method">Phương pháp & tái lập</a></aside><main>
<div class="note"><strong>Cách đọc kết quả</strong>Các hình 1–5 dùng mô phỏng Monte Carlo; hình 6 là tham chiếu lý thuyết tiệm cận. Bộ mã chưa tạo khóa bí mật dùng trong thực tế. Thí nghiệm xác suất thấy lỗi dùng số lần lặp và cỡ khối riêng theo chú thích.</div>
{"".join(cards)}<section class="method" id="method"><h2>Phương pháp, giới hạn và tái lập</h2><p>{escape(limitations)}</p>
<p>Preset: <strong>{escape(preset)}</strong> · Thời gian tính toán: <strong>{escape(duration_text)}</strong>.
Python {escape(env['python'])}; NumPy {escape(env['packages'].get('numpy','?'))}; Matplotlib {escape(env['packages'].get('matplotlib','?'))}.</p>
<p>Dùng đúng phiên bản và mã nguồn trong metadata để đối chiếu số liệu:</p><pre><code>{escape(command)}</code></pre>
<p><a href="metadata.json">Cấu hình, phiên bản, mã băm nguồn ↗</a> · <a href="RESULTS.md">Bản kết quả Markdown ↗</a></p>
<p>Nền tảng: <a href="https://doi.org/10.1103/PhysRevLett.85.441">Shor–Preskill (2000)</a>;
<a href="https://doi.org/10.1103/RevModPhys.81.1301">Scarani và cộng sự (2009)</a>. Đọc docs/SCIENCE.md trong bộ mã để xem dẫn xuất và giả định.</p>
</section><footer>BB84 Course Project {__version__} · Báo cáo cục bộ, không cần Internet để xem hình và dữ liệu.</footer></main></div></body></html>'''
    html_path = folder/"report.html"
    html_path.write_text(page,encoding="utf-8")
    markdown = ("# Kết quả mô phỏng BB84\n\n"
        + f"Preset **{preset}**, N={signals}, repetitions={repetitions}, seed={seed}. "
        + "Thí nghiệm xác suất thấy lỗi dùng cỡ khối/số lần lặp riêng theo metadata.\n\n"
        + limitations + "\n\n" + "\n\n".join(sections)
        + "\n\n## Tái lập\n\n```text\n" + command + "\n```\n\n"
        + "Xem metadata.json để biết phiên bản, cấu hình và SHA-256 mã nguồn. Seed từng lần chạy nằm trong CSV thô.\n")
    (folder/"RESULTS.md").write_text(markdown,encoding="utf-8")
    return html_path
