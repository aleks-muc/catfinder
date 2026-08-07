---
quick_id: 260807-wnv
description: Krankheits-/Pflegeaufwand-Feld — Claude-Klassifikation, Card-Marker, Filter
date: 2026-08-07
status: incomplete
commits: [df1731f]
---

# Quick Task 260807-wnv — Summary

Code vollständig, **Backfill offen** (siehe unten).

## Umgesetzt (Commit `df1731f`, `catfinder.py`)

**Datenmodell.** `CatRating` um `health`
(`keine` / `erwaehnt` / `dauerbehandlung` / `unbekannt`) und `health_note`
erweitert, beide mit Default — sonst wären aus dem State rehydrierte Ratings
ohne Health-Schlüssel ungültig.

**Prompt.** `SYSTEM_PROMPT` klassifiziert den Pflegeaufwand aus dem
`Besonderheiten`-Abschnitt. Zwei Ausschlüsse explizit benannt, weil sonst jede
Katze als krank durchläuft: `Kastriert: Ja` / Impfungen (Routine, steht überall)
und `Sorgentier` / `Nur für erfahrene Halter` (Verhaltens-, keine
Gesundheitsmarker).

**State.** `health` + `health_note` werden geschrieben. Die zweifach identische
`CatRating`-aus-State-Konstruktion (`_ratings_from_state` und der
`no_longer_listed`-Pfad) zu `_rating_from_entry` zusammengezogen — beide
Aufrufer laufen jetzt durch eine Funktion, sonst driften die Health-Defaults
auseinander. Klemmt ungültige Werte auf `unbekannt`.

**Report.** `_health_line` rendert einen Marker mit Farbbalken und Kurzhinweis,
aber nur bei `erwaehnt` / `dauerbehandlung`; `keine` und `unbekannt` bleiben
unsichtbar. `data-health` am Card-Div. CSS `.card .health`.

**Filter.** Toggle `healthBtn` („Dauerbehandlung ausblenden"), im
`filter()`-Durchlauf als Zusatzbedingung, im Reset-Handler mit abgeschaltet
(Reset = alle Filter aus, Semantik aus 260506-lu3).

### Abweichung vom Frage-Preview

Der Preview zur Taxonomie-Frage nannte „4 Buttons". Gebaut wurde **ein Toggle**.
Die Leiste hat bereits vier Controls, und `dauerbehandlung` ist die einzige
Kategorie, die man aktiv wegfiltern will — die übrigen drei sind am Card-Marker
ablesbar. Vier Buttons bleiben nachrüstbar, falls sich das im Betrieb anders
anfühlt.

## Verify (Fixture-Render, ohne Netz und ohne API)

- `ast.parse` sauber.
- Rehydrierung: Alt-Eintrag ohne `health` → `unbekannt`, kein Crash; Müllwert
  → `unbekannt`; Normalfall durchgereicht.
- Vier Cards mit allen vier Health-Werten: `data-health` überall gesetzt,
  **genau zwei** Badges gerendert, mit korrektem Label und Notiz.
- `healthBtn`, `hideTreat`, die Filter-Bedingung, der Reset-Handler und
  `.card .health` im Output vorhanden.
- `health_note` wird escaped (`<script>` → `&lt;script&gt;`).

## Offen: Backfill

`python catfinder.py --all --no-browser` ist **noch nicht gelaufen** —
`ANTHROPIC_API_KEY` ist weder in der Arbeits-Shell noch im Login-Profil
(`zsh -lic`) gesetzt.

Bis der Lauf erfolgt, stehen alle 38 State-Einträge auf `health: unbekannt`
und zeigen keinen Marker. Der reguläre CI-Lauf holt das **nicht** nach: er
bewertet nur neu aufgetauchte Katzen, die bestehenden 38 blieben ohne
Health-Wert, bis sie einmal aus dem Listing verschwinden und neu erscheinen.

State-Backup vor dem geplanten Lauf liegt im Scratchpad
(`state_vorher.json`), da der Scratchpad session-gebunden ist bei Bedarf
vorher neu ziehen.
