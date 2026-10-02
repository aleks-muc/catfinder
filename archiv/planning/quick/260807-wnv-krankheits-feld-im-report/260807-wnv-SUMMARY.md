---
quick_id: 260807-wnv
description: Krankheits-/Pflegeaufwand-Feld — Claude-Klassifikation, Card-Marker, Filter
date: 2026-08-07
status: complete
commits: [df1731f, 9b40c87, ce9ee0c, f502f1f]
---

# Quick Task 260807-wnv — Summary

Abgeschlossen. Vier Commits: Feature, zwei Prompt-Korrekturen, Backfill-State.

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

## Prompt-Korrekturen nach dem ersten Backfill

Der erste `--all`-Lauf stufte **39 von 47** Katzen als gesundheitlich
auffällig ein. Drei Fehlerklassen, in zwei Runden behoben:

**Runde 1 (`9b40c87`).** Ausstehende Kastration („Kastration muss nachgeholt
werden", „noch zu jung") wurde als Befund gelesen — der Prompt schloss nur
`Kastriert: Ja` aus. Verhalten und Entwicklung (Unsauberkeit bei Jungtieren,
Hyperaktivität, Beißvorfälle, Anknabbern) landete als Erkrankung im Report.
Allgemeine Rassehinweise ohne Befund ebenfalls. Prompt führt seitdem mit dem
positiven Kriterium statt mit einer Verbotsliste.

**Runde 2 (`ce9ee0c`)**, nach Prüflauf 12/16:

- *GIZMO* trug weiter Pashas Nierenwerte — sein `Besonderheiten`-Abschnitt
  handelt ausschließlich von der Partnerkatze. Nicht am Prompt gelöst,
  sondern an den Daten: `cat.partner_name` ist zum Bewertungszeitpunkt
  bereits gefüllt (`main` setzt es vor `evaluate_all`) und wird jetzt in den
  User-Prompt injiziert.
- *BILL-KAUL-QUAPPI* blieb trotz nahezu wörtlicher Ausschlussregel auf
  `erwaehnt`. Das Modell liest die Existenz eines `Besonderheiten`-Abschnitts
  selbst als Befund → steht jetzt explizit dagegen.
- *SUCUK* begründete `erwaehnt` selbst mit „aber keine diagnostizierte
  Erkrankung". Neue Schlussprüfung bindet die Kategorie an die Notiz: ohne
  benennbaren körperlichen Befund ist es `keine`.

**Falsche Testerwartung, kein Bug:** KIM war als `keine` erwartet, ist aber
korrekt `erwaehnt` — Svens Medikation ist verschwunden, übrig bleibt Kims
eigenes Übergewicht. Das ist dieselbe Begründung, mit der PFU als Kontrolle
auf `erwaehnt` steht.

## Backfill-Ergebnis (`f502f1f`)

Prüflauf 16/16, danach `--all` über alle 47 Katzen.

| | vor dem Fix | nach dem Fix |
|---|---|---|
| `keine` | 8 | 20 |
| `erwaehnt` | 21 | 12 |
| `dauerbehandlung` | 18 | 15 |

Gegenchecks: null Rest-Kontamination (keine Notiz nennt noch den
Partnernamen), keine Kategorie ohne Notiz, kein `unbekannt`. Pärchen sind
jetzt korrekt asymmetrisch — PAMUK `keine` / DUMAN `dauerbehandlung`,
GIZMO `keine` / PASHA `erwaehnt`, SVEN `dauerbehandlung` / KIM `erwaehnt`.

**Nebenbefund:** WASTL wechselte beim Kinder-Rating von `nicht_geeignet` zu
`aeltere_kinder`. Gegen den Steckbrief geprüft („gerne auch in einer Familie
mit größeren, verständigen Kindern") — die neue Einstufung ist korrekt, die
alte war falsch. Der überarbeitete Prompt hat also eine Bestands-Fehl-
klassifikation mitkorrigiert, und zwar in die Richtung, die zählt: eine
Katze, die fälschlich aussortiert war.

**Grenzfall bewusst so belassen:** INCI (`erwaehnt`, „rassetypische
Veranlagung … in tierärztlicher Abklärung") gegenüber RUDI (`keine`,
allgemeiner Rassehinweis). Die Trennung ist gewollt.

## Verifikations-Skript

Der Prüflauf über die 16 kritischen Fälle liegt bewusst **nicht** im Repo
(Scratchpad, session-gebunden). Er braucht einen API-Key und war ein
Einmal-Werkzeug für diese Prompt-Iteration. Falls der Health-Prompt nochmal
angefasst wird: er prüft zehn Muss-Kipper, drei Pärchen auf Partnername in
der Notiz und sechs Kontrollen, die sich nicht ändern dürfen.
