#!/usr/bin/env python3
"""Build the learning-llms HTML site in-place.

Walks the repo for `README.md` (homepage) and `**/notes.md` (every other
page) and renders each to a sibling `index.html`. The folder structure IS
the URL structure — no docs/ vs notes/ split, no path rewriting for
ordinary files. Per-page assets (PDFs, images) live in the same folder as
the notes that reference them.

Source extras handled:
  - `{{ include: <path>::<symbol> }}`  — transclude a Python symbol's source
    from a .py file at <path> (resolved from repo root) into a fenced code
    block via `ast`.
  - `[[wiki-link]]`                    — slug-keyed cross-link. Slug is the
    folder path from repo root (e.g., `cs336/lectures/foo`); the homepage
    has slug `""`. Unresolved links render as red stubs.
  - `$…$` / `$$…$$`                    — math, stashed past the markdown
    parser and restored before output so KaTeX renders client-side.

Link rewriting:
  Only one case rewrites: anchor hrefs that resolve into a git submodule
  path. Those become URLs in the submodule's own GitHub repo (since
  GH Pages doesn't pull submodule contents by default). Every other link
  is left alone — relative paths in the source already resolve in the
  output because source and rendered HTML sit in the same folder.

Run from repo root: python3 scripts/build.py
"""

import ast
import hashlib
import os
import re
import sys
from html import escape
from pathlib import Path

try:
    import markdown as md_lib
    from markdown.extensions.toc import TocExtension
except ImportError:
    sys.stderr.write(
        "Missing dependency: markdown. Install: pip install markdown pygments\n"
    )
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent  # scripts/build.py → repo root
TEMPLATE = ROOT / "templates" / "page.html"
SITE_CSS = ROOT / "assets" / "css" / "site.css"
SYNTAX_CSS = ROOT / "assets" / "css" / "syntax.css"

# Folders the walker should never enter (build infra + git internals).
SKIP_DIRS = {".git", "scripts", "templates", "assets", "node_modules", "__pycache__"}


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)
LIST_RE = re.compile(r"^\[(.*)\]$")
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
INLINE_MATH_RE = re.compile(r"\$([^\$\n]+)\$")
WIKI_LINK_RE = re.compile(r"\[\[([^\]\|]+?)(?:\|([^\]]+))?\]\]")
INCLUDE_RE = re.compile(
    r"\{\{\s*include:\s*([^\s:}]+)(?:::([A-Za-z_][\w.]*))?\s*\}\}"
)
PROGRESS_RE = re.compile(
    r"\{\{\s*progress:\s*([^\s,}]+)(?:\s*,\s*total:\s*(\d+))?\s*\}\}"
)
ANCHOR_HREF_RE = re.compile(r'(<a\b[^>]*\bhref=")([^"]+)(")')


def asset_version(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]


def parse_frontmatter(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip().strip('"').strip("'")
        lm = LIST_RE.match(val)
        if lm:
            val = [v.strip().strip('"').strip("'") for v in lm.group(1).split(",") if v.strip()]
        fm[key.strip()] = val
    return fm, body


def parse_submodules() -> dict:
    """Return {submodule_relative_path: github_repo_url_no_dot_git}."""
    gm = ROOT / ".gitmodules"
    if not gm.exists():
        return {}
    out = {}
    path = url = None
    for line in gm.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("[submodule"):
            path = url = None
        elif line.startswith("path"):
            path = line.split("=", 1)[1].strip()
        elif line.startswith("url"):
            url = line.split("=", 1)[1].strip()
        if path and url:
            m = re.match(r"https?://github\.com/([^/]+)/([^/.]+)", url)
            if m:
                out[path] = f"https://github.com/{m.group(1)}/{m.group(2)}"
            path = url = None
    return out


def extract_symbol(source: str, symbol: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    parts = symbol.split(".")
    nodes = tree.body
    node = None
    for p in parts:
        found = None
        for n in nodes:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == p:
                found = n
                break
        if found is None:
            return None
        node = found
        nodes = getattr(node, "body", [])
    return ast.get_source_segment(source, node) if node else None


def resolve_includes(body: str) -> str:
    def _sub(m: re.Match) -> str:
        rel_path = m.group(1).strip()
        symbol = m.group(2)
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            return f'\n<pre class="include-error">include: missing file {escape(rel_path)}</pre>\n'
        source = abs_path.read_text(encoding="utf-8")
        if symbol:
            snippet = extract_symbol(source, symbol)
            if snippet is None:
                return f'\n<pre class="include-error">include: symbol {escape(symbol)} not found in {escape(rel_path)}</pre>\n'
            label = f"{rel_path}::{symbol}"
        else:
            snippet = source
            label = rel_path
        lang = "python" if abs_path.suffix == ".py" else ""
        return f"\n\n*From `{label}`:*\n\n```{lang}\n{snippet}\n```\n\n"

    return INCLUDE_RE.sub(_sub, body)


def slug_for(md_path: Path) -> str:
    """index.md → ""; <dir>/notes.md → "<dir>". Slug is the folder path
    relative to the repo root."""
    if md_path == ROOT / "index.md":
        return ""
    return str(md_path.parent.relative_to(ROOT)).replace("\\", "/")


def output_for(md_path: Path) -> Path:
    return ROOT / "index.html" if md_path.name == "index.md" else md_path.with_name("index.html")


def build_index() -> dict:
    """Walk the repo, collecting renderable pages keyed by slug."""
    index = {}
    sources = []
    home = ROOT / "index.md"
    if home.exists():
        sources.append(home)
    for md_path in ROOT.rglob("notes.md"):
        parts = md_path.relative_to(ROOT).parts
        if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
            continue
        sources.append(md_path)
    for md_path in sources:
        slug = slug_for(md_path)
        fm, _ = parse_frontmatter(md_path.read_text(encoding="utf-8"))
        index[slug] = {
            "path": md_path,
            "title": fm.get("title", md_path.parent.name.replace("_", " ") or "Home"),
        }
    return index


def resolve_progress(body: str) -> str:
    """Expand `{{ progress: <path>[, total: N] }}` into a <details> widget.
    Walks <path>'s subdirectories; each subdir contributes one list item.
    A subdir is "ready" iff its notes.md has `ready: true` in frontmatter
    (anything else, including no notes.md, is a stub). The summary holds
    the progress bar; the body holds the numbered list."""

    def _sub(m: re.Match) -> str:
        rel_path = m.group(1).strip()
        explicit_total = int(m.group(2)) if m.group(2) else None
        abs_path = ROOT / rel_path
        if not abs_path.is_dir():
            return f'<pre class="include-error">progress: not a directory: {escape(rel_path)}</pre>'
        subdirs = sorted(
            p for p in abs_path.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_DIRS
        )
        items = []
        ready_count = 0
        for sub in subdirs:
            notes_path = sub / "notes.md"
            slug = str(sub.relative_to(ROOT)).replace("\\", "/")
            if notes_path.exists():
                fm, _ = parse_frontmatter(notes_path.read_text(encoding="utf-8"))
                title = str(fm.get("title", sub.name.replace("_", " ")))
                ready = str(fm.get("ready", "")).lower() in ("true", "1", "yes")
            else:
                title = sub.name.replace("_", " ")
                ready = False
            items.append({"slug": slug, "title": title, "ready": ready})
            if ready:
                ready_count += 1
        total = explicit_total if explicit_total is not None else len(subdirs)
        if total == 0:
            return ""
        label = abs_path.name.replace("_", " ").title()
        pct = max(0.0, min(100.0, (ready_count / total) * 100)) if total else 0.0
        lines = [
            '<details class="progress-section">',
            '<summary class="progress">',
            f'  <span class="progress__label">{escape(label)}</span>',
            f'  <span class="progress__bar" aria-hidden="true"><span class="progress__fill" style="width: {pct:.2f}%"></span></span>',
            f'  <span class="progress__count">{ready_count}&thinsp;/&thinsp;{total}</span>',
            '</summary>',
            '<ol class="progress-list">',
        ]
        for item in items:
            if item["ready"]:
                lines.append(
                    f'  <li class="ready"><a href="{escape(item["slug"])}/">{escape(item["title"])}</a></li>'
                )
            else:
                lines.append(f'  <li class="stub">{escape(item["title"])}</li>')
        lines.append('</ol>')
        lines.append('</details>')
        return "\n".join(lines)

    return PROGRESS_RE.sub(_sub, body)


def url_for_slug(target_slug: str, from_md_path: Path) -> str:
    """Build a relative URL from `from_md_path` to the page at `target_slug`.
    Both render to index.html in their slug's folder (homepage = repo root),
    so the URL is folder-to-folder."""
    from_dir = ROOT if from_md_path.name == "README.md" else from_md_path.parent
    to_dir = ROOT / target_slug if target_slug else ROOT
    rel = os.path.relpath(to_dir, from_dir).replace("\\", "/")
    return "./" if rel == "." else rel + "/"


def resolve_wiki_links(body: str, index: dict, md_path: Path) -> str:
    def _sub(m: re.Match) -> str:
        target = m.group(1).strip()
        label = (m.group(2) or "").strip()
        if target in index:
            url = url_for_slug(target, md_path)
            text = label or index[target]["title"]
            return f'<a href="{escape(url)}" class="wiki-link">{escape(text)}</a>'
        text = label or target
        return (
            f'<a class="wiki-link wiki-link--stub" '
            f'title="Page not yet created: {escape(target)}">{escape(text)}</a>'
        )

    return WIKI_LINK_RE.sub(_sub, body)


def render_markdown(body: str):
    math_blocks: dict[str, str] = {}

    def _stash(m: re.Match) -> str:
        key = f"@@MATH{len(math_blocks):04d}@@"
        math_blocks[key] = m.group(0)
        return key

    body = DISPLAY_MATH_RE.sub(_stash, body)
    body = INLINE_MATH_RE.sub(_stash, body)

    toc_ext = TocExtension(toc_depth="2-3", marker="")
    md = md_lib.Markdown(
        extensions=["extra", "sane_lists", "smarty", "fenced_code", "codehilite", toc_ext],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False, "linenums": False},
        },
    )
    html = md.convert(body)
    for key, content in math_blocks.items():
        html = html.replace(key, content)
    return html, md.toc_tokens


def rewrite_submodule_links(html: str, md_path: Path, submodules: dict) -> str:
    """If an <a href> resolves to a path inside a submodule, rewrite it to
    that submodule's own GitHub repo URL — because GH Pages doesn't serve
    submodule contents by default. Other links are left alone."""

    def _sub(m: re.Match) -> str:
        prefix, url, suffix = m.group(1), m.group(2), m.group(3)
        if url.startswith(("http://", "https://", "#", "mailto:", "/")):
            return m.group(0)
        path_part, _, fragment = url.partition("#")
        try:
            resolved = (md_path.parent / path_part).resolve()
            rel = resolved.relative_to(ROOT)
        except (ValueError, OSError):
            return m.group(0)
        rel_str = str(rel).replace("\\", "/")
        for sm_path, sm_url in submodules.items():
            if rel_str == sm_path or rel_str.startswith(sm_path + "/"):
                inner = rel_str[len(sm_path) + 1 :] if rel_str != sm_path else ""
                if not inner:
                    new_url = sm_url
                else:
                    base = f"{sm_url}/tree/main" if path_part.endswith("/") else f"{sm_url}/blob/main"
                    new_url = f"{base}/{inner.rstrip('/')}"
                if fragment:
                    new_url += f"#{fragment}"
                return f"{prefix}{new_url}{suffix}"
        return m.group(0)

    return ANCHOR_HREF_RE.sub(_sub, html)


def render_toc(toc_tokens) -> str:
    if not toc_tokens:
        return ""
    return "\n".join(
        f'          <li><a href="#{t["id"]}" data-toc>{t["name"]}</a></li>'
        for t in toc_tokens
    )


def breadcrumb_for(slug: str) -> str:
    if not slug:
        return ""
    return " &rsaquo; ".join(escape(p.replace("_", " ")) for p in slug.split("/"))


def root_for(md_path: Path) -> str:
    """Number of '../' segments from the rendered page's dir back to repo root."""
    if md_path.name == "index.md":
        return "./"
    depth = len(md_path.parent.relative_to(ROOT).parts)
    return "../" * depth if depth else "./"


def render_page(md_path: Path, index: dict, submodules: dict, template: str, css_versions: dict):
    text = md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    slug = slug_for(md_path)

    body = resolve_includes(body)
    body = resolve_progress(body)
    body = resolve_wiki_links(body, index, md_path)

    html_body, toc_tokens = render_markdown(body)
    html_body = rewrite_submodule_links(html_body, md_path, submodules)

    title = fm.get("title", md_path.parent.name.replace("_", " ") or "Home")
    body_class = "home" if md_path.name == "index.md" else ""
    page = template
    page = page.replace("{{title}}", escape(str(title)))
    page = page.replace("{{body_class}}", body_class)
    page = page.replace("{{breadcrumb}}", breadcrumb_for(slug))
    page = page.replace("{{root}}", root_for(md_path))
    page = page.replace("{{toc}}", render_toc(toc_tokens))
    page = page.replace("{{content}}", html_body)
    page = page.replace("{{css_v_site}}", css_versions["site"])
    page = page.replace("{{css_v_syntax}}", css_versions["syntax"])

    out = output_for(md_path)
    out.write_text(page, encoding="utf-8")
    return slug or "(home)"


def main():
    if not TEMPLATE.exists():
        sys.exit(f"Missing template: {TEMPLATE}")
    template = TEMPLATE.read_text(encoding="utf-8")
    css_versions = {"site": asset_version(SITE_CSS), "syntax": asset_version(SYNTAX_CSS)}

    submodules = parse_submodules()
    index = build_index()

    rendered = []
    for slug, info in sorted(index.items()):
        rendered.append(render_page(info["path"], index, submodules, template, css_versions))

    print(f"Built {len(rendered)} pages:")
    for r in rendered:
        print(f"  {r}")


if __name__ == "__main__":
    main()
