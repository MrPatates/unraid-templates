#!/usr/bin/env python3
"""Check this repository against the Community Applications submission rules.

Offline checks: XML structure, required fields, TemplateURL, unique names,
masked secrets, ca_profile.xml. With --online: every linked URL answers and
every Docker image can be pulled anonymously (needs skopeo).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_SELF = "https://raw.githubusercontent.com/MrPatates/unraid-templates/main/"
SECRET = re.compile(r"PASSWORD|PASSWD|TOKEN|SECRET|WEBHOOK|API_?KEY", re.I)

errors: list[str] = []
urls: set[str] = set()
images: set[str] = set()


def fail(where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def text(root: ET.Element, tag: str) -> str:
    return (root.findtext(tag) or "").strip()


def collect(root: ET.Element, *tags: str) -> None:
    for tag in tags:
        for node in root.findall(tag):
            value = (node.text or "").strip()
            if value.startswith("http"):
                urls.add(value)


def check_docker(path: Path) -> str:
    where = path.relative_to(ROOT).as_posix()
    root = ET.parse(path).getroot()
    if root.tag != "Container" or root.get("version") != "2":
        fail(where, 'root element must be <Container version="2">')
    for tag in ("Name", "Repository", "Overview", "Category", "Icon", "TemplateURL"):
        if not text(root, tag):
            fail(where, f"<{tag}> is missing or empty")
    if not (text(root, "Support") or text(root, "Project")):
        fail(where, "<Support> or <Project> is required")
    if len(text(root, "Overview")) < 100:
        fail(where, "<Overview> is too short for review")
    if text(root, "TemplateURL") != RAW_SELF + where:
        fail(where, f"<TemplateURL> must be {RAW_SELF + where}")
    if text(root, "Privileged").lower() == "true":
        fail(where, "privileged containers need a moderator-visible justification")
    for config in root.findall("Config"):
        if not config.get("Description"):
            fail(where, f"Config {config.get('Name')!r} has no description")
        if config.get("Type") == "Variable" and SECRET.search(config.get("Target", "")) and config.get("Mask") != "true":
            fail(where, f"secret variable {config.get('Target')} must have Mask=\"true\"")
    images.add(text(root, "Repository"))
    collect(root, "Icon", "Project", "Support", "ReadMe", "Screenshot")
    return text(root, "Name")


def check_plugin(path: Path) -> str:
    where = path.relative_to(ROOT).as_posix()
    root = ET.parse(path).getroot()
    if root.tag != "Plugin":
        fail(where, "root element must be <Plugin>")
    for tag in ("Name", "PluginURL", "Overview", "Category", "Icon"):
        if not text(root, tag):
            fail(where, f"<{tag}> is missing or empty")
    if not (text(root, "Support") or text(root, "Project")):
        fail(where, "<Support> or <Project> is required")
    plugin_url = text(root, "PluginURL")
    if not (plugin_url.startswith("https://") and plugin_url.endswith(".plg")):
        fail(where, "<PluginURL> must be an https URL to a .plg file")
    collect(root, "Icon", "Project", "Support", "ReadMe", "PluginURL")
    return text(root, "Name")


def check_profile() -> None:
    path = ROOT / "ca_profile.xml"
    if not path.is_file():
        fail("ca_profile.xml", "missing (required at the repository root)")
        return
    root = ET.parse(path).getroot()
    if root.tag != "CommunityApplications":
        fail("ca_profile.xml", "root element must be <CommunityApplications>")
    if len(text(root, "Profile")) < 50:
        fail("ca_profile.xml", "<Profile> must describe the repository")
    icon = text(root, "Icon")
    if icon.startswith(RAW_SELF) and not (ROOT / icon[len(RAW_SELF):]).is_file():
        fail("ca_profile.xml", f"{icon} does not exist in this repository")
    collect(root, "WebPage", "Forum")


def check_online() -> None:
    for url in sorted(urls):
        if url.startswith(RAW_SELF):
            continue  # files of this repository, checked offline
        request = urllib.request.Request(url, headers={"User-Agent": "unraid-templates-validate"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            fail(url, f"unreachable ({getattr(exc, 'reason', exc)})")
            continue
        if status != 200:
            fail(url, f"HTTP {status}")
    if not shutil.which("skopeo"):
        print("skopeo not installed: Docker image check skipped", file=sys.stderr)
        return
    for image in sorted(images):
        result = subprocess.run(["skopeo", "inspect", "--no-creds", "--raw", f"docker://{image}"],
                                capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            fail(image, "image cannot be pulled anonymously")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="also check URLs and Docker images")
    args = parser.parse_args()

    for required in ("LICENSE", "README.md"):
        if not (ROOT / required).is_file():
            fail(required, "missing")
    check_profile()
    names: dict[str, str] = {}
    for path in sorted(ROOT.glob("templates/*.xml")):
        name = check_docker(path)
        if name.lower() in names:
            fail(path.name, f"name {name!r} already used by {names[name.lower()]}")
        names[name.lower()] = path.name
    for path in sorted(ROOT.glob("plugins/*.xml")):
        name = check_plugin(path)
        if name.lower() in names:
            fail(path.name, f"name {name!r} already used by {names[name.lower()]}")
        names[name.lower()] = path.name
    if not names:
        fail("repository", "no template found")
    if args.online:
        check_online()

    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    print(f"{len(names)} app(s) checked{' online' if args.online else ''}: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
