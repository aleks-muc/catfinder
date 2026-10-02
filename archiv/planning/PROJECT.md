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
- ✓ **REPORT-DELTA**: "Nicht mehr verfügbar"-Sektion zeigt nur Katzen, die seit dem letzten Lauf verschwunden sind (Delta-Modus statt Vollhistorie) — v1.0 (Phase 1, REPORT-01)
- ✓ **REPORT-DELTA-PURGE**: Verschwundene Katzen werden komplett aus `state/seen_cats.json` entfernt — keine Zombie-Einträge — v1.0 (Phase 1, REPORT-02)
- ✓ **REPORT-DELTA-EMPTY**: Empty-State-Hinweis "Seit dem letzten Lauf sind keine Katzen verschwunden" wenn nichts verschwunden ist — v1.0 (Phase 1, REPORT-03)
- ✓ **FILTER-RESET**: Button "↺ Filter zurücksetzen" rechts in der Filterleiste, atomarer Reset aller Controls (Slider, fitBtn, pairBtn, sorgBtn) via single `update()`-Call — v1.0 (Phase 2, FILTER-01 + FILTER-02)

### Active

<!-- Next milestone scope — to be defined via /gsd-new-milestone. -->

(Keine — v1.0 ist abgeschlossen. Nächster Milestone wird via `/gsd-new-milestone` definiert.)

### Out of Scope

<!-- Explicit non-goals. -->

- Modularisierung von `catfinder.py` (Aufsplittung in Package) — bewusst aufgeschoben, single-file ist für die Größe noch tragbar; siehe `.planning/codebase/ARCHITECTURE.md#Anti-Patterns`
- Test-Infrastruktur (pytest etc.) — kein Bestandteil dieses Milestones
- Neue Scraping-Quellen (andere Tierheime) — fokussiert auf den Münchner Tierschutzverein
- Änderungen an der Rating-Taxonomie oder am System-Prompt — Modell und Bewertungsschema bleiben stabil
- Persistente Filter-Auswahl über Reloads hinweg — Filter sind weiter session-lokal im Browser
- Migration der State-Datei oder Backwards-Compatibility-Wrapper für alte Einträge — die Purge-Änderung darf bestehende "Zombie"-Einträge beim ersten Lauf einfach entfernen

## Context

- **Bestehender Code:** Single-file `catfinder.py` (~901 Zeilen nach v1.0; +31 Zeilen vs. Pre-Milestone), Python 3.9+ lokal / 3.12 in CI, keine Tests, keine Linter-Config (siehe `.planning/codebase/STACK.md`).
- **Report-Pipeline:** Filterleiste und Report-Shell sind als f-string-eingebettetes HTML/CSS/JS in `_build_filter_bar` (`catfinder.py:297`) und `HTML_TEMPLATE` realisiert — Anpassungen am Filter-UI sind Python-Edits, kein separates Frontend-Build. v1.0 hat dieses Pattern beibehalten und erweitert (Reset-Button + DEFAULT_LO/DEFAULT_HI-Injection ins inline JS).
- **State-Modell:** Nach v1.0 ist das State-Modell sauberes Delta — `seen_cats.json` enthält nur noch aktuell gelistete Katzen. Verschwundene Katzen werden in einer Run-Iteration als "Nicht mehr verfügbar" gemeldet und im selben Schritt aus dem State entfernt. Keine Zombies, keine Vollhistorie.
- **CI-Schreibrechte:** Der Workflow committet `state/seen_cats.json` und `docs/index.html` zurück nach `main` (`contents: write`); Bot-Commit-Message und Pages-URL sind durch v1.0 nicht angetastet.
- **Privater Use-Case:** Kein Multi-User, keine öffentliche API. Akzeptabel: Migrationen ohne Versionierung, Zustandsverlust ist rückholbar (`--reset` re-evaluiert alles). v1.0 hat genau diesen Spielraum genutzt (Hard-Purge ohne Migration).

## Constraints

- **Tech stack**: Python 3.9+ Single-File, `requests` + `bs4` + `anthropic` + `pydantic`. v1.0 hat keine neuen Runtime-Dependencies hinzugefügt; Constraint bleibt für nachfolgende Milestones in Kraft, sofern nicht explizit gelockert.
- **Filter-UI**: Muss in der bestehenden `_build_filter_bar`-Logik (inline CSS/JS in Python f-string) bleiben — kein React/Vue/Build-Step.
- **State-Format**: JSON in `state/seen_cats.json`. Änderungen am Format dürfen vorhandene gültige Einträge nicht zerstören (lediglich verschwundene Einträge dürfen wegfallen).
- **CI-Verhalten**: Nach dem Milestone muss der Bot-Commit (`chore: state & report aktualisiert`) weiterhin gleich aussehen (gleiche Pfade, gleiche Permissions); E-Mail-Subject und Pages-URL bleiben unverändert.
- **Performance**: Nicht relevant — Listing < 100 Katzen, Reportrender < 1 s, kein Skalierungsdruck.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| "Nicht mehr verfügbar" wird zu Delta-only-Sektion | Vollhistorie wuchs unbegrenzt und war im Report nicht informativ — relevant ist "wer ist *gerade jetzt* weg, den ich kenne?" | ✓ Phase 1 — Delta gegen Pre-Run-State, Empty-State-Hinweis bei Null-Delta |
| Verschwundene Einträge werden komplett aus dem State entfernt (kein Zeitfenster, kein Soft-Delete) | Einfachster Mechanismus, passt zum privaten Use-Case (kein Reporting / keine Statistik nötig); Wieder-Auftauchen wird neu bewertet — akzeptabel | ✓ Phase 1 — Hard-Purge in Save-Schritt (Haupt-Pfad + no-new-cats Early-Return), keine Migration |
| "Filter zurücksetzen" sitzt zentral in der Filterleiste und resettet alle Filter zugleich | Schnellster Pfad zurück zur Übersicht; pro-Kategorie-Resets wären UI-Overkill für so wenige Filter | ✓ Phase 2 — Button rechts in der Leiste (margin-left:auto), Link-Stil mit ↺-Icon, atomarer Reset via single update()-Call |
| Single-file `catfinder.py` bleibt unangetastet (keine Modularisierung in diesem Milestone) | Scope-Schutz — Änderungen sind klein und lokal, Refactor wäre Selbstzweck | ✓ v1.0 — beide Phasen nur in `catfinder.py`, +31 Zeilen, kein neues Modul |

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
*Last updated: 2026-05-06 after v1.0 milestone completion (Delta-Report + Filter-Reset shipped; alle 5 v1-Requirements validated)*
