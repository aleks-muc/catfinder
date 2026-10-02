<!-- refreshed: 2026-05-05 -->
# Architecture

**Analysis Date:** 2026-05-05

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Entry Point / CLI Layer                   │
│              `catfinder.py` (`main()`, `if __name__`)        │
│      flags: --reset · --all · --no-browser                   │
└────────┬─────────┬────────────────┬────────────┬────────────┘
         │         │                │            │
         ▼         ▼                ▼            ▼
┌─────────────┐ ┌─────────┐ ┌──────────────┐ ┌─────────────┐
│  Scraper    │ │  State  │ │  Evaluator   │ │  Reporter   │
│ (HTTP+BS4)  │ │  (JSON) │ │ (Claude API) │ │   (HTML)    │
│             │ │         │ │              │ │             │
│scrape_listing│ │load_state│ │evaluate_all │ │render_report│
│fetch_profile_│ │save_state│ │evaluate_cat │ │write_and_   │
│text          │ │         │ │              │ │open_report  │
└──────┬──────┘ └────┬────┘ └──────┬───────┘ └──────┬──────┘
       │             │             │                │
       ▼             ▼             ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│  External Targets / Generated Artifacts                      │
│   tierschutzverein-muenchen.de  ·  Anthropic API             │
│   `state/seen_cats.json`  ·  `reports/report.html`           │
│   `docs/index.html` (CI banner-injected copy)                │
└─────────────────────────────────────────────────────────────┘
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

**Overall:** Single-file procedural pipeline (extract → diff → enrich → classify → render → persist).

**Key Characteristics:**
- One Python module, no packages. All public functions live in `catfinder.py` and are organized by section comments.
- Pure functions for scraping / parsing; side-effecting functions (state I/O, HTTP, browser launch) are explicit and named.
- Stateless run model: each invocation rebuilds everything in memory; `state/seen_cats.json` is the only durable artifact between runs.
- "Diff-driven" evaluation: only previously unseen `cat_id`s are sent to Claude; cached ratings come straight out of state.
- Cost optimization via Anthropic prompt caching (`cache_control: ephemeral` on system prompt) plus a small `MAX_EVAL_WORKERS=2` thread pool.

## Layers

**CLI layer:**
- Purpose: argument parsing, environment validation, top-level orchestration.
- Location: `catfinder.py` `main()` (lines 709-859).
- Contains: `argparse`, env-var check, branch logic for `--reset` / `--all` / cold-start, calls into all other layers in sequence.
- Depends on: every other layer in the file.
- Used by: `if __name__ == "__main__": sys.exit(main())` (line 862-863) and `.github/workflows/catfinder.yml` step "Catfinder ausführen".

**Domain layer (data models + constants):**
- Purpose: define the shape of a cat, of a rating, and the rating taxonomy.
- Location: `catfinder.py` lines 42-119.
- Contains: `Cat` (dataclass), `CatRating` (Pydantic `BaseModel`), `Rating` Literal, `RATING_META`, `SYSTEM_PROMPT`.
- Depends on: stdlib + Pydantic only.
- Used by: scraper, evaluator, reporter, state.

**Scraping layer:**
- Purpose: fetch HTML and extract structured fields.
- Location: `catfinder.py` lines 154-414.
- Contains: `_http_get`, `scrape_listing`, `_pick`, `detect_interested`, `find_companion_names`, `extract_age_hint`, `age_hint_to_months`, `fetch_profile_text`.
- Depends on: `requests`, `bs4.BeautifulSoup`, regex constants (`CAT_ID_PATTERN`, `INTERESTED_PATTERN`, `BIRTH_DATE_PATTERN`).
- Used by: `main()` and `evaluate_all` (indirectly, via `profile_texts`).

**Evaluation layer:**
- Purpose: call Claude on each new cat, parse a structured `CatRating`.
- Location: `catfinder.py` lines 421-481.
- Contains: `evaluate_cat` (single call with retry on 429), `evaluate_all` (thread-pool fan-out).
- Depends on: `anthropic.Anthropic`, `concurrent.futures`, `MODEL`, `API_RETRY_DELAYS`, `MAX_EVAL_WORKERS`, `SYSTEM_PROMPT`.
- Used by: `main()`.

**Persistence layer:**
- Purpose: load/save the JSON state with crash-safe atomic writes.
- Location: `catfinder.py` lines 126-147.
- Contains: `load_state`, `save_state` (writes to `tempfile.mkstemp`, then `os.replace`).
- Depends on: stdlib only.
- Used by: `main()` (before scraping and after evaluation).

**Rendering layer:**
- Purpose: turn `(Cat, CatRating)` pairs into the standalone HTML report.
- Location: `catfinder.py` lines 297-695.
- Contains: `_build_filter_bar`, `_card_sort_key`, `HTML_TEMPLATE`, `render_report`, `write_and_open_report`.
- Depends on: `html.escape`, `datetime`, `webbrowser`.
- Used by: `main()`.

## Data Flow

### Primary Request Path (interactive run, default mode)

1. CLI start: `python catfinder.py` invokes `main()` (`catfinder.py:862`, dispatched via `sys.exit(main())`).
2. Arg parse + env guard: `argparse` reads flags; abort if `ANTHROPIC_API_KEY` is unset (`catfinder.py:716-722`).
3. Optional reset: if `--reset`, delete `state/seen_cats.json` (`catfinder.py:724-726`).
4. List scrape: `scrape_listing()` GETs `LISTING_URL` and produces `list[Cat]` (`catfinder.py:729`).
5. State load: `load_state()` reads `state/seen_cats.json` into `dict[cat_id, entry]` (`catfinder.py:733`).
6. Diff: split current listing into `to_evaluate` (new IDs) and `still_known` (already in state). Compute `no_longer_listed` from `known_ids - current_ids` (`catfinder.py:736-778`).
7. Profile fetch: for each cat in `to_evaluate`, `fetch_profile_text` pulls and trims the profile HTML (`catfinder.py:794-803`); sleep `PROFILE_FETCH_DELAY_S` (0.4 s) between calls.
8. Enrichment from profile text: `detect_interested`, `find_companion_names`, `extract_age_hint` populate `has_interested`, `companion_count`, `partner_name`, and a fallback `age_hint` (`catfinder.py:805-822`).
9. Age index built for filter slider via `age_hint_to_months` (`catfinder.py:824-829`).
10. Claude classification: `evaluate_all(to_evaluate, profile_texts)` runs up to `MAX_EVAL_WORKERS=2` parallel `messages.parse` calls; 429s retried per `API_RETRY_DELAYS = [10, 30, 60]` (`catfinder.py:831-832`).
11. Render: `render_report(...)` returns full HTML, including the new section, "weiterhin verfügbar" section (cached ratings from state), and "nicht mehr verfügbar" section (`catfinder.py:836-839`).
12. Write + open: `write_and_open_report()` writes `reports/report.html` and (unless `--no-browser`) opens it in `webbrowser` (`catfinder.py:840`).
13. Persist: merge new cats into `state`, attach `rating`, `reason`, `has_interested`, `companion_count`, `partner_name`, then `save_state(state)` atomically (`catfinder.py:842-856`).
14. CI handoff: `_write_github_output(len(evaluated))` appends `new_count=...` to `$GITHUB_OUTPUT` (`catfinder.py:858`).

### Cold-start / `--all` Flow

- If state is empty or `--all` is passed, `to_evaluate = cats` (the whole listing) and `still_known = []`. `scope_note` is set to `" · Erstlauf"` or `" · alle bewertet"` and shown in the report header (`catfinder.py:736-739`).

### "No new cats" Flow

- When `to_evaluate` is empty, the pipeline skips Claude entirely, renders a report consisting only of "Weiterhin verfügbar" + "Nicht mehr verfügbar" sections, writes `reports/report.html`, and emits `new_count=0` to `$GITHUB_OUTPUT` (`catfinder.py:783-792`).

### CI / Scheduled Flow (`.github/workflows/catfinder.yml`)

1. Cron triggers at 07:00 and 14:00 UTC (twice daily).
2. Checkout repo, set up Python 3.12, `pip install -r requirements.txt`.
3. Run `python catfinder.py --no-browser` with `ANTHROPIC_API_KEY` from secrets; capture `new_count` step output.
4. Inline Python heredoc reads `reports/report.html`, injects a "Im Browser öffnen" banner pointing at GitHub Pages, writes both `reports/report.html` and `docs/index.html`.
5. Bot commit: `git add state/seen_cats.json docs/index.html` and push (commit message `chore: state & report aktualisiert [skip ci]`).
6. SendGrid SMTP sends the HTML report by mail with subject `"Catfinder – <new_count> neue Katzen"`.

**State Management:**
- Single source of truth: `state/seen_cats.json` (entries keyed by `cat_id`). Each entry stores listing metadata, `first_seen`, plus `rating`, `reason`, `has_interested`, `companion_count`, `partner_name`.
- Atomic writes via `tempfile.mkstemp` + `os.replace` so a crash never leaves a half-written JSON (`catfinder.py:136-147`).
- The state is committed back to the repo by CI; locally it's untracked diff (the file is not in `.gitignore` — only `reports/*.html` is).

## Key Abstractions

**`Cat` dataclass:**
- Purpose: in-memory representation of a single cat, both for currently-listed cats and rehydrated-from-state ones.
- Examples: `catfinder.py:80-91`.
- Pattern: plain `@dataclass`, mutated in-place after profile enrichment; serialized to state via `dataclasses.asdict`.

**`CatRating` Pydantic model:**
- Purpose: structured Claude output (`rating` + `reason`); used both as the Anthropic SDK `output_format` and as an in-memory carrier for cached ratings rebuilt from state.
- Examples: `catfinder.py:94-107`.
- Pattern: Pydantic v2 `BaseModel` with a `Literal` rating and a free-text reason, validated on parse.

**`RATING_META`:**
- Purpose: single dictionary mapping rating → emoji, label, color, sort order. Used for both the report rendering (CSS accent + label) and for `_card_sort_key`.
- Examples: `catfinder.py:68-73`.
- Pattern: lookup table; the `order` field is a string used as the primary sort key, ensuring `"geeignet" < "unbekannt" < "aeltere_kinder" < "nicht_geeignet"` lexicographically by `"0".."3"`.

**Sort key `_card_sort_key`:**
- Purpose: deterministic ordering — by rating, then pairs (`companion_count == 2`) before singles, then partners adjacent.
- Examples: `catfinder.py:484-491`.
- Pattern: function returning a tuple consumed by `sorted(..., key=...)`.

## Entry Points

**CLI script:**
- Location: `catfinder.py` (`if __name__ == "__main__": sys.exit(main())` at line 862).
- Triggers: developer running `python catfinder.py [--reset|--all|--no-browser]`, or CI step "Catfinder ausführen".
- Responsibilities: drives the full pipeline; non-zero exit on missing API key.

**Scheduled job:**
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

**What happens:** All pipeline stages (config, models, scraping, state, Claude calls, HTML rendering with inline CSS+JS, CLI) live in one ~865-line `catfinder.py`.
**Why it's wrong:** Cross-cutting changes (e.g., touching the rating taxonomy) require editing the model, the rendering CSS, the sort key, and the system prompt simultaneously, all in one file. Hard to review and impossible to unit-test in isolation.
**Do this instead:** When growth continues, split into a package: `catfinder/scraper.py`, `catfinder/state.py`, `catfinder/evaluator.py`, `catfinder/report.py`, `catfinder/cli.py`. Re-export from `catfinder/__init__.py`. Keep the entry point thin.

### Inline HTML/CSS/JS as Python f-strings

**What happens:** `_build_filter_bar` (`catfinder.py:297-393`) and `HTML_TEMPLATE` (`catfinder.py:498-545`) embed full CSS and a JavaScript IIFE inside Python f-strings, with `{{` / `}}` escaping for braces.
**Why it's wrong:** Any change to the filter UI is a Python edit with no JS tooling, no syntax highlighting in editors that detect by file type, and a real risk of f-string brace escaping bugs.
**Do this instead:** Move the report shell to `templates/report.html` and the filter logic to `static/filter.js`; render with a small templating engine (Jinja2 is already a transitive dep through nothing here, but is one line in `requirements.txt`).

### Best-effort scraping with substring `_pick`

**What happens:** `_pick(haystack, needles)` (`catfinder.py:222-230`) returns a 50-char window around the first matching substring as the value of `breed`/`sex`/`age_hint`. The result is the surrounding text, not the field value.
**Why it's wrong:** Slight markup drift on the source site silently corrupts these fields with no error. The "value" is positional noise, not a parse.
**Do this instead:** Anchor the parse to specific DOM nodes (e.g., dt/dd pairs, label spans) and produce a typed extractor per field with explicit failure (return `None`, log).

### Mixing rendering and business logic

**What happens:** `render_report` does sorting, age-fallback computation, slider-bound calculation, and HTML emission — all in one ~140-line function (`catfinder.py:548-687`).
**Why it's wrong:** No way to test "did sort produce the right order?" without rendering HTML and string-matching. Hard to reuse the sort/age logic for, say, a JSON export.
**Do this instead:** Extract `prepare_report_model(...)` returning a typed view-model, and a `render_html(view_model)` that's pure formatting.

## Error Handling

**Strategy:** Fail loud at the boundaries (missing key, no cats found), be lenient at the edges (per-cat profile fetch / classification errors are caught, logged, and yield `unbekannt` ratings rather than aborting the run).

**Patterns:**
- Hard exit on missing API key with a remediation hint (`catfinder.py:716-722`).
- `RuntimeError` with diagnostic message if the listing has zero cats (`catfinder.py:213-217`) — protects against silent breakage when the source site changes.
- `evaluate_cat` retries 429 / "rate_limit" exceptions on the schedule `[10, 30, 60]` seconds, then re-raises a `RuntimeError` (`catfinder.py:431-456`); other exceptions surface immediately.
- `evaluate_all` catches per-cat exceptions inside its worker and converts them to a `CatRating(rating="unbekannt", reason=f"Bewertungsfehler: {e}")` so one bad cat never sinks the whole run (`catfinder.py:464-470`).
- `load_state` recovers from corrupt JSON / OS errors with a warning print and an empty dict (`catfinder.py:129-133`).
- `save_state` cleans up the temp file on exception before re-raising (`catfinder.py:140-147`).
- Profile fetch errors are caught in `main()` and become an empty `profile_text`, which `evaluate_cat` translates into `unbekannt` (`catfinder.py:798-802`, `421-423`).

## Cross-Cutting Concerns

**Logging:** Plain `print()` to stdout for progress (e.g., `[3/12] 242724 → geeignet`). No structured logging, no log levels. CI captures this in the GitHub Actions job log.

**Validation:** Pydantic v2 validates the Claude response (`output_format=CatRating`) — invalid output would raise. Loaded state ratings are validated against the allowed Literal set and clamped to `"unbekannt"` if unknown (`catfinder.py:750-751`, `776-777`), so taxonomy changes don't crash on legacy state.

**Authentication:** Single env var `ANTHROPIC_API_KEY`; the `Anthropic()` client picks it up automatically. CI additionally injects `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM` via `secrets`.

**Caching:** The Claude system prompt is sent with `cache_control: {"type": "ephemeral"}` (`catfinder.py:441-445`) so subsequent calls in the same window pay the cheaper cached-input price. State acts as a per-cat result cache across runs (no re-classification of a known `cat_id`).

**Publishing pipeline:** `reports/report.html` is the local artifact (gitignored). CI duplicates it as `docs/index.html` with an injected banner so GitHub Pages serves the latest report at a stable URL. State is committed back to `main` by `github-actions[bot]`.

---

*Architecture analysis: 2026-05-05*
