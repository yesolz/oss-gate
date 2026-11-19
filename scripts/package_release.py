"""Create a deterministic source distribution without local environments or private outputs."""

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", "dist", "verification-local"}
ALLOWED_ROOTS = {"plugins", "examples", "docs", "scripts", "tests", ".github", ".claude-plugin", ".agents", "site"}
ALLOWED_FILES = {
    "README.md",
    "README.ko.md",
    "LICENSE",
    "NOTICE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
    ".gitattributes",
}


def build():
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or any(p in EXCLUDED_PARTS for p in rel.parts):
            continue
        if rel.parts[0] not in ALLOWED_ROOTS and str(rel) not in ALLOWED_FILES:
            continue
        if str(rel).startswith("site/generated/") or str(rel) == "docs/IMPLEMENTATION.md":
            continue
        if path.is_symlink():
            raise ValueError(f"symlink in release: {rel}")
        if path.name.startswith(".env") or path.suffix in (".pyc", ".log"):
            raise ValueError(f"private/runtime file in release: {rel}")
        files.append((path, rel))
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    archive = out / "oss-gate-v0.2.0.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, rel in files:
            info = zipfile.ZipInfo("oss-gate-v0.2.0/" + rel.as_posix(), date_time=(2026, 11, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")
    print(f"{archive}: {len(files)} files, {archive.stat().st_size} bytes\nSHA-256: {digest}")
    return archive


if __name__ == "__main__":
    build()
