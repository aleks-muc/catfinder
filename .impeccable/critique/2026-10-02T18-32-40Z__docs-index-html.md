---
target: docs/index.html
total_score: 27
max_score: 36
na_heuristics: 10
p0_count: 0
p1_count: 2
target_identity: "file:/Users/aleksandarotasevic/Coding/Catfinder/docs/index.html"
target_fingerprint: "sha256:12c07d663629fcd827059e94e43d6ca5c3dfe439d15b10eabb4c01cb92a2edc1"
target_path: /Users/aleksandarotasevic/Coding/Catfinder/docs/index.html
timestamp: 2026-10-02T18-32-40Z
slug: docs-index-html
---
Method: dual-agent (A: Design-Review · B: Detector + Browser)

## Design Health Score: 27/36 (75 %, Good; Heuristik 10 n/a: Einzelnutzer)
| # | Heuristik | Score | Kernproblem |
|---|---|---|---|
| 1 | Systemstatus | 3 | "Nichts Neues" sagt nicht, ob Top-Kandidaten verfügbar sind |
| 2 | Sprache | 4 | – |
| 3 | Kontrolle | 3 | Filter überleben kein Neuladen |
| 4 | Konsistenz | 3 | "Nur Pärchen" ohne Gruppenüberschrift |
| 5 | Fehlervermeidung | 3 | – |
| 6 | Wiedererkennen | 3 | – |
| 7 | Effizienz | 2 | Keine Sortierung; 34 Karten untereinander am Handy |
| 8 | Ästhetik | 3 | Pärchen-Begründung doppelt; Subgrid-Lücken |
| 9 | Fehler beheben | 3 | – |
| 10 | Hilfe | n/a | Einzelnutzer |

## Design-Spezifität
Eigenständig: ruhige Zeitung, Serifen, Petrol als einzige Aktionsfarbe, Etiketten-Hierarchie, Subgrid-Vergleich. Fremdkörper: CI-Banner "Im Browser öffnen".
Detector: 0 echte Befunde. CLI 2× cramped-padding (.cf-seg) = False Positive. Browser 4× text-occlusion an .badge-int im zugeklappten Interessenten-Abschnitt = False Positive; 1× layout-transition aus Browser-Erweiterung.

## Priority Issues
1. [P1] CI-Banner "Im Browser öffnen →" verlinkt auf sich selbst (.github/workflows/catfinder.yml 37–47), stärkster Kontrast der Seite, 42px am Handy. Fix: Einfügen streichen. → distill
2. [P1] "Nichts Neues" verschweigt verfügbare Top-Kandidaten. Fix: zweite Zeile "3 geeignet und gesund weiterhin verfügbar". → clarify
3. [P2] Kinder-Filter 4 vs. 34 Treffer; 29/43 "Nur ältere Kinder" zu grob; Sortierung "Keine Angabe" vor "Nur ältere Kinder". Fix: erst Frage klären (Prompt/Spec). → clarify
4. [P2] "Weiterhin verfügbar" ohne zweite Ordnung (alphabetisch). Fix: innerhalb Bewertung nach first_seen. → layout
5. [P3] Pärchen-Begründung doppelt, Subgrid-Lücken. → polish

## Personas
Casey: Banner zuerst; Filter/Zähler nach Scrollen außer Sicht.
Sam: Pärchen-Knopf ohne Gruppe; alt = Name doppelt zum h3; h2 in summary.
Laptop: Subgrid hervorragend; keine Sortierung; Filter nicht in URL.

## Kleinere Beobachtungen
.cid Rauschen; "Nur Pärchen" ohne Überschrift; Interessenten vor Weiterhin; "Nicht mehr verfügbar" vor verfügbaren Katzen; Dunkelmodus als Frage.
