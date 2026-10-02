---
target: docs/index.html
total_score: 24
max_score: 36
na_heuristics: 10
p0_count: 0
p1_count: 2
target_identity: "file:/Users/aleksandarotasevic/Coding/Catfinder/docs/index.html"
target_fingerprint: "sha256:e9fbc0685617e62aa634db1fc25f4e8e7f6c2e9f10f5e66456d215722ef56e44"
target_path: /Users/aleksandarotasevic/Coding/Catfinder/docs/index.html
timestamp: 2026-10-02T18-00-36Z
slug: docs-index-html
closed: true
---
Method: dual-agent (A: Design-Review · B: Detector + Browser)

## Design Health Score: 24/36 (67 %, Acceptable; Heuristik 10 n/a: Einzelnutzer = Entwickler)
| # | Heuristik | Score | Kernproblem |
|---|---|---|---|
| 1 | Systemstatus | 3 | Am Handy Filter nicht sticky; aktiver Filter nach Scrollen unsichtbar |
| 2 | Sprache | 3 | "0 neu bewertet" wiederholt "Nichts Neues" |
| 3 | Kontrolle | 3 | Filter überleben kein Neuladen (ok) |
| 4 | Konsistenz | 2 | Filter "Nur Kinder geeignet" vs. Label "Geeignet und gesund" |
| 5 | Fehlervermeidung | 3 | – |
| 6 | Wiedererkennen | 2 | Vergleich über springende Kartenzeilen und zugeklappte Abschnitte |
| 7 | Effizienz | 2 | Keine Sortierung |
| 8 | Ästhetik | 3 | Leere 0-Abschnitte, doppelte Pärchen-Karten |
| 9 | Fehler beheben | 3 | – |
| 10 | Hilfe | n/a | Einzelnutzer baut das Tool selbst |

## Design-Spezifität
Eigenständig: Serif-Schlagzeile als Antwort, Haarlinien, ein Petrol-Akzent, neutrale Fläche. Generisch: Kartenraster, Ampel-Labels.
Detector: CLI 1× cramped-padding (.cf-seg) = False Positive (Handy padding 0 + border 0; Desktop 20px Abstand). Browser 3× text-occlusion = False Positive (Filter zugeklappt), 1× layout-transition = aus Browser-Erweiterungen. Side-tab und cream-palette weg.

## Priority Issues
1. [P1] Tage ohne Neue: Vergleich standardmäßig zugeklappt; leere Box + (0)-Abschnitt. Fix: "Weiterhin verfügbar" offen wenn keine Neuen, Leerbox als Zeile, (0)-Abschnitt in Statuszeile. → distill
2. [P1] Filterleiste verschwindet: schmal laden, dann verbreitern → details zu, summary am Desktop versteckt. Fix: matchMedia change-Listener. → harden
3. [P2] Kartenzeilen springen; .reason flex:1 schiebt Gesundheitsnotiz weg vom Label; Pärchen doppelt. → layout
4. [P2] Filterbegriffe ≠ Labels; kein Filter "nur ohne Erkrankung". → clarify
5. [P2] Screenreader: 43× "Steckbrief →", h2 in summary, Kinder-Gruppe als aria-pressed statt Radio, Regler ohne aria-valuetext. → audit/harden

## Personas
Casey: kein Hinweis auf aktiven Filter nach Scrollen; "Nur Kinder geeignet" bricht bei 390px um; 13.500px Seite ohne Sprung zu den Filtern.
Sam: s. Issue 5; positiv: Fokusring, aria-live, lang=de.
Laptop-Vergleich: keine Merkliste/Sortierung, Katzen wechseln Abschnitt bei Interessenten.

## Kleinere Beobachtungen
Punkt-Fragment links am Regler; Umriss "Gesundheit beachten" < 3:1; .cid Rauschen; Bild-Ladefehler sieht aus wie "kein Foto".

## Fragen
Interessenten als eigener Abschnitt nötig? Merkliste (localStorage)? Dunkelmodus?
