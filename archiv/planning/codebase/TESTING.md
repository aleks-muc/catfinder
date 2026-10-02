# Testing Patterns

**Analysis Date:** 2026-05-05

## Test Framework

**No automated tests exist in this repository.**

A full scan of the repo found:

- No `tests/` or `test/` directory.
- No files matching `test_*.py` or `*_test.py` anywhere outside `.venv/`.
- No `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `conftest.py`, or `noxfile.py`.
- No test framework declared in `requirements.txt` (`requirements.txt:1-4` contains only `anthropic`, `beautifulsoup4`, `pydantic`, `requests`).
- No test step in the GitHub Actions workflow (`.github/workflows/catfinder.yml:9-71`) — the CI job runs `python catfinder.py --no-browser` against the live website and treats a clean exit as success.

The project's "test" today is effectively the daily scheduled CI run (`.github/workflows/catfinder.yml:4-7`, cron at 07:00 and 14:00 UTC), which exercises the scraper, the Claude evaluation path, the report renderer, and the state-write end-to-end against production data.

**Runner:** Not configured. Recommended choice if/when tests are added: `pytest` (idiomatic for a single-script Python 3.12 project).

**Assertion Library:** Not configured. With `pytest`, plain `assert` is the standard.

**Run Commands:**

```bash
# Today: nothing to run.
# Once tests are added (see "Suggested layout" below):
pytest                       # Run all tests
pytest -k name_of_test       # Run a subset
pytest --cov=catfinder       # Coverage (requires pytest-cov)
```

## Test File Organization

**Location:** Not present. There is no convention to follow yet.

**Suggested layout** (matches the single-module shape of the project):

```
Catfinder/
├── catfinder.py
├── requirements.txt
├── requirements-dev.txt        # add: pytest, pytest-cov, responses (or respx), pydantic
└── tests/
    ├── conftest.py             # shared fixtures (sample HTML, fake Anthropic client)
    ├── fixtures/
    │   ├── listing.html        # captured copy of the listing page
    │   └── profile_12345.html  # captured copy of one cat profile
    ├── test_scraper.py         # scrape_listing, fetch_profile_text, _pick, detect_interested,
    │                           # find_companion_names, extract_age_hint, age_hint_to_months
    ├── test_state.py           # load_state, save_state (atomic write, corruption recovery)
    ├── test_evaluation.py      # evaluate_cat retry loop, evaluate_all isolation
    ├── test_report.py          # _card_sort_key, _build_filter_bar, render_report snapshots
    └── test_main.py            # main() CLI flags: --reset, --all, --no-browser
```

Tests should live in a sibling `tests/` directory rather than co-located, because `catfinder.py` is a top-level executable script (no package). With this layout, `pytest` will pick up `tests/` automatically when invoked from the repo root.

**Naming:**
- Files: `test_<area>.py`.
- Functions: `test_<unit>_<behaviour>` — e.g. `test_load_state_returns_empty_dict_when_file_missing`, `test_evaluate_cat_retries_on_429`.

## Test Structure

No real examples exist. The expected pytest pattern for this codebase:

```python
# tests/test_state.py
from pathlib import Path

import catfinder


def test_load_state_returns_empty_dict_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(catfinder, "STATE_FILE", tmp_path / "missing.json")
    assert catfinder.load_state() == {}


def test_save_state_writes_atomically(monkeypatch, tmp_path):
    monkeypatch.setattr(catfinder, "STATE_DIR", tmp_path)
    monkeypatch.setattr(catfinder, "STATE_FILE", tmp_path / "seen_cats.json")
    catfinder.save_state({"123": {"name": "Mimi"}})
    assert (tmp_path / "seen_cats.json").exists()
    # No leftover temp files.
    assert not list(tmp_path.glob("seen_cats_*.json"))
```

**Patterns to follow once tests exist:**
- One assertion focus per test, descriptive name in the function.
- Use `tmp_path` for any code path that touches `STATE_DIR` / `REPORT_DIR`.
- Use `monkeypatch.setattr(catfinder, "X", ...)` to override module-level constants and the `Anthropic` client.

## Mocking

**Framework:** Not configured. Recommended: `pytest`'s built-in `monkeypatch` for module attributes plus one of:

- `responses` or `respx` for `requests.get` / HTTPX calls — to test `_http_get` (`catfinder.py:154-157`), `scrape_listing` (`catfinder.py:160-219`), and `fetch_profile_text` (`catfinder.py:396-414`) against checked-in fixture HTML.
- A hand-rolled fake for `anthropic.Anthropic.messages.parse` — to test `evaluate_cat` (`catfinder.py:421-456`) without hitting the real API.

**Suggested pattern:**

```python
# tests/conftest.py
import pytest
from pydantic import BaseModel

import catfinder


class _FakeMessages:
    def __init__(self, queue):
        self._queue = list(queue)

    def parse(self, **kwargs):
        outcome = self._queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return type("Resp", (), {"parsed_output": outcome})()


@pytest.fixture
def fake_anthropic(monkeypatch):
    def _make(queue):
        client = type("Client", (), {"messages": _FakeMessages(queue)})()
        monkeypatch.setattr(catfinder, "Anthropic", lambda: client)
        return client
    return _make
```

```python
# tests/test_evaluation.py
from catfinder import CatRating, Cat, evaluate_cat


def test_evaluate_cat_retries_on_rate_limit(fake_anthropic, monkeypatch):
    monkeypatch.setattr("catfinder.time.sleep", lambda _s: None)  # don't actually sleep
    monkeypatch.setattr(catfinder, "API_RETRY_DELAYS", [0, 0, 0])
    client = fake_anthropic([
        Exception("429 rate_limit"),
        CatRating(rating="geeignet", reason="kinderlieb"),
    ])
    cat = Cat(cat_id="1", name="Mimi", profile_url="https://x")
    out = evaluate_cat(client, cat, "Profil-Text mit Kindern.")
    assert out.rating == "geeignet"
```

**What to Mock:**
- All outbound HTTP (`requests.get` via `responses`/`respx`).
- The `Anthropic` client (the SDK is imported at `catfinder.py:30`, instantiated at `catfinder.py:461`).
- `time.sleep` inside the retry loop (`catfinder.py:435`) and the per-profile delay (`catfinder.py:803`) so tests run in milliseconds.
- `webbrowser.open` (`catfinder.py:695`) — replace with a no-op so tests don't open a browser.
- `os.environ["GITHUB_OUTPUT"]` (`catfinder.py:703`) — clear or set via `monkeypatch.setenv`.

**What NOT to Mock:**
- `BeautifulSoup` parsing — feed it real fixture HTML instead so parser changes are caught.
- The Pydantic `CatRating` model — exercise the real schema.
- `json.loads`/`json.dumps` and `tempfile.mkstemp`/`os.replace` — use `tmp_path` and observe actual filesystem behaviour. The atomic-write logic in `save_state` (`catfinder.py:136-147`) is one of the most important things to cover end-to-end.

## Fixtures and Factories

No fixtures exist today. Suggested approach:

- **HTML fixtures:** capture one full listing page and 2-3 profile pages from `https://tierschutzverein-muenchen.de/...` and store under `tests/fixtures/`. Drive `scrape_listing` / `fetch_profile_text` against these via `responses`/`respx`. This is the only way to lock down the regex/heuristics in `_pick` (`catfinder.py:222-230`), `find_companion_names` (`catfinder.py:238-250`), and `BIRTH_DATE_PATTERN` (`catfinder.py:60-63`).
- **Object factories:** since `Cat` is a `@dataclass` with sensible defaults (`catfinder.py:80-91`), prefer construction over a factory library:

  ```python
  def make_cat(cat_id="1", name="Mimi", **overrides):
      return Cat(cat_id=cat_id, name=name,
                 profile_url=f"https://example.test/{cat_id}", **overrides)
  ```

- **State factories:** generate the JSON shape that `seen_cats.json` uses — see the keys written in `main` (`catfinder.py:846-855`): `name`, `profile_url`, `image_url`, `breed`, `sex`, `age_hint`, `has_interested`, `companion_count`, `partner_name`, `first_seen`, `rating`, `reason`. The current production file `state/seen_cats.json` (~43 KB) is itself a usable golden fixture for state-migration tests.

**Location:** put them in `tests/fixtures/` (HTML, JSON) and `tests/conftest.py` (Python factories and pytest fixtures).

## Coverage

**Requirements:** None enforced. There is no coverage configuration.

**View Coverage** (once `pytest` and `pytest-cov` are installed):

```bash
pytest --cov=catfinder --cov-report=term-missing
pytest --cov=catfinder --cov-report=html      # writes htmlcov/index.html
```

A reasonable initial target for this codebase is 80% line coverage on `catfinder.py`. The HTML/CSS/JS literal in `_build_filter_bar` (`catfinder.py:297-393`) and the `HTML_TEMPLATE` constant (`catfinder.py:498-545`) are formatting-only and can be excluded with `# pragma: no cover` if they pull the percentage down without adding signal.

## Test Types

**Unit Tests:**
- *Scope:* pure functions in `catfinder.py` — `_pick` (`:222`), `detect_interested` (`:233`), `find_companion_names` (`:238`), `extract_age_hint` (`:253`), `age_hint_to_months` (`:273`), `_card_sort_key` (`:484`).
- *Approach:* table-driven tests; pass strings and dataclass instances, assert the return value. No mocking required.

**Integration Tests:**
- *Scope:*
  - `scrape_listing` + `fetch_profile_text` against fixture HTML served by `responses`/`respx`.
  - `evaluate_cat` and `evaluate_all` against the fake `Anthropic` client (covers the retry loop at `catfinder.py:431-456` and the per-item isolation at `catfinder.py:464-470`).
  - `load_state`/`save_state` round-trip including the corrupt-file recovery branch (`catfinder.py:131-133`) and the atomic-write cleanup branch (`catfinder.py:144-147`).
  - `render_report` snapshot test — compare a stable substring of the output (timestamps must be patched).
- *Approach:* one test module per concern, real filesystem via `tmp_path`, mocked network and SDK.

**E2E Tests:**
- Not used and likely not appropriate for this project — the daily CI run (`.github/workflows/catfinder.yml`) already serves as a live smoke test against the upstream website. If an offline E2E is wanted, drive `main()` end-to-end with mocked HTTP + Anthropic + `webbrowser.open` and assert on the generated `reports/report.html` and `state/seen_cats.json`.

## Common Patterns

**Async Testing:** Not applicable — `catfinder.py` uses `concurrent.futures.ThreadPoolExecutor` (`catfinder.py:472-481`), not `asyncio`. Test the thread-pool path by setting `MAX_EVAL_WORKERS = 1` via `monkeypatch.setattr(catfinder, "MAX_EVAL_WORKERS", 1)` so failures are deterministic.

**Error Testing:**

```python
import pytest
from catfinder import scrape_listing


def test_scrape_listing_raises_when_no_cats_found(monkeypatch):
    monkeypatch.setattr("catfinder._http_get", lambda url: "<html><body>nothing</body></html>")
    with pytest.raises(RuntimeError, match="Keine Katzen"):
        scrape_listing()
```

This mirrors the defensive guard at `catfinder.py:213-217`.

**Filesystem Testing:**

```python
def test_save_state_recovers_from_corrupt_file(monkeypatch, tmp_path, capsys):
    state_file = tmp_path / "seen_cats.json"
    state_file.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(catfinder, "STATE_FILE", state_file)
    assert catfinder.load_state() == {}
    assert "Warnung" in capsys.readouterr().out
```

Covers the `(json.JSONDecodeError, OSError)` branch at `catfinder.py:131-133`.

---

*Testing analysis: 2026-05-05*
