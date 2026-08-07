---
sketch: 002
name: farbkante-kontrast
question: "Wie viel Fläche braucht ein Label, damit Bewertung und Gesundheit auf Distanz lesbar sind?"
winner: null
tags: [farbe, kontrast, informationsarchitektur]
builds-on: 001
---

# Sketch 002: Farbkante, kontrastreicher

Verfeinerungsrunde auf Variante C aus [Sketch 001](../001-report-ohne-emojis/). Die
Richtung steht fest — offen ist nur noch die Label-Behandlung.

## Was sich gegenüber 001 geändert hat

**Kräftigere Palette.** Der Kontrastgewinn ist messbar, und zwei Töne lagen vorher unter
dem WCAG-AA-Schwellwert von 4.5:1 für Text:

| Kategorie | Sketch 001 | Sketch 002 |
|---|---|---|
| Kinder geeignet | `#4a6741` — 6.3:1 | `#2e5f34` — **7.5:1** |
| Nur ältere Kinder | `#96742a` — 4.3:1 ✗ | `#8a5800` — **6.0:1** |
| Nicht für Kinder | `#a04e38` — 5.8:1 | `#9c2b17` — **7.6:1** |
| Keine Angabe | `#8a857c` — 3.7:1 ✗ | `#5f5b54` — **6.8:1** |

Farbkante von 3px auf 4px, zusätzlich eine Haarlinie um die restliche Card, damit sie auf
dem Papierton als Fläche steht.

**Neue Reihenfolge im Card-Body** (vom Nutzer vorgegeben):

1. Name + ID
2. Rasse · Geschlecht · Alter
3. Pärchen-Partner und/oder „Interessenten vorhanden"
4. Zwei Labels: Bewertung und Gesundheit
5. Beschreibung aus Verhaltenssicht (`reason`)
6. Beschreibung aus Gesundheitssicht (`health_note`), im Ton der Kategorie
7. Fußzeile: Standdauer und Steckbrief-Link

## Drei Interpretationen, die ich beim Umsetzen getroffen habe

**Der Gesundheits-Hinweis erscheint immer**, auch im Negativfall („Keine Erkrankung
bekannt", neutrales Grau). Vorgabe war „der Hinweis, ob Erkrankungen bekannt sind" — eine
fehlende Markierung ist mehrdeutig, sie könnte auch „nicht bewertet" heißen. Das kostet
Fläche bei den 20 gesunden Katzen; falls das zu laut wirkt, ist der Negativfall die erste
Zeile, die wieder wegfällt.

**Das Bewertungs-Label bleibt** und steht als zweiter Chip neben dem Gesundheits-Chip.
Es war in der Vorgabe nicht erwähnt, ist aber die Kernaussage des Tools — die Farbkante
allein kann vier Stufen nicht unterscheidbar tragen.

**Die Meta-Zeile bleibt direkt am Namen**, vor Pärchen und Interessenten. Sie gehört zur
Identität der Katze, nicht zu ihrem Status.

## Varianten

Aufbau und Farben sind in allen dreien identisch. Nur die Label-Behandlung wechselt:

- **C1 — Umrandet.** Beide Labels als Umriss auf Weiß. Ruhigste Fassung, beide Aussagen
  gleichrangig.
- **C2 — Getönt.** Blasse Füllung in der eigenen Farbfamilie. Mehr Fläche pro Signal,
  auf Distanz am besten unterscheidbar — die Card wird bunter.
- **C3 — Rating gefüllt.** Bewertung vollflächig, Gesundheit umrandet. Setzt eine
  Rangfolge: Bewertung ist die Hauptaussage, Gesundheit die Nebenbedingung.

## Offen

- Bei einer Card mit langem Namen (CONSTANTIN CHRISTOMANOS) und beiden Labels wird die
  Chip-Zeile zweizeilig. In allen drei Varianten enthalten, ist im Mockup prüfbar.
- Dark Mode weiterhin nicht vorgesehen.
