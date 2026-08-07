---
sketch: 004
name: signalfarben
question: "Wie gesättigt dürfen die Kategoriefarben werden, bevor die gefüllten Labels ihre einheitliche Schriftfarbe verlieren?"
winner: null
tags: [farbe, kontrast, signalfarben]
builds-on: 003
---

# Sketch 004: Signalfarben

Aufbau exakt wie **D1** aus [Sketch 003](../003-c3-gestapelt-kontrast/) — gestapelte Labels,
gefülltes Bewertungs-Label, umrandetes Gesundheits-Label, 4px Kante, Papierton `#f5f3ef`.
Es wechselt ausschließlich die Palette.

## Zwei technische Zwänge, die die Sättigung begrenzen

**Gefüllte Labels.** Weiße Schrift trägt nur auf ausreichend dunklem Grund. Je gesättigter
und heller ein Ton wird, desto eher muss die Schrift auf Dunkel umschlagen. Die
Schriftfarbe wird deshalb je Kategorie automatisch gewählt: Weiß, solange es 4.5:1
erreicht, sonst `#17150f`.

**Umrandete Labels und die Gesundheitsnotiz** zeigen farbigen Text auf Weiß. Ein echtes
Gelb wie `#eab308` erreicht dort nur 2.2:1 und ist unlesbar. Jede Kategorie führt deshalb
zwei Werte: einen Signalton für Fläche, Kante und Rahmen, und einen abgedunkelten Ton
derselben Familie für Text.

Die Farbtafel oben in jedem Tab zeigt beide Werte samt Kontrast.

## Varianten

### E1 — Kräftige Signalfarben

| Kategorie | Fläche | gefüllt | Text | umrandet |
|---|---|---|---|---|
| Kinder geeignet | `#1e7a35` | weiß, 5.4:1 | `#145c26` | 8.1:1 |
| Nur ältere Kinder | `#c9880a` | **dunkel**, 6.1:1 | `#8a5c00` | 5.8:1 |
| Nicht für Kinder | `#c62020` | weiß, 5.8:1 | `#971616` | 8.6:1 |
| Keine Angabe | `#6b6560` | weiß, 5.7:1 | `#4d4843` | 9.0:1 |

Drei von vier gefüllten Labels tragen weiße Schrift, nur Gelb kippt auf Dunkel.

### E2 — Volle Ampel

| Kategorie | Fläche | gefüllt | Text | umrandet |
|---|---|---|---|---|
| Kinder geeignet | `#17a03e` | **dunkel**, 5.3:1 | `#10702b` | 6.2:1 |
| Nur ältere Kinder | `#eab308` | **dunkel**, 9.5:1 | `#8a6800` | 5.2:1 |
| Nicht für Kinder | `#e02424` | weiß, 4.7:1 | `#a01414` | 8.1:1 |
| Keine Angabe | `#8a8580` | **dunkel**, 5.0:1 | `#55504b` | 8.0:1 |

Hier kehrt sich das Verhältnis um: **drei von vier** Labels brauchen dunkle Schrift, nur
Rot bleibt weiß — und das nur knapp mit 4.7:1.

## Der eigentliche Befund

Volle Ampelsättigung kostet die einheitliche Schriftfarbe im gefüllten Label. In E2 steht
ein weißes Rot-Label neben drei dunkel beschrifteten — die Labels wirken dadurch nicht
mehr wie eine Familie, sondern wie vier Einzelfälle. E1 hält diese Einheitlichkeit weit
besser (nur Gelb fällt heraus) und ist trotzdem deutlich signalhafter als D1.

Wer die volle Ampel will, müsste konsequenterweise **alle** gefüllten Labels auf dunkle
Schrift stellen, auch Rot. Das ist als dritte Variante nachrüstbar, war aber nicht
angefragt.

## Offen

- Die Kartenkante nutzt den Signalton. In E2 ist die gelbe Kante bei
  `aeltere_kinder` (31 von 47 Katzen) sehr präsent — das ist der Ton, der die
  Gesamtwirkung am stärksten bestimmt.
- Dark Mode weiterhin nicht vorgesehen.
