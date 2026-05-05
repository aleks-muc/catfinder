# Catfinder

## What This Is

Catfinder ist eine private CLI-Pipeline, die zweimal täglich das Listing des Tierschutzvereins München scrapt, neue Katzen mit Claude gegen ein Familien-Eignungsprofil bewertet und einen filterbaren HTML-Report per E-Mail (SendGrid) und GitHub Pages ausliefert. Zielnutzer ist eine einzelne Familie auf Katzensuche, die nicht ständig manuell nachschauen möchte.

## Core Value

Sobald eine geeignete Katze neu auf der Seite auftaucht, weiß die Familie es ohne manuelles Nachsehen — der Report muss zuverlässig laufen und den Unterschied zwischen "neu", "weiter verfügbar" und "verschwunden" sauber kommunizieren.

## Requirements

### Validated

<!-- Existing capabilities of the shipped pipeline (see .planning/codebase/ARCHITECTURE.md) -->

- ✓ **EXIST-01**: Listing-Scrape von `tierschutzverein-muenchen.de` mit Aufbau eines `Cat`-Datenmodells — existing
- ✓ **EXIST-02**: Profil-Enrichment je Katze (Interessenten-Marker, Partner-Namen, Altersangabe) — existing
- ✓ **EXIST-03**: Claude-Bewertung (Haiku 4.5) mit 4-stufiger Rating-Taxonomie und strukturiertem Pydantic-Output — existing
- ✓ **EXIST-04**: Diff-basierte Auswertung — nur unbekannte `cat_id`s werden an die API gesendet, bekannte Bewertungen kommen aus dem State — existing
- ✓ **EXIST-05**: Atomarer State-Write nach `state/seen_cats.json` (`tempfile` + `os.replace`) — existing
- ✓ **EXIST-06**: HTML-Report mit eingebetteter Filterleiste (Bewertung, Slider für Alter, Toggles für Pärchen/Interessenten) — existing
- ✓ **EXIST-07**: Sektionen "Neu", "Weiterhin verfügbar", "Nicht mehr verfügbar" im Report — existing
- ✓ **EXIST-08**: Zweimal-täglicher CI-Lauf (07:00 + 14:00 UTC) mit GitHub-Pages-Publish und SendGrid-Mail — existing
- ✓ **EXIST-09**: Robustes Error-Handling — Single-Cat-Fehler degradieren zu `unbekannt`, RateLimit-Backoff `[10, 30, 60]`s — existing

### Active

<!-- Current milestone scope. -->

- [x] **REPORT-DELTA**: "Nicht mehr verfügbar"-Sektion zeigt nur Katzen, die *seit dem letzten Lauf* verschwunden sind (Delta-Modus statt Vollhistorie) — validated in Phase 1 (REPORT-01)
- [x] **REPORT-DELTA-PURGE**: Katzen, die in früheren Läufen verschwunden sind, werden komplett aus `state/seen_cats.json` entfernt — keine Zombie-Einträge — validated in Phase 1 (REPORT-02)
- [x] **REPORT-DELTA-EMPTY**: Wenn beim aktuellen Lauf keine Katze verschwunden ist, zeigt die Sektion einen Hinweis ("Seit dem letzten Lauf sind keine Katzen verschwunden") statt zu fehlen oder leer zu wirken — validated in Phase 1 (REPORT-03)
- [ ] **FILTER-RESET**: Button "Filter zurücksetzen" in der Filterleiste, der mit einem Klick alle aktiven Filter (Bewertungs-Buttons, Alters-Slider, Toggle-Buttons) auf den Default zurücksetzt

### Out of Scope

<!-- Explicit non-goals. -->

- Modularisierung von `catfinder.py` (Aufsplittung in Package) — bewusst aufgeschoben, single-file ist für die Größe noch tragbar; siehe `.planning/codebase/ARCHITECTURE.md#Anti-Patterns`
- Test-Infrastruktur (pytest etc.) — kein Bestandteil dieses Milestones
- Neue Scraping-Quellen (andere Tierheime) — fokussiert auf den Münchner Tierschutzverein
- Änderungen an der Rating-Taxonomie oder am System-Prompt — Modell und Bewertungsschema bleiben stabil
- Persistente Filter-Auswahl über Reloads hinweg — Filter sind weiter session-lokal im Browser
- Migration der State-Datei oder Backwards-Compatibility-Wrapper für alte Einträge — die Purge-Änderung darf bestehende "Zombie"-Einträge beim ersten Lauf einfach entfernen

## Context

- **Bestehender Code:** Single-file `catfinder.py` (~865 Zeilen), Python 3.9+ lokal / 3.12 in CI, keine Tests, keine Linter-Config (siehe `.planning/codebase/STACK.md`).
- **Report-Pipeline:** Filterleiste und Report-Shell sind als f-string-eingebettetes HTML/CSS/JS in `_build_filter_bar` (`catfinder.py:297`) und `HTML_TEMPLATE` (`catfinder.py:498`) realisiert — Anpassungen am Filter-UI sind Python-Edits, kein separates Frontend-Build.
- **State-Modell:** Heute wandern alle je gesehenen Katzen in `seen_cats.json` und bleiben dort; "Nicht mehr verfügbar" leitet sich aktuell aus `known_ids - current_ids` über die gesamte Historie ab. Die Delta-Anforderung verändert diese State-Semantik: ein zusätzliches "Was war im *vorigen* Lauf gelistet?" muss persistiert werden, oder verschwundene Einträge werden direkt entfernt nachdem sie einmal im Delta-Report aufgetaucht sind.
- **CI-Schreibrechte:** Der Workflow committet `state/seen_cats.json` und `docs/index.html` zurück nach `main` (`contents: write`). Änderungen an State-Schema oder Reportstruktur müssen in beiden Pfaden — lokal und in CI — funktionieren.
- **Privater Use-Case:** Kein Multi-User, keine öffentliche API. Akzeptabel: Migrationen ohne Versionierung, Zustandsverlust ist rückholbar (`--reset` re-evaluiert alles).

## Constraints

- **Tech stack**: Bleibt bei Python 3.9+ Single-File, `requests` + `bs4` + `anthropic` + `pydantic`. Keine neuen Runtime-Dependencies für diesen Milestone.
- **Filter-UI**: Muss in der bestehenden `_build_filter_bar`-Logik (inline CSS/JS in Python f-string) bleiben — kein React/Vue/Build-Step.
- **State-Format**: JSON in `state/seen_cats.json`. Änderungen am Format dürfen vorhandene gültige Einträge nicht zerstören (lediglich verschwundene Einträge dürfen wegfallen).
- **CI-Verhalten**: Nach dem Milestone muss der Bot-Commit (`chore: state & report aktualisiert`) weiterhin gleich aussehen (gleiche Pfade, gleiche Permissions); E-Mail-Subject und Pages-URL bleiben unverändert.
- **Performance**: Nicht relevant — Listing < 100 Katzen, Reportrender < 1 s, kein Skalierungsdruck.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| "Nicht mehr verfügbar" wird zu Delta-only-Sektion | Vollhistorie wuchs unbegrenzt und war im Report nicht informativ — relevant ist "wer ist *gerade jetzt* weg, den ich kenne?" | — Pending |
| Verschwundene Einträge werden komplett aus dem State entfernt (kein Zeitfenster, kein Soft-Delete) | Einfachster Mechanismus, passt zum privaten Use-Case (kein Reporting / keine Statistik nötig); Wieder-Auftauchen wird neu bewertet — akzeptabel | — Pending |
| "Filter zurücksetzen" sitzt zentral in der Filterleiste und resettet alle Filter zugleich | Schnellster Pfad zurück zur Übersicht; pro-Kategorie-Resets wären UI-Overkill für so wenige Filter | — Pending |
| Single-file `catfinder.py` bleibt unangetastet (keine Modularisierung in diesem Milestone) | Scope-Schutz — Änderungen sind klein und lokal, Refactor wäre Selbstzweck | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-06 after Phase 1 completion (Delta-Report + State-Purge live)*
