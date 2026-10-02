# Coding Conventions

**Analysis Date:** 2026-05-05

The repository is a single-script Python tool (`catfinder.py`, 864 lines) plus a GitHub Actions workflow. There is no formal style configuration in the repo — no `pyproject.toml`, `setup.cfg`, `.flake8`, `.pylintrc`, `pre-commit`, `ruff.toml`, or `black` config exists. Conventions below are inferred from the actual code in `catfinder.py:1-864` and should be treated as the *de facto* style for new code in this project.

## Naming Patterns

**Files:**
- Single top-level script `catfinder.py` (lowercase, no underscores). State and reports live in dedicated directories (`state/seen_cats.json`, `reports/report.html`).
- No package layout (no `__init__.py`, no `src/`).

**Functions:**
- `snake_case` for all functions: `scrape_listing`, `fetch_profile_text`, `evaluate_cat`, `evaluate_all`, `render_report`, `write_and_open_report` (e.g. `catfinder.py:160`, `catfinder.py:396`, `catfinder.py:421`, `catfinder.py:548`, `catfinder.py:690`).
- Private/internal helpers are prefixed with a single underscore: `_http_get` (`catfinder.py:154`), `_pick` (`catfinder.py:222`), `_build_filter_bar` (`catfinder.py:297`), `_card_sort_key` (`catfinder.py:484`), `_write_github_output` (`catfinder.py:702`), and the closure helpers `_img`, `_meta_line`, `_interested_badge`, `_pair_attr`, `_partner_line`, `_age_months_with_fallback`, `_ratings_from_state` (`catfinder.py:565-587`, `catfinder.py:745-781`).

**Variables:**
- Local variables are `snake_case`: `profile_url`, `card_text`, `age_min`, `age_max`, `last_exc` (e.g. `catfinder.py:175`, `catfinder.py:198`, `catfinder.py:597`, `catfinder.py:431`).
- Loop variables stay short (`a`, `c`, `m`, `r`, `idx`) when their meaning is local and obvious — e.g. `for a in soup.find_all(...)` (`catfinder.py:167`), `for c in cats` (`catfinder.py:741`), `m = CAT_ID_PATTERN.search(...)` (`catfinder.py:168`).

**Constants:**
- `UPPER_SNAKE_CASE` at module level: `BASE`, `LISTING_URL`, `PROFILE_URL_TMPL`, `USER_AGENT`, `MODEL`, `MAX_EVAL_WORKERS`, `API_RETRY_DELAYS`, `PROFILE_FETCH_DELAY_S`, `DEFAULT_AGE_LO`, `DEFAULT_AGE_HI` (`catfinder.py:42-56`, `catfinder.py:293-294`).
- Compiled regex constants share the same convention with a `_PATTERN` suffix: `CAT_ID_PATTERN`, `INTERESTED_PATTERN`, `BIRTH_DATE_PATTERN` (`catfinder.py:58-63`).
- Path constants computed from `__file__`: `ROOT`, `STATE_DIR`, `STATE_FILE`, `REPORT_DIR`, `REPORT_FILE` (`catfinder.py:47-51`).

**Types:**
- Classes use `PascalCase`: `Cat` (dataclass at `catfinder.py:81`), `CatRating` (Pydantic model at `catfinder.py:94`).
- Type aliases use `PascalCase`: `Rating = Literal[...]` (`catfinder.py:66`).
- Dict-of-dict literal metadata uses lowercase string keys (`"geeignet"`, `"unbekannt"`, `"aeltere_kinder"`, `"nicht_geeignet"` — `catfinder.py:69-72`). The same enum-like keys are reused as the `CatRating.rating` literal values.

## Code Style

**Formatting:**
- No formatter is configured. Code is hand-formatted but consistent.
- 4-space indentation, no tabs.
- Lines run up to ~120 characters; wide lines appear in the metadata table (`catfinder.py:69-72`), the HTML/CSS literals (`catfinder.py:498-545`), and the embedded JS in `_build_filter_bar` (`catfinder.py:340-393`). Pure Python statements typically stay under ~100 chars.
- Section banners separate logical regions of the file:

  ```python
  # ---------------------------------------------------------------------------
  # Konfiguration
  # ---------------------------------------------------------------------------
  ```

  See `catfinder.py:38-40`, `:76-78`, `:122-124`, `:150-152`, `:417-419`, `:494-496`, `:698-700`. Use these banners when adding a new logical section.

- Strings: double quotes are the default (`"https://..."`, `"utf-8"`). Single quotes appear inside f-strings for HTML attribute values (`'<div class="card" ...>'`) and in the CSS/JS literals to avoid escaping.
- Trailing commas are used in multi-line collection literals (`catfinder.py:55`, `:69-73`).

**Linting:**
- No linter is configured. There is no `ruff`, `flake8`, `pylint`, or `mypy` config. Treat the existing patterns in `catfinder.py` as the lint target.

## Import Organization

Imports follow PEP 8 grouping with blank lines between groups (`catfinder.py:8-35`):

1. **Future / stdlib:**
   ```python
   from __future__ import annotations

   import argparse
   import concurrent.futures
   import html
   import json
   ...
   from dataclasses import dataclass, asdict
   from datetime import date, datetime
   from pathlib import Path
   from typing import Literal
   ```
2. **Third-party:**
   ```python
   import requests
   from bs4 import BeautifulSoup
   from pydantic import BaseModel, Field
   ```
3. **Optional third-party with fallback** — wrapped in `try/except ImportError` so the script can fail with a friendly message:
   ```python
   try:
       from anthropic import Anthropic
   except ImportError:
       sys.exit("Fehler: anthropic SDK nicht installiert.\n  pip install -r requirements.txt")
   ```
   See `catfinder.py:29-35`. Reuse this pattern for any optional heavy dependency.

**Path Aliases:**
- None. The project is a single module, so absolute or relative package imports are not used.

## Error Handling

**Strategy:** narrow `except` clauses for expected failures, top-level `try/except` blocks that print a German user-facing message and either continue (best-effort) or `sys.exit` / `return 1`.

**Patterns observed:**

- **Expected I/O errors → log + sane default:** state loading catches `(json.JSONDecodeError, OSError)`, prints a warning, and starts fresh:
  ```python
  except (json.JSONDecodeError, OSError) as e:
      print(f"Warnung: State-Datei konnte nicht gelesen werden ({e}). Starte frisch.")
      return {}
  ```
  See `catfinder.py:131-133`.

- **Atomic file writes:** `save_state` writes to a `tempfile.mkstemp` path then `os.replace`s it onto `STATE_FILE`. The `try/except` cleans up the temp file on failure and re-raises (`catfinder.py:136-147`).

- **HTTP retries with backoff:** API rate-limits trigger a retry loop driven by `API_RETRY_DELAYS = [10, 30, 60]`:
  ```python
  for attempt, delay in enumerate([0] + API_RETRY_DELAYS):
      if delay:
          print(f"  Rate-Limit erreicht — warte {delay}s und versuche es erneut …")
          time.sleep(delay)
      try:
          response = client.messages.parse(...)
          return response.parsed_output
      except Exception as e:
          if "429" in str(e) or "rate_limit" in str(e).lower():
              last_exc = e
              continue
          raise
  raise RuntimeError(...) from last_exc
  ```
  See `catfinder.py:431-456`. Non-rate-limit errors propagate immediately.

- **Per-item failure isolation:** in `evaluate_all`, the worker function catches all exceptions, logs them with the cat name and id, and returns a `CatRating(rating="unbekannt", reason=f"Bewertungsfehler: {e}")` so one failed call does not abort the batch (`catfinder.py:464-470`). Apply this pattern when adding new per-item batch operations.

- **Best-effort profile fetches:** the main loop catches everything around `fetch_profile_text` and stores an empty string for that cat id (`catfinder.py:798-802`).

- **Hard failures with user guidance:** `sys.exit` / `return 1` are used when the run cannot continue, accompanied by a multi-line German message that tells the user how to fix it (`catfinder.py:32-35`, `catfinder.py:716-722`).

- **Defensive scraping invariants:** if the listing page yields zero cats, the scraper raises `RuntimeError` with the URL and a hint that the page structure may have changed (`catfinder.py:213-217`). Use `RuntimeError` for this kind of "the world looks wrong" condition.

- **Avoid in new code:** there are bare `except Exception as e:` blocks in three places (`catfinder.py:451`, `:468`, `:800`). They are intentional (best-effort batch isolation), but for new code prefer the narrowest exception type that fits.

## Logging

**Framework:** `print()` only. No `logging` module is configured.

**Patterns:**
- Top-level progress messages have no prefix:
  ```python
  print(f"Rufe Listenseite ab: {LISTING_URL}")
  print(f"  {len(cats)} Katzen gelistet.")
  ```
  See `catfinder.py:728-731`.
- Nested / sub-step messages are indented with two spaces; per-item failures use four spaces and a leading `!`:
  ```python
  print(f"  [{i}/{len(to_evaluate)}] {cat.name} ({cat.cat_id})")
  ...
  print(f"    ! Fehler: {e}")
  ```
  See `catfinder.py:797-801`. The same `!` prefix is used in `evaluate_all` (`catfinder.py:469`).
- Warnings are prefixed with `Warnung:` (`catfinder.py:132`); fatal user-facing errors with `Fehler:` (`catfinder.py:33`, `catfinder.py:717`).
- All user-facing output is **German**. Keep new log/error/UI strings in German to match the report and the workflow naming.
- Progress counters use the `[done/total]` format (`catfinder.py:479`, `catfinder.py:797`).

If you introduce structured logging, replace `print` consistently across the module rather than mixing the two.

## Type Hints

The module opts into `from __future__ import annotations` (`catfinder.py:8`) so all annotations are lazy strings — modern PEP 604 union syntax (`int | None`) is used freely (`catfinder.py:273`, `catfinder.py:431`, `catfinder.py:552`).

**Conventions:**
- All public functions have full parameter and return annotations: `def scrape_listing() -> list[Cat]:` (`catfinder.py:160`), `def evaluate_cat(client: Anthropic, cat: Cat, profile_text: str) -> CatRating:` (`catfinder.py:421`), `def render_report(...) -> str:` (`catfinder.py:548-555`).
- Built-in generics are preferred over `typing` equivalents: `list[Cat]`, `dict[str, dict]`, `dict[str, CatRating]`, `set[str]`, `tuple[str, CatRating]` (`catfinder.py:126`, `:166`, `:238`, `:459`, `:464`).
- `Literal` from `typing` is used for closed enums:
  ```python
  Rating = Literal["geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt"]
  ```
  See `catfinder.py:66`. Reuse `Rating` where applicable instead of redefining the literal.
- Optional values use `X | None` (e.g. `int | None`, `Exception | None`, `dict[str, int | None] | None`) rather than `Optional[X]` (`catfinder.py:273`, `:431`, `:552`).
- Closures and small inner functions are also annotated where the result feeds into typed code paths (`def work(c: Cat) -> tuple[str, CatRating]:` at `catfinder.py:464`).
- Dataclass fields use simple inline annotations with default values for optional attributes (`catfinder.py:81-91`):
  ```python
  @dataclass
  class Cat:
      cat_id: str
      name: str
      profile_url: str
      image_url: str = ""
      ...
      has_interested: bool = False
      companion_count: int = 0
      partner_name: str = ""
  ```
- Pydantic models use `Field(description=...)` so the description is fed back to Claude as part of the structured-output schema (`catfinder.py:97-107`). Keep descriptions in German to match `SYSTEM_PROMPT`.

There is no `mypy`/`pyright` config; type hints are documentation-grade, not statically enforced.

## Docstrings

- Module docstring is present at `catfinder.py:1-6` and explains *what* the script does in German.
- Function docstrings are short — one line, German, describing intent rather than mechanics. Examples:
  - `"""Holt die Listenseite und extrahiert alle Katzen-Einträge."""` (`catfinder.py:161`)
  - `"""True wenn der Steckbrief-Text Interessenten-Hinweise enthält."""` (`catfinder.py:234`)
  - `"""Holt den Steckbrief und extrahiert den relevanten Beschreibungstext."""` (`catfinder.py:397`)
  - `"""Parallelisiert Claude-Calls über mehrere Katzen."""` (`catfinder.py:460`)
- Multi-line docstrings appear when behaviour needs more nuance — e.g. `find_companion_names` (`catfinder.py:238-243`), `extract_age_hint` (`catfinder.py:254`), `_build_filter_bar` (`catfinder.py:298`), `_card_sort_key` (`catfinder.py:485`).
- Pydantic field docstrings live in `Field(description=...)` and double as the LLM schema description (`catfinder.py:97-107`).
- No Sphinx / Google / Numpy section formatting is used. Stay consistent with this lightweight, German, intent-first style.

## Comments

**When to Comment:**
- Inline comments explain *why*, not *what* — German one-liners above the relevant block:
  - `# Defensiv: wir suchen alle Links, die auf /tiervermittlung/tierheim/katzen/{id} zeigen.` (`catfinder.py:165`)
  - `# Navigation, Footer, Scripts rauswerfen` (`catfinder.py:406`)
  - `# Defaultwerte auf tatsächliche Datenbandbreite klemmen` (`catfinder.py:305`)
  - `# Atomic-write` style is implemented but not heavily commented; the temp-file dance speaks for itself (`catfinder.py:138-147`).
- Section banners (see "Formatting" above) divide the file into ~7 logical sections.
- Inline trailing comments document numeric magic constants:
  ```python
  API_RETRY_DELAYS = [10, 30, 60]  # Sekunden warten nach 429, je Versuch
  DEFAULT_AGE_LO = 36   # 3 Jahre in Monaten
  DEFAULT_AGE_HI = 144  # 12 Jahre in Monaten
  ```
  See `catfinder.py:55`, `catfinder.py:293-294`. Always annotate numeric constants this way.

**JSDoc/TSDoc:** N/A — Python only.

## Function Design

**Size:** most functions are 5-30 lines and do one thing. The two exceptions are intentional aggregators:
- `_build_filter_bar` (`catfinder.py:297-393`, ~95 lines) — embeds CSS+JS as a heredoc-style f-string.
- `render_report` (`catfinder.py:548-687`, ~140 lines) — composes the full HTML report with several local helpers.
- `main` (`catfinder.py:709-859`, ~150 lines) — orchestration; uses local closures (`_ratings_from_state`, `_age_months_with_fallback`) to keep helpers near their data.

When a function grows past ~30 lines, the existing pattern is to extract local closures rather than top-level helpers if the helper closes over `state` / `args`.

**Parameters:**
- Positional for required arguments, keyword arguments with defaults for optional flags. Booleans are explicit named flags (`no_browser: bool = False` at `catfinder.py:690`).
- Optional collection inputs default to `None` and are normalised at the top of the function:
  ```python
  still_known = still_known or []
  no_longer_listed = no_longer_listed or []
  ```
  See `catfinder.py:556-557`. This avoids the mutable-default-argument pitfall.

**Return Values:**
- Functions return concrete typed values; no tuples-as-poor-mans-record. Where a structured value is needed, a `@dataclass` (`Cat`) or a `BaseModel` (`CatRating`) is used.
- Functions that mutate state are explicit about it (e.g. `save_state`, `_write_github_output` return `None`).
- Helpers that produce HTML return strings; no DOM/builder pattern.

## Module Design

**Exports:**
- The repository is a single executable script. There is no public API surface, no `__all__`, and no `__init__.py`.
- The entrypoint is gated by:
  ```python
  if __name__ == "__main__":
      sys.exit(main())
  ```
  See `catfinder.py:862-863`. `main()` returns an `int` exit code (0 on success, 1 on missing API key).

**Barrel Files:** N/A.

**Where to put new code:**
- Small additions: a new function in the matching `# ---` section of `catfinder.py`. Use the existing section banners (Konfiguration, Datenmodelle, State, Scraper, Claude-Bewertung, HTML-Report, Main).
- New data shapes: extend the `Cat` dataclass (`catfinder.py:80-91`) or add a new `BaseModel` near `CatRating` (`catfinder.py:94-107`). Keep state-serialisable fields as plain types so `dataclasses.asdict` and `json.dumps` keep working (`catfinder.py:846`, `:138`).
- New CLI flags: extend `argparse` in `main()` near `catfinder.py:710-714`.
- If the file grows past ~1500 lines, split out the HTML/JS rendering (`_build_filter_bar`, `HTML_TEMPLATE`, `render_report`) into a sibling `report.py` first — that section is the most self-contained.

---

*Convention analysis: 2026-05-05*
