#!/usr/bin/env python3
"""Patch exported HTML for GitHub Pages (relative assets + demo fetch shim)."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

_NAV_REPLACEMENTS = (
    ('href="/"', 'href="./index.html"'),
    ('href="/topology"', 'href="./topology.html"'),
    ('href="/specs"', 'href="./master-story.html?id=pdu-session-sm-policy"'),
    ('href="/stories"', 'href="./master-story.html?id=pdu-session-sm-policy"'),
    ('href="/ladder"', 'href="./ladder.html?id=pdu-session-sm-policy&amp;nfs=SMF,PCF"'),
)


def patch_html_for_pages(text: str) -> str:
    text = text.replace('href="/static/', 'href="./static/')
    text = text.replace("href='/static/", "href='./static/")
    text = text.replace('src="/static/', 'src="./static/')
    text = text.replace("src='/static/", "src='./static/")

    for old, new in _NAV_REPLACEMENTS:
        text = text.replace(old, new)

    if 'name="demo-mode"' not in text:
        text = text.replace(
            '<meta name="viewport"',
            '<meta name="demo-mode" content="true">\n  <meta name="viewport"',
            1,
        )

    if "demo-loader.js" not in text:
        text = re.sub(
            r'(<script\s+src="\./static/site-nav\.js">)',
            r'<script src="./static/demo-loader.js"></script>\n  \1',
            text,
            count=1,
        )
        if "demo-loader.js" not in text:
            text = text.replace("</head>", '  <script src="./static/demo-loader.js"></script>\n</head>', 1)

    return text


def patch_docs_html_files() -> int:
    count = 0
    for name in ("ladder.html", "master-story.html", "topology.html"):
        path = DOCS_DIR / name
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        patched = patch_html_for_pages(original)
        if patched != original:
            path.write_text(patched, encoding="utf-8")
            count += 1
    return count


if __name__ == "__main__":
    n = patch_docs_html_files()
    print(f"Patched {n} HTML file(s) under {DOCS_DIR}")
