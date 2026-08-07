---
sketch: 006
name: bestfall-hervorheben
question: "Wie wird 'für Kinder geeignet und ohne bekannte Erkrankung' auf einen Blick erfassbar?"
winner: null
tags: [hierarchie, farbe, struktur]
builds-on: 005
---

# Sketch 006: Bestfall hervorheben

Aufsetzend auf [Sketch 005](../005-e1-gesund-gruen/). Drei Vorschläge, die absichtlich
**unterschiedliche Mechanismen** nutzen — Fläche, Text, Struktur. Sie sind kombinierbar,
werden hier aber einzeln gezeigt.

Bestfall im Bestand: **3 von 47** — KEVIN, HILDEGARD, RUDI.

## Vorschlag 1 — Die Card wird zum Signal

Blassgrüne Fläche `#eaf4ec` plus durchgehend grüner Rahmen statt grauer Haarlinie. Kein
neues Element, keine Änderung an Reihenfolge oder Labels.

- **Stärke:** wirkt als Fläche, nicht als Text — bleibt erkennbar, wenn beim Überfliegen
  längst nichts mehr lesbar ist. Der einzige Vorschlag, der aus zwei Metern noch trägt.
- **Preis:** die weiße Card ist im Report bisher konstant; eine getönte bricht diese Regel.
  Grüner Text auf der Tönung erreicht 7.2:1, Lesbarkeit ist also unkritisch.

## Vorschlag 2 — Ein Label statt zwei

Die beiden grünen Labels werden zu einer Aussage: **Geeignet und gesund**, etwas größer
gesetzt.

- **Stärke:** beseitigt die Doppelung aus Sketch 005 an der Wurzel, statt sie zu
  kaschieren. Der Bestfall ist daran erkennbar, dass diese Karten als einzige *ein* Label
  tragen statt zwei — eine Strukturaussage, kein zusätzliches Signal.
- **Preis:** funktioniert nur auf Lesedistanz. Beim schnellen Scrollen fällt ein fehlendes
  zweites Label kaum auf. Der leiseste der drei Eingriffe.

## Vorschlag 3 — Eigene Sektion mit Kopfband

Die Bestfälle stehen zusätzlich ganz oben in einem grün gerahmten Block
„Passt ohne Einschränkung", jede Card mit Kopfband über dem Foto.

- **Stärke:** man muss gar nicht scannen. Für den eigentlichen Zweck des Reports — „gibt es
  etwas, das passt?" — ist das die direkteste Antwort.
- **Preis:** die Katzen erscheinen doppelt, oben und in ihrer regulären Sektion. Bei 3 von
  47 vertretbar; würden es zwanzig, wäre der Report redundant. Ein Deckel („höchstens die
  ersten sechs") wäre dann nötig. Außerdem der größte Eingriff in `render_report` — die
  anderen beiden sind reine CSS-/Label-Änderungen.

## Einschätzung

**1 und 2 ergänzen sich** und stören sich nicht: die Fläche trägt auf Distanz, das
zusammengezogene Label räumt aus der Nähe auf. Zusammen kosten sie wenig Code.

**3 löst ein anderes Problem** — nicht „wie erkenne ich den Bestfall unter vielen", sondern
„wo fange ich an zu lesen". Wenn die Antwort meist null bis drei Treffer sind, ist das der
wirksamste Vorschlag; wenn die Familie ohnehin den Filter „nur geeignet" nutzt, ist er
weitgehend redundant zum Filter.

## Offen

- Der Bestfall ist hier hart als `geeignet` + `keine` definiert. Ob `unbekannt` bei der
  Gesundheit mitzählen soll (der Steckbrief war nicht ladbar, die Katze ist deshalb nicht
  krank), ist eine offene Frage.
- Dark Mode weiterhin nicht vorgesehen.
