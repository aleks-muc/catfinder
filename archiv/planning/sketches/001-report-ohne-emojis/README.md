---
sketch: 001
name: report-ohne-emojis
question: "Wie lesen sich Bewertung und Gesundheit ohne Emoji — und wie viel Struktur braucht die Card?"
winner: null
tags: [layout, typografie, farbe]
---

# Sketch 001: Report ohne Emojis

## Design Question

Die Emojis tragen heute Bedeutung: `🟢/🟡/🔴` codieren die Kindertauglichkeit, `💊` die
Dauerbehandlung, `🐱🐱` das Pärchen. Fallen sie weg, muss diese Information anders
transportiert werden. Die drei Varianten unterscheiden sich genau darin — und darin,
wie viel Kastenstruktur die Card behält.

## Varianten

**A — Haarlinien & Kapitälchen.** Keine Karten, keine Schatten. Einträge stehen frei auf
dem Papier, getrennt durch Weißraum und feine Linien. Bewertung als gesperrte Versalzeile
mit kurzem Farbstrich davor, Gesundheit als eingerückte Notiz mit Randlinie. Filterleiste
rein typografisch, aktiver Zustand durch Unterstreichung.
*Am ruhigsten, am weitesten weg vom Ist-Zustand — die Bewertung ist dafür leiser.*

**B — Stiller Rahmen.** Die Card bleibt Fläche, verliert aber Schatten und Rundung: weiß
auf Papierton, 1px Haarlinie. Bewertung und Gesundheit als umrandete Chips nebeneinander.
Filterbuttons gefüllt statt unterstrichen.
*Am schnellsten zu scannen, konservativster Schritt — Struktur bleibt, Oberfläche wechselt.*

**C — Farbkante.** Führt die farbige Kante des heutigen Reports fort, aber schmaler (3px
statt 6px) und gedeckt. Name in der Serife, Bewertung typografisch in der Akzentfarbe.
*Kompromiss: Bewertung bleibt auf Distanz erkennbar, ohne dass Chips den Blick zerteilen.*

## Aufbau

Eine Datei, drei Tabs (Klick oder Tasten 1/2/3). Jede Variante zeigt den kompletten
Report: Header, Filterleiste, alle drei Sektionen (neu / weiterhin verfügbar / nicht mehr
verfügbar). Die Filterbuttons sind klickbar, damit der aktive Zustand beurteilbar ist.

**Echte Daten** aus `state/seen_cats.json`, ausgewählt für Abdeckung: alle vier
Bewertungsstufen (`geeignet`, `aeltere_kinder`, `nicht_geeignet`, `unbekannt`), alle drei
sichtbaren Gesundheitswerte, ein Pärchen (MATILDA / CONSTANTIN CHRISTOMANOS), eine Katze
mit Interessenten (BRAUNIE), und mit CONSTANTIN CHRISTOMANOS der längste Name im Bestand
als Umbruch-Härtetest.

Die Fotos werden wie im echten Report extern geladen — die Datei braucht eine
Internetverbindung, sonst bleiben die Bildflächen grau.

## Offen

- Dark Mode ist in keiner Variante vorgesehen. Der Report wird meist per ntfy-Link am
  Handy geöffnet; falls das gewünscht ist, wäre es ein eigener Sketch.
- Die gedeckte Palette (`--moss` / `--ochre` / `--clay`) senkt den Kontrast gegenüber den
  heutigen Signalfarben bewusst ab. Ob "nicht für Kinder" damit noch deutlich genug
  absticht, ist die Frage, die am ehesten gegen die Richtung sprechen könnte.

## Generator

Das Mockup ist aus `scratchpad/gen_sketch.py` erzeugt, nicht von Hand geschrieben — bei
30 Cards war das der kürzere Weg. Das Skript ist Wegwerfcode und liegt bewusst nicht im
Repo; die Datei hier ist das Artefakt.
