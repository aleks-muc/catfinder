# External Integrations

**Analysis Date:** 2026-05-05

## APIs & External Services

**LLM / AI:**
- **Anthropic Claude API** — classifies whether each scraped cat profile is suitable for families with children.
  - SDK: `anthropic>=0.40.0` (PyPI), imported at `catfinder.py:30`.
  - Client init: `Anthropic()` (no kwargs — relies on `ANTHROPIC_API_KEY` from env) at `catfinder.py:461`.
  - Endpoint used: `client.messages.parse(...)` at `catfinder.py:437-449`.
  - Model: `claude-haiku-4-5` (constant `MODEL` at `catfinder.py:53`).
  - Auth: env var `ANTHROPIC_API_KEY` (validated at `catfinder.py:716`; CI value comes from `secrets.ANTHROPIC_API_KEY` in `.github/workflows/catfinder.yml:32`).
  - Structured output: `output_format=CatRating` (Pydantic model defined at `catfinder.py:94-107`).
  - Prompt caching: system prompt sent with `"cache_control": {"type": "ephemeral"}` (`catfinder.py:444`) so subsequent calls in the same run reuse the cached system prompt.
  - Retry strategy: `API_RETRY_DELAYS = [10, 30, 60]` (`catfinder.py:55`); only HTTP 429 / `rate_limit` errors are retried (`catfinder.py:452`). Non-rate-limit errors propagate.
  - Concurrency: `ThreadPoolExecutor(max_workers=MAX_EVAL_WORKERS=2)` at `catfinder.py:472`.
  - Cost note (per `README.md:39-41`): ~50 calls on first run, only deltas afterward.

**Web Scraping Target:**
- **Tierschutzverein München** website — primary data source.
  - Listing URL: `https://tierschutzverein-muenchen.de/tiervermittlung/tierheim/katzen` (constant `LISTING_URL` at `catfinder.py:43`).
  - Profile URL pattern: `…/katzen/{cat_id}` (constant `PROFILE_URL_TMPL` at `catfinder.py:44`).
  - HTTP client: `requests.get(...)` at `catfinder.py:155` with `User-Agent: Catfinder/1.0 (privater Gebrauch; Katzensuche)` and `timeout=30`.
  - Politeness: `PROFILE_FETCH_DELAY_S = 0.4` between profile fetches (`catfinder.py:803`).
  - Auth: none (public site).
  - HTML parsing: `BeautifulSoup(html_doc, "html.parser")` at `catfinder.py:163` and `catfinder.py:399`.
  - Defensive selectors: ID extracted via regex `CAT_ID_PATTERN = re.compile(r"/tiervermittlung/tierheim/katzen/(\d+)")` (`catfinder.py:58`) rather than CSS classes — survives moderate template changes.

## Data Storage

**Databases:**
- None. No SQL, NoSQL, ORM, or external DB connection in the codebase.

**File Storage:**
- Local filesystem only.
  - State: `state/seen_cats.json` (atomically written via `tempfile.mkstemp` + `os.replace` at `catfinder.py:139-143`). Keyed by `cat_id`; stores name, URL, image, breed, sex, age hint, rating, reason, partner info, `first_seen` ISO timestamp.
  - Reports: `reports/report.html` (overwritten each run at `catfinder.py:692`). `reports/*.html` is git-ignored except `.gitkeep`.
  - GitHub Pages: `docs/index.html` (created in CI by the workflow at `.github/workflows/catfinder.yml:38-49`, committed to `main`).

**Caching:**
- No external cache (no Redis/Memcached/etc.).
- Anthropic prompt caching is used in-call (see above) but is server-side at Anthropic.
- pip cache is enabled in CI via `actions/setup-python@v6` `cache: pip`.

## Authentication & Identity

**Auth Provider:**
- None for end users (the project is a single-user CLI / scheduled job, no login flow).
- Outbound auth:
  - Anthropic via `ANTHROPIC_API_KEY` bearer-style header (handled by the SDK).
  - SendGrid via SMTP `username: apikey` + `password: secrets.SENDGRID_API_KEY` (`.github/workflows/catfinder.yml:65-66`).
  - GitHub via the workflow's auto-provisioned `GITHUB_TOKEN` (used implicitly by `actions/checkout@v6` and the `git push` in the "State committen" step at `.github/workflows/catfinder.yml:51-57`).

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Rollbar, or similar.
- Per-cat failures are caught and converted to a fallback `CatRating(rating="unbekannt", reason="Bewertungsfehler: {e}")` (`catfinder.py:469-470`) so one bad profile does not abort the run.

**Logs:**
- Plain `print(...)` to stdout. Examples:
  - Progress: `print(f"  [{done}/{len(cats)}] {cid} → {rating.rating}")` at `catfinder.py:479`.
  - Rate-limit warnings: `catfinder.py:434`.
  - Final summary: `catfinder.py:857`.
- In CI, stdout is captured by GitHub Actions; nothing is shipped to an external log sink.

**Metrics:**
- One workflow output: `new_count` (count of newly evaluated cats), written via `_write_github_output` (`catfinder.py:702`) and consumed by the e-mail subject in `.github/workflows/catfinder.yml:67`.

## CI/CD & Deployment

**Hosting:**
- **GitHub Actions** — sole compute platform.
  - Workflow file: `.github/workflows/catfinder.yml`.
  - Runner: `ubuntu-latest`.
  - Triggers: cron `0 7 * * *` and `0 14 * * *` UTC plus `workflow_dispatch`.
- **GitHub Pages** — serves the public report at `https://aleks-muc.github.io/catfinder/` (referenced in the injected banner at `.github/workflows/catfinder.yml:42`).

**CI Pipeline steps (`.github/workflows/catfinder.yml`):**
1. `actions/checkout@v6` — checkout repository.
2. `actions/setup-python@v6` (Python 3.12 + pip cache).
3. `pip install -r requirements.txt`.
4. `python catfinder.py --no-browser` (with `ANTHROPIC_API_KEY` injected).
5. Heredoc Python step prepends an "Im Browser öffnen" banner to `reports/report.html` and copies it to `docs/index.html`.
6. `git commit` of `state/seen_cats.json` + `docs/index.html` back to `main` (`[skip ci]` in the message to avoid loops). Requires `permissions: contents: write` (`.github/workflows/catfinder.yml:13-14`).
7. `dawidd6/action-send-mail@v16` sends the report.

## Environment Configuration

**Required env vars (runtime):**
- `ANTHROPIC_API_KEY` — Claude API key. Local: exported in `~/.zshrc`. CI: `secrets.ANTHROPIC_API_KEY`.

**Optional env vars:**
- `GITHUB_OUTPUT` — auto-set by GitHub Actions; consumed at `catfinder.py:703`.

**Workflow-only secrets (`.github/workflows/catfinder.yml`):**
- `secrets.ANTHROPIC_API_KEY` — line 32.
- `secrets.SENDGRID_API_KEY` — line 66.
- `secrets.MAIL_TO` — line 68 (recipient e-mail).
- `secrets.MAIL_FROM` — line 69 (sender e-mail; must match a verified SendGrid sender).

**Secrets location:**
- Locally: shell environment (no `.env` is read by the script — `.env` is in `.gitignore` defensively but the code does not load it).
- CI: GitHub repository → Settings → Secrets and variables → Actions.

## Webhooks & Callbacks

**Incoming:**
- None. No HTTP server is exposed; no callback endpoints.

**Outgoing:**
- E-mail via SendGrid SMTP (`smtp.sendgrid.net:465`, TLS) sent by `dawidd6/action-send-mail@v16` after each scheduled run (`.github/workflows/catfinder.yml:60-70`). Subject contains the dynamic count `${{ steps.catfinder.outputs.new_count }}`; body is the generated `reports/report.html` (`html_body: file://reports/report.html`).
- `git push` to the repository's `main` branch from inside the workflow (`.github/workflows/catfinder.yml:57`).

---

*Integration audit: 2026-05-05*
