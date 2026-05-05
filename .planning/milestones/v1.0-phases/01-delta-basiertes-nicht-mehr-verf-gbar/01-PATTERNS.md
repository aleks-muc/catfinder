# Phase 1: Delta-basiertes "Nicht mehr verfügbar" — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 1 modified file (`catfinder.py`) — single-file project, no new files
**Touchpoints:** 4 distinct edit regions / 4 with strong in-file analogs

## File Classification

Single-file Python script. The "files" mapped below are the **edit regions** within `catfinder.py`, classified by role and data-flow. All analogs are excerpts from the same file (this is a single-module codebase by deliberate constraint — see `CLAUDE.md` "Single-file convention").

| Edit Region | Role | Data Flow | Closest In-File Analog | Match Quality |
|-------------|------|-----------|------------------------|---------------|
| `catfinder.py:136-147` — purge logic in `save_state` (or new helper) | state / persistence | file-I/O (atomic write) | `save_state` itself (lines 136-147) | exact |
| `catfinder.py:733-779` — delta computation in `main()` | orchestration | request-response (set diff) | existing `known_ids - current_ids` block (lines 759-778) | exact |
| `catfinder.py:842-856` — state update at end of `main()` | orchestration / state mutation | CRUD (dict mutation + save) | existing state-update block (lines 842-856) | exact |
| `catfinder.py:603-678` + `render_report` signature (lines 548-555) — empty-state render in zombie section | view / template | transform (data → HTML) | `sect1_inner` empty branch (line 605) and `sect_gone` block (lines 636-655) | exact |

All four edit regions have an **exact** analog (same role + same data flow) inside the same file. No `RESEARCH.md` patterns are needed.

---

## Pattern Assignments

### 1. State Purge Logic (state, file-I/O)

**Where it lands:** Either as a new private helper near `save_state` in the `# --- State ---` section (`catfinder.py:122-147`), or inline in `main()` directly before the existing `save_state(state)` call at `catfinder.py:856`. CONTEXT.md `<code_context>` recommends inline-in-`main()`; planner decides.

**Analog:** `save_state` itself (`catfinder.py:136-147`) — for the **atomic-write guarantee that must remain intact**. The purge mutates the in-memory dict; `save_state` then handles durability.

**Atomic-write pattern to PRESERVE unchanged** (`catfinder.py:136-147`):
```python
def save_state(state: dict[str, dict]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    fd, tmp_path = tempfile.mkstemp(prefix="seen_cats_", suffix=".json", dir=str(STATE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

**Hard rule (D-02 in CONTEXT.md, REPORT-02):** Purge happens on the in-memory `state` dict **before** calling `save_state(state)` so the existing atomic-write path stays the only disk-touching code. Do **not** introduce a second write path.

**Type-hint convention** for any new helper (per `CLAUDE.md` "Type Hints"): use built-in generics + `from __future__ import annotations` (already at file top). Example shape:
```python
def purge_disappeared(state: dict[str, dict], current_ids: set[str]) -> None:
    """Entferne State-Einträge, deren cat_id nicht mehr im Listing steht."""
    for cid in list(state.keys()):
        if cid not in current_ids:
            del state[cid]
```
- Imperative German one-line docstring (matches `save_state`'s style — see also `_card_sort_key`'s docstring at `catfinder.py:485`).
- Mutates in place, returns `None` — same convention as `save_state` and `_write_github_output` (see `CLAUDE.md` "Function Design": *"Functions that mutate state are explicit about it"*).
- `set[str]` return/param style matches `current_ids = {c.cat_id for c in cats}` (`catfinder.py:759`) and `known_ids = set(state.keys())` (`catfinder.py:734`).

**Logging style for the purge** (only if planner adds a log line — optional). Matches `catfinder.py:857`:
```python
print(f"State aktualisiert: {len(state)} Katzen bekannt.")
```
Indentation, German, no prefix at top-level. For sub-step status use 2-space indent (per `CLAUDE.md` "Logging").

---

### 2. Delta Computation in `main()` (orchestration, request-response)

**Where it lands:** Inside `main()`, between `state = load_state()` (`catfinder.py:733`) and the state-update block (`catfinder.py:842-856`). The existing `known_ids - current_ids` block at `catfinder.py:759-778` is **already the delta**; the semantic change is that this delta now reflects only *one* run's worth of disappearances (because state was purged at the previous run's end), not the full history.

**Analog (existing delta block, `catfinder.py:759-778`)** — keep this loop nearly verbatim; the only change is what `known_ids` semantically means downstream:
```python
# Katzen die letztes Mal gelistet waren, jetzt aber nicht mehr
current_ids = {c.cat_id for c in cats}
no_longer_listed: list[tuple[Cat, CatRating]] = []
for cid in sorted(known_ids - current_ids):
    entry = state[cid]
    c = Cat(
        cat_id=cid,
        name=entry.get("name", cid),
        profile_url=entry.get("profile_url", ""),
        image_url=entry.get("image_url", ""),
        breed=entry.get("breed", ""),
        sex=entry.get("sex", ""),
        age_hint=entry.get("age_hint", ""),
        has_interested=entry.get("has_interested", False),
        companion_count=entry.get("companion_count", 0),
        partner_name=entry.get("partner_name", ""),
    )
    r = entry.get("rating", "unbekannt")
    if r not in ("geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt"):
        r = "unbekannt"
    no_longer_listed.append((c, CatRating(rating=r, reason=entry.get("reason", ""))))
```

**Pattern to copy:**
- **Defensive `.get(..., default)`** for every state-derived field — the `Cat(...)` rebuild is tolerant of partial entries. Same defensive style appears in `_ratings_from_state` (`catfinder.py:745-756`).
- **Whitelist for `Rating`** — the `r not in (...)` check at lines 750-751 and 776-777 is duplicated; planner *may* extract once but this is **not required** (mirroring is the existing house style here).
- **Sorted iteration** of `known_ids - current_ids` (`sorted(...)` at line 761) — keeps output deterministic. Preserve this.

**Required new signal — "had prior state":** Per CONTEXT.md `<code_context>` D-07, the renderer must distinguish "Erstlauf, hide section" from "regular run, empty-state hint". Two viable approaches (planner picks):

a) **New parameter** added to `render_report` signature. Existing signature (`catfinder.py:548-555`) is the analog for shape — note the `... | None = None` defaults that get normalized at the function top:
```python
def render_report(
    evaluated: list[tuple[Cat, CatRating]],
    total_listed: int,
    scope_note: str = "",
    listing_ages: dict[str, int | None] | None = None,
    still_known: list[tuple[Cat, CatRating]] | None = None,
    no_longer_listed: list[tuple[Cat, CatRating]] | None = None,
) -> str:
    still_known = still_known or []
    no_longer_listed = no_longer_listed or []
```
A new `had_prior_state: bool = False` follows this exact convention (booleans default to `False`, named explicitly — per `CLAUDE.md` "Function Design").

b) **Infer** from `scope_note`. The values written at `catfinder.py:739, 743` are `" · alle bewertet"`, `" · Erstlauf"`, or `""`. "Erstlauf" implies empty prior state. This avoids signature growth but couples rendering to a string sentinel.

**Planner recommendation:** Option (a) — explicit parameter is more honest and matches the existing "explicit boolean flag" convention (`no_browser: bool = False` at `catfinder.py:690`).

**Computing `had_prior_state`** in `main()`. The analog is the existing branch at `catfinder.py:736`:
```python
if args.all or not state:
    to_evaluate = cats
    still_known: list[Cat] = []
    scope_note = " · alle bewertet" if args.all else " · Erstlauf"
```
The `not state` test is exactly the negative of `had_prior_state`. So `had_prior_state = bool(state)` computed immediately after `state = load_state()` (`catfinder.py:733`) — captured **before any mutation** — is the cleanest spot.

---

### 3. State-Update Block + Purge Integration (orchestration, CRUD)

**Where it lands:** `catfinder.py:842-856` — the existing `# State: alle aktuell gelisteten Katzen eintragen, Bewertungen speichern.` block. The purge (D-02) hooks in immediately before `save_state(state)` at line 856. Also affects the early-return path at `catfinder.py:783-792` (the "no new cats" branch) — that branch *also* calls a render but does **not** currently save state. Per REPORT-02, the purge must happen on every run, including the early-return branch, so the no-new-cats path now needs a `save_state(state)` after the purge too.

**Analog (existing state-update block, `catfinder.py:842-856`)**:
```python
# State: alle aktuell gelisteten Katzen eintragen, Bewertungen speichern.
now_iso = datetime.now().isoformat(timespec="seconds")
for cat in cats:
    if cat.cat_id not in state:
        entry = asdict(cat)
        entry["first_seen"] = now_iso
        state[cat.cat_id] = entry
for cat in to_evaluate:
    if cat.cat_id in ratings:
        state[cat.cat_id]["rating"] = ratings[cat.cat_id].rating
        state[cat.cat_id]["reason"] = ratings[cat.cat_id].reason
        state[cat.cat_id]["has_interested"] = cat.has_interested
        state[cat.cat_id]["companion_count"] = cat.companion_count
        state[cat.cat_id]["partner_name"] = cat.partner_name
save_state(state)
print(f"State aktualisiert: {len(state)} Katzen bekannt.")
```

**Pattern to copy:**
- **Comment style:** German one-line `# Section header...` comment above the mutation block (line 842). Add a similar comment for the purge step, e.g. `# Purge: nur Katzen aus dem aktuellen Listing bleiben im State.`
- **Order matters:** Insert/update entries **first**, then purge entries no longer in `current_ids`, then `save_state`. This preserves entries for cats currently listed (which is the whole point) and removes Zombies.
- **Idempotency:** The whole block is idempotent on a given `(cats, ratings)` input — the purge addition keeps that property.
- **Final log** at line 857 (`print(f"State aktualisiert: {len(state)} Katzen bekannt.")`) reflects post-purge state count automatically — no change needed.

**Early-return branch fix (`catfinder.py:783-792`):**
```python
if not to_evaluate:
    print("Keine neuen Katzen seit dem letzten Lauf.")
    la = {c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c in still_known}
    la.update({c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c, _ in no_longer_listed})
    html_text = render_report([], len(cats), listing_ages=la,
                              still_known=_ratings_from_state(still_known),
                              no_longer_listed=no_longer_listed)
    write_and_open_report(html_text, no_browser=args.no_browser)
    _write_github_output(0)
    return 0
```
Today this branch never calls `save_state`. With the purge requirement, **even this branch must purge + save** before returning — otherwise Zombies persist when no new cats arrive. Pattern to add (mirror lines 856-857):
- Call the purge.
- Call `save_state(state)`.
- Optionally log `f"State aktualisiert: {len(state)} Katzen bekannt."`.

This is the most subtle correctness point in the phase — flag it clearly in the plan.

---

### 4. Empty-State Section Rendering (view / template, transform)

**Where it lands:** `render_report` `sect_gone` block at `catfinder.py:634-655`. Today the section is **only** emitted if `no_longer_listed` is truthy (line 636). After the change, three branches exist:

| Condition | Render |
|-----------|--------|
| `no_longer_listed` non-empty | Existing card grid (lines 637-655) — unchanged |
| `no_longer_listed` empty AND `had_prior_state` is True | Empty-state hint section (NEW) |
| `no_longer_listed` empty AND `had_prior_state` is False | Section omitted entirely (`sect_gone = ""`) — current behavior |

**Analog A — Empty-state pattern from sibling section (`catfinder.py:603-605`):**
```python
# Sektion 1 — neue Katzen
if not evaluated_sorted:
    sect1_inner = '<div class="empty">Keine neuen Katzen seit dem letzten Lauf. 🎉</div>'
```
This is the **exact** pattern to mirror per CONTEXT.md D-06: `<div class="empty">…</div>`, German text, sparkles emoji at the end. CSS for `.empty` already exists at `catfinder.py:521`:
```css
.empty { text-align: center; color: #666; padding: 4rem 1rem; }
```
**Do not add new CSS.** The `.empty` class is already in `HTML_TEMPLATE`.

**Analog B — Section wrapper from existing `sect_gone` (`catfinder.py:655`):**
```python
sect_gone = f'<section><h2 class="group">🚫 Nicht mehr verfügbar ({len(no_longer_listed)})</h2><div class="grid">{"".join(cards)}</div></section>'
```
Pattern to copy for the new empty-state branch (per CONTEXT.md D-05 wording + `<specifics>` count-suffix `(0)`):
```python
sect_gone = (
    '<section><h2 class="group">🚫 Nicht mehr verfügbar (0)</h2>'
    '<div class="empty">Seit dem letzten Lauf sind keine Katzen verschwunden. ✨</div>'
    '</section>'
)
```
- Same `<section>` / `<h2 class="group">` wrapper as the populated branch — keeps visual rhythm consistent with sibling sections (`sect1` lines 630-632, `sect2` line 678).
- `(0)` count suffix matches `({len(...)})` style at lines 630, 655, 678.
- The trailing sparkle `✨` matches the cheerful tone of the sibling empty-state at line 605 (`🎉`) — different emoji, same semantic register.

**Analog C — Conditional dispatch shape from existing branch at `catfinder.py:629-632`:**
```python
if two_sections:
    sect1 = f'<section><h2 class="group">✨ Neu seit letztem Lauf ({len(evaluated_sorted)})</h2>{sect1_inner}</section>'
else:
    sect1 = f'<section>{sect1_inner}</section>'
```
This shows the "build inner first, wrap conditionally" idiom. Pattern for the rewritten zombie block (after planner refactor):
```python
# Sektion 2 — nicht mehr verfügbare Katzen
sect_gone = ""
if no_longer_listed:
    # … existing card-rendering loop unchanged …
    sect_gone = f'<section><h2 class="group">🚫 Nicht mehr verfügbar ({len(no_longer_listed)})</h2><div class="grid">{"".join(cards)}</div></section>'
elif had_prior_state:
    sect_gone = (
        '<section><h2 class="group">🚫 Nicht mehr verfügbar (0)</h2>'
        '<div class="empty">Seit dem letzten Lauf sind keine Katzen verschwunden. ✨</div>'
        '</section>'
    )
# else: leave sect_gone = "" (Erstlauf / Cold-Start: section completely hidden)
```

**Sort key reuse (already correct, no change):** Line 638 uses `sorted(no_longer_listed, key=_card_sort_key)` — the existing `_card_sort_key` from `catfinder.py:484-491` stays the canonical ordering for the populated branch (per CONTEXT.md `<decisions>` "Sortierung in der Sektion bleibt `_card_sort_key`").

**Visual treatment of populated cards stays unchanged** (`catfinder.py:643-654`): `opacity: .6;` on the card and grey button background `style="background:#9e9e9e;"` — explicitly kept per CONTEXT.md `<decisions>` last bullet.

---

## Shared Patterns

### German user-facing strings
**Source:** Throughout `catfinder.py` — all log lines, HTML text, section titles in German.
**Apply to:** Every new string in this phase.
**Examples to mirror:**
- `f"Warnung: State-Datei konnte nicht gelesen werden ({e}). Starte frisch."` (`catfinder.py:132`) — `Warnung:` prefix for non-fatal recovery.
- `f"State aktualisiert: {len(state)} Katzen bekannt."` (`catfinder.py:857`) — top-level status, no prefix.
- `'<div class="empty">Keine neuen Katzen seit dem letzten Lauf. 🎉</div>'` (`catfinder.py:605`) — empty-state idiom.
- New string per CONTEXT.md D-05: `"Seit dem letzten Lauf sind keine Katzen verschwunden. ✨"`

### Atomic file writes (already present, don't break)
**Source:** `catfinder.py:136-147` (`save_state`).
**Apply to:** Any code path that triggers a state write — including the new "no new cats" early-return branch, which now needs `save_state(state)` after the purge. Do **not** add a second write path; route everything through `save_state`.

### Defensive `.get(..., default)` for state reads
**Source:** `catfinder.py:745-756` (`_ratings_from_state`) and `catfinder.py:761-778` (zombie rebuild).
**Apply to:** Any code that pulls fields out of `state[cid]`. Use `entry.get("field", default)` so partially-populated state entries (e.g. legacy Zombies on first purge run) don't crash the report. Especially relevant for the **Big-Bang first run** (D-04): old state may pre-date some fields.

### Type hints (PEP 604, builtin generics)
**Source:** Throughout — e.g. `dict[str, dict]` (`catfinder.py:126`), `set[str]` implicit at `catfinder.py:734, 759`, `int | None` (`catfinder.py:552`).
**Apply to:** Any new helper or signature change. Use `set[str]` not `Set[str]`, `bool` defaults explicit (`had_prior_state: bool = False`).

### Section banners for code organization
**Source:** `# --- State ---` (line 122-124), `# --- Main ---` (line 698-700) — see also `_card_sort_key`'s placement in `# --- HTML-Report ---` (line 494-496).
**Apply to:** If the planner extracts a new helper (e.g. `purge_disappeared`), it goes in the `# --- State ---` section (i.e. between `save_state` at line 147 and the next `# ---` banner at line 150). If logic stays inline in `main()`, no new banner needed.

---

## No Analog Found

None. Every edit region has a strong in-file analog. Single-file project, contained scope.

---

## Metadata

**Analog search scope:** `catfinder.py` (the only source file in the repo). Planning artifacts at `.planning/` reviewed for constraints, not code.
**Files scanned:** 1 (`catfinder.py`, 863 lines).
**Pattern extraction date:** 2026-05-05.
