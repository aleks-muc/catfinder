# Requirements: Catfinder

**Defined:** 2026-05-05
**Core Value:** Sobald eine geeignete Katze neu auf der Seite auftaucht, weiß die Familie es ohne manuelles Nachsehen — der Report muss zuverlässig laufen und den Unterschied zwischen "neu", "weiter verfügbar" und "verschwunden" sauber kommunizieren.

## v1 Requirements

Anforderungen für diesen Milestone. Jede REQ-ID wird im Roadmap genau einer Phase zugeordnet.

### Report

- [x] **REPORT-01**: Im HTML-Report listet die Sektion "Nicht mehr verfügbar" ausschließlich Katzen, die zwischen dem unmittelbar vorigen und dem aktuellen Lauf vom Listing verschwunden sind (Delta — nicht die gesamte Historie).
- [x] **REPORT-02**: Katzen, die in einem früheren Lauf bereits als verschwunden gemeldet wurden, sind danach aus `state/seen_cats.json` entfernt und tauchen in keinem zukünftigen Report mehr in der "Nicht mehr verfügbar"-Sektion auf — bis sie ggf. wieder neu auf dem Listing erscheinen.
- [x] **REPORT-03**: Wenn beim aktuellen Lauf keine Katze verschwunden ist, zeigt die Sektion "Nicht mehr verfügbar" einen klaren Hinweistext (z.B. "Seit dem letzten Lauf sind keine Katzen verschwunden") statt zu fehlen oder leer zu wirken.

### Filter

- [ ] **FILTER-01**: In der Filterleiste des Reports ist ein klar beschrifteter Button "Filter zurücksetzen" sichtbar.
- [ ] **FILTER-02**: Ein Klick auf "Filter zurücksetzen" setzt alle aktiven Filter (Bewertungs-Buttons, Alters-Slider, Toggle-Buttons) auf ihren Default zurück und die angezeigten Karten reflektieren den ungefilterten Zustand sofort.

## v2 Requirements

(Keine — User hat bestätigt, dass nur die obigen Änderungen für diesen Milestone vorgesehen sind.)

## Out of Scope

Explizite Ausschlüsse — verhindert Scope-Creep.

| Feature | Grund |
|---------|-------|
| Modularisierung von `catfinder.py` (Aufteilung in Package) | Single-file ist für die aktuelle Größe noch tragbar; Refactor wäre Selbstzweck |
| Test-Infrastruktur (pytest etc.) | Nicht Bestandteil dieses Milestones |
| Neue Scraping-Quellen (andere Tierheime) | Fokus auf Münchner Tierschutzverein |
| Änderungen an Rating-Taxonomie / System-Prompt | Modell und Bewertungsschema bleiben stabil |
| Persistente Filter-Auswahl über Reloads | Filter bleiben session-lokal im Browser |
| State-Migration / Backwards-Compatibility-Wrapper | Purge darf bestehende "Zombie"-Einträge beim ersten Lauf einfach entfernen |
| Konfigurierbares Zeitfenster für verschwundene Katzen | User hat sich klar für hartes Purge ohne Zeitfenster entschieden |
| Pro-Kategorie-Reset-Buttons in der Filterleiste | UI-Overkill bei der Anzahl Filter; ein zentraler Reset reicht |

## Traceability

Welche Phase deckt welche Anforderung ab.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPORT-01 | Phase 1 | ✓ Validated (2026-05-06) |
| REPORT-02 | Phase 1 | ✓ Validated (2026-05-06) |
| REPORT-03 | Phase 1 | ✓ Validated (2026-05-06) |
| FILTER-01 | Phase 2 | Pending |
| FILTER-02 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-05*
*Last updated: 2026-05-06 after Phase 1 completion (REPORT-01..03 validated)*
