# Phase 1: Delta-basiertes "Nicht mehr verfügbar" - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 1-Delta-basiertes "Nicht mehr verfügbar"
**Areas discussed:** State-Schema & Delta-Quelle, Zombie-Migration beim Erstlauf, Empty-State Wording & Visual, Sektion bei Erstlauf / --reset

---

## State-Schema & Delta-Quelle

### Frage 1: Wie soll "Was war im vorigen Lauf gelistet?" im State persistiert werden?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat dict, Hard-Purge (Recommended) | State bleibt {cat_id → entry} wie heute. Semantik ändert sich: State repräsentiert "Katzen aus dem letzten Lauf". Nach jedem Lauf werden alle Einträge entfernt, die nicht im aktuellen Listing sind. Delta = state.keys() − current_ids. Minimal-Edit am State-Format, keine Migration nötig. | ✓ |
| Neues `_meta`-Feld | State erhält zusätzlich {`_meta`: {`last_run_listed_ids`: [...]}}. Cat-Einträge bleiben länger im State. Mehr Flexibilität für spätere Features, aber komplexeres Schema und neuer Top-Level-Key bricht das heutige flache Format. | |
| Du entscheidest | Empfehlung: Variante 1 — sie bleibt im Spirit des heutigen Codes, erfüllt REPORT-01..03 vollständig, und PROJECT.md-Constraints sagen explizit "verschwundene dürfen wegfallen". | |

**User's choice:** Flat dict, Hard-Purge
**Notes:** Bewusste Entscheidung für minimale Schema-Änderung. State-Semantik wechselt von "alle je gesehenen" zu "Katzen aus dem vorigen Lauf".

### Frage 2: Brauchen wir ein Sicherheitsnetz gegen Mass-Purge bei sehr kleinem Listing?

| Option | Description | Selected |
|--------|-------------|----------|
| Kein Sicherheitsnetz — trust the scraper (Recommended) | `scrape_listing` raised heute schon RuntimeError wenn 0 Katzen gefunden werden (catfinder.py:213). Bei einem Hiccup mit wenigen Katzen wären das ggf. echte Katzen — wir vertrauen dem Listing. | ✓ |
| Plausibilitäts-Check | Wenn aktuelles Listing < N Katzen oder weniger als X% des State liefert, abort mit Warnung statt Purge. | |
| Du entscheidest | Empfehlung: Variante 1. Bei einem privaten Tool ist Recovery via `--reset` trivial. | |

**User's choice:** Kein Sicherheitsnetz — trust the scraper
**Notes:** Privater Use-Case rechtfertigt minimale Defensive Logik; `--reset` ist ausreichender Recovery-Pfad.

---

## Zombie-Migration beim Erstlauf

### Frage 1: Was soll beim ersten Lauf nach Deploy mit den vorhandenen Zombies passieren?

| Option | Description | Selected |
|--------|-------------|----------|
| Big-Bang (1x als 'Nicht mehr verfügbar' melden) (Recommended) | Alle Zombies tauchen einmalig in der Sektion auf, danach ist State sauber. Konsistent mit "state = vorheriger Lauf"-Semantik. Kein Sondercode. Lauter aber einmaliger Report. | ✓ |
| Silent Migration (still purgen) | Zombies werden geschluckt, ohne im Report aufzutauchen. Erfordert Marker (Schema-Version, mtime-Check). Sauberer Erst-Report, aber Sondercode der nur 1x feuert. | |
| Manuell vor Deploy aufräumen | User löscht state via `--reset` vor Deploy. Erstlauf bewertet alles neu. Kein Code-Aufwand, aber manueller Schritt + Re-Eval-Kosten für alle aktuell gelisteten Katzen. | |

**User's choice:** Big-Bang (1x als 'Nicht mehr verfügbar' melden)
**Notes:** Akzeptiert den einmaligen großen Report-Diff zugunsten von Code-Einfachheit; keine Migrations-Sondercode-Pfade.

---

## Empty-State Wording & Visual

### Frage 1: Wenn beim aktuellen Lauf nichts verschwunden ist: welche Formulierung & welcher Stil?

| Option | Description | Selected |
|--------|-------------|----------|
| Bestehender `.empty`-Style + 'Seit dem letzten Lauf sind keine Katzen verschwunden. ✨' (Recommended) | Wiederverwendet den exakten CSS-Stil von 'Keine neuen Katzen seit dem letzten Lauf. 🎉' (catfinder.py:605). Konsistente Optik, kein neuer CSS-Code. Sparkle-Emoji unterstreicht 'gute Nachricht'. | ✓ |
| Knapper, sachlicher Stil | Z.B. '— keine Veränderungen —' ohne Emoji, kleinere Typo, grauer Text. Reduzierter visueller Footprint. | |
| Du formulierst es | User gibt exakten Text vor. | |

**User's choice:** Bestehender `.empty`-Style + 'Seit dem letzten Lauf sind keine Katzen verschwunden. ✨'
**Notes:** Stilistische Konsistenz mit der bestehenden "keine neuen Katzen"-Empty-State.

---

## Sektion bei Erstlauf / --reset

### Frage 1: Wie soll sich die Sektion bei leerem State (Erstlauf / --reset) verhalten?

| Option | Description | Selected |
|--------|-------------|----------|
| Sektion komplett ausblenden bei Erstlauf (Recommended) | Wenn State leer war beim Lauf-Start, wird die Sektion gar nicht gerendert. Empty-State-Hinweis erscheint nur in regulären Läufen mit nicht-leerem vorigen State. Vermeidet semantisch falschen Hinweis ('keine verschwunden' obwohl es nie welche gab). | ✓ |
| Empty-State-Hinweis auch bei Erstlauf zeigen | Sektion immer sichtbar mit Standard-Empty-Text. Konsistente Layout-Struktur. Aber semantisch leicht irreführend. | |
| Spezieller Erstlauf-Hinweis | Sektion sichtbar mit anderem Text wie 'Erstlauf — noch kein Vergleich möglich'. Klare Kommunikation, aber zusätzlicher Text-Variant. | |

**User's choice:** Sektion komplett ausblenden bei Erstlauf
**Notes:** Bevorzugt semantische Klarheit über Layout-Konsistenz. Keine zusätzlichen Text-Varianten zu pflegen.

---

## Claude's Discretion

- Genaue Reihenfolge und Atomicity der Schritte "compute disappeared" → "render report" → "mutate state" → "save_state" innerhalb von `main()`. Heutiger atomic save (`tempfile.mkstemp` + `os.replace`) bleibt; Detail-Implementierung dem Planner überlassen.
- Position der "Nicht mehr verfügbar"-Sektion im Report (heute zwischen "Neu" und "Weiterhin verfügbar") — bleibt unverändert ohne Diskussion.
- Sortierung in der Sektion — `_card_sort_key` (catfinder.py:484-491) bleibt.
- Zombie-Card Visual-Treatment (graue Buttons, `opacity:.6`) bleibt unverändert.
- Format des Sektion-Titels bei `(0)` vs. ohne Count-Suffix — Detail-Frage, Konsistenz zu "Neu seit letztem Lauf (N)" spricht für `(0)`.
- Erkennungs-Hook für "leerer State zu Lauf-Beginn" (Parameter `had_prior_state` in `render_report` vs. Inferenz aus `scope_note`) — Planner entscheidet.

## Deferred Ideas

- Konfigurierbares Zeitfenster für "Nicht mehr verfügbar" — Out-of-Scope (REQUIREMENTS.md / PROJECT.md).
- State-Statistik / History-Tracking — würde zusätzliches Schema erfordern, bewusst nicht jetzt.
- Plausibilitäts-Check gegen Mass-Purge — irrelevant für privaten Use-Case.
- Banner / Hinweis für den Big-Bang-Erstlauf — verworfen als unnötig.
- Modularisierung von `catfinder.py` (Aufteilung in Package) — explizit Out-of-Scope für den Milestone.
