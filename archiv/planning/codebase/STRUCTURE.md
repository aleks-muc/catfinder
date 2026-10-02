# Codebase Structure

**Analysis Date:** 2026-05-05

## Directory Layout

```
Catfinder/
├── catfinder.py                # Single-file pipeline (CLI entry, scrape, evaluate, render, persist)
├── requirements.txt            # Pinned-min dependency floor (anthropic, bs4, pydantic, requests)
├── README.md                   # Setup, usage, "wie es funktioniert" overview
├── .gitignore                  # Ignores .venv, __pycache__, .env, reports/*.html, .DS_Store
├── .github/
│   └── workflows/
│       └── catfinder.yml       # Twice-daily cron: run script, publish docs/, commit state, mail report
├── state/
│   ├── .gitkeep                # Forces directory to exist in git
│   └── seen_cats.json          # Persistent cat-by-cat ratings & metadata (committed by CI)
├── reports/
│   ├── .gitkeep
│   └── report.html             # Local-only artifact, gitignored, overwritten each run
├── docs/
│   └── index.html              # CI-published report + injected GitHub Pages banner (committed)
├── .planning/
│   └── codebase/               # GSD codebase maps (this directory)
├── .venv/                      # Local virtualenv (gitignored)
└── .claude/                    # Claude Code workspace (worktrees, etc.)
```

## Directory Purposes

**Repo root:**
- Purpose: holds the executable script + manifest + meta files. There is no `src/` layout.
- Contains: `catfinder.py`, `requirements.txt`, `README.md`, dotfiles.
- Key files: `catfinder.py` (the entire program), `requirements.txt`.

**`.github/workflows/`:**
- Purpose: GitHub Actions CI/CD. Single workflow that schedules + publishes the report.
- Contains: `catfinder.yml`.
- Key files: `catfinder.yml` — defines cron, env injection, Pages publishing, SendGrid mail step.

**`state/`:**
- Purpose: durable run-to-run memory of which cats have been seen and how Claude rated them.
- Contains: `seen_cats.json` (one JSON object keyed by `cat_id`), `.gitkeep`.
- Key files: `state/seen_cats.json` — tracked in git so CI can pick up where the previous run left off.
- Generated: yes (by `catfinder.py` `save_state`).
- Committed: yes (by CI bot, hand-edits possible).

**`reports/`:**
- Purpose: the human-facing HTML report from a local run.
- Contains: `report.html`, `.gitkeep`.
- Key files: `reports/report.html` — gitignored (`reports/*.html`), overwritten on every run.
- Generated: yes.
- Committed: no.

**`docs/`:**
- Purpose: GitHub Pages publishing root. CI copies the report here with an extra banner header.
- Contains: `index.html`.
- Key files: `docs/index.html` — same content as `reports/report.html` plus an injected banner div linking back to the Pages URL.
- Generated: yes (by the workflow's inline Python heredoc step, `.github/workflows/catfinder.yml` lines 35-49).
- Committed: yes.

**`.planning/codebase/`:**
- Purpose: GSD agent-generated codebase maps (architecture, structure, conventions, etc.).
- Contains: this file and `ARCHITECTURE.md`.
- Generated: yes (by `gsd-map-codebase`).
- Committed: typically yes.

**`.venv/`:**
- Purpose: local Python virtualenv for development.
- Generated: yes (developer runs `python3 -m venv .venv`).
- Committed: no (in `.gitignore`).

**`.claude/`:**
- Purpose: Claude Code session/worktree storage. Not part of the application.
- Generated: yes.
- Committed: no (project-local).

## Key File Locations

**Entry Points:**
- `catfinder.py`: CLI entry; the `main()` function (line 709) wired by `if __name__ == "__main__": sys.exit(main())` (line 862-863).
- `.github/workflows/catfinder.yml`: scheduled & dispatchable entry; runs `python catfinder.py --no-browser`.

**Configuration:**
- `catfinder.py` lines 42-73: hard-coded URLs (`BASE`, `LISTING_URL`, `PROFILE_URL_TMPL`), `USER_AGENT`, paths (`ROOT`, `STATE_DIR`, `STATE_FILE`, `REPORT_DIR`, `REPORT_FILE`), Claude params (`MODEL = "claude-haiku-4-5"`, `MAX_EVAL_WORKERS = 2`, `API_RETRY_DELAYS = [10, 30, 60]`, `PROFILE_FETCH_DELAY_S = 0.4`), regexes, `RATING_META`.
- `requirements.txt`: dependency floors only (`anthropic>=0.40.0`, `beautifulsoup4>=4.12.0`, `pydantic>=2.0`, `requests>=2.31.0`). No `pyproject.toml`, no lockfile.
- `.github/workflows/catfinder.yml`: CI configuration — cron schedule, Python version (`3.12`), secrets (`ANTHROPIC_API_KEY`, `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM`).
- Environment variables (runtime): `ANTHROPIC_API_KEY` (required), `GITHUB_OUTPUT` (auto-set by CI).

**Core Logic:**
- `catfinder.py` lines 80-119: data models (`Cat`, `CatRating`) and `SYSTEM_PROMPT`.
- `catfinder.py` lines 126-147: state I/O (`load_state`, `save_state`).
- `catfinder.py` lines 154-414: scraping & text extraction (`_http_get`, `scrape_listing`, `fetch_profile_text`, `detect_interested`, `find_companion_names`, `extract_age_hint`, `age_hint_to_months`).
- `catfinder.py` lines 421-481: Claude evaluation (`evaluate_cat`, `evaluate_all`).
- `catfinder.py` lines 297-695: HTML report rendering (`_build_filter_bar`, `HTML_TEMPLATE`, `render_report`, `write_and_open_report`, `_card_sort_key`).
- `catfinder.py` lines 702-859: CLI orchestration (`_write_github_output`, `main`).

**Generated Artifacts:**
- `state/seen_cats.json`: cat-keyed JSON (committed).
- `reports/report.html`: HTML report (gitignored).
- `docs/index.html`: HTML report with banner (committed by CI).

**Testing:**
- None present. There is no `tests/`, `pytest`, or `unittest` scaffolding. Adding tests is an open task.

## Naming Conventions

**Files:**
- Python script: lowercase, single word — `catfinder.py`.
- Workflow file: lowercase, matches the project name — `.github/workflows/catfinder.yml`.
- JSON state: snake_case descriptive — `seen_cats.json`.
- HTML reports: short, lowercase — `report.html`, `index.html`.

**Directories:**
- All lowercase, single word: `state/`, `reports/`, `docs/`.
- Hidden meta dirs: leading dot — `.github/`, `.planning/`, `.claude/`, `.venv/`.

**Inside `catfinder.py`:**
- Constants: `UPPER_SNAKE_CASE` (`BASE`, `LISTING_URL`, `MODEL`, `RATING_META`).
- Public functions: `lower_snake_case` (`scrape_listing`, `evaluate_all`, `render_report`).
- Private helpers: leading underscore (`_http_get`, `_pick`, `_build_filter_bar`, `_card_sort_key`, `_write_github_output`).
- Classes: `PascalCase` (`Cat`, `CatRating`).
- Section dividers: `# --- ... ---` block comments grouping related top-level definitions (lines 38-40, 76-78, 122-124, 150-152, 417-419, 494-496, 698-700).

## Where to Add New Code

**Adding new CLI flags:**
- Edit `argparse` setup in `main()` at `catfinder.py:710-714`.
- Branch on the flag in `main()`'s body, around the `--reset` / `--all` checks (`catfinder.py:724-743`).
- If the flag affects CI runs, also update `.github/workflows/catfinder.yml` step "Catfinder ausführen".

**Adding a new scraping field on a Cat:**
- Add a field to the `Cat` dataclass at `catfinder.py:80-91` (with a default for back-compat with old state entries).
- Extract it inside `scrape_listing` (`catfinder.py:160-219`) or in the post-fetch enrichment block in `main()` (`catfinder.py:805-822`).
- Display it in `render_report` either in `_meta_line` (`catfinder.py:572-579`) or as a new line/badge near `_partner_line` / `_interested_badge`.
- If it should survive into next run, ensure it's stored in the `state[cat.cat_id]` update at `catfinder.py:849-855`.

**Adding a new rating category:**
- Update the `Rating = Literal[...]` alias and `CatRating.rating` Literal at `catfinder.py:66, 97-104`.
- Add an entry in `RATING_META` (`catfinder.py:68-73`) — emoji, label, color, sort `order` string.
- Update the `SYSTEM_PROMPT` (`catfinder.py:108-119`) so Claude knows about it.
- Update the legacy-state guard lists at `catfinder.py:750-751` and `catfinder.py:776-777` so old state values still parse.

**Adding a new report section:**
- Add a new section block alongside `sect1`, `sect_gone`, `sect2` inside `render_report` (`catfinder.py:603-678`).
- Concatenate it into the `body=` argument of `HTML_TEMPLATE.format(...)` (`catfinder.py:680-687`).

**Adding a new filter to the report UI:**
- Edit `_build_filter_bar` (`catfinder.py:297-393`): add a button to the HTML, add CSS in the `<style>` block, add toggle handler + state variable in the embedded JS IIFE. Make sure the `filter()` JS function reads a corresponding `data-...` attribute from each card.
- Set the matching `data-...` attribute when emitting cards in `render_report` (`catfinder.py:614-626`, `642-654`, `665-677`).

**Adding a new external integration (e.g. Slack alerts):**
- Add a new function near `_write_github_output` (`catfinder.py:702-706`) that emits/POSTs the data.
- Call it from `main()` after `save_state` (`catfinder.py:856-858`).
- For CI-only side effects, prefer adding a new step to `.github/workflows/catfinder.yml` rather than calling out from Python.

**Adding tests (currently none):**
- Create `tests/` at the repo root with `test_*.py` files.
- Add `pytest` to `requirements.txt` (or split into a separate `requirements-dev.txt`).
- Functions most worth covering first: `_card_sort_key`, `find_companion_names`, `age_hint_to_months`, `extract_age_hint`, `detect_interested` (all pure, no HTTP).

## Special Directories

**`state/`:**
- Purpose: only `seen_cats.json` plus a `.gitkeep`.
- Generated: yes.
- Committed: yes (so CI runs are stateful across days).
- Caveat: hand-edits affect the next diff. To force a full re-evaluation, delete the file or use `python catfinder.py --reset`.

**`reports/`:**
- Purpose: local artifact directory; the script auto-creates it via `REPORT_DIR.mkdir(parents=True, exist_ok=True)` (`catfinder.py:691`).
- Generated: yes.
- Committed: no — `.gitignore` line `reports/*.html` excludes the report itself; the directory persists via `.gitkeep`.

**`docs/`:**
- Purpose: GitHub Pages publishing root.
- Generated: yes, but only by CI (`.github/workflows/catfinder.yml` step "Report für GitHub Pages vorbereiten").
- Committed: yes — committed back to `main` by the workflow's `git add state/seen_cats.json docs/index.html` step.
- Caveat: do not hand-edit; the next CI run will overwrite it.

**`.venv/`:**
- Purpose: developer-local Python environment.
- Generated: yes.
- Committed: no.

**`.planning/`:**
- Purpose: GSD planning artifacts (codebase maps, phase plans).
- Generated: yes.
- Committed: project decision; nothing currently in `.gitignore` excludes it.

---

*Structure analysis: 2026-05-05*
