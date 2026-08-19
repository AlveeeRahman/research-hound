#!/usr/bin/env python3
"""Search-visibility pipeline driven by one manifest.

`.github/repository-metadata.yml` is the single source of truth for everything a
search engine sees: the repository description and topics on github.com, and the
title, description, canonical URL, Open Graph tags, JSON-LD, robots.txt and
sitemap.xml on the GitHub Pages site.

Nothing here rewrites hand-authored prose. The builder only replaces the regions
between `seo:*:begin` / `seo:*:end` markers, and refuses to run when a marker is
missing rather than guessing where generated content belongs.

Subcommands
    validate        the manifest is well-formed, internally consistent, truthful
    build           regenerate the generated regions of docs/ from the manifest
    check           like build but writes nothing; exit 1 if anything would change
    verify          quality gates over the built site
    sync-metadata   reconcile github.com repository description/homepage/topics
    indexnow        submit materially-changed canonical URLs to IndexNow

Standard library only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / ".github" / "repository-metadata.yml"
SCHEMA_VERSION = 1

GENERATED_FROM = ".github/repository-metadata.yml"
GENERATOR = ".github/seo/seo.py"

# GitHub's own limits, not house preference.
MAX_TOPICS = 20
MAX_TOPIC_LEN = 50
MAX_REPO_DESCRIPTION = 350
# Google's sitemap limits.
MAX_SITEMAP_URLS = 50_000
MAX_SITEMAP_BYTES = 50 * 1024 * 1024
# IndexNow's documented batch ceiling.
MAX_INDEXNOW_URLS = 10_000
# GitHub's recommended social preview size.
SOCIAL_PREVIEW_SIZE = (1280, 640)

TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEX_KEY_RE = re.compile(r"^[a-f0-9]{8,128}$")

# Words that describe how good software is rather than what it does. GitHub's topic
# guidance asks for the latter; these read as marketing to a human and as noise to a
# crawler trying to work out what the repository actually is.
PROMOTIONAL_TOPIC_WORDS = (
    "best", "top", "awesome", "must-have", "musthave", "amazing", "ultimate",
    "greatest", "perfect", "insane", "killer", "unmatched", "revolutionary",
)


class ManifestError(Exception):
    """The manifest is unreadable or violates the schema."""


class BuildError(Exception):
    """A generated file could not be produced safely."""


# --------------------------------------------------------------------------
# A deliberately small YAML reader
# --------------------------------------------------------------------------
# These repositories ship standard library only, and the manifest is a fixed, flat
# shape. Pulling in PyYAML to read forty lines of `key: value` would make it the
# single third-party dependency in the tree. So: parse the subset actually used and
# fail loudly on anything outside it, rather than silently misreading it.

_KV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:(\s|$)")


def _scalar(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    if text[0] in "\"'" and len(text) > 1 and text[-1] == text[0]:
        return text[1:-1]
    # Strip an unquoted trailing comment. The leading space is required, so a URL
    # fragment such as `https://example.com/#anchor` survives intact.
    cut = text.find(" #")
    if cut != -1:
        text = text[:cut].strip()
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def parse_yaml(text: str) -> Dict[str, Any]:
    """Parse the manifest subset: nested maps, lists of scalars, lists of maps."""
    lines: List[str] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        leading = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise ManifestError("tabs are not valid YAML indentation")
        lines.append(raw.rstrip())

    pos = [0]

    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def parse_block(min_indent: int) -> Any:
        if pos[0] >= len(lines):
            return None
        line = lines[pos[0]]
        if indent_of(line) < min_indent:
            return None
        if line.lstrip().startswith("- "):
            return parse_list(indent_of(line))
        return parse_map(indent_of(line))

    def parse_list(indent: int) -> List[Any]:
        items: List[Any] = []
        while pos[0] < len(lines):
            line = lines[pos[0]]
            if indent_of(line) != indent or not line.lstrip().startswith("- "):
                break
            rest = line.lstrip()[2:]
            if _KV_RE.match(rest):
                # A list of maps. Rewrite `- key: v` as an ordinary map line so the
                # map parser picks it up together with the sibling keys beneath it.
                lines[pos[0]] = " " * (indent + 2) + rest
                items.append(parse_map(indent + 2))
            else:
                pos[0] += 1
                items.append(_scalar(rest))
        return items

    def parse_map(indent: int) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        while pos[0] < len(lines):
            line = lines[pos[0]]
            here = indent_of(line)
            if here < indent:
                break
            if here > indent:
                raise ManifestError("unexpected indentation at: " + line.strip())
            body = line.strip()
            if body.startswith("- "):
                break
            if ":" not in body:
                raise ManifestError("expected 'key: value' at: " + body)
            key, _, value = body.partition(":")
            pos[0] += 1
            if value.strip() == "":
                child = parse_block(indent + 1)
                out[key.strip()] = child if child is not None else None
            else:
                out[key.strip()] = _scalar(value)
        return out

    result = parse_block(0)
    if pos[0] != len(lines):
        raise ManifestError("could not parse manifest at: " + lines[pos[0]].strip())
    if not isinstance(result, dict):
        raise ManifestError("manifest must be a mapping at the top level")
    return result


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise ManifestError("no manifest at " + str(path))
    return parse_yaml(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Manifest shape
# --------------------------------------------------------------------------

def pages_of(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every page the site publishes, root first, with inherited defaults filled in."""
    canonical = str(manifest.get("canonical_url", ""))
    default_lastmod = manifest.get("content_updated")
    declared = manifest.get("pages") or []
    pages: List[Dict[str, Any]] = []

    root = {
        "path": "",
        "file": "docs/index.html",
        "title": manifest.get("title"),
        "description": manifest.get("description"),
        "lastmod": default_lastmod,
        "url": canonical,
    }
    if declared and isinstance(declared[0], dict) and not declared[0].get("path"):
        root.update({k: v for k, v in declared[0].items() if v is not None})
        root["url"] = canonical
        declared = declared[1:]
    pages.append(root)

    for entry in declared:
        if not isinstance(entry, dict):
            raise ManifestError("each pages[] entry must be a mapping")
        path = str(entry.get("path") or "").lstrip("/")
        pages.append({
            "path": path,
            "file": entry.get("file") or ("docs/" + path.rstrip("/") + "/index.html"),
            "title": entry.get("title"),
            "description": entry.get("description"),
            "lastmod": entry.get("lastmod") or default_lastmod,
            "url": canonical.rstrip("/") + "/" + path,
        })
    return pages


def repo_url(manifest: Dict[str, Any]) -> str:
    return "https://github.com/" + str(manifest.get("repository", ""))


def count_runnable_scripts() -> int:
    """User-facing CLIs under scripts/, ignoring underscore-prefixed helper modules.

    Counting is the job of a program, not of whoever last edited the README. A
    headline number like "26 scripts" that nothing checks drifts the moment a file
    is added or removed, and it drifts in the direction of the more impressive
    number.
    """
    root = REPO_ROOT / "scripts"
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if any(part.startswith("_") for part in relative.parts):
            continue
        total += 1
    return total


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------

def validate(manifest: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    def require(key: str) -> Any:
        value = manifest.get(key)
        if value in (None, "", []):
            errors.append("missing required key: " + key)
        return value

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            "schema_version must be {}, got {!r}".format(
                SCHEMA_VERSION, manifest.get("schema_version")))

    repository = require("repository")
    canonical = require("canonical_url")
    title = require("title")
    description = require("description")
    keyword = require("primary_keyword")
    sitemap_url = require("sitemap_url")
    require("content_updated")

    if repository and not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", str(repository)):
        errors.append("repository must be 'owner/name', got: " + str(repository))

    # URL ownership: every published URL has to live under the canonical host, and
    # the canonical host has to be one this repository can actually publish to.
    if canonical:
        canonical = str(canonical)
        if not canonical.startswith("https://"):
            errors.append("canonical_url must be https")
        if not canonical.endswith("/"):
            errors.append("canonical_url must end in '/' so relative URLs resolve")
        if repository and "github.io" in canonical:
            owner, _, name = str(repository).partition("/")
            expected = "https://{}.github.io/{}/".format(owner.lower(), name)
            if canonical != expected:
                errors.append(
                    "canonical_url {!r} is not this repository's Pages URL ({!r}); "
                    "a custom domain needs a CNAME file in docs/".format(canonical, expected))

    if sitemap_url and canonical and not str(sitemap_url).startswith(str(canonical)):
        errors.append("sitemap_url must live under canonical_url")

    if description and len(str(description)) > MAX_REPO_DESCRIPTION:
        errors.append("description is {} chars; GitHub caps it at {}".format(
            len(str(description)), MAX_REPO_DESCRIPTION))

    # Human-first SEO: the primary phrase has to appear where a reader would meet it
    # naturally, and not so often that it reads as stuffing.
    if keyword and title and str(keyword).lower() not in str(title).lower():
        warnings.append("primary_keyword does not appear in the title")
    if keyword and description and str(keyword).lower() not in str(description).lower():
        warnings.append("primary_keyword does not appear in the description")

    topics = manifest.get("topics") or []
    if not isinstance(topics, list):
        errors.append("topics must be a list")
        topics = []
    if len(topics) > MAX_TOPICS:
        errors.append("{} topics; GitHub allows at most {}".format(len(topics), MAX_TOPICS))
    seen_topics = set()
    for topic in topics:
        text = str(topic)
        if not TOPIC_RE.fullmatch(text):
            errors.append("topic {!r} must be lowercase words separated by hyphens".format(text))
        if len(text) > MAX_TOPIC_LEN:
            errors.append("topic {!r} exceeds {} characters".format(text, MAX_TOPIC_LEN))
        if text in seen_topics:
            errors.append("duplicate topic: " + text)
        seen_topics.add(text)
        for word in PROMOTIONAL_TOPIC_WORDS:
            if word in text.split("-") or text.startswith(word + "-"):
                errors.append(
                    "topic {!r} promotes rather than describes; GitHub topics should "
                    "say what the software is".format(text))
                break

    versions = manifest.get("supported_python") or []
    if not isinstance(versions, list) or not versions:
        errors.append("supported_python must be a non-empty list")
    else:
        for version in versions:
            if not re.fullmatch(r"3\.\d+", str(version)):
                errors.append("supported_python entry {!r} is not a 3.x version".format(version))

    # Network disclosure is a claim about the code, so it must be explicit. An empty
    # list means "nothing here talks to the network" and gets checked in verify.
    surfaces = manifest.get("network_surfaces")
    if surfaces is None:
        errors.append("network_surfaces is required; use [] to declare no network access")
    elif surfaces:
        for surface in surfaces:
            if not isinstance(surface, dict):
                errors.append("each network_surfaces[] entry must be a mapping")
                continue
            for key in ("script", "hosts", "purpose"):
                if not surface.get(key):
                    errors.append("network surface missing {!r}: {!r}".format(key, surface))
            script = surface.get("script")
            if script and not (REPO_ROOT / str(script)).exists():
                errors.append("network surface names a script that does not exist: " + str(script))

    # A headline count is a factual claim about the tree. Check it against the tree.
    declared = manifest.get("runnable_scripts")
    if declared is not None:
        actual = count_runnable_scripts()
        if not isinstance(declared, int):
            errors.append("runnable_scripts must be an integer")
        elif declared != actual:
            errors.append(
                "runnable_scripts says {} but scripts/ holds {} runnable CLI(s); "
                "the manifest, the README and the Pages copy must all say {}".format(
                    declared, actual, actual))

    updated = manifest.get("content_updated")
    if updated and not ISO_DATE_RE.fullmatch(str(updated)):
        errors.append("content_updated must be an ISO 8601 date (YYYY-MM-DD)")
    elif updated:
        try:
            when = datetime.strptime(str(updated), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if when > datetime.now(timezone.utc):
                errors.append("content_updated is in the future; lastmod must be truthful")
        except ValueError:
            errors.append("content_updated is not a real date")

    indexing = manifest.get("indexing") or {}
    if indexing.get("indexnow"):
        key = indexing.get("indexnow_key")
        if not key or not HEX_KEY_RE.fullmatch(str(key)):
            errors.append("indexing.indexnow is on but indexnow_key is missing or not hex")

    # Page titles and descriptions must be distinct. Google's guidance calls out
    # repetitive and boilerplate titles specifically.
    seen_titles: Dict[str, str] = {}
    seen_descriptions: Dict[str, str] = {}
    for page in pages_of(manifest):
        where = page["url"] or "(root)"
        if not page.get("title"):
            errors.append("page {} has no title".format(where))
        elif page["title"] in seen_titles:
            errors.append("page {} repeats the title of {}".format(where, seen_titles[page["title"]]))
        else:
            seen_titles[page["title"]] = where
        if not page.get("description"):
            errors.append("page {} has no description".format(where))
        elif page["description"] in seen_descriptions:
            errors.append("page {} repeats the description of {}".format(
                where, seen_descriptions[page["description"]]))
        else:
            seen_descriptions[page["description"]] = where
        if not (REPO_ROOT / str(page["file"])).exists():
            errors.append("page {} points at a missing file: {}".format(where, page["file"]))

    return errors, warnings


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def esc(text: Any) -> str:
    """Escape for an HTML attribute value."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _marker(name: str, edge: str) -> str:
    if edge == "begin":
        return "<!-- seo:{}:begin  generated from {} by {}; edit the manifest, not this block -->".format(
            name, GENERATED_FROM, GENERATOR)
    return "<!-- seo:{}:end -->".format(name)


def json_ld(manifest: Dict[str, Any], page: Dict[str, Any]) -> str:
    """Honest SoftwareSourceCode. Only fields the repository can actually back up."""
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": manifest.get("name") or str(manifest.get("repository", "")).split("/")[-1],
        "description": page.get("description"),
        "url": page.get("url"),
        "codeRepository": repo_url(manifest),
    }
    if manifest.get("programming_language"):
        data["programmingLanguage"] = manifest["programming_language"]
    if manifest.get("runtime_platform"):
        data["runtimePlatform"] = manifest["runtime_platform"]
    if manifest.get("license_url"):
        data["license"] = manifest["license_url"]
    if manifest.get("version"):
        data["version"] = str(manifest["version"])
    if page.get("lastmod"):
        data["dateModified"] = str(page["lastmod"])
    author = manifest.get("author") or {}
    if author.get("name"):
        person = {"@type": "Person", "name": author["name"]}
        if author.get("url"):
            person["url"] = author["url"]
        data["author"] = person
    if manifest.get("supported_python"):
        versions = [str(v) for v in manifest["supported_python"]]
        data["runtimeRequirement"] = "Python " + ", ".join(versions)
    return json.dumps(data, indent=2, ensure_ascii=False)


def render_head(manifest: Dict[str, Any], page: Dict[str, Any]) -> str:
    canonical = str(manifest.get("canonical_url", ""))
    image = str(manifest.get("og_image") or "")
    image_url = canonical + image.lstrip("/") if image else ""
    lines = [
        _marker("head", "begin"),
        "<title>{}</title>".format(esc(page["title"])),
        '<meta name="description" content="{}">'.format(esc(page["description"])),
        '<link rel="canonical" href="{}">'.format(esc(page["url"])),
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="{}">'.format(esc(manifest.get("site_name") or page["title"])),
        '<meta property="og:title" content="{}">'.format(esc(page["title"])),
        '<meta property="og:description" content="{}">'.format(esc(page["description"])),
        # og:url is kept identical to the canonical link on purpose: a mismatch is a
        # conflicting signal about which URL is the real one.
        '<meta property="og:url" content="{}">'.format(esc(page["url"])),
    ]
    if image_url:
        lines += [
            '<meta property="og:image" content="{}">'.format(esc(image_url)),
            '<meta property="og:image:width" content="{}">'.format(SOCIAL_PREVIEW_SIZE[0]),
            '<meta property="og:image:height" content="{}">'.format(SOCIAL_PREVIEW_SIZE[1]),
            '<meta property="og:image:alt" content="{}">'.format(esc(manifest.get("og_image_alt") or page["title"])),
            '<meta name="twitter:card" content="summary_large_image">',
        ]
    lines += [
        '<script type="application/ld+json">',
        json_ld(manifest, page),
        "</script>",
        _marker("head", "end"),
    ]
    return "\n".join(lines)


def render_links(manifest: Dict[str, Any]) -> str:
    """Truthful internal links. A link is only emitted if its target really exists."""
    base = repo_url(manifest)
    items: List[Tuple[str, str]] = [("Source repository", base)]

    resources = manifest.get("resources") or {}
    if resources.get("releases", True):
        items.append(("Releases and changelog", base + "/releases"))
    for label, relative in (
        ("Security policy", "SECURITY.md"),
        ("Contributing guide", "CONTRIBUTING.md"),
        (resources.get("examples_label") or "Examples", resources.get("examples_path")),
        (resources.get("benchmarks_label") or "Benchmark artifacts", resources.get("benchmarks_path")),
    ):
        if not relative:
            continue
        target = REPO_ROOT / str(relative)
        if target.exists():
            # GitHub serves directories under /tree/ and files under /blob/.
            kind = "/tree/HEAD/" if target.is_dir() else "/blob/HEAD/"
            items.append((str(label), base + kind + str(relative)))

    lines = [
        _marker("links", "begin"),
        '  <h2 id="project-resources">Project resources</h2>',
        "  <ul>",
    ]
    for label, href in items:
        lines.append('    <li><a href="{}">{}</a></li>'.format(esc(href), esc(label)))
    lines.append("  </ul>")

    suite = manifest.get("suite") or []
    if suite:
        rendered = []
        for entry in suite:
            if not isinstance(entry, dict) or not entry.get("url"):
                continue
            name = esc(entry.get("name") or entry["url"])
            if str(entry.get("url")) == str(manifest.get("canonical_url")):
                rendered.append("<strong>{}</strong> (this page)".format(name))
            else:
                rendered.append('<a href="{}">{}</a>'.format(esc(entry["url"]), name))
        if rendered:
            lines.append('  <h2 id="the-suite">Part of a three-skill suite</h2>')
            lines.append("  <p>" + " · ".join(rendered) + "</p>")
    lines.append(_marker("links", "end"))
    return "\n".join(lines)


def render_readme(manifest: Dict[str, Any]) -> str:
    """The handful of README facts that have to agree with the manifest."""
    versions = [str(v) for v in (manifest.get("supported_python") or [])]
    lines = [
        "<!-- seo:readme:begin  generated from {} by {}; edit the manifest, not this block -->".format(
            GENERATED_FROM, GENERATOR),
        "**Documentation**: [{}]({})".format(
            str(manifest.get("canonical_url", "")).replace("https://", "").rstrip("/"),
            manifest.get("canonical_url", "")),
        "",
    ]
    facts = []
    if versions:
        facts.append("Python {}+ (tested on {})".format(versions[0], ", ".join(versions)))
    if manifest.get("runnable_scripts") is not None:
        facts.append("{} runnable scripts".format(manifest["runnable_scripts"]))
    surfaces = manifest.get("network_surfaces")
    if surfaces == []:
        facts.append("no network access from any bundled script")
    elif surfaces:
        facts.append("{} script(s) reach the network".format(len(surfaces)))
    if manifest.get("license_spdx"):
        facts.append("{} licensed".format(manifest["license_spdx"]))
    if facts:
        lines.append(" · ".join(facts))
        lines.append("")

    if surfaces:
        lines.append("<details>")
        lines.append("<summary>What touches the network</summary>")
        lines.append("")
        lines.append("| Script | Reaches | Why |")
        lines.append("| --- | --- | --- |")
        for surface in surfaces:
            hosts = ", ".join(str(h) for h in (surface.get("hosts") or []))
            lines.append("| `{}` | {} | {} |".format(
                surface.get("script"), hosts, surface.get("purpose")))
        lines.append("")
        lines.append("</details>")
        lines.append("")

    suite = manifest.get("suite") or []
    if suite:
        rendered = []
        for entry in suite:
            if not isinstance(entry, dict) or not entry.get("url"):
                continue
            name = str(entry.get("name") or entry["url"])
            if str(entry.get("url")) == str(manifest.get("canonical_url")):
                rendered.append("**{}** (you are here)".format(name))
            else:
                rendered.append("[{}]({})".format(name, entry["url"]))
        if rendered:
            lines.append("Part of a three-skill suite: " + " · ".join(rendered))
            lines.append("")

    lines.append("<!-- seo:readme:end -->")
    return "\n".join(lines)


def render_robots(manifest: Dict[str, Any]) -> str:
    return "\n".join([
        "# Generated from {} by {}. Do not edit by hand.".format(GENERATED_FROM, GENERATOR),
        "# robots.txt controls crawling, not indexing: a blocked URL can still be",
        "# listed without a description. This site is public and wants to be crawled.",
        "User-agent: *",
        "Allow: /",
        "",
        "Sitemap: " + str(manifest.get("sitemap_url", "")),
        "",
    ])


def render_sitemap(manifest: Dict[str, Any]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!-- Generated from {} by {}. Do not edit by hand. -->".format(GENERATED_FROM, GENERATOR),
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in pages_of(manifest):
        lines.append("  <url>")
        lines.append("    <loc>{}</loc>".format(esc(page["url"])))
        if page.get("lastmod"):
            lines.append("    <lastmod>{}</lastmod>".format(esc(page["lastmod"])))
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    return "\n".join(lines)


def replace_region(source: str, name: str, replacement: str, where: str) -> str:
    begin_token = "<!-- seo:{}:begin".format(name)
    end_token = _marker(name, "end")
    start = source.find(begin_token)
    if start == -1:
        raise BuildError(
            "{} has no '{}' marker. Add the marker pair where the generated block "
            "belongs; this tool will not guess a location inside hand-written HTML."
            .format(where, begin_token))
    end = source.find(end_token, start)
    if end == -1:
        raise BuildError("{} opens '{}' but never closes it".format(where, begin_token))
    # Keep the indentation the author used for the opening marker.
    line_start = source.rfind("\n", 0, start) + 1
    indent = source[line_start:start]
    if indent.strip():
        indent = ""
    body = "\n".join((indent + line) if line else line for line in replacement.splitlines())
    return source[:line_start] + body + source[end + len(end_token):]


# --------------------------------------------------------------------------
# build / check
# --------------------------------------------------------------------------

def generate(manifest: Dict[str, Any]) -> Dict[Path, str]:
    """Every file this pipeline owns, mapped to the content it should have."""
    out: Dict[Path, str] = {}

    for page in pages_of(manifest):
        path = REPO_ROOT / str(page["file"])
        if not path.exists():
            raise BuildError("page file does not exist: " + str(page["file"]))
        source = path.read_text(encoding="utf-8")
        source = replace_region(source, "head", render_head(manifest, page), str(page["file"]))
        if "<!-- seo:links:begin" in source:
            source = replace_region(source, "links", render_links(manifest), str(page["file"]))
        out[path] = source

    # The README is hand-written prose with one generated region for the facts that
    # must agree with the manifest. If the markers are absent the README is left
    # entirely alone rather than being restructured.
    readme = REPO_ROOT / "README.md"
    if readme.exists():
        source = readme.read_text(encoding="utf-8")
        if "<!-- seo:readme:begin" in source:
            out[readme] = replace_region(source, "readme", render_readme(manifest), "README.md")

    docs = REPO_ROOT / "docs"
    out[docs / "robots.txt"] = render_robots(manifest)
    out[docs / "sitemap.xml"] = render_sitemap(manifest)

    indexing = manifest.get("indexing") or {}
    if indexing.get("indexnow") and indexing.get("indexnow_key"):
        key = str(indexing["indexnow_key"])
        # IndexNow verifies ownership by fetching <host>/<key>.txt containing the key.
        out[docs / (key + ".txt")] = key + "\n"

    return out


def cmd_build(manifest: Dict[str, Any], dry_run: bool) -> int:
    generated = generate(manifest)
    changed: List[str] = []
    for path, content in generated.items():
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing == content:
            continue
        changed.append(str(path.relative_to(REPO_ROOT)))
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    if not changed:
        print("Generated site is already in sync with the manifest.")
        return 0
    verb = "would change" if dry_run else "wrote"
    for name in sorted(changed):
        print("  {} {}".format(verb, name))
    if dry_run:
        print("\n{} file(s) diverge from {}. Run: python {} build".format(
            len(changed), GENERATED_FROM, GENERATOR))
        return 1
    print("\n{} file(s) regenerated from {}.".format(len(changed), GENERATED_FROM))
    return 0


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------

def png_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        header = path.read_bytes()[:33]
    except OSError:
        return None
    if len(header) < 33 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return (int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big"))


def verify(manifest: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    canonical = str(manifest.get("canonical_url", ""))
    docs = REPO_ROOT / "docs"

    titles: Dict[str, str] = {}
    descriptions: Dict[str, str] = {}

    for page in pages_of(manifest):
        path = REPO_ROOT / str(page["file"])
        name = str(page["file"])
        if not path.exists():
            errors.append("{}: missing".format(name))
            continue
        html = path.read_text(encoding="utf-8")

        found_titles = re.findall(r"<title>(.*?)</title>", html, re.S)
        if len(found_titles) != 1:
            errors.append("{}: expected exactly one <title>, found {}".format(name, len(found_titles)))
        else:
            title = found_titles[0].strip()
            if not title:
                errors.append("{}: empty <title>".format(name))
            if title in titles:
                errors.append("{}: <title> duplicates {}".format(name, titles[title]))
            titles[title] = name
            if len(title) > 65:
                warnings.append("{}: <title> is {} chars; search results truncate near 60".format(
                    name, len(title)))

        desc = re.search(r'<meta name="description" content="(.*?)">', html, re.S)
        if not desc:
            errors.append("{}: no meta description".format(name))
        else:
            text = desc.group(1)
            if text in descriptions:
                errors.append("{}: meta description duplicates {}".format(name, descriptions[text]))
            descriptions[text] = name
            if not 50 <= len(text) <= 165:
                warnings.append("{}: meta description is {} chars; aim for 50-165".format(
                    name, len(text)))

        canon = re.search(r'<link rel="canonical" href="(.*?)">', html)
        if not canon:
            errors.append("{}: no rel=canonical".format(name))
        elif canon.group(1) != page["url"]:
            errors.append("{}: canonical is {!r}, expected the self-referencing {!r}".format(
                name, canon.group(1), page["url"]))

        og_url = re.search(r'<meta property="og:url" content="(.*?)">', html)
        if not og_url:
            errors.append("{}: no og:url".format(name))
        elif canon and og_url.group(1) != canon.group(1):
            errors.append("{}: og:url disagrees with rel=canonical".format(name))

        for prop in ("og:title", "og:type", "og:description"):
            if 'property="{}"'.format(prop) not in html:
                errors.append("{}: no {}".format(name, prop))

        og_image = re.search(r'<meta property="og:image" content="(.*?)">', html)
        if not og_image:
            errors.append("{}: no og:image".format(name))
        else:
            if not og_image.group(1).startswith(canonical):
                errors.append("{}: og:image is not under the canonical host".format(name))
            relative = og_image.group(1)[len(canonical):]
            image_path = docs / relative
            if not image_path.exists():
                errors.append("{}: og:image points at a missing file: docs/{}".format(name, relative))
            else:
                size = png_size(image_path)
                if size is None:
                    warnings.append("docs/{}: not a readable PNG; cannot check dimensions".format(relative))
                elif size != SOCIAL_PREVIEW_SIZE:
                    errors.append("docs/{}: social image is {}x{}, must be {}x{}".format(
                        relative, size[0], size[1], *SOCIAL_PREVIEW_SIZE))

        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if not blocks:
            errors.append("{}: no JSON-LD block".format(name))
        for block in blocks:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append("{}: JSON-LD does not parse: {}".format(name, exc))
                continue
            if data.get("@type") != "SoftwareSourceCode":
                warnings.append("{}: JSON-LD @type is {!r}".format(name, data.get("@type")))
            if data.get("url") != page["url"]:
                errors.append("{}: JSON-LD url disagrees with the canonical URL".format(name))

        # Internal links into the repository must resolve to files that exist.
        for href in re.findall(r'href="([^"]+)"', html):
            for marker in ("/blob/HEAD/", "/tree/HEAD/"):
                prefix = repo_url(manifest) + marker
                if not href.startswith(prefix):
                    continue
                relative = href[len(prefix):].split("#")[0]
                target = REPO_ROOT / relative
                if not target.exists():
                    errors.append("{}: links to {} which is not in the repository".format(
                        name, relative))
                elif marker == "/tree/HEAD/" and not target.is_dir():
                    errors.append("{}: links to {} as a directory, but it is a file".format(
                        name, relative))
                elif marker == "/blob/HEAD/" and target.is_dir():
                    errors.append("{}: links to {} as a file, but it is a directory".format(
                        name, relative))

    robots = docs / "robots.txt"
    if not robots.exists():
        errors.append("docs/robots.txt: missing")
    else:
        text = robots.read_text(encoding="utf-8")
        if str(manifest.get("sitemap_url")) not in text:
            errors.append("docs/robots.txt: does not reference the sitemap")
        if re.search(r"^Disallow:\s*/\s*$", text, re.M):
            errors.append("docs/robots.txt: disallows the whole site")

    sitemap = docs / "sitemap.xml"
    if not sitemap.exists():
        errors.append("docs/sitemap.xml: missing")
    else:
        raw = sitemap.read_bytes()
        if len(raw) > MAX_SITEMAP_BYTES:
            errors.append("docs/sitemap.xml: exceeds Google's 50MB uncompressed limit")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            errors.append("docs/sitemap.xml: not well-formed XML: {}".format(exc))
        else:
            ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
            locations = [e.text or "" for e in root.iter(ns + "loc")]
            if len(locations) > MAX_SITEMAP_URLS:
                errors.append("docs/sitemap.xml: more than {} URLs".format(MAX_SITEMAP_URLS))
            expected = {str(p["url"]) for p in pages_of(manifest)}
            if set(locations) != expected:
                errors.append("docs/sitemap.xml: URLs do not match the manifest pages")
            for loc in locations:
                if not loc.startswith("https://"):
                    errors.append("docs/sitemap.xml: {} is not an https URL".format(loc))
                if not loc.startswith(canonical):
                    errors.append("docs/sitemap.xml: {} is outside the canonical host".format(loc))
            for element in root.iter(ns + "lastmod"):
                if not ISO_DATE_RE.fullmatch((element.text or "").strip()):
                    errors.append("docs/sitemap.xml: lastmod {!r} is not an ISO 8601 date".format(
                        element.text))

    indexing = manifest.get("indexing") or {}
    if indexing.get("indexnow"):
        key = str(indexing.get("indexnow_key", ""))
        key_file = docs / (key + ".txt")
        if not key_file.exists():
            errors.append("docs/{}.txt: IndexNow key file missing".format(key))
        elif key_file.read_text(encoding="utf-8").strip() != key:
            errors.append("docs/{}.txt: does not contain the key".format(key))
    if indexing.get("google_search_console"):
        found = list(docs.glob("google*.html"))
        if not found:
            warnings.append(
                "no google*.html verification file in docs/; Search Console cannot "
                "confirm ownership until one is committed")
    if indexing.get("bing_webmaster_tools"):
        if not (docs / "BingSiteAuth.xml").exists():
            warnings.append("no docs/BingSiteAuth.xml; Bing cannot confirm ownership")

    # An empty network_surfaces list is a positive claim. Check it against the code.
    if manifest.get("network_surfaces") == []:
        offenders = []
        for script in sorted((REPO_ROOT / "scripts").rglob("*.py")) if (REPO_ROOT / "scripts").exists() else []:
            body = script.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\brequests\.(get|post|put|patch|delete)\b|urlopen\(", body):
                offenders.append(str(script.relative_to(REPO_ROOT)))
        for offender in offenders:
            errors.append(
                "network_surfaces is empty but {} makes network calls".format(offender))

    return errors, warnings


# --------------------------------------------------------------------------
# sync-metadata
# --------------------------------------------------------------------------

def github_request(method: str, path: str, token: str, body: Optional[dict] = None) -> Any:
    url = "https://api.github.com" + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "repository-seo-sync")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def cmd_sync_metadata(manifest: Dict[str, Any], apply: bool) -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("error: set GITHUB_TOKEN (needs repository administration write to apply)",
              file=sys.stderr)
        return 2
    full_name = str(manifest["repository"])
    current = github_request("GET", "/repos/" + full_name, token)
    topics = [str(t) for t in (manifest.get("topics") or [])]

    wanted = {
        "description": str(manifest.get("description", "")),
        "homepage": str(manifest.get("canonical_url", "")),
    }
    drift: List[str] = []
    for key, value in wanted.items():
        if (current.get(key) or "") != value:
            drift.append("  {}:\n    on github: {!r}\n    manifest:  {!r}".format(
                key, current.get(key) or "", value))
    if sorted(current.get("topics") or []) != sorted(topics):
        drift.append("  topics:\n    on github: {}\n    manifest:  {}".format(
            sorted(current.get("topics") or []), sorted(topics)))

    if not drift:
        print("github.com metadata already matches the manifest.")
        return 0

    print("Repository metadata diverges from " + GENERATED_FROM + ":")
    for item in drift:
        print(item)

    if not apply:
        print("\nRun with --apply to reconcile (needs a token with repository admin).")
        return 1

    github_request("PATCH", "/repos/" + full_name, token, wanted)
    github_request("PUT", "/repos/" + full_name + "/topics", token, {"names": topics})
    print("\nApplied description, homepage, and topics to " + full_name + ".")
    return 0


# --------------------------------------------------------------------------
# indexnow
# --------------------------------------------------------------------------

def cmd_indexnow(manifest: Dict[str, Any], urls: List[str], dry_run: bool) -> int:
    indexing = manifest.get("indexing") or {}
    if not indexing.get("indexnow"):
        print("IndexNow is off in the manifest; nothing submitted.")
        return 0
    key = str(indexing.get("indexnow_key", ""))
    canonical = str(manifest.get("canonical_url", ""))
    host = canonical.split("/")[2]

    # Never submit anything that is not a live canonical URL on the production host.
    # Preview environments, localhost and duplicate hosts burn crawl quota and teach
    # the index the wrong URL.
    known = {str(p["url"]) for p in pages_of(manifest)}
    submit: List[str] = []
    for url in urls:
        if url not in known:
            print("  skipped (not a canonical page in the manifest): " + url)
            continue
        if not url.startswith("https://" + host + "/"):
            print("  skipped (wrong host): " + url)
            continue
        submit.append(url)

    if not submit:
        print("No materially changed canonical URLs to submit.")
        return 0
    if len(submit) > MAX_INDEXNOW_URLS:
        print("error: {} URLs exceeds the IndexNow batch limit of {}".format(
            len(submit), MAX_INDEXNOW_URLS), file=sys.stderr)
        return 2

    payload = {
        "host": host,
        "key": key,
        "keyLocation": canonical + key + ".txt",
        "urlList": submit,
    }
    print("Submitting {} URL(s) to IndexNow:".format(len(submit)))
    for url in submit:
        print("  " + url)
    if dry_run:
        print("(dry run; nothing sent)")
        return 0

    request = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json; charset=utf-8")
    request.add_header("User-Agent", "repository-seo-sync")
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        if status == 429:
            # IndexNow asks for at least a ten-minute back-off. Retrying inside the
            # same job would be exactly the behaviour the protocol discourages, so
            # this run stops here and the next material change submits again.
            print("IndexNow returned 429 at {}. Backing off; not retrying in this run."
                  .format(stamp))
            return 0
        print("error: IndexNow returned HTTP {} at {}".format(status, stamp), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print("error: could not reach IndexNow: {}".format(exc), file=sys.stderr)
        return 1

    # A 2xx means the notification was accepted, not that anything was indexed.
    print("IndexNow accepted the notification: HTTP {} at {} ({} URL(s)). "
          "Acceptance is not indexing.".format(status, stamp, len(submit)))
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def report(errors: List[str], warnings: List[str], subject: str) -> int:
    for warning in warnings:
        print("  warning: " + warning)
    for error in errors:
        print("  error:   " + error)
    if errors:
        print("\n{}: {} error(s), {} warning(s).".format(subject, len(errors), len(warnings)))
        return 1
    print("{}: OK ({} warning(s)).".format(subject, len(warnings)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check the manifest is well-formed and truthful")
    sub.add_parser("build", help="regenerate the generated regions of docs/")
    sub.add_parser("check", help="exit 1 if the generated site diverges from the manifest")
    sub.add_parser("verify", help="run quality gates over the built site")

    sync = sub.add_parser("sync-metadata", help="reconcile github.com repository metadata")
    sync.add_argument("--apply", action="store_true",
                      help="write the changes (needs repository administration write)")

    index = sub.add_parser("indexnow", help="submit changed canonical URLs to IndexNow")
    index.add_argument("--url", action="append", default=[],
                       help="a canonical URL that materially changed; repeatable")
    index.add_argument("--all", action="store_true", help="submit every canonical page")
    index.add_argument("--dry-run", action="store_true", help="print, do not send")

    args = parser.parse_args(argv)

    try:
        manifest = load_manifest()
    except ManifestError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2

    try:
        if args.command == "validate":
            errors, warnings = validate(manifest)
            return report(errors, warnings, "manifest")
        if args.command in ("build", "check"):
            errors, _ = validate(manifest)
            if errors:
                print("Refusing to build from an invalid manifest:")
                for error in errors:
                    print("  error:   " + error)
                return 2
            return cmd_build(manifest, dry_run=(args.command == "check"))
        if args.command == "verify":
            errors, warnings = verify(manifest)
            return report(errors, warnings, "site")
        if args.command == "sync-metadata":
            return cmd_sync_metadata(manifest, apply=args.apply)
        if args.command == "indexnow":
            urls = [str(p["url"]) for p in pages_of(manifest)] if args.all else args.url
            return cmd_indexnow(manifest, urls, dry_run=args.dry_run)
    except (ManifestError, BuildError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
