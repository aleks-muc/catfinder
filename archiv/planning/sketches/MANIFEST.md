# Sketch Manifest

## Design Direction

Ruhig und redaktionell. Der Report soll weniger nach Admin-Oberfläche und mehr nach
gedruckter Seite aussehen: viel Weißraum, Serifen-Überschriften aus dem System-Stack,
gedeckte Farben statt Ampel-Signalfarben, feine Linien statt Kästen und Schatten. Die
Katze steht im Vordergrund, nicht die Bedienelemente.

**Harte Vorgabe:** keinerlei Emojis. Der heutige Report nutzt sie an 23 Stellen, die
meisten davon redundant — die Rating-Emojis doppeln den farbigen Kantenakzent, das
Pillen-Emoji den Gesundheits-Farbbalken.

**Fotogröße bleibt** wie heute (~220px Cover, Grid mit `minmax(280px, 1fr)`). Bewusst
nicht verändert, damit der Vergleich nur die Gestaltung betrifft.

## Constraints

- Inline CSS/JS im Python-f-string (`HTML_TEMPLATE`, `_build_filter_bar`), kein Build-Step,
  kein Framework, keine Webfonts (Serife kommt aus dem System-Stack).
- Bestehende Filterlogik und `data-*`-Attribute bleiben unangetastet.
- Nur eine HTML-Datei, offline lauffähig (die Fotos liegen extern, wie im echten Report).

## Reference Points

Keine konkreten Vorbilder benannt — die Richtung kam aus dem Vergleich dreier
ASCII-Skizzen (redaktionell / funktional / warm).

## Sketches

| # | Name | Design Question | Winner | Tags |
|---|------|----------------|--------|------|
| 001 | report-ohne-emojis | Wie lesen sich Bewertung und Gesundheit ohne Emoji — und wie viel Struktur braucht die Card? | **C — Farbkante** | layout, typografie, farbe |
| 002 | farbkante-kontrast | Wie viel Fläche braucht ein Label, damit Bewertung und Gesundheit auf Distanz lesbar sind? | **C3 — Rating gefüllt** | farbe, kontrast, informationsarchitektur |
| 003 | c3-gestapelt-kontrast | Wie weit lässt sich der Kontrast anheben, bevor "ruhig & redaktionell" kippt? | **D1 — Kräftig** (Aufbau) | farbe, kontrast |
| 004 | signalfarben | Wie gesättigt dürfen die Kategoriefarben werden, bevor die gefüllten Labels ihre einheitliche Schriftfarbe verlieren? | **E1 — Kräftig** | farbe, kontrast, signalfarben |
| 005 | e1-gesund-gruen | Trägt Grün für "gesund", obwohl die Kindertauglichkeit dieselbe Farbe nutzt? | **ja** — gesund grün, unbekannt grau | farbe, semantik |
| 006 | bestfall-hervorheben | Wie wird "für Kinder geeignet und ohne bekannte Erkrankung" auf einen Blick erfassbar? | — | hierarchie, farbe, struktur |

## Entschieden

- **Sketch 001 → Variante C (Farbkante).** Die schmale Akzentkante überzeugt, die gedeckte
  Palette war aber zu kontrastarm. Zwei Töne lagen unter WCAG AA — in 002 korrigiert.
- **Card-Reihenfolge** (Nutzer-Vorgabe, in 002 umgesetzt): Name → Meta → Pärchen/Interessenten
  → Labels → Verhaltensbeschreibung → Gesundheitsbeschreibung → Fußzeile.
- **Sketch 002 → C3 (Rating gefüllt, Gesundheit umrandet).** Setzt die Rangfolge:
  Kindertauglichkeit ist die Hauptaussage, Gesundheit die Nebenbedingung.
- **Labels gestapelt** (Nutzer-Vorgabe, in 003 umgesetzt): Gesundheit immer unter
  Kindertauglichkeit, nicht daneben.
