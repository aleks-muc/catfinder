---
target: docs/index.html
total_score: 32
max_score: 36
na_heuristics: 10
p0_count: 0
p1_count: 1
target_identity: "file:/Users/aleksandarotasevic/Coding/Catfinder/docs/index.html"
target_fingerprint: "sha256:08de8b5e84553802985e6d38a9331472fe07aefa34da975d03225ea27e1e45d5"
target_path: /Users/aleksandarotasevic/Coding/Catfinder/docs/index.html
timestamp: 2026-10-02T19-13-32Z
slug: docs-index-html
---
Method: dual-agent (A: Design-Review · B: Detektor + Browser)

## Heuristiken (32/36, n/a: 10)
1 Status 3 – bei Neuen nennt Kopfzeile keine passenden Weiterhin-Katzen
2 Sprache 4
3 Kontrolle 3 – "Filter zurücksetzen" zeigt weiter "1 aktiv"; Filter weg nach Reload
4 Einheitlich 3 – "1 Kinder geeignet" gleicher grüner Punkt wie "Geeignet und gesund"
5 Fehler vermeiden 4
6 Erkennen 4
7 Effizienz 3 – kein Sortieren, keine Filter-URL
8 Schlicht 4
9 Fehler-Ausweg 4 – Leer-Hinweis ohne Reset-Link
10 Hilfe n/a – Einzelnutzer

## Design-Spezifität
Spezifisch: ruhige Zeitungsseite, Kopfzeile beantwortet die Tagesfrage. Detektor: cramped-padding ×3 (.cf-seg) und layout-transition (Browser-Erweiterung) — alles Fehlalarme.

## Priority Issues
1. [P1] Neue, aber unpassende Katzen → Seite wirkt leer (Weiterhin zugeklappt via is_open=not evaluated_sorted, _today_line zeigt passende Weiterhin-Katzen nur ohne Neue). Fix: Weiterhin öffnen + Zeile zeigen, wenn keine neue passt. /impeccable clarify
2. [P2] "1 Kinder geeignet" in Kopfzeile missverständlich. /impeccable clarify
3. [P2] "Filter zurücksetzen" lässt "1 aktiv" stehen. /impeccable polish
4. [P3] Leer-Hinweis "Keine Katze passt" ohne Aktion → "Alle zeigen". /impeccable harden
5. [P3] Pärchen-Begründung doppelt, .cid-Nummer Lärm. /impeccable distill

## Persona Red Flags
Power-User: kein Sortieren, Filter nicht persistent, Filterleiste 2-zeilig bei 1280px.
Screenreader: h2 in summary; #visibleCount aria-live bei jedem Slider-Schritt.
Handy: P1 trifft am härtesten; "Interessenten vorhanden (0 von 9)" bricht bei 390px um.

## Minor
PRODUCT.md Capabilities nennt alte Sektionsreihenfolge; "Neu seit letztem Lauf" → "Neu seit gestern"; Namen in Versalien; Statuszeile wiederholt Kopfzeilen-Zahl.

## Fragen
Push nur bei neu UND passend? Interessenten-Sektion nur wenn etwas passt? Alters-Slider nötig?
