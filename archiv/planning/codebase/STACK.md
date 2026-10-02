# Technology Stack

**Analysis Date:** 2026-05-05

## Languages

**Primary:**
- Python 3.9+ (local dev), Python 3.12 (CI) — entire codebase. Single-file application in `catfinder.py` using `from __future__ import annotations` for PEP 604 union syntax (`int | None`) on older Python versions.

**Secondary:**
- HTML/CSS/JavaScript — embedded as f-string templates inside `catfinder.py` (see `HTML_TEMPLATE` at `catfinder.py:498` and `_build_filter_bar` at `catfinder.py:297`). Generated client-side filter UI (range sliders + toggle buttons) for the report.
- YAML — single GitHub Actions workflow at `.github/workflows/catfinder.yml`.
- JSON — state persistence format (`state/seen_cats.json`).
- Bash — inline `python3 - <<'EOF'` heredoc inside the workflow (`.github/workflows/catfinder.yml:36`) for post-processing the HTML report.

## Runtime

**Environment:**
- Local: Python 3.9.6 in `.venv/` (per `.venv/pyvenv.cfg`, sourced from Xcode developer toolchain).
- CI: Python 3.12 (per `actions/setup-python@v6` step in the workflow).
- No async runtime — uses `concurrent.futures.ThreadPoolExecutor` (`catfinder.py:472`) with `MAX_EVAL_WORKERS = 2` for parallel Claude API calls.

**Package Manager:**
- `pip` (no Poetry/uv/Pipenv detected).
- No lockfile — only `requirements.txt` with `>=` version pins. The CI step `pip install -r requirements.txt` resolves transitive dependencies fresh on each run.
- CI caches the pip download cache via `cache: pip` on `actions/setup-python@v6`.

## Frameworks

**Core:**
- No web/application framework. The script is a pure CLI tool entered via `if __name__ == "__main__": sys.exit(main())` at `catfinder.py:862`.
- `argparse` (stdlib) — CLI flag handling (`--reset`, `--all`, `--no-browser`) at `catfinder.py:710`.

**Testing:**
- None detected. No `tests/` directory, no `pytest`, `unittest`, or `tox` configuration. Verification is done by running `python catfinder.py` manually or via the CI cron schedule.

**Build/Dev:**
- No build step (pure Python source, no compilation).
- No formatter/linter config (`black`, `ruff`, `flake8`, `pylint`, `mypy` all absent).
- No `pyproject.toml`, `setup.py`, or `setup.cfg` — project is not installable as a package.

## Key Dependencies

**Critical (from `requirements.txt`):**
- `anthropic>=0.40.0` — Claude SDK. Imported lazily with a friendly fallback at `catfinder.py:29-35`. Used to call `claude-haiku-4-5` via `client.messages.parse(...)` with structured Pydantic output (`catfinder.py:437-449`).
- `beautifulsoup4>=4.12.0` — HTML parsing for the listing page and individual cat profiles (`catfinder.py:163`, `catfinder.py:399`). Uses the stdlib `html.parser` backend (no `lxml`).
- `pydantic>=2.0` — defines the `CatRating` model (`catfinder.py:94-107`) used as the Anthropic SDK's `output_format` to enforce a typed response with `rating` (Literal of 4 values) and `reason` fields.
- `requests>=2.31.0` — HTTP client for scraping (`catfinder.py:155`). Sets a custom `User-Agent` header (`Catfinder/1.0 (privater Gebrauch; Katzensuche)`) and a 30 s timeout.

**Stdlib (notable usage):**
- `dataclasses` — `Cat` dataclass at `catfinder.py:80-91`.
- `concurrent.futures` — thread pool for parallel Claude calls.
- `tempfile` + `os.replace` — atomic state-file write pattern at `catfinder.py:139-147`.
- `webbrowser` — auto-opens the generated report locally (`catfinder.py:695`).
- `html` — output escaping via `html.escape(...)` throughout the report rendering (`catfinder.py:567+`).
- `re` — regex constants for cat IDs, "Interessenten" markers, and birth-date extraction (`catfinder.py:58-63`).

**Infrastructure:**
- `dawidd6/action-send-mail@v16` (GitHub Action) — sends the generated report by e-mail through SendGrid SMTP after each scheduled run (`.github/workflows/catfinder.yml:60-70`).

## Configuration

**Environment Variables:**
- `ANTHROPIC_API_KEY` — required. Checked at `catfinder.py:716`; the script exits with a friendly error if unset. In CI it comes from `secrets.ANTHROPIC_API_KEY`.
- `GITHUB_OUTPUT` — optional. When present (CI only), `_write_github_output` (`catfinder.py:702`) appends `new_count=<n>` so subsequent workflow steps can read `steps.catfinder.outputs.new_count`.
- `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM` — workflow-only secrets used by the e-mail step.

**Build Config:**
- None. No `tsconfig`, `webpack`, `vite`, etc. The Python source is run directly.

**Constants (in-code config) at `catfinder.py:42-56`:**
- `BASE = "https://tierschutzverein-muenchen.de"` — scrape target.
- `MODEL = "claude-haiku-4-5"` — Anthropic model ID.
- `MAX_EVAL_WORKERS = 2` — thread-pool size for Claude calls.
- `API_RETRY_DELAYS = [10, 30, 60]` — back-off (seconds) on HTTP 429.
- `PROFILE_FETCH_DELAY_S = 0.4` — politeness delay between profile scrapes.

**.env handling:**
- `.env` listed in `.gitignore` but no `python-dotenv` dependency. The script reads env vars directly via `os.environ` — secrets must be exported in the shell (`~/.zshrc`) or injected by GitHub Actions.

## Platform Requirements

**Development:**
- macOS / Linux. `python3 -m venv .venv` workflow documented in `README.md:7-12`.
- A working web browser for the auto-opened HTML report (skippable with `--no-browser`).
- Outbound HTTPS to `tierschutzverein-muenchen.de` and `api.anthropic.com`.

**Production / CI:**
- `ubuntu-latest` GitHub-hosted runner.
- Scheduled twice daily via cron (`0 7 * * *` and `0 14 * * *` UTC) plus on-demand `workflow_dispatch`.
- Requires `contents: write` permission so the workflow can commit `state/seen_cats.json` and `docs/index.html` back to `main`.
- GitHub Pages serves `docs/index.html` as the public report (linked from the e-mail banner injected at `.github/workflows/catfinder.yml:40-46`).

## Build & Test Scripts

**Run locally (from `README.md`):**
```bash
python catfinder.py            # Diff-Modus: nur neue Katzen seit letztem Lauf
python catfinder.py --all      # Alle aktuell gelisteten Katzen bewerten
python catfinder.py --reset    # State löschen → alles als "neu" behandeln
python catfinder.py --no-browser   # Report nicht im Browser öffnen (CI)
```

**No test command exists.** Adding tests would require introducing a `tests/` directory plus `pytest` in `requirements.txt`.

---

*Stack analysis: 2026-05-05*
