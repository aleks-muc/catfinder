# Roadmap: Catfinder — Delta-Report & Filter-Reset Milestone

**Created:** 2026-05-05
**Granularity:** coarse
**Mode:** yolo
**Parallelization:** enabled
**Coverage:** 5/5 v1 requirements mapped

## Project Reference

**Core Value:** Sobald eine geeignete Katze neu auf der Seite auftaucht, weiß die Familie es ohne manuelles Nachsehen — der Report muss zuverlässig laufen und den Unterschied zwischen "neu", "weiter verfügbar" und "verschwunden" sauber kommunizieren.

**Milestone Goal:** "Nicht mehr verfügbar"-Sektion kommuniziert ehrliches Run-zu-Run-Delta, und ein Klick reicht, um die Filterleiste in den Default-Zustand zurückzusetzen.

## Phases

- [ ] **Phase 1: Delta-basiertes "Nicht mehr verfügbar"** — `seen_cats.json` und Report zeigen nur das Run-zu-Run-Delta verschwundener Katzen, mit Empty-State-Hinweis.
- [ ] **Phase 2: Filter-Reset-Button** — Ein Button in der Filterleiste setzt alle aktiven Filter mit einem Klick auf den Default zurück.

**Parallelization:** Phase 1 und Phase 2 sind unabhängig (verschiedene Code-Regionen, keine Daten-Dependency) und können parallel geplant/ausgeführt werden.

## Phase Details

### Phase 1: Delta-basiertes "Nicht mehr verfügbar"
**Goal:** Der Report zeigt in der "Nicht mehr verfügbar"-Sektion ausschließlich Katzen, die seit dem unmittelbar vorigen Lauf vom Listing verschwunden sind, und der State enthält keine Zombie-Einträge mehr.
**Depends on:** Nothing (first phase, parallel-eligible with Phase 2)
**Requirements:** REPORT-01, REPORT-02, REPORT-03
**Success Criteria** (what must be TRUE):
  1. Nach einem Lauf, in dem genau die Katzen X und Y vom Listing verschwunden sind, listet die "Nicht mehr verfügbar"-Sektion im neu generierten `reports/report.html` (bzw. `docs/index.html` in CI) genau X und Y — keine früher verschwundenen Katzen.
  2. Beim Folgelauf (nichts Neues verschwunden) sind X und Y weder in `state/seen_cats.json` noch in der "Nicht mehr verfügbar"-Sektion zu finden.
  3. Wenn beim aktuellen Lauf keine Katze verschwunden ist, zeigt die "Nicht mehr verfügbar"-Sektion einen klar lesbaren Hinweistext (z.B. "Seit dem letzten Lauf sind keine Katzen verschwunden") — die Sektion ist sichtbar, nicht entfernt, nicht visuell leer.
  4. Ein bestehender Pre-Milestone-State mit "Zombie"-Einträgen (Katzen, die schon vor langer Zeit verschwunden sind) führt beim ersten neuen Lauf nicht zu einem aufgeblähten "Nicht mehr verfügbar" — entweder wird das Delta korrekt gegen den letzten beobachteten Lauf gebildet oder die Zombies werden sauber gepurged.
  5. Der CI-Lauf committet weiterhin nur `state/seen_cats.json` und `docs/index.html` mit der bisherigen Commit-Message; das State-File bleibt valide JSON nach dem Lauf.
**Plans:** 1 plan

Plans:
- [x] 01-01-PLAN.md — Delta-Erfassung, Hard-Purge im Save-Schritt (Haupt-Pfad + no-new-cats Early-Return), had_prior_state-Signal, Empty-State-Branch ("Seit dem letzten Lauf sind keine Katzen verschwunden. ✨"), Sektion bei Erstlauf/--reset komplett ausblenden

### Phase 2: Filter-Reset-Button
**Goal:** Nutzer:innen können mit einem Klick alle aktiven Filter (Bewertungs-Buttons, Alters-Slider, Toggle-Buttons) auf den Default zurücksetzen, ohne die Seite neu zu laden.
**Depends on:** Nothing (parallel-eligible with Phase 1)
**Requirements:** FILTER-01, FILTER-02
**Success Criteria** (what must be TRUE):
  1. In der Filterleiste des generierten Reports ist ein klar beschrifteter Button "Filter zurücksetzen" sichtbar und visuell stimmig in die bestehende Leiste integriert.
  2. Nach beliebigen Filter-Interaktionen (Bewertungs-Button gewählt, Alters-Slider verschoben, Pärchen-/Interessenten-Toggle aktiv) setzt ein Klick auf "Filter zurücksetzen" alle Controls atomar auf den Default zurück.
  3. Unmittelbar nach dem Klick zeigt die Karten-Liste im Report den ungefilterten Zustand — d.h. dieselben Karten wie nach Erstaufruf der Seite, ohne Reload.
  4. Der Button-Klick verändert keinen Server-/State-Zustand — die Filter bleiben weiterhin rein session-lokal im Browser.
**Plans:** TBD
**UI hint:** yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Delta-basiertes "Nicht mehr verfügbar" | 0/0 | Not started | - |
| 2. Filter-Reset-Button | 0/0 | Not started | - |

## Coverage Validation

| REQ-ID | Phase | Status |
|--------|-------|--------|
| REPORT-01 | Phase 1 | Pending |
| REPORT-02 | Phase 1 | Pending |
| REPORT-03 | Phase 1 | Pending |
| FILTER-01 | Phase 2 | Pending |
| FILTER-02 | Phase 2 | Pending |

- v1 requirements: 5 total
- Mapped: 5/5
- Unmapped: 0
- Duplicates: 0

## Notes

- **No upstream UI design contract needed** for Phase 2 — the filter bar lives as inline f-string HTML/CSS/JS in `catfinder.py:297` (`_build_filter_bar`); design decisions happen during planning of that phase.
- **Single-file constraint** stays in force — neither phase touches the modularization decision (out of scope per PROJECT.md).
- **No new runtime dependencies** — both phases are achievable with the existing `requests` + `bs4` + `anthropic` + `pydantic` stack.

---
*Roadmap created: 2026-05-05*
