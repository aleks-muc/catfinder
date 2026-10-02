# Phase 2: Filter-Reset-Button - Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 1 (modified) / 0 (created)
**Analogs found:** 5 / 5 (all in-file — single-file architecture)

## Scope Note

This phase modifies a single function (`_build_filter_bar` in `catfinder.py:297-393`) and creates no new files. All required patterns live in the same function — the new button HTML, CSS, JS state, and click handler are direct extensions of existing siblings within the same f-string. PATTERNS.md is therefore intentionally focused on intra-function analogs.

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `catfinder.py` (`_build_filter_bar`, lines 297-393) | report renderer (HTML/CSS/JS via f-string) | event-driven (DOM click → state mutation → `update()`) | Existing toggle-button handlers in same IIFE (`pairBtn`/`fitBtn`/`sorgBtn`, lines 371-388) | exact |

## Pattern Assignments

### `catfinder.py` — `_build_filter_bar` extension (4 sub-edits)

All four sub-edits target one function. Each has a precise in-file analog.

---

#### Sub-edit 1: Inject Python defaults into JS via f-string

**Need:** Make `default_lo` / `default_hi` (already computed at lines 306-307) visible to the JS reset handler as `DEFAULT_LO` / `DEFAULT_HI`.

**Analog:** existing IIFE header that injects `age_min` / `age_max` into JS at `catfinder.py:346`.

```python
  var LO={age_min},HI={age_max},showSorg=false,showOnlyFit=true,showOnlyPair=true;
```

**Pattern to copy:** comma-separated `var` declaration on a single line, Python f-string interpolation of integer values via `{name}`. Variable name `UPPER_SNAKE_CASE` for "constants" injected from Python (matches `LO` / `HI`).

**Adapted form (planner reference, do not implement here):**

```python
  var LO={age_min},HI={age_max},DEFAULT_LO={default_lo},DEFAULT_HI={default_hi},showSorg=false,showOnlyFit=true,showOnlyPair=true;
```

Place on the same line as the existing `var LO=...` to keep the IIFE header compact (matches existing one-line state-declaration style).

---

#### Sub-edit 2: Append reset-button HTML to `#filterBar`

**Need:** Add `<button id="resetBtn">↺ Filter zurücksetzen</button>` after the existing three toggle buttons.

**Analog:** the three sibling buttons at `catfinder.py:336-338`.

```python
<div id="filterBar" style="position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid #e0e0e0;padding:.9rem 1rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;">{slider}
  <button id="fitBtn" class="active">🟢 Nur geeignet</button>
  <button id="pairBtn" class="active">🐱🐱 Nur Pärchen (aktiv)</button>
  <button id="sorgBtn" class="hidden">🔴 Sorgenkinder einblenden</button>
</div>
```

**Pattern to copy:**
- Two-space indent, single `<button>` tag per line.
- ID convention: lowercase camelCase suffixed with `Btn` (`#fitBtn`/`#pairBtn`/`#sorgBtn` → `#resetBtn`).
- Emoji-prefixed German label inside the tag.
- No `class` attribute (button is stateless — no active/hidden toggling), unlike the three siblings which carry an initial CSS class.
- Inline `style="margin-left:auto"` on the new button to push it to the right end of the flex row (per CONTEXT.md D-01). This is the only inline style; all other visual rules go in the `<style>` block (sub-edit 3).

---

#### Sub-edit 3: Add `#resetBtn` CSS rule

**Need:** Link-style appearance (transparent, no border, hover accent in `#1976d2`) per CONTEXT.md D-02.

**Analog:** the existing button rules in the same `<style>` block at `catfinder.py:330-333`.

```python
#sorgBtn,#fitBtn,#pairBtn{{padding:.4rem .85rem;border-radius:6px;border:1px solid #ddd;background:#f5f5f5;font-size:.85rem;cursor:pointer;white-space:nowrap;transition:background .15s,border-color .15s;}}
#sorgBtn.hidden{{background:#ffebee;border-color:#ef9a9a;color:#c62828;}}
#fitBtn.active{{background:#e8f5e9;border-color:#a5d6a7;color:#2e7d32;}}
#pairBtn.active{{background:#e3f2fd;border-color:#90caf9;color:#1565c0;}}
```

**Pattern to copy:**
- Single-line CSS rule per selector, semicolons between properties, no whitespace.
- F-string requires doubled braces `{{ }}` around the rule body (already used throughout the block).
- Existing accent color `#1976d2` (used on slider thumb at line 328 and `ageLabel` at line 315) is the natural hover color — reuse, do not introduce a new palette entry.

**Adapted form (planner reference):**

```css
#resetBtn{{background:transparent;border:none;padding:.4rem .25rem;color:#666;cursor:pointer;font-size:.85rem;}}
#resetBtn:hover{{color:#1976d2;}}
```

Insert immediately after the three existing button rules (line 333), before `</style>`.

---

#### Sub-edit 4: Append reset click-handler to IIFE

**Need:** On click, reset all four control groups and call `update()` exactly once.

**Analog:** the three sibling click handlers at `catfinder.py:371-388`. The most structurally complete is `sorgBtn` (covers state + label + class):

```python
  pairBtn.addEventListener('click',function(){{
    showOnlyPair=!showOnlyPair;
    pairBtn.textContent=showOnlyPair?'🐱🐱 Nur Pärchen (aktiv)':'🐱🐱 Nur Pärchen';
    pairBtn.classList.toggle('active',showOnlyPair);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  fitBtn.addEventListener('click',function(){{
    showOnlyFit=!showOnlyFit;
    fitBtn.textContent=showOnlyFit?'🟢 Nur geeignet':'🟢 Alle Bewertungen';
    fitBtn.classList.toggle('active',showOnlyFit);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  sorgBtn.addEventListener('click',function(){{
    showSorg=!showSorg;
    sorgBtn.textContent=showSorg?'🔴 Sorgenkinder ausblenden':'🔴 Sorgenkinder einblenden';
    sorgBtn.classList.toggle('hidden',!showSorg);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
```

**Patterns to copy:**

1. **`addEventListener('click', function(){{ ... }})`** — anonymous function, doubled braces for f-string. Trailing `}});` to close.
2. **State mutation first**, then **DOM updates** (label + class), then **filter/render call last**. The reset handler keeps this ordering: assign all four state vars + slider values → reassign all four button labels + classes → call `update()` once.
3. **Slider null-check pattern** (`minR?parseInt(minR.value):LO`) appears in every existing handler at lines 375, 381, 387. The reset handler must use `if(minR)minR.value=DEFAULT_LO;` and `if(maxR)maxR.value=DEFAULT_HI;` to tolerate the single-input edge case (lines 310-322 only emit `<input>` elements when `age_min < age_max`; otherwise `minR`/`maxR` are `null`).
4. **`classList.toggle(name, bool)`** is the existing pattern when the boolean is dynamic (lines 374, 380, 386). For the reset handler the desired class state is **fixed** (always-active for fit/pair, always-hidden for sorg), so the planner should prefer **`classList.add(name)`** over `toggle(name, true)` — both work, but `add` makes intent ("force the default") explicit and matches CONTEXT.md "Known Pitfalls" guidance (avoid invert-on-second-click bugs).
5. **Re-render call:** existing handlers call `filter(lo, hi)` directly with re-parsed slider values. The reset handler should call **`update()` instead** (defined at lines 349-355). `update()` already re-parses sliders, repositions `#sliderFill`, refreshes `#ageLabel`, and then calls `filter(lo, hi)` — exactly the post-reset state we need with one call. Calling `filter()` directly would skip the slider-fill/label refresh.
6. **Default-label strings** for fit/pair/sorg must match the initial `<button>` text (lines 336-338): `'🟢 Nur geeignet'`, `'🐱🐱 Nur Pärchen (aktiv)'`, `'🔴 Sorgenkinder einblenden'`. These are the same strings the existing handlers produce on the "active/default" branch of their ternaries (lines 373, 379, 385) — copy them verbatim to keep one source of truth per label.

**Placement:** append the new `resetBtn.addEventListener('click', ...)` block after the `sorgBtn` handler (after line 388) and before the slider input listeners (line 389). Also add `resetBtn=document.getElementById('resetBtn')` to the existing `var ... = document.getElementById(...)` declaration block (lines 342-345), continuing the comma-separated declaration style.

---

## Shared Patterns

Single-file project — "shared" patterns are reused conventions inside the same f-string.

### F-String Brace Escaping
**Source:** entire `_build_filter_bar` body, especially `catfinder.py:325-388`.
**Apply to:** every CSS rule body and every JS function body added.
**Rule:** literal `{` and `}` in the emitted CSS/JS must be written `{{` and `}}`. Python interpolation uses single `{name}`.

### IIFE State-Variable Style
**Source:** `catfinder.py:342-346`.
**Apply to:** the new `DEFAULT_LO`/`DEFAULT_HI` injections and the new `resetBtn` DOM ref.
```python
  var minR=document.getElementById('ageMin'),maxR=document.getElementById('ageMax'),
      fill=document.getElementById('sliderFill'),lbl=document.getElementById('ageLabel'),
      sorgBtn=document.getElementById('sorgBtn'),fitBtn=document.getElementById('fitBtn'),
      pairBtn=document.getElementById('pairBtn');
  var LO={age_min},HI={age_max},showSorg=false,showOnlyFit=true,showOnlyPair=true;
```
- DOM refs: one chained `var` declaration with two-space indent on continuation lines.
- Constants and toggle state: a separate one-line `var` declaration. Append `DEFAULT_LO`/`DEFAULT_HI` here (not on a new `var` line).

### Slider Null-Tolerance
**Source:** `catfinder.py:375, 381, 387` (`minR?parseInt(minR.value):LO`) and `catfinder.py:350, 389-390` (`if(minR)...`).
**Apply to:** any new code that touches `minR` or `maxR`.
**Rule:** never assume `minR`/`maxR` exist. The slider HTML at lines 310-322 is conditional on `age_min < age_max`, so on degenerate listings these elements are absent. Use `if(minR)minR.value=DEFAULT_LO;` for assignment.

### German User-Facing Strings
**Source:** all existing button labels (lines 336-338, 373, 379, 385).
**Apply to:** the new button label `↺ Filter zurücksetzen`.
**Rule:** all UI text remains German per `CLAUDE.md` §Code Style. Icon-prefixed labels match the surrounding convention (🟢 / 🐱🐱 / 🔴 / ↺).

## No Analog Found

None. Every new construct (button HTML, CSS rule, JS state injection, click handler) has a direct sibling pattern in the same function. No need to fall back to RESEARCH.md general patterns.

## Metadata

**Analog search scope:** `catfinder.py:297-393` (`_build_filter_bar` only — single-file project, all relevant patterns colocated).
**Files scanned:** 1 (`catfinder.py`) plus context (`02-CONTEXT.md`).
**Pattern extraction date:** 2026-05-06
