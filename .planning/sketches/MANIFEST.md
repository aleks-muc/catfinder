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
| 002 | farbkante-kontrast | Wie viel Fläche braucht ein Label, damit Bewertung und Gesundheit auf Distanz lesbar sind? | — | farbe, kontrast, informationsarchitektur |

## Entschieden

- **Sketch 001 → Variante C (Farbkante).** Die schmale Akzentkante überzeugt, die gedeckte
  Palette war aber zu kontrastarm. Zwei Töne lagen unter WCAG AA — in 002 korrigiert.
- **Card-Reihenfolge** (Nutzer-Vorgabe, in 002 umgesetzt): Name → Meta → Pärchen/Interessenten
  → Labels → Verhaltensbeschreibung → Gesundheitsbeschreibung → Fußzeile.
