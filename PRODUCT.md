# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Ein einziger Nutzer: der Entwickler selbst, auf Katzensuche für seine Familie in München. Er liest gleichermaßen am Handy (ntfy-Push antippen → GitHub-Pages-Report öffnen, kurz scannen) und am Laptop (in Ruhe vergleichen) und will nicht täglich selbst beim Tierschutzverein nachsehen. Er kennt das Tool und weiß, woher die Bewertungen kommen — Erklärtexte für Fremde sind nicht nötig.

**Was für die Familie in Frage kommt** (Stand 2026-10-02, Begriff *Passend* in `CONTEXT.md`): ein gesundes Pärchen, bei dem keine der beiden Katzen *Nicht für Kinder* ist — *Nur ältere Kinder* kommt inzwischen in Frage. Die Standard-Filter des Reports zeigen genau das.

## Product Purpose
Catfinder scrapt einmal täglich das Katzen-Listing des Tierschutzvereins München, lässt neue Katzen von Claude gegen ein Familien-Eignungsprofil (Kinder, Gesundheit) einordnen und liefert einen filterbaren HTML-Report aus.

Erfolg hat zwei Momente, beide gleich wichtig:
1. **Schneller Blick:** In Sekunden wissen, ob heute eine passende Katze neu dabei ist.
2. **Vergleichen:** Mehrere Kandidaten abwägen — Alter, Kindertauglichkeit, Gesundheit, Pärchen, Interessenten.

## Positioning
Kein weiteres Tierportal, sondern ein persönlicher Tagesfilter: Er merkt sich, was die Familie schon gesehen hat, und trennt sauber zwischen „neu", „weiter verfügbar", „Interessenten vorhanden" und „nicht mehr verfügbar".

## Operating Context
- Täglicher CI-Lauf (GitHub Actions), danach ntfy-Push bei neuen Katzen; Report öffentlich über GitHub Pages (`docs/index.html`), lokal unter `reports/report.html`.
- Jede Karte verlinkt auf den Original-Steckbrief beim Tierschutzverein; dort passiert der echte nächste Schritt (Kontakt, Besuch).

## Capabilities and Constraints
- Report-Abschnitte: *Neu seit letztem Lauf*, *Weiterhin verfügbar*, *Interessenten vorhanden*, *Nicht mehr verfügbar*.
- Bewertung Kinder: *Kinder geeignet* · *Nur ältere Kinder* · *Nicht für Kinder* · *Keine Angabe*. Bewertung Gesundheit: *Keine Erkrankung bekannt* · *Gesundheit beachten* · *Dauerbehandlung nötig* · *Gesundheit unbekannt*.
- Filterleiste: Alter, Bewertung, Gesundheit, Pärchen.
- Report ist eine einzelne, statische HTML-Datei, erzeugt aus Python-f-Strings in `catfinder.py` (`HTML_TEMPLATE`, `_build_filter_bar`, `render_report`). Inline CSS/JS, kein Framework, kein Build-Step, keine neuen Runtime-Dependencies.
- ntfy-Titel und Pages-URL bleiben unverändert.
- Alle Texte auf Deutsch.

## Evidence on Hand
- Katzenfotos, Namen und Stammdaten stammen live vom Tierschutzverein-Listing; der Report hat keine eigenen Bild-Assets.
- Echte Inhalte: aktueller Report unter `docs/index.html`, State in `state/seen_cats.json`.
- Keine Testimonials, keine Marke, kein Logo — nichts davon erfinden.

## Product Principles
1. **Die Claude-Bewertung ist ein Hinweis, keine Wahrheit.** Der Steckbrief beim Tierschutzverein bleibt maßgeblich; der Report muss immer zu ihm führen. Eine eigene KI-Kennzeichnung im Report ist nicht nötig — der Nutzer weiß das.
2. **„Neu" zuerst.** Was seit dem letzten Lauf dazugekommen ist, muss ohne Scrollen und Filtern erkennbar sein.
3. **Status ehrlich kommunizieren.** Neu, weiter verfügbar, Interessenten, verschwunden — nie verwischen.
4. **Handy und Laptop gleichberechtigt.** Schneller Blick am Handy, Vergleich am Laptop — keins darf das andere opfern.
5. **Wartungsfrei bleiben.** Eine Datei, kein Build, keine Betriebslast.
