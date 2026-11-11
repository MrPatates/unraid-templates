#!/usr/bin/env python3
"""Copy each app's template from its own repository (listed in sources.json).

The app repositories stay the source of truth; this repository only republishes
their templates for Community Applications. Docker templates get their
<TemplateURL> rewritten to the raw URL of the copy in this repository.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_SELF = "https://raw.githubusercontent.com/MrPatates/unraid-templates/main/"
HEADER = "<!-- Synced automatically from https://github.com/{repo}/blob/{ref}/{path} - edit it there, not here. -->"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "unraid-templates-sync"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def transform(source: dict, text: str) -> str:
    ref = source.get("ref", "main")
    header = HEADER.format(repo=source["repo"], ref=ref, path=source["path"])
    if source["type"] == "docker":
        target_url = RAW_SELF + source["target"]
        text, count = re.subn(r"<TemplateURL>.*?</TemplateURL>", f"<TemplateURL>{target_url}</TemplateURL>", text, count=1, flags=re.S)
        if count != 1:
            raise ValueError(f"{source['path']}: no <TemplateURL> element")
    text = re.sub(r"^\s*<!-- Synced automatically from .*? -->\n", "", text, flags=re.M)
    declaration = re.match(r"\s*<\?xml[^>]*\?>\s*\n?", text)
    if declaration:
        text = declaration.group(0).rstrip() + "\n" + header + "\n" + text[declaration.end():]
    else:
        text = header + "\n" + text
    return text.rstrip() + "\n"


def main() -> int:
    sources = json.loads((ROOT / "sources.json").read_text())
    failed = False
    for source in sources:
        url = f"https://raw.githubusercontent.com/{source['repo']}/{source.get('ref', 'main')}/{source['path']}"
        try:
            text = transform(source, fetch(url))
        except Exception as exc:  # report every source, fail at the end
            print(f"ERROR {source['repo']}/{source['path']}: {exc}", file=sys.stderr)
            failed = True
            continue
        target = ROOT / source["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_text() == text:
            print(f"unchanged {source['target']}")
        else:
            target.write_text(text)
            print(f"updated {source['target']} from {source['repo']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
