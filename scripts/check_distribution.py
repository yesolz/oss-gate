"""Check public artifact paths, local links, language pairs and static-only behavior."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.forms = []
        self.scripts = []
        self.in_script = False
        self.resources = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.in_script = tag == "script" or self.in_script
        if tag in ("script", "img", "link") and (attrs.get("src") or attrs.get("href")):
            self.resources.append(attrs.get("src") or attrs.get("href"))
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag in ("form", "input", "textarea"):
            self.forms.append(tag)

    def handle_data(self, data):
        if self.in_script:
            self.scripts.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False


def check(root=ROOT):
    errors = []
    site = root / "site/generated"
    html_files = list(site.rglob("*.html"))
    if not html_files:
        errors.append("static demo has not been built")
    for path in html_files:
        parsed = Links()
        text = path.read_text(encoding="utf-8")
        parsed.feed(text)
        if parsed.forms:
            errors.append(f"input form in {path.relative_to(root)}")
        if re.search(r"fetch\s*\(|XMLHttpRequest", "".join(parsed.scripts)) or any(
            urlsplit(u).scheme in ("http", "https") for u in parsed.resources
        ):
            errors.append(f"live dependency in {path.relative_to(root)}")
        for link in parsed.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
            if not target.is_relative_to(site.resolve()):
                errors.append(f"link leaves static root: {path.name} -> {link}")
            elif not target.exists():
                errors.append(f"broken link: {path.relative_to(site)} -> {link}")
            elif not url.path and url.fragment and url.fragment not in parsed.ids:
                errors.append(f"missing anchor: {path.name} -> {link}")
    for folder in (root / "examples/reviews").iterdir():
        if not folder.is_dir():
            continue
        for lang in ("ko", "en"):
            for ext, stem in [("md", "review"), ("html", "report")]:
                if not (folder / f"{stem}.{lang}.{ext}").is_file():
                    errors.append(f"missing {folder.name}/{stem}.{lang}.{ext}")
        data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
        for lang in ("ko", "en"):
            text = (folder / f"review.{lang}.md").read_text(encoding="utf-8")
            if data["target"]["version"] not in text:
                errors.append("missing target version")
    for path in (root / "plugins/oss-gate").rglob("*"):
        if not path.is_file() or any(part in (".venv", "__pycache__") for part in path.parts):
            continue
        if path.suffix not in (".py", ".md", ".json", ".css", ".toml"):
            continue
        text = path.read_text(encoding="utf-8")
        if any(x in text for x in ["/home/ec2-user/", "claude-lab/capstone", "캡스톤 교육생"]):
            errors.append(f"workshop residue: {path.relative_to(root)}")
        if "\u2014" in text:
            errors.append(f"em dash in authored plugin text: {path.relative_to(root)}")
    manifest = json.loads((root / "plugins/oss-gate/plugin.json").read_text(encoding="utf-8"))
    claude = json.loads((root / "plugins/oss-gate/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
    if manifest["version"] != claude["version"]:
        errors.append("manifest version mismatch")
    marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    if marketplace["plugins"][0]["version"] != manifest["version"]:
        errors.append("marketplace version mismatch")
    for relative, key in [
        ("pyproject.toml", "version"),
        ("plugins/oss-gate/pyproject.toml", "version"),
        ("plugins/oss-gate/mcp/depsdev/server.py", "VERSION"),
    ]:
        match = re.search(rf'^{key} = "([^"]+)"', (root / relative).read_text(encoding="utf-8"), re.M)
        if not match or match[1] != manifest["version"]:
            errors.append(f"release version mismatch: {relative}")
    if (root / "LICENSE").read_text(encoding="utf-8") != (root / "plugins/oss-gate/LICENSE").read_text(
        encoding="utf-8"
    ):
        errors.append("plugin license mismatch")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(html_files)} static pages, local links, language pairs, plugin paths and licenses")


if __name__ == "__main__":
    check()
