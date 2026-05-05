# Phase 2: Filter-Reset-Button - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Ein einzelner „Filter zurücksetzen"-Button in der bestehenden Filterleiste (`catfinder.py:_build_filter_bar`, Zeilen 297-393) setzt mit einem Klick alle vier Filter-Controls atomar auf ihren Default zurück:

1. Alters-Slider (`#ageMin`, `#ageMax`) → `default_lo` / `default_hi` (datenbasiert geclampt, `catfinder.py:306-307`)
2. „Nur geeignet"-Toggle (`#fitBtn`) → `showOnlyFit = true` (active)
3. „Nur Pärchen"-Toggle (`#pairBtn`) → `showOnlyPair = true` (active)
4. „Sorgenkinder einblenden"-Toggle (`#sorgBtn`) → `showSorg = false` (hidden)

Reines Frontend: HTML-Button + IIFE-Click-Handler im bestehenden inline-`<script>`-Block. Kein Server-State, keine Persistenz, kein Reload, keine neue Datei, keine neue Dependency. Karten werden via `update()` → `filter()` (existierende Funktionen, `catfinder.py:349-370`) sofort neu gerendert.

</domain>

<decisions>
## Implementation Decisions

### Position & Layout

- **D-01:** Reset-Button sitzt **ganz rechts** in der `#filterBar`-Flex-Row, vom Filter-Cluster visuell abgesetzt durch `margin-left: auto`. Nimmt das mentale Modell ernst: Reset ist eine Meta-Aktion, nicht ein weiterer Filter. Bestehender `flex-wrap: wrap`-Layout wird respektiert — bei schmaler Viewport-Breite wrappt der Button auf eine eigene Zeile, das ist akzeptabel.

### Visuelle Sprache

- **D-02:** **Dezenter Link-Stil**, nicht Button-Stil. Konkret: `background: transparent; border: none; padding: .4rem .25rem; color: #666; cursor: pointer; font-size: .85rem;` plus Hover-Akzent `color: #1976d2` (existierende Slider-Akzentfarbe). Mit Icon-Präfix `↺ Filter zurücksetzen`. Liest sich als Meta-Aktion und macht keinen visuellen Lärm neben den drei farbig-hervorgehobenen Toggle-Buttons.

### Sichtbarkeit

- **D-03:** **Immer sichtbar, immer klickbar.** Kein Disabled-State, kein dynamisches Hide. Klick im bereits-Default-Zustand ist No-Op (alle vier Reset-Operationen sind idempotent — `update()` rendert dieselben Karten). Spart eine `isAnyFilterActive()`-Heuristik im JS und hält das Layout der Sticky-Bar stabil (kein Springen).

### Reset-Verhalten & Feedback

- **D-04:** **Stilles Reset.** Keine Animation, kein Toast, kein Button-Flash. Die unmittelbare sichtbare Änderung (Slider-Thumbs springen, Button-Texte/Klassen wechseln, Karten erscheinen) ist Feedback genug. Minimaler JS-Code, keine `setTimeout`-State-Machine.

- **D-05:** **Kein Tastatur-Shortcut** (kein Esc-Handler). Reset läuft ausschließlich über den Button-Klick. Vermeidet Konflikte mit Browser-Defaults und Slider-Tastatur-Bedienung. Nachrüstbar falls später gewünscht.

### Reset-Definition (implizit aus existierenden Defaults)

- **D-06:** Reset bedeutet: identische Werte wie beim ersten Render der Seite. Die Defaults stehen bereits an zwei Stellen im Code:
  - **JS-Variablen** (catfinder.py:346): `showSorg=false`, `showOnlyFit=true`, `showOnlyPair=true`.
  - **Slider-Defaults** (catfinder.py:306-307): `default_lo = max(age_min, min(DEFAULT_AGE_LO, age_max))`, `default_hi = min(age_max, max(DEFAULT_AGE_HI, age_min))`. **Diese müssen via Python-f-string ins JS injiziert werden** (z.B. als `var DEFAULT_LO={default_lo}, DEFAULT_HI={default_hi};`), damit der Reset-Handler sie zur Laufzeit kennt — sie sind bisher nur clientseitig in den `value`-Attributen der `<input type="range">` Elemente sichtbar.

- **D-07:** **Atomarität via einzelner `filter()`-Call:** Der Reset-Handler setzt zuerst alle JS-State-Variablen + Slider-Werte + Button-Texte/CSS-Klassen, ruft dann **genau einen** `update()` (der intern `filter()` ruft). Keine Sequenz von 4 separaten Klick-Events — vermeidet Zwischen-Renders.

### Claude's Discretion

- Exakte CSS-Werte für Padding/Hover-Transition-Timing.
- ID-Vergabe für den neuen Button (`#resetBtn` ist der naheliegende Name, konsistent mit `#fitBtn`/`#pairBtn`/`#sorgBtn`).
- Reihenfolge der State-Reset-Operationen im Handler (so lange alle vor dem `update()`-Call passieren, ist die Reihenfolge egal).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap

- `.planning/REQUIREMENTS.md` — FILTER-01 (Button sichtbar in Filterleiste), FILTER-02 (Klick setzt alle Controls atomar zurück, sofortiges Re-Render).
- `.planning/ROADMAP.md` §Phase 2 — Goal + 4 Success Criteria (Button sichtbar/integriert, atomar, sofortiges Re-Render, kein Server-State).
- `.planning/PROJECT.md` §Active Requirements — `FILTER-RESET` als Active.

### Code-Anchors (modification target)

- `catfinder.py:297-393` — komplette `_build_filter_bar`-Funktion. Die einzige Stelle, an der HTML/CSS/JS für die Filterleiste lebt.
- `catfinder.py:335-339` — `#filterBar`-Div mit den drei bestehenden Toggle-Buttons. Hier sitzt der neue Reset-Button (mit `margin-left:auto`).
- `catfinder.py:340-393` — IIFE mit Event-Handlern. Hier kommt der Reset-Click-Handler dazu.
- `catfinder.py:346` — JS-Defaults (`showSorg=false`, `showOnlyFit=true`, `showOnlyPair=true`). Reset-Werte für die Toggle-Variablen.
- `catfinder.py:306-307` — Python-Defaults für Slider-Range. Müssen ins JS gespiegelt werden, damit der Reset-Handler sie kennt.
- `catfinder.py:349-370` — `update()` und `filter()`. Der Reset-Handler ruft `update()` (single Re-Render).

### Constraints

- `CLAUDE.md` §Project, §Constraints, §Code Style — Single-File, keine neuen Deps, kein Build-Step, deutsche User-Strings, snake_case Python, inline CSS/JS in f-string.
- `.planning/phases/01-delta-basiertes-nicht-mehr-verf-gbar/01-CONTEXT.md` — Beispiel-Konvention für „kleine Änderung im inline f-string ohne Architektur-Bruch" (kürzlich abgeschlossen).
- `.planning/codebase/ARCHITECTURE.md` — Single-File-Architektur, Anti-Pattern-Liste (inline HTML/CSS/JS als f-string ist explizit dokumentiert und akzeptiert).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`update()` und `filter()` in der IIFE** (`catfinder.py:349-370`): bereits idempotent, lesen aktuelle State-Variablen + Slider-Werte und rendern Karten neu. Der Reset-Handler muss nur State setzen und einmal `update()` rufen.
- **Bestehende `addEventListener`-Pattern** für `pairBtn`/`fitBtn`/`sorgBtn` (catfinder.py:371-388): die exakte Struktur (State-Toggle → Text/Klassen-Update → `filter(...)`-Call) wird für den Reset-Handler abgewandelt zu (alle State setzen → alle Texte/Klassen → einmal `update()`).
- **`.cf-fill` und `#sliderFill`-Mechanik**: Wenn `ageMin.value` und `ageMax.value` per JS gesetzt werden, muss `update()` gerufen werden, um den Fill-Balken neu zu positionieren (das macht die existierende `update()`-Funktion bereits, `catfinder.py:352`).

### Established Patterns

- **Inline HTML/CSS/JS in f-string** mit verdoppelten Braces `{{ }}` für CSS/JS-Literals — bestehend, wird beibehalten.
- **JS-IIFE-Scope** mit `var` (kein `let`/`const`) und kompakter ein-Linien-Funktionssyntax — passt zum Stil.
- **Button-IDs `#xxxBtn`**, Click-Handler im IIFE-Scope, State-Variablen auf IIFE-Ebene.
- **Defaults zentral als Python-Konstanten** (`DEFAULT_AGE_LO=36`, `DEFAULT_AGE_HI=144`, catfinder.py:293-294). Werden bereits per f-string ins JS interpoliert (`{age_min}`, `{age_max}`).

### Integration Points

- **Einziger Modifikations-Punkt:** `_build_filter_bar`-Funktion in `catfinder.py`. Kein anderer Code wird angefasst. `render_report` als Caller bleibt unverändert.
- **Keine Auswirkung auf** State-File, Anthropic-API, Scraper, CI-Workflow, Pages-Output.

### Known Pitfalls (zur Beachtung im Plan)

- **Slider-Default-Spiegelung**: `default_lo` / `default_hi` müssen explizit ins JS injiziert werden — bisher leben sie nur in den `value`-Attributen der `<input>`-Elemente und sind nicht als JS-Variablen verfügbar. Naive Lösung: `var DEFAULT_LO={default_lo}, DEFAULT_HI={default_hi};` im IIFE-Header neben den existierenden `var LO={age_min},HI={age_max},...`.
- **Slider mit nur einem `<input>`** (Edge Case `age_min == age_max`): der `slider`-Block wird in dem Fall nicht gerendert (`catfinder.py:310-322`), `minR`/`maxR` sind dann `null`. Reset-Handler muss das tolerieren (`if(minR)minR.value=...`), wie es die bestehenden Handler auch tun.
- **CSS-Klassen-Reset-Reihenfolge** für `#fitBtn` und `#pairBtn`: beide sind im Default `class="active"`. Der Reset muss `.classList.add('active')` (nicht toggle) verwenden, damit Doppel-Klicks nicht den Default invertieren.
- **`#sorgBtn` im Default**: hat `class="hidden"` (rote Sorgenkinder-Variante). Reset muss `.classList.add('hidden')` rufen.

</code_context>

<specifics>
## Specific Ideas

- Icon-Präfix `↺` (Unicode U+21BA) für den Button-Text — passt zur „Reset"-Semantik und ist konsistent mit der bestehenden Inline-Emoji-Konvention der Filter-Buttons (🟢, 🐱🐱, 🔴, ✨, 🚫).
- Kein Tooltip-Wunsch geäußert — Button-Text ist selbsterklärend.

</specifics>

<deferred>
## Deferred Ideas

Folgende Ideen kamen zur Sprache, gehören aber nicht in Phase 2:

- **Tastatur-Shortcut Esc** — explizit abgelehnt für jetzt; nachrüstbar ohne Architektur-Bruch falls später gewünscht.
- **Toast „Filter zurückgesetzt"** — abgelehnt zugunsten stillem Reset; bei Bedarf eigene Mini-Phase oder Polish-Pass.
- **Button-Flash-Animation** — abgelehnt; gleiche Begründung.
- **Disabled-State wenn alle Filter Default sind** — abgelehnt zugunsten „immer klickbar"; vermeidet `isAnyFilterActive()`-Heuristik.
- **Pro-Kategorie-Reset-Buttons** — bereits in REQUIREMENTS.md `Out of Scope` (UI-Overkill für 4 Controls).
- **Persistente Filter-Auswahl über Reloads** — bereits in REQUIREMENTS.md `Out of Scope` (Filter bleiben session-lokal).

</deferred>

---

*Phase: 2-filter-reset-button*
*Context gathered: 2026-05-06*
