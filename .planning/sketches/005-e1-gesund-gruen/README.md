---
sketch: 005
name: e1-gesund-gruen
question: "Trägt Grün für 'gesund', obwohl die Kindertauglichkeit dieselbe Farbe nutzt?"
winner: null
tags: [farbe, semantik]
builds-on: 004
---

# Sketch 005: E1, gesund = grün

Einzige Änderung gegenüber **E1** aus [Sketch 004](../004-signalfarben/): die
Gesundheitskategorie `keine` wechselt von Grau auf Grün. `unbekannt` bleibt Grau.

## Gesundheits-Kategorien

| Wert | Label | Rahmen | Text | Kontrast |
|---|---|---|---|---|
| `keine` | Keine Erkrankung bekannt | `#1e7a35` Grün | `#145c26` | 8.1:1 |
| `erwaehnt` | Gesundheit beachten | `#c9880a` Gelb | `#8a5c00` | 5.8:1 |
| `dauerbehandlung` | Dauerbehandlung nötig | `#c62020` Rot | `#971616` | 8.6:1 |
| `unbekannt` | Gesundheit unbekannt | `#6b6560` Grau | `#4d4843` | 9.0:1 |

Damit ist der Unterschied behoben, der in Sketch 004 farblich unterging: „geprüft, nichts
gefunden" (grün) gegen „Steckbrief nicht ladbar" (grau) waren vorher beide grau und nur am
Wortlaut zu unterscheiden.

Die Legende oben im Mockup zeigt alle acht Labels nebeneinander — `Gesundheit unbekannt`
kommt im echten Datensatz nicht vor, weil aktuell jede der 47 Katzen einen Gesundheitswert
trägt.

## Der Nebeneffekt, der bewusst in Kauf genommen wurde

Kindertauglichkeit und Gesundheit teilen sich jetzt Grün. Eine Katze, die für Kinder
geeignet **und** gesund ist, zeigt zwei grüne Labels übereinander — das gefüllte oben,
das umrandete darunter.

Im Bestand betrifft das **3 von 47** Katzen: KEVIN, HILDEGARD und RUDI. Zwei davon
(KEVIN, HILDEGARD) stehen in der Sektion "Neu seit letztem Lauf" ganz oben im Mockup und
sind sofort sichtbar.

Der Fall ist selten, aber es ist der *wünschenswerteste* Fall — die Katzen, die die
Familie eigentlich sucht. Dass ausgerechnet diese Karten am wenigsten differenziert
wirken, ist die Kehrseite. Die Füllung gegen den Umriss trägt den Unterschied; ob das
reicht, entscheidet der Blick.

Falls es stört, ohne die Semantik aufzugeben: das Gesundheits-Label könnte im Positivfall
ganz entfallen (wie ursprünglich in Sketch 002) oder einen abweichenden Grünton bekommen.

## Offen

- Dark Mode weiterhin nicht vorgesehen.
