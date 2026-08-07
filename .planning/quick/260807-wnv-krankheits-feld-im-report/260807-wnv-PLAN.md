---
quick_id: 260807-wnv
description: Krankheits-/Pflegeaufwand-Feld — Claude-Klassifikation, Card-Marker, Filter
date: 2026-08-07
status: ready
---

# Quick Task 260807-wnv — Krankheits-Feld im Report

Ein atomarer Commit für den Code, danach ein `--all`-Lauf als Backfill.

## Vorab-Befund (Steckbrief-Stichprobe, 10 Profile)

Krankheiten stehen in einem eigenen `Besonderheiten`-Abschnitt. Beispiele:
WALLACE (Futtermittelallergie + Bluthochdruck, 1× tägl. Tablette), MALIKA
(Epilepsie, 2× tägl. Medikamente), MIU-MIU (Epilepsie, 3× tägl.), KAI
(Harnwegsproblem, evtl. OP). 6/10 ohne gesundheitliche Einschränkung.

**Prompt-Fallen:** `Kastriert: Ja` steht bei jeder Katze; `Sorgentier` und
`Nur für erfahrene Halter` sind Verhaltens-, keine Gesundheitsmarker. Beides
muss der Prompt ausdrücklich ausschließen.

## Entscheidungen (mit Nutzer geklärt)

| Entscheidung | Wahl | Begründung |
|---|---|---|
| Achse | Pflegeaufwand: `keine` / `erwaehnt` / `dauerbehandlung` / `unbekannt` | Die Trennlinie, die den Alltag ändert, ist tägliche Medikamentengabe — nicht der medizinische Schweregrad, den der Steckbrief nicht hergibt. |
| Backfill | bestehendes `--all` | Flag existiert; 38 Haiku-Calls, 0 Zeilen Migrationscode. |
| Marker-Optik | Textbadge mit CSS-Farbe, **kein Emoji** | Idee 3 (Design-Auffrischung) entfernt Emojis — keine neuen dazubauen. |

## Task 1: Datenmodell + Prompt

**files:** `catfinder.py`

- `CatRating` um zwei Felder erweitern:
  `health: Literal["keine","erwaehnt","dauerbehandlung","unbekannt"] = "unbekannt"`
  und `health_note: str = ""`. Defaults sind nötig, damit aus dem State
  rehydrierte Ratings ohne Health-Feld valide bleiben.
- `SYSTEM_PROMPT` um einen Health-Block ergänzen, inkl. der beiden
  Ausschlüsse (kastriert/geimpft ist Routine; Sorgentier/erfahrene Halter
  ist Verhalten). `health_note`: max. ein Halbsatz, bevorzugt Zitat, leer bei
  `keine`/`unbekannt`.
- `HEALTH_META` neben `RATING_META`: nur die zwei sichtbaren Kategorien
  (`erwaehnt`, `dauerbehandlung`) mit `label` + `color`. `keine`/`unbekannt`
  rendern nichts → kein Eintrag nötig.

## Task 2: State-Rehydrierung entdoppeln

**files:** `catfinder.py`

`CatRating`-aus-State-Bau steht heute zweimal identisch da (`:767`, `:788`).
Vor dem Feature-Anbau zu einem Helper `_rating_from_entry(entry)` zusammenziehen,
den beide Aufrufer nutzen — sonst driften die Health-Defaults auseinander.
`_safe_rating` bekommt ein Gegenstück `_safe_health`.

State-Schreibpfad (`:871-875`) um `health` + `health_note` ergänzen.

## Task 3: Card-Marker + Filter

**files:** `catfinder.py`

- `_render_card`: `data-health="{...}"` aufs Card-Div, plus `_health_line(rating)`
  — rendert nur bei `erwaehnt`/`dauerbehandlung` eine `<div class="health">`
  mit Label und `health_note`.
- CSS `.card .health` in `HTML_TEMPLATE`.
- `_build_filter_bar`: ein Toggle `healthBtn` („Dauerbehandlung ausblenden"),
  im `filter()`-Durchlauf als zusätzliche Bedingung, und im `resetBtn`-Handler
  mit zurücksetzen (Reset = alle Filter aus).

**Abweichung vom Frage-Preview:** Dort stand „4 Buttons". Umgesetzt wird **ein
Toggle** — die Leiste hat bereits 4 Controls, und die einzige Kategorie, die
man aktiv wegfiltern will, ist `dauerbehandlung`. Die anderen drei sind am
Card-Marker ablesbar. Vier Buttons bleiben nachrüstbar.

## Verify

Fixture-Render ohne Netz/API: Cards mit allen vier Health-Werten durchrendern,
prüfen dass Badge nur bei `erwaehnt`/`dauerbehandlung` erscheint,
`data-health` gesetzt ist, `healthBtn` + Reset-Handler im JS stehen,
`ast.parse` sauber. Rehydrierung aus einem Alt-State-Eintrag ohne
`health`-Schlüssel muss `unbekannt` liefern, nicht crashen.

## Backfill

`python catfinder.py --all --no-browser` nach dem Commit; State-Diff prüfen.
