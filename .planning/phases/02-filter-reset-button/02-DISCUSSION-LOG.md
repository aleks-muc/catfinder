# Phase 2: Filter-Reset-Button - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 2-filter-reset-button
**Areas discussed:** Position & Layout, Visuelle Sprache, Sichtbarkeit / Disabled-State, Reset-Verhalten & Feedback

---

## Position & Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Ganz rechts, abgesetzt | Mit `margin-left: auto` rechts gepinnt, vom Filter-Cluster visuell getrennt. Nimmt Reset als Meta-Aktion ernst. | ✓ |
| Inline am Ende der Toggle-Reihe | Direkt nach Sorgenkinder-Button, gleicher gap, gleicher Stil — als ob es ein weiterer Toggle wäre. | |
| Eigene Zeile unter der Filterleiste | Komplett separate Zeile rechts ausgerichtet. Maximaler visueller Abstand, kostet aber vertikalen Platz in der Sticky-Bar. | |

**User's choice:** Ganz rechts, abgesetzt (Recommended)
**Notes:** Bestätigt das Modell „Reset ist eine Meta-Aktion, kein weiterer Filter". Implementierung via `margin-left: auto` ohne extra Spacer-DOM.

---

## Visuelle Sprache

| Option | Description | Selected |
|--------|-------------|----------|
| Dezenter Link-Stil | Transparenter Background, kein Border, color:#666, hover:#1976d2, mit ↺ Icon-Präfix. | ✓ |
| Wie die anderen Toggle-Buttons | Gleicher Stil wie #fitBtn/#pairBtn/#sorgBtn (grauer #f5f5f5-Hintergrund, 6px radius). | |
| Sekundär mit Akzent-Outline | Outline-Stil in #1976d2 (Slider-Akzentfarbe), wirkt „gewichtiger". | |

**User's choice:** Dezenter Link-Stil (Recommended)
**Notes:** Hover-Akzent passt zur existierenden Slider-/Label-Akzentfarbe #1976d2 — visuell konsistent ohne neue Farbe einzuführen.

---

## Sichtbarkeit / Disabled-State

| Option | Description | Selected |
|--------|-------------|----------|
| Immer sichtbar, immer klickbar | Permanent in der Leiste. Klick im Default-Zustand ist No-Op. Keine Heuristik nötig, Layout stabil. | ✓ |
| Disabled wenn alle Defaults aktiv | Visuell gedämpft (`opacity: .35; pointer-events: none`) bei Default-Zustand. Erfordert `isAnyFilterActive()`-Check. | |
| Komplett hidden wenn alle Defaults aktiv | Verschwindet (`display:none`) bei Default-Zustand, taucht bei Abweichung auf. Leiste „springt". | |

**User's choice:** Immer sichtbar, immer klickbar (Recommended)
**Notes:** Vermeidet zusätzliche JS-Komplexität (`isAnyFilterActive()`) und ein „springendes" Sticky-Bar-Layout. Mit dem dezenten Link-Stil ist permanente Sichtbarkeit visuell unproblematisch.

---

## Reset-Verhalten & Feedback

### Visuelles Feedback beim Klick

| Option | Description | Selected |
|--------|-------------|----------|
| Stilles Reset | Defaults werden gesetzt, `update()`/`filter()` rendert Karten sofort neu — keine Animation, kein Toast. | ✓ |
| Kurzer Button-Flash | Kurzes Aufflackern des Reset-Buttons (background #e3f2fd für 250ms via CSS-Klasse + setTimeout). | |
| Toast „Filter zurückgesetzt" | Schwebender Toast für ~2s. Vollständigste Bestätigung, größter Code-Footprint. | |

**User's choice:** Stilles Reset (Recommended)

### Tastatur-Shortcut (Esc)

| Option | Description | Selected |
|--------|-------------|----------|
| Nein | Kein Shortcut. Reset nur über Button-Klick. Vermeidet Konflikte mit Browser-Defaults. | ✓ |
| Ja — Esc als Reset-Trigger | `keydown`-Listener auf `document`. Praktisch, aber präjudiziert die Tastatur-UX. | |

**User's choice:** Nein (Recommended)
**Notes:** Beide Entscheidungen halten den JS-Code minimal. Sichtbare Änderungen (Slider-Thumbs, Button-Texte/Klassen, Karten-Liste) sind Feedback genug. Esc-Shortcut nachrüstbar falls später gewünscht.

---

## Claude's Discretion

- Exakte CSS-Werte für Padding/Hover-Transition-Timing.
- ID-Vergabe für den neuen Button (`#resetBtn` ist der naheliegende Name, konsistent mit `#fitBtn`/`#pairBtn`/`#sorgBtn`).
- Reihenfolge der State-Reset-Operationen im Handler (so lange alle vor dem `update()`-Call passieren, ist die Reihenfolge egal).

## Deferred Ideas

- Tastatur-Shortcut Esc — explizit abgelehnt, nachrüstbar.
- Toast „Filter zurückgesetzt" — abgelehnt zugunsten stillem Reset.
- Button-Flash-Animation — abgelehnt zugunsten stillem Reset.
- Disabled-State wenn alle Filter Default sind — abgelehnt zugunsten „immer klickbar".
- Pro-Kategorie-Reset-Buttons — bereits in REQUIREMENTS.md `Out of Scope` markiert.
- Persistente Filter-Auswahl über Reloads — bereits in REQUIREMENTS.md `Out of Scope` markiert.
