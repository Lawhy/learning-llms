# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal LLM-learning knowledge base, published as a static site. Content is organized per-course (currently only `cs336/` — Stanford CS336 "Language Modeling from Scratch", Spring 2026). Course materials (lecture slides, assignment submodules) sit alongside the `notes.md` that references them; the folder structure IS the URL structure.

## Build & preview

```bash
pip install markdown pygments
python3 scripts/build.py        # render every notes.md → sibling index.html
python3 -m http.server          # preview at http://localhost:8000/
```

**Rebuild after editing any `.md`** — the committed `index.html` siblings are build artifacts, not hand-written. `scripts/build.py` must be run from the repo root (it derives `ROOT` from its own location, so `cd` first if needed).

There is no test suite, linter, or CI; correctness is verified by previewing the rendered site.

## Renderer architecture (`scripts/build.py`)

One self-contained script. To stay productive when editing it, keep these design rules in mind:

- **Discovery**: walks the repo for `index.md` (homepage) and every `**/notes.md`, skipping `SKIP_DIRS` (`.git`, `scripts`, `templates`, `assets`, …). Each source renders to a sibling `index.html` — no `docs/` vs `notes/` split, no path rewriting for ordinary files.
- **Slug = folder path from repo root.** Homepage has slug `""`. `cs336/lectures/foo/notes.md` → slug `cs336/lectures/foo`. Slugs key the wiki-link index and drive `url_for_slug` (folder-to-folder relative URLs).
- **Frontmatter** is a tiny custom parser (not PyYAML): `title:`, `ready:` (controls progress widget), and bracket-list values. Don't reach for YAML features it doesn't support.
- **Source extras** processed in order before markdown: `{{ include: path[::symbol] }}` (AST-extracts a Python symbol into a fenced block), `{{ progress: <dir>[, total: N] }}` (renders the `<details>` progress widget by scanning subdirs for `ready: true`), `[[wiki-link]]` (slug-keyed cross-link; unresolved → red stub).
- **Math is stashed past the markdown parser.** `$…$` / `$$…$$` are replaced with `@@MATHnnnn@@` sentinels before `markdown` runs, then restored verbatim so KaTeX renders client-side. Don't change this without checking math still survives Python-Markdown's smartypants/extras.
- **Link rewriting is intentionally minimal**: only anchors that resolve into a git submodule path are rewritten — to the submodule's own GitHub URL (since GH Pages doesn't serve submodule contents). Every other relative link is left alone.
- **Cache-busting**: `site.css` / `syntax.css` get an 8-char md5 query string injected into the template. Add a new CSS file → wire it through `css_versions` and `templates/page.html` the same way.

`templates/page.html` is a single string-replace template — placeholders are literal `{{title}}`, `{{content}}`, `{{toc}}`, `{{root}}`, `{{breadcrumb}}`, `{{body_class}}`, `{{css_v_site}}`, `{{css_v_syntax}}`. Not Jinja; don't introduce control flow syntax there.

## Content conventions

- **Pages**: every renderable page is a `notes.md` (or the root `index.md`) with frontmatter. Set `ready: true` to mark a lecture/assignment as written — the homepage progress bars count `ready` subdirs only.
- **Lecture folders**: snake_case `lecture_NN_title` (zero-padded `NN`, lowercase, fs-unsafe punctuation dropped). The `{{ progress: cs336/lectures }}` widget walks these alphabetically, so the `NN` prefix is what gives them stable order.
- **Assignment folders**: `cs336/assignments/assignmentN/` contains the upstream Stanford repo as a git submodule (e.g. `assignment1-basics/`) plus a sibling `notes.md`. The submodule name follows the assignment theme (`-basics`, `-systems`, `-scaling`, `-data`, `-alignment`), not a fixed suffix. Links into the submodule are rewritten to GitHub by the build script.
- **Per-page assets** (PDFs, images) live in the same folder as the `notes.md` that references them — relative links resolve identically in source and rendered HTML.

## CS336 assignment walkthroughs

The `/cs336-assignment` skill (defined in `.claude/commands/cs336-assignment.md`) drives interactive, problem-by-problem assignment sessions and **enforces an academic-integrity protocol — never write code or give solutions directly for assignment problems.** Use the skill when the user wants to work through an assignment; final answers get recorded in that assignment's `notes.md`.
