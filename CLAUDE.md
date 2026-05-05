<!-- GSD:project-start source:PROJECT.md -->
## Project

**Catfinder**

Catfinder ist eine private CLI-Pipeline, die zweimal täglich das Listing des Tierschutzvereins München scrapt, neue Katzen mit Claude gegen ein Familien-Eignungsprofil bewertet und einen filterbaren HTML-Report per E-Mail (SendGrid) und GitHub Pages ausliefert. Zielnutzer ist eine einzelne Familie auf Katzensuche, die nicht ständig manuell nachschauen möchte.

**Core Value:** Sobald eine geeignete Katze neu auf der Seite auftaucht, weiß die Familie es ohne manuelles Nachsehen — der Report muss zuverlässig laufen und den Unterschied zwischen "neu", "weiter verfügbar" und "verschwunden" sauber kommunizieren.

### Constraints

- **Tech stack**: Bleibt bei Python 3.9+ Single-File, `requests` + `bs4` + `anthropic` + `pydantic`. Keine neuen Runtime-Dependencies für diesen Milestone.
- **Filter-UI**: Muss in der bestehenden `_build_filter_bar`-Logik (inline CSS/JS in Python f-string) bleiben — kein React/Vue/Build-Step.
- **State-Format**: JSON in `state/seen_cats.json`. Änderungen am Format dürfen vorhandene gültige Einträge nicht zerstören (lediglich verschwundene Einträge dürfen wegfallen).
- **CI-Verhalten**: Nach dem Milestone muss der Bot-Commit (`chore: state & report aktualisiert`) weiterhin gleich aussehen (gleiche Pfade, gleiche Permissions); E-Mail-Subject und Pages-URL bleiben unverändert.
- **Performance**: Nicht relevant — Listing < 100 Katzen, Reportrender < 1 s, kein Skalierungsdruck.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.9+ (local dev), Python 3.12 (CI) — entire codebase. Single-file application in `catfinder.py` using `from __future__ import annotations` for PEP 604 union syntax (`int | None`) on older Python versions.
- HTML/CSS/JavaScript — embedded as f-string templates inside `catfinder.py` (see `HTML_TEMPLATE` at `catfinder.py:498` and `_build_filter_bar` at `catfinder.py:297`). Generated client-side filter UI (range sliders + toggle buttons) for the report.
- YAML — single GitHub Actions workflow at `.github/workflows/catfinder.yml`.
- JSON — state persistence format (`state/seen_cats.json`).
- Bash — inline `python3 - <<'EOF'` heredoc inside the workflow (`.github/workflows/catfinder.yml:36`) for post-processing the HTML report.
## Runtime
- Local: Python 3.9.6 in `.venv/` (per `.venv/pyvenv.cfg`, sourced from Xcode developer toolchain).
- CI: Python 3.12 (per `actions/setup-python@v6` step in the workflow).
- No async runtime — uses `concurrent.futures.ThreadPoolExecutor` (`catfinder.py:472`) with `MAX_EVAL_WORKERS = 2` for parallel Claude API calls.
- `pip` (no Poetry/uv/Pipenv detected).
- No lockfile — only `requirements.txt` with `>=` version pins. The CI step `pip install -r requirements.txt` resolves transitive dependencies fresh on each run.
- CI caches the pip download cache via `cache: pip` on `actions/setup-python@v6`.
## Frameworks
- No web/application framework. The script is a pure CLI tool entered via `if __name__ == "__main__": sys.exit(main())` at `catfinder.py:862`.
- `argparse` (stdlib) — CLI flag handling (`--reset`, `--all`, `--no-browser`) at `catfinder.py:710`.
- None detected. No `tests/` directory, no `pytest`, `unittest`, or `tox` configuration. Verification is done by running `python catfinder.py` manually or via the CI cron schedule.
- No build step (pure Python source, no compilation).
- No formatter/linter config (`black`, `ruff`, `flake8`, `pylint`, `mypy` all absent).
- No `pyproject.toml`, `setup.py`, or `setup.cfg` — project is not installable as a package.
## Key Dependencies
- `anthropic>=0.40.0` — Claude SDK. Imported lazily with a friendly fallback at `catfinder.py:29-35`. Used to call `claude-haiku-4-5` via `client.messages.parse(...)` with structured Pydantic output (`catfinder.py:437-449`).
- `beautifulsoup4>=4.12.0` — HTML parsing for the listing page and individual cat profiles (`catfinder.py:163`, `catfinder.py:399`). Uses the stdlib `html.parser` backend (no `lxml`).
- `pydantic>=2.0` — defines the `CatRating` model (`catfinder.py:94-107`) used as the Anthropic SDK's `output_format` to enforce a typed response with `rating` (Literal of 4 values) and `reason` fields.
- `requests>=2.31.0` — HTTP client for scraping (`catfinder.py:155`). Sets a custom `User-Agent` header (`Catfinder/1.0 (privater Gebrauch; Katzensuche)`) and a 30 s timeout.
- `dataclasses` — `Cat` dataclass at `catfinder.py:80-91`.
- `concurrent.futures` — thread pool for parallel Claude calls.
- `tempfile` + `os.replace` — atomic state-file write pattern at `catfinder.py:139-147`.
- `webbrowser` — auto-opens the generated report locally (`catfinder.py:695`).
- `html` — output escaping via `html.escape(...)` throughout the report rendering (`catfinder.py:567+`).
- `re` — regex constants for cat IDs, "Interessenten" markers, and birth-date extraction (`catfinder.py:58-63`).
- `dawidd6/action-send-mail@v16` (GitHub Action) — sends the generated report by e-mail through SendGrid SMTP after each scheduled run (`.github/workflows/catfinder.yml:60-70`).
## Configuration
- `ANTHROPIC_API_KEY` — required. Checked at `catfinder.py:716`; the script exits with a friendly error if unset. In CI it comes from `secrets.ANTHROPIC_API_KEY`.
- `GITHUB_OUTPUT` — optional. When present (CI only), `_write_github_output` (`catfinder.py:702`) appends `new_count=<n>` so subsequent workflow steps can read `steps.catfinder.outputs.new_count`.
- `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM` — workflow-only secrets used by the e-mail step.
- None. No `tsconfig`, `webpack`, `vite`, etc. The Python source is run directly.
- `BASE = "https://tierschutzverein-muenchen.de"` — scrape target.
- `MODEL = "claude-haiku-4-5"` — Anthropic model ID.
- `MAX_EVAL_WORKERS = 2` — thread-pool size for Claude calls.
- `API_RETRY_DELAYS = [10, 30, 60]` — back-off (seconds) on HTTP 429.
- `PROFILE_FETCH_DELAY_S = 0.4` — politeness delay between profile scrapes.
- `.env` listed in `.gitignore` but no `python-dotenv` dependency. The script reads env vars directly via `os.environ` — secrets must be exported in the shell (`~/.zshrc`) or injected by GitHub Actions.
## Platform Requirements
- macOS / Linux. `python3 -m venv .venv` workflow documented in `README.md:7-12`.
- A working web browser for the auto-opened HTML report (skippable with `--no-browser`).
- Outbound HTTPS to `tierschutzverein-muenchen.de` and `api.anthropic.com`.
- `ubuntu-latest` GitHub-hosted runner.
- Scheduled twice daily via cron (`0 7 * * *` and `0 14 * * *` UTC) plus on-demand `workflow_dispatch`.
- Requires `contents: write` permission so the workflow can commit `state/seen_cats.json` and `docs/index.html` back to `main`.
- GitHub Pages serves `docs/index.html` as the public report (linked from the e-mail banner injected at `.github/workflows/catfinder.yml:40-46`).
## Build & Test Scripts
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Single top-level script `catfinder.py` (lowercase, no underscores). State and reports live in dedicated directories (`state/seen_cats.json`, `reports/report.html`).
- No package layout (no `__init__.py`, no `src/`).
- `snake_case` for all functions: `scrape_listing`, `fetch_profile_text`, `evaluate_cat`, `evaluate_all`, `render_report`, `write_and_open_report` (e.g. `catfinder.py:160`, `catfinder.py:396`, `catfinder.py:421`, `catfinder.py:548`, `catfinder.py:690`).
- Private/internal helpers are prefixed with a single underscore: `_http_get` (`catfinder.py:154`), `_pick` (`catfinder.py:222`), `_build_filter_bar` (`catfinder.py:297`), `_card_sort_key` (`catfinder.py:484`), `_write_github_output` (`catfinder.py:702`), and the closure helpers `_img`, `_meta_line`, `_interested_badge`, `_pair_attr`, `_partner_line`, `_age_months_with_fallback`, `_ratings_from_state` (`catfinder.py:565-587`, `catfinder.py:745-781`).
- Local variables are `snake_case`: `profile_url`, `card_text`, `age_min`, `age_max`, `last_exc` (e.g. `catfinder.py:175`, `catfinder.py:198`, `catfinder.py:597`, `catfinder.py:431`).
- Loop variables stay short (`a`, `c`, `m`, `r`, `idx`) when their meaning is local and obvious — e.g. `for a in soup.find_all(...)` (`catfinder.py:167`), `for c in cats` (`catfinder.py:741`), `m = CAT_ID_PATTERN.search(...)` (`catfinder.py:168`).
- `UPPER_SNAKE_CASE` at module level: `BASE`, `LISTING_URL`, `PROFILE_URL_TMPL`, `USER_AGENT`, `MODEL`, `MAX_EVAL_WORKERS`, `API_RETRY_DELAYS`, `PROFILE_FETCH_DELAY_S`, `DEFAULT_AGE_LO`, `DEFAULT_AGE_HI` (`catfinder.py:42-56`, `catfinder.py:293-294`).
- Compiled regex constants share the same convention with a `_PATTERN` suffix: `CAT_ID_PATTERN`, `INTERESTED_PATTERN`, `BIRTH_DATE_PATTERN` (`catfinder.py:58-63`).
- Path constants computed from `__file__`: `ROOT`, `STATE_DIR`, `STATE_FILE`, `REPORT_DIR`, `REPORT_FILE` (`catfinder.py:47-51`).
- Classes use `PascalCase`: `Cat` (dataclass at `catfinder.py:81`), `CatRating` (Pydantic model at `catfinder.py:94`).
- Type aliases use `PascalCase`: `Rating = Literal[...]` (`catfinder.py:66`).
- Dict-of-dict literal metadata uses lowercase string keys (`"geeignet"`, `"unbekannt"`, `"aeltere_kinder"`, `"nicht_geeignet"` — `catfinder.py:69-72`). The same enum-like keys are reused as the `CatRating.rating` literal values.
## Code Style
- No formatter is configured. Code is hand-formatted but consistent.
- 4-space indentation, no tabs.
- Lines run up to ~120 characters; wide lines appear in the metadata table (`catfinder.py:69-72`), the HTML/CSS literals (`catfinder.py:498-545`), and the embedded JS in `_build_filter_bar` (`catfinder.py:340-393`). Pure Python statements typically stay under ~100 chars.
- Section banners separate logical regions of the file:
- Strings: double quotes are the default (`"https://..."`, `"utf-8"`). Single quotes appear inside f-strings for HTML attribute values (`'<div class="card" ...>'`) and in the CSS/JS literals to avoid escaping.
- Trailing commas are used in multi-line collection literals (`catfinder.py:55`, `:69-73`).
- No linter is configured. There is no `ruff`, `flake8`, `pylint`, or `mypy` config. Treat the existing patterns in `catfinder.py` as the lint target.
## Import Organization
- None. The project is a single module, so absolute or relative package imports are not used.
## Error Handling
- **Expected I/O errors → log + sane default:** state loading catches `(json.JSONDecodeError, OSError)`, prints a warning, and starts fresh:
- **Atomic file writes:** `save_state` writes to a `tempfile.mkstemp` path then `os.replace`s it onto `STATE_FILE`. The `try/except` cleans up the temp file on failure and re-raises (`catfinder.py:136-147`).
- **HTTP retries with backoff:** API rate-limits trigger a retry loop driven by `API_RETRY_DELAYS = [10, 30, 60]`:
- **Per-item failure isolation:** in `evaluate_all`, the worker function catches all exceptions, logs them with the cat name and id, and returns a `CatRating(rating="unbekannt", reason=f"Bewertungsfehler: {e}")` so one failed call does not abort the batch (`catfinder.py:464-470`). Apply this pattern when adding new per-item batch operations.
- **Best-effort profile fetches:** the main loop catches everything around `fetch_profile_text` and stores an empty string for that cat id (`catfinder.py:798-802`).
- **Hard failures with user guidance:** `sys.exit` / `return 1` are used when the run cannot continue, accompanied by a multi-line German message that tells the user how to fix it (`catfinder.py:32-35`, `catfinder.py:716-722`).
- **Defensive scraping invariants:** if the listing page yields zero cats, the scraper raises `RuntimeError` with the URL and a hint that the page structure may have changed (`catfinder.py:213-217`). Use `RuntimeError` for this kind of "the world looks wrong" condition.
- **Avoid in new code:** there are bare `except Exception as e:` blocks in three places (`catfinder.py:451`, `:468`, `:800`). They are intentional (best-effort batch isolation), but for new code prefer the narrowest exception type that fits.
## Logging
- Top-level progress messages have no prefix:
- Nested / sub-step messages are indented with two spaces; per-item failures use four spaces and a leading `!`:
- Warnings are prefixed with `Warnung:` (`catfinder.py:132`); fatal user-facing errors with `Fehler:` (`catfinder.py:33`, `catfinder.py:717`).
- All user-facing output is **German**. Keep new log/error/UI strings in German to match the report and the workflow naming.
- Progress counters use the `[done/total]` format (`catfinder.py:479`, `catfinder.py:797`).
## Type Hints
- All public functions have full parameter and return annotations: `def scrape_listing() -> list[Cat]:` (`catfinder.py:160`), `def evaluate_cat(client: Anthropic, cat: Cat, profile_text: str) -> CatRating:` (`catfinder.py:421`), `def render_report(...) -> str:` (`catfinder.py:548-555`).
- Built-in generics are preferred over `typing` equivalents: `list[Cat]`, `dict[str, dict]`, `dict[str, CatRating]`, `set[str]`, `tuple[str, CatRating]` (`catfinder.py:126`, `:166`, `:238`, `:459`, `:464`).
- `Literal` from `typing` is used for closed enums:
- Optional values use `X | None` (e.g. `int | None`, `Exception | None`, `dict[str, int | None] | None`) rather than `Optional[X]` (`catfinder.py:273`, `:431`, `:552`).
- Closures and small inner functions are also annotated where the result feeds into typed code paths (`def work(c: Cat) -> tuple[str, CatRating]:` at `catfinder.py:464`).
- Dataclass fields use simple inline annotations with default values for optional attributes (`catfinder.py:81-91`):
- Pydantic models use `Field(description=...)` so the description is fed back to Claude as part of the structured-output schema (`catfinder.py:97-107`). Keep descriptions in German to match `SYSTEM_PROMPT`.
## Docstrings
- Module docstring is present at `catfinder.py:1-6` and explains *what* the script does in German.
- Function docstrings are short — one line, German, describing intent rather than mechanics. Examples:
- Multi-line docstrings appear when behaviour needs more nuance — e.g. `find_companion_names` (`catfinder.py:238-243`), `extract_age_hint` (`catfinder.py:254`), `_build_filter_bar` (`catfinder.py:298`), `_card_sort_key` (`catfinder.py:485`).
- Pydantic field docstrings live in `Field(description=...)` and double as the LLM schema description (`catfinder.py:97-107`).
- No Sphinx / Google / Numpy section formatting is used. Stay consistent with this lightweight, German, intent-first style.
## Comments
- Inline comments explain *why*, not *what* — German one-liners above the relevant block:
- Section banners (see "Formatting" above) divide the file into ~7 logical sections.
- Inline trailing comments document numeric magic constants:
## Function Design
- `_build_filter_bar` (`catfinder.py:297-393`, ~95 lines) — embeds CSS+JS as a heredoc-style f-string.
- `render_report` (`catfinder.py:548-687`, ~140 lines) — composes the full HTML report with several local helpers.
- `main` (`catfinder.py:709-859`, ~150 lines) — orchestration; uses local closures (`_ratings_from_state`, `_age_months_with_fallback`) to keep helpers near their data.
- Positional for required arguments, keyword arguments with defaults for optional flags. Booleans are explicit named flags (`no_browser: bool = False` at `catfinder.py:690`).
- Optional collection inputs default to `None` and are normalised at the top of the function:
- Functions return concrete typed values; no tuples-as-poor-mans-record. Where a structured value is needed, a `@dataclass` (`Cat`) or a `BaseModel` (`CatRating`) is used.
- Functions that mutate state are explicit about it (e.g. `save_state`, `_write_github_output` return `None`).
- Helpers that produce HTML return strings; no DOM/builder pattern.
## Module Design
- The repository is a single executable script. There is no public API surface, no `__all__`, and no `__init__.py`.
- The entrypoint is gated by:
- Small additions: a new function in the matching `# ---` section of `catfinder.py`. Use the existing section banners (Konfiguration, Datenmodelle, State, Scraper, Claude-Bewertung, HTML-Report, Main).
- New data shapes: extend the `Cat` dataclass (`catfinder.py:80-91`) or add a new `BaseModel` near `CatRating` (`catfinder.py:94-107`). Keep state-serialisable fields as plain types so `dataclasses.asdict` and `json.dumps` keep working (`catfinder.py:846`, `:138`).
- New CLI flags: extend `argparse` in `main()` near `catfinder.py:710-714`.
- If the file grows past ~1500 lines, split out the HTML/JS rendering (`_build_filter_bar`, `HTML_TEMPLATE`, `render_report`) into a sibling `report.py` first — that section is the most self-contained.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
```
## Component Responsibilities
| Component | Responsibility | File |
|-----------|----------------|------|
| CLI / orchestrator | Parse args, gate on `ANTHROPIC_API_KEY`, drive whole pipeline | `catfinder.py` (`main`, lines 709-859) |
| Configuration | URLs, paths, model, retry/delay constants, rating metadata | `catfinder.py` (lines 42-73) |
| Data models | `Cat` dataclass, `CatRating` Pydantic model, `SYSTEM_PROMPT` | `catfinder.py` (lines 80-119) |
| State store | Read/atomically write `seen_cats.json` | `catfinder.py` (`load_state`, `save_state`, lines 126-147) |
| Listing scraper | Fetch + parse cat cards from listing page | `catfinder.py` (`scrape_listing`, `_pick`, lines 160-230) |
| Profile scraper | Fetch + clean individual cat profile text | `catfinder.py` (`fetch_profile_text`, lines 396-414) |
| Text extractors | Detect interested, partner names, age from profile text | `catfinder.py` (lines 233-290) |
| Claude evaluator | Call Anthropic API with retries, parallelize via thread pool | `catfinder.py` (`evaluate_cat`, `evaluate_all`, lines 421-481) |
| Report renderer | Build HTML with filter bar, sections, sort key | `catfinder.py` (`render_report`, `_build_filter_bar`, lines 297-695) |
| CI bridge | Emit `new_count` to `GITHUB_OUTPUT` | `catfinder.py` (`_write_github_output`, lines 702-706) |
| Scheduler / publisher | Run twice daily, commit state, publish to Pages, send mail | `.github/workflows/catfinder.yml` |
## Pattern Overview
- One Python module, no packages. All public functions live in `catfinder.py` and are organized by section comments.
- Pure functions for scraping / parsing; side-effecting functions (state I/O, HTTP, browser launch) are explicit and named.
- Stateless run model: each invocation rebuilds everything in memory; `state/seen_cats.json` is the only durable artifact between runs.
- "Diff-driven" evaluation: only previously unseen `cat_id`s are sent to Claude; cached ratings come straight out of state.
- Cost optimization via Anthropic prompt caching (`cache_control: ephemeral` on system prompt) plus a small `MAX_EVAL_WORKERS=2` thread pool.
## Layers
- Purpose: argument parsing, environment validation, top-level orchestration.
- Location: `catfinder.py` `main()` (lines 709-859).
- Contains: `argparse`, env-var check, branch logic for `--reset` / `--all` / cold-start, calls into all other layers in sequence.
- Depends on: every other layer in the file.
- Used by: `if __name__ == "__main__": sys.exit(main())` (line 862-863) and `.github/workflows/catfinder.yml` step "Catfinder ausführen".
- Purpose: define the shape of a cat, of a rating, and the rating taxonomy.
- Location: `catfinder.py` lines 42-119.
- Contains: `Cat` (dataclass), `CatRating` (Pydantic `BaseModel`), `Rating` Literal, `RATING_META`, `SYSTEM_PROMPT`.
- Depends on: stdlib + Pydantic only.
- Used by: scraper, evaluator, reporter, state.
- Purpose: fetch HTML and extract structured fields.
- Location: `catfinder.py` lines 154-414.
- Contains: `_http_get`, `scrape_listing`, `_pick`, `detect_interested`, `find_companion_names`, `extract_age_hint`, `age_hint_to_months`, `fetch_profile_text`.
- Depends on: `requests`, `bs4.BeautifulSoup`, regex constants (`CAT_ID_PATTERN`, `INTERESTED_PATTERN`, `BIRTH_DATE_PATTERN`).
- Used by: `main()` and `evaluate_all` (indirectly, via `profile_texts`).
- Purpose: call Claude on each new cat, parse a structured `CatRating`.
- Location: `catfinder.py` lines 421-481.
- Contains: `evaluate_cat` (single call with retry on 429), `evaluate_all` (thread-pool fan-out).
- Depends on: `anthropic.Anthropic`, `concurrent.futures`, `MODEL`, `API_RETRY_DELAYS`, `MAX_EVAL_WORKERS`, `SYSTEM_PROMPT`.
- Used by: `main()`.
- Purpose: load/save the JSON state with crash-safe atomic writes.
- Location: `catfinder.py` lines 126-147.
- Contains: `load_state`, `save_state` (writes to `tempfile.mkstemp`, then `os.replace`).
- Depends on: stdlib only.
- Used by: `main()` (before scraping and after evaluation).
- Purpose: turn `(Cat, CatRating)` pairs into the standalone HTML report.
- Location: `catfinder.py` lines 297-695.
- Contains: `_build_filter_bar`, `_card_sort_key`, `HTML_TEMPLATE`, `render_report`, `write_and_open_report`.
- Depends on: `html.escape`, `datetime`, `webbrowser`.
- Used by: `main()`.
## Data Flow
### Primary Request Path (interactive run, default mode)
### Cold-start / `--all` Flow
- If state is empty or `--all` is passed, `to_evaluate = cats` (the whole listing) and `still_known = []`. `scope_note` is set to `" · Erstlauf"` or `" · alle bewertet"` and shown in the report header (`catfinder.py:736-739`).
### "No new cats" Flow
- When `to_evaluate` is empty, the pipeline skips Claude entirely, renders a report consisting only of "Weiterhin verfügbar" + "Nicht mehr verfügbar" sections, writes `reports/report.html`, and emits `new_count=0` to `$GITHUB_OUTPUT` (`catfinder.py:783-792`).
### CI / Scheduled Flow (`.github/workflows/catfinder.yml`)
- Single source of truth: `state/seen_cats.json` (entries keyed by `cat_id`). Each entry stores listing metadata, `first_seen`, plus `rating`, `reason`, `has_interested`, `companion_count`, `partner_name`.
- Atomic writes via `tempfile.mkstemp` + `os.replace` so a crash never leaves a half-written JSON (`catfinder.py:136-147`).
- The state is committed back to the repo by CI; locally it's untracked diff (the file is not in `.gitignore` — only `reports/*.html` is).
## Key Abstractions
- Purpose: in-memory representation of a single cat, both for currently-listed cats and rehydrated-from-state ones.
- Examples: `catfinder.py:80-91`.
- Pattern: plain `@dataclass`, mutated in-place after profile enrichment; serialized to state via `dataclasses.asdict`.
- Purpose: structured Claude output (`rating` + `reason`); used both as the Anthropic SDK `output_format` and as an in-memory carrier for cached ratings rebuilt from state.
- Examples: `catfinder.py:94-107`.
- Pattern: Pydantic v2 `BaseModel` with a `Literal` rating and a free-text reason, validated on parse.
- Purpose: single dictionary mapping rating → emoji, label, color, sort order. Used for both the report rendering (CSS accent + label) and for `_card_sort_key`.
- Examples: `catfinder.py:68-73`.
- Pattern: lookup table; the `order` field is a string used as the primary sort key, ensuring `"geeignet" < "unbekannt" < "aeltere_kinder" < "nicht_geeignet"` lexicographically by `"0".."3"`.
- Purpose: deterministic ordering — by rating, then pairs (`companion_count == 2`) before singles, then partners adjacent.
- Examples: `catfinder.py:484-491`.
- Pattern: function returning a tuple consumed by `sorted(..., key=...)`.
## Entry Points
- Location: `catfinder.py` (`if __name__ == "__main__": sys.exit(main())` at line 862).
- Triggers: developer running `python catfinder.py [--reset|--all|--no-browser]`, or CI step "Catfinder ausführen".
- Responsibilities: drives the full pipeline; non-zero exit on missing API key.
- Location: `.github/workflows/catfinder.yml`.
- Triggers: `schedule` (cron `0 7 * * *`, `0 14 * * *`) and `workflow_dispatch` (manual).
- Responsibilities: run script with `--no-browser`, publish to Pages via `docs/index.html`, push state, email the report through SendGrid.
## Architectural Constraints
- **Threading:** Single-process Python. The only concurrency is `concurrent.futures.ThreadPoolExecutor(max_workers=MAX_EVAL_WORKERS)` (=2) inside `evaluate_all` (`catfinder.py:472-481`). Listing scrape and profile fetches are sequential; profile fetches sleep `PROFILE_FETCH_DELAY_S = 0.4` s between requests to be polite.
- **Global state:** Module-level constants (`BASE`, `STATE_FILE`, `REPORT_FILE`, `MODEL`, `API_RETRY_DELAYS`, `RATING_META`, regex patterns) are immutable singletons. The runtime `state` dict is local to `main()` only; no module-level mutable state.
- **Filesystem layout is path-anchored:** `ROOT = Path(__file__).resolve().parent` (`catfinder.py:47`). All artifact paths derive from this, so the script must live alongside `state/` and `reports/` directories.
- **Network dependencies:** every run does live HTTP to `tierschutzverein-muenchen.de` and `api.anthropic.com`. There is no offline mode and no fixture-replay testing scaffold.
- **No tests, no lint config:** there is no `tests/`, `pyproject.toml`, `pytest`, `ruff`, or `mypy` configuration in the repo.
- **External secret dependence:** `ANTHROPIC_API_KEY` is required (script aborts otherwise, `catfinder.py:716`). CI additionally needs `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM`.
## Anti-Patterns
### Monolithic single file
### Inline HTML/CSS/JS as Python f-strings
### Best-effort scraping with substring `_pick`
### Mixing rendering and business logic
## Error Handling
- Hard exit on missing API key with a remediation hint (`catfinder.py:716-722`).
- `RuntimeError` with diagnostic message if the listing has zero cats (`catfinder.py:213-217`) — protects against silent breakage when the source site changes.
- `evaluate_cat` retries 429 / "rate_limit" exceptions on the schedule `[10, 30, 60]` seconds, then re-raises a `RuntimeError` (`catfinder.py:431-456`); other exceptions surface immediately.
- `evaluate_all` catches per-cat exceptions inside its worker and converts them to a `CatRating(rating="unbekannt", reason=f"Bewertungsfehler: {e}")` so one bad cat never sinks the whole run (`catfinder.py:464-470`).
- `load_state` recovers from corrupt JSON / OS errors with a warning print and an empty dict (`catfinder.py:129-133`).
- `save_state` cleans up the temp file on exception before re-raising (`catfinder.py:140-147`).
- Profile fetch errors are caught in `main()` and become an empty `profile_text`, which `evaluate_cat` translates into `unbekannt` (`catfinder.py:798-802`, `421-423`).
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
