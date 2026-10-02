---
sketch: 003
name: c3-gestapelt-kontrast
question: "Wie weit lässt sich der Kontrast anheben, bevor 'ruhig & redaktionell' kippt?"
winner: null
tags: [farbe, kontrast]
builds-on: 002
---

# Sketch 003: C3 gestapelt, mehr Kontrast

Verfeinerung von **C3** aus [Sketch 002](../002-farbkante-kontrast/) — gefülltes
Bewertungs-Label, umrandetes Gesundheits-Label.

## Was sich geändert hat

**Labels gestapelt.** Gesundheit steht jetzt immer unter der Kindertauglichkeit, nicht
mehr daneben. Nebeneffekt: der Umbruchfall aus Sketch 002 (langer Name plus zwei Labels
in einer Zeile) existiert nicht mehr — die Chip-Zeile kann nicht mehr unkontrolliert
zweizeilig werden.

**Kontrast in zwei Stufen**, damit die Spanne beurteilbar ist statt geraten:

| Kategorie | Sketch 002 | D1 Kräftig | D2 Maximal |
|---|---|---|---|
| Kinder geeignet | 7.5:1 | `#1f4d26` **9.8:1** | `#14401c` 11.8:1 |
| Nur ältere Kinder | 6.0:1 | `#7a4a00` **7.5:1** | `#653c00` 9.5:1 |
| Nicht für Kinder | 7.6:1 | `#8c1f0d` **9.1:1** | `#78140A` 11.0:1 |
| Keine Angabe | 6.8:1 | `#4a4640` **9.4:1** | `#33302b` 13.1:1 |

Die Werte gelten für beide Label-Formen: das umrandete Gesundheits-Label zeigt farbigen
Text auf Weiß, das gefüllte Bewertungs-Label weißen Text auf derselben Farbe — beide
Richtungen ergeben denselben Kontrastwert.

**Papierton mit abgesenkt.** Die weißen Cards standen auf `#faf9f7` mit 1.05:1 praktisch
unsichtbar auf dem Hintergrund. D1 senkt auf `#f5f3ef` (1.11:1), D2 auf `#efece6`
(1.18:1) — dadurch wirkt die Card als Fläche, ohne dass ein Schatten nötig wird.

Zusätzlich in D2: Überschriften auf reines Schwarz, Kante von 4px auf 5px.

## Varianten

- **D1 — Kräftig.** Der angeforderte Schritt. Bleibt in der redaktionellen Anmutung.
- **D2 — Maximal.** Obergrenze zur Orientierung. Härter und technischer — irgendwo
  zwischen D1 und D2 kippt die Richtung von "ruhig" nach "Dashboard".

## Offen

- Ob D2 schon zu weit geht, ist genau die Frage. D1 ist die Empfehlung; D2 existiert,
  damit die Entscheidung eine Grenze hat statt nur einen Vorschlag.
- Dark Mode weiterhin nicht vorgesehen.
