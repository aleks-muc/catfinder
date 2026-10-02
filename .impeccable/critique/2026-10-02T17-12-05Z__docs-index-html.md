---
target: docs/index.html
total_score: 20
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/aleksandarotasevic/Coding/Catfinder/docs/index.html"
target_fingerprint: "sha256:94d1576b1107f384b1953558c4728c3b546f13ff4d04c80c1b610281263526a7"
target_path: /Users/aleksandarotasevic/Coding/Catfinder/docs/index.html
timestamp: 2026-10-02T17-12-05Z
slug: docs-index-html
---
Method: dual-agent (A: Design-Review · B: Detector + Browser)

## Design Health Score: 20/40 (Acceptable)
| # | Heuristik | Score | Kernproblem |
|---|---|---|---|
| 1 | Systemstatus | 2 | `#visibleCount` zählt Karten in zugeklappten Sektionen mit ("43 angezeigt", sichtbar sind 4) |
| 2 | Sprache der Nutzer | 3 | "Sorgenkinder" im Filter, auf der Karte heißt es "Nicht für Kinder" |
| 3 | Kontrolle | 2 | Reset ok, Filter werden nicht gemerkt |
| 4 | Konsistenz | 1 | 4 Toggles mit 4 Label-Mustern; `fitBtn` heißt nach Aus-Schalten "Alle Bewertungen"; roter `#sorgBtn` wirkt aktiv |
| 5 | Fehlervermeidung | 2 | "Nur geeignet" + "Sorgenkinder ausblenden" gleichzeitig möglich, zweiter wirkungslos |
| 6 | Wiedererkennen | 3 | Labels ausgeschrieben; Pärchen-Infos über zwei Karten verteilt |
| 7 | Effizienz | 2 | Keine Sortierung, kein Merken |
| 8 | Ästhetik | 3 | Ruhig; Selbstlink-Banner und leere Sektion "Nicht mehr verfügbar (0)" |
| 9 | Fehler beheben | 1 | Weggefilterte Sektion zeigt leere Fläche; roher `Bewertungsfehler: {e}` auf Karte |
| 10 | Hilfe | 1 | Nirgends steht, dass die Einordnung von Claude kommt |

## Design-Spezifität
LLM: eher produkteigen (Papierton, Serif, Statussektionen, "seit X Tagen gelistet", "Geeignet und gesund"). Austauschbar: Filterleiste. Die Kernfrage "ist heute eine Passende neu?" beantwortet die Seite nicht selbst.
Detector: 43 Warnungen, 2 Regeln. `side-tab` 42× (`.card { border-left: 4px solid var(--accent) }`, HTML_TEMPLATE Z. 739), `cream-palette` 1× (`--paper: #f5f3ef`, Z. 727 + _build_filter_bar Z. 465/466/474). Effektiv 2 Code-Stellen. side-tab teils False Positive: Rand kodiert die Bewertung, ist aber redundant zum Label. cream-palette: bewusster Token, aber genau der generische Editorial-Creme-Ton.

## Priority Issues
1. [P1] Kernfrage am Handy nicht above the fold. Banner + Header + sticky Filterleiste (181px, 21 % Viewport) + 345px-Foto vor dem ersten Label. Fix: Ergebniszeile im Header ("Heute neu: 4 · 0 kindergeeignet"), Leiste am Handy einklappbar/nicht sticky, kleinere Mobilfotos. → /impeccable layout, /impeccable adapt
2. [P1] Toggle-Logik inkonsistent/fehlerhaft (Label-Bug fitBtn Z. 528, roter Ruhezustand sorgBtn Z. 469, widersprüchliche Kombi). Fix: feste Labels + `.active`/`aria-pressed`; "Nur geeignet" und "Sorgenkinder" zu einer 3er-Segmentwahl. → /impeccable clarify
3. [P2] Claude-Bewertung wirkt als Urteil; `.reason` ohne Absender, oft in "Wir"-Stimme des Vereins. Fix: "Einschätzung (KI) · Steckbrief ist maßgeblich", Steckbrief-Link stärker. → /impeccable clarify
4. [P2] Leere/Fehlerzustände: "0 von N" ohne Text, falscher Zähler, roher Exception-Text. Fix: `.empty`-Zeile pro Sektion bei vis===0, Zähler nur offene Sektionen, Fehlertext vereinfachen. → /impeccable harden
5. [P3] Filter-A11y: `.cf-range` outline:none, Slider ohne aria-label, kein aria-pressed, Tap-Ziele 24px. → /impeccable audit

## Personas
Casey (Handy): sticky Leiste frisst Platz, 24px-Toggles eng, Antwort unter dem Foto, Banner verlinkt auf sich selbst.
Sam (Screenreader): unbeschriftete, unsichtbar fokussierte Slider; kein aria-pressed/aria-live; Katzen-ID im h2 wird mitgelesen; .gone (opacity .6) drückt Kontrast.
Elternteil am Laptop: Kandidaten in verschiedenen Sektionen, keine Merkfunktion/Sortierung, Pärchen-Gesundheit über zwei Karten.

## Kleinere Beobachtungen
Namen in VERSALIEN; Karten-Titel h2 statt h3; .cid mit Inline-Font; Slider-Track 130px; "kein Foto" mit hartkodiertem #e0e0e0/#999.

## Fragen
Braucht es vier Filter, oder reicht Ergebniszeile + Sortierung? Pärchen als eine Doppelkarte? Ist "Interessenten vorhanden" eher Archiv?
