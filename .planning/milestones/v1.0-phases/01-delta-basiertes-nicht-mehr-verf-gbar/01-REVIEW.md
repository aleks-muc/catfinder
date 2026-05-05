---
phase: 01-delta-basiertes-nicht-mehr-verf-gbar
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - catfinder.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-06
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed the delta-based "Nicht mehr verfügbar" feature plus inline state-purge in `catfinder.py`. The change is small, surgically scoped, and the core logic is sound:

- `had_prior_state` is captured at the right moment (immediately after `load_state()` and before any state mutation).
- Purge runs AFTER `render_report` is called in both paths, so `no_longer_listed` (built from `known_ids - current_ids` BEFORE the purge) renders correctly without being clobbered.
- Purge runs AFTER ratings are written into `state[cat.cat_id]` in the main path; this is safe because purge only deletes IDs not in `current_ids`, and rated cats are by construction in `current_ids`.
- The atomic-write pattern in `save_state` is untouched as promised.
- The new `had_prior_state` parameter is backward-compatible (default `False`).

No critical bugs or security issues were found. Three warnings concern logic edge cases and maintainability hazards (duplicated purge block, `--all` UX inconsistency, unconditional state write on the early-return path). Four info items document minor cleanup opportunities.

## Warnings

### WR-01: Purge logic duplicated verbatim across two execution paths

**File:** `catfinder.py:802-805` and `catfinder.py:874-877`
**Issue:** The purge block

```python
for cid in list(state.keys()):
    if cid not in current_ids:
        del state[cid]
```

is repeated identically in both the early-return path and the main path. This is a classic maintainability hazard: any future change to purge semantics (e.g., grace period, archival, audit logging) must be made in two places. The phase plan explicitly accepts this duplication, but it is still a real risk — drift between the two locations would produce subtly different behavior depending on whether new cats were evaluated this run.

**Fix:** Extract a tiny private helper kept inline in `main()` (no new module surface), e.g.:

```python
def _purge_state(state: dict[str, dict], current_ids: set[str]) -> None:
    """Entfernt Einträge, die nicht mehr im aktuellen Listing stehen (D-02)."""
    for cid in list(state.keys()):
        if cid not in current_ids:
            del state[cid]
```

Defined once near `_ratings_from_state` / `_age_months_with_fallback` and called from both branches. Keeps the single-file constraint, costs ~6 lines, eliminates the drift risk.

### WR-02: `had_prior_state=True` triggers "Nicht mehr verfügbar (0)" empty-state hint on `--all` re-runs

**File:** `catfinder.py:743` (capture) and `catfinder.py:657-663` (render)
**Issue:** When the user runs `python catfinder.py --all` against an existing non-empty state, `had_prior_state` evaluates to `True`. If the listing has no disappearances, the report renders the "🚫 Nicht mehr verfügbar (0) — Seit dem letzten Lauf sind keine Katzen verschwunden. ✨" hint section. But on `--all` the user has explicitly asked for "alle bewertet" (scope_note ` · alle bewertet`), so a delta-empty-state message in that context is conceptually inconsistent — the user did not ask for a delta view.

The same concern applies less acutely to the main "no new cats" early-return path on `--all`: that path is unreachable under `--all` (because `to_evaluate = cats` is always non-empty when scraping succeeds), so this only manifests in the rendered output of the main path with `--all`.

**Fix:** Treat `--all` as semantically equivalent to a fresh-start view for the purposes of the empty-state hint:

```python
# In main(), where scope_note is set:
had_prior_state = bool(state) and not args.all
```

This matches the spirit of `had_prior_state` — "is this a delta-style run?" — and suppresses the hint when the user has opted out of the delta view.

### WR-03: Early-return path now writes state unconditionally — silent behavior change worth verifying against CI commit logic

**File:** `catfinder.py:806-807`
**Issue:** Before this phase, the early-return path (`if not to_evaluate:`) did NOT call `save_state`. Now it always does. In normal operation this is fine because:

1. `json.dumps(..., sort_keys=True, indent=2)` produces deterministic byte output, so an unchanged `state` dict serializes to a byte-identical file → no git diff → no CI commit churn.
2. Atomic-write via `tempfile.mkstemp` + `os.replace` is safe to repeat.

However, two edge cases deserve a sanity check before shipping:

- **CLAUDE.md constraint:** "Nach dem Milestone muss der Bot-Commit (`chore: state & report aktualisiert`) weiterhin gleich aussehen." If the workflow uses `git commit -a` style (it does — see `.github/workflows/catfinder.yml`), an unchanged state file produces no diff and therefore no commit, matching the pre-phase behavior. If the workflow ever switches to `git add state/seen_cats.json && git commit -m ...`, an unchanged file would trigger an empty commit attempt; the existing `if-no-changes-then-skip` guard in the workflow currently protects against that, but the contract is now load-bearing.
- **mtime/inode churn:** `os.replace` swaps the inode every run, even when content is identical. Tools watching inode (rare) would see a touch. Harmless for this project.

**Fix:** No code change required if the existing workflow correctly skips no-op commits. Recommend:
1. A one-time manual verification on the next two CI runs that no spurious "chore: state & report aktualisiert" commits appear when nothing has changed.
2. Optionally short-circuit the write when no purge happened and no ratings changed:

```python
if not to_evaluate:
    print("Keine neuen Katzen seit dem letzten Lauf.")
    # ... render ...
    purged_count = sum(1 for cid in list(state.keys()) if cid not in current_ids)
    for cid in list(state.keys()):
        if cid not in current_ids:
            del state[cid]
    if purged_count > 0:
        save_state(state)
        print(f"State aktualisiert: {len(state)} Katzen bekannt ({purged_count} entfernt).")
    else:
        print(f"State unverändert: {len(state)} Katzen bekannt.")
```

This makes the no-op case observably no-op and removes any future fragility around CI commit semantics.

## Info

### IN-01: Phase ticket IDs leak into the rendered code as comments

**File:** `catfinder.py:658` and `catfinder.py:664` and `catfinder.py:743` and `catfinder.py:802` and `catfinder.py:874`
**Issue:** Comments such as `# D-05/D-06/D-07: voriger State nicht-leer …`, `# D-07: Erstlauf vs. regulärer Lauf …`, `# D-02 …` reference internal planning tickets that are meaningless to anyone reading the source without access to `.planning/`. CLAUDE.md's comment convention is "explain *why*, not *what* — German one-liners".

**Fix:** Drop the `D-0x` prefixes; keep the German rationale:

```python
# voriger State nicht-leer, aber nichts verschwunden — Empty-State-Hint mit bestehendem .empty-Pattern.
```

```python
had_prior_state = bool(state)  # Erstlauf vs. regulärer Lauf — voriger State nicht-leer?
```

```python
# Purge: nur Katzen aus dem aktuellen Listing bleiben im State.
```

### IN-02: `had_prior_state` parameter has no docstring update for `render_report`

**File:** `catfinder.py:548-556`
**Issue:** The new `had_prior_state: bool = False` parameter is undocumented. `render_report` has no docstring at all today, so this matches existing style — but the new parameter has non-obvious semantics ("did the previous run see any cats?") that future maintainers will not infer from the name.

**Fix:** Add a one-line German docstring per the project convention, e.g.:

```python
def render_report(
    ...
    had_prior_state: bool = False,
) -> str:
    """Rendert den HTML-Report. had_prior_state=True zeigt den Empty-State-Hinweis im 'Nicht mehr verfügbar'-Block."""
```

### IN-03: Filter bar omitted when only `no_longer_listed` exists

**File:** `catfinder.py:600`
**Issue:** `filter_bar = _build_filter_bar(...) if (evaluated_sorted or still_known) else ""`. If a run produces zero new cats AND zero still-known (which can happen when `args.all` is False, state is non-empty, and every prior cat has disappeared), the filter bar is hidden but the "🚫 Nicht mehr verfügbar (N)" cards are rendered with full `data-rating` / `data-companions` / `data-age-months` attributes. The user cannot interact with them.

This is pre-existing and not introduced by this phase, but the new "Nicht mehr verfügbar" section makes it more reachable than before. Worth noting for a future polish pass.

**Fix:** Include `no_longer_listed` in the filter-bar visibility check:

```python
filter_bar = _build_filter_bar(age_min, age_max, False) if (evaluated_sorted or still_known or no_longer_listed) else ""
```

### IN-04: Magic Unicode emojis in user-facing strings sit alongside German prose without a glossary

**File:** `catfinder.py:660-662`
**Issue:** "🚫 Nicht mehr verfügbar (0)" and "Seit dem letzten Lauf sind keine Katzen verschwunden. ✨" mix German text and emojis directly in source. This matches the existing pattern in `RATING_META` and the section headers ("✨ Neu seit letztem Lauf", "📋 Weiterhin verfügbar"), so it is consistent.

No fix required — flagging only because the new strings lock in the inline-emoji convention further. If a future internationalization or accessibility pass arrives, all of these strings will need to be touched together.

---

_Reviewed: 2026-05-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
