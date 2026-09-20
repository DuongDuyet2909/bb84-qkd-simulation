"""Build a portable hand-in ZIP from an explicit list of project artifacts.

Run: python tools/build_release.py
The environment, Git history, private source papers and scratch files are excluded.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build_release() -> Path:
    paths = set()
    for pattern in ("README.md", "requirements*.txt", "pyproject.toml", "*.cmd", ".gitignore"):
        paths.update(ROOT.glob(pattern))
    for directory, suffixes in {
        "bb84": {".py", ".css"}, "docs": {".md", ".bib"},
        "notebooks": {".ipynb"}, "tests": {".py"}, "tools": {".py"},
        "results-demo": {".json"},
        "results-quick": {".csv", ".json", ".html", ".md", ".png", ".pdf"},
        "results-standard": {".csv", ".json", ".html", ".md", ".png", ".pdf"},
    }.items():
        paths.update(p for p in (ROOT/directory).rglob("*")
            if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts
            and ".ipynb_checkpoints" not in p.parts)
    for path in paths:
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Refusing file outside project: {path}")
    expected = [ROOT/"bb84/__main__.py", ROOT/"bb84/report.py", ROOT/"requirements.txt",
                ROOT/"results-standard/report.html", ROOT/"tests/test_protocol.py"]
    if any(p not in paths for p in expected):
        raise ValueError("Required code/results are missing; complete the project before packaging.")
    output = ROOT/"output"
    output.mkdir(exist_ok=True)
    target = output/"BB84_Project_Complete.zip"
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(paths)}
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(paths):
            archive.write(path,"BB84_Project/"+path.relative_to(ROOT).as_posix())
        log = output/"test-results.txt"
        if log.exists():
            archive.write(log,"BB84_Project/validation/test-results.txt")
        archive.writestr("BB84_Project/FILE_SHA256.json",json.dumps(hashes,ensure_ascii=False,indent=2)+"\n")
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC verification failed.")
        print(f"ZIP verified: {len(archive.namelist())} files; {target.stat().st_size/1024**2:.2f} MiB")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output/"BB84_Project_Complete.zip.sha256").write_text(digest+"  "+target.name+"\n",encoding="ascii")
    print(target)
    return target


if __name__ == "__main__":
    build_release()
