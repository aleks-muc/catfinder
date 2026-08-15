# Catfinder

Findet neue Katzen beim [Tierschutzverein München](https://tierschutzverein-muenchen.de/tiervermittlung/tierheim/katzen) und bewertet sie via Claude API automatisch auf **Kindertauglichkeit** und **gesundheitlichen Pflegeaufwand**. Ergebnis: filterbarer HTML-Report mit Farbcodierung und Direkt-Link zum Steckbrief.

Bewertung Kinder: *Kinder geeignet* · *Nur ältere Kinder* · *Nicht für Kinder* · *Keine Angabe*
Bewertung Gesundheit: *Keine Erkrankung bekannt* · *Gesundheit beachten* · *Dauerbehandlung nötig* · *Gesundheit unbekannt*

## Setup

```bash
cd /Users/aleksandarotasevic/Coding/Catfinder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Anthropic-API-Key setzen (in `~/.zshrc` oder temporär):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Bedienung

```bash
python catfinder.py              # Standard: nur neue Katzen seit letztem Lauf bewerten
python catfinder.py --all        # Alle aktuell gelisteten Katzen bewerten
python catfinder.py --reset      # State löschen → alle wieder als "neu" behandeln
python catfinder.py --no-browser # Report nur schreiben, nicht öffnen (nutzt die CI)
```

Der Report wird nach `reports/report.html` geschrieben und automatisch im Default-Browser geöffnet.

Die Selbst-Checks laufen ohne Framework, ohne Netz und ohne API-Key direkt gegen den vorhandenen State:

```bash
.venv/bin/python test_pairs.py
.venv/bin/python test_report_sections.py
.venv/bin/python test_interested_refresh.py
```

## Wie es funktioniert

1. **Scrape** der Listenseite → alle ~50 Katzen mit ID, Name, Foto, Stammdaten.
2. **Diff** gegen `state/seen_cats.json` → nur neue Einträge werden von Claude bewertet.
3. **Fetch** jeder Steckbriefseite (mit 400 ms Pause, höflicher User-Agent) — für *alle* gelisteten Katzen, nicht nur die neuen. Sonst würde der Interessenten-Status bekannter Katzen nie nachziehen.
4. **Bewertung via Claude Haiku 4.5** — strukturierte Ausgabe (Pydantic), System-Prompt gecacht → ab Katze 2 billiger. Bereits bekannte Katzen behalten ihre gespeicherte Bewertung und kosten nichts.
5. **HTML-Report** in vier Abschnitten, jeweils nach Bewertung sortiert (grün zuerst, rot zuletzt):
   - *Neu seit letztem Lauf*
   - *Nicht mehr verfügbar*
   - *Interessenten vorhanden* — Katzen, für die sich schon jemand gemeldet hat
   - *Weiterhin verfügbar*

   Dazu eine Filterleiste (Alter, Bewertung, Gesundheit, Pärchen) — reines Inline-JS, kein Build-Step.
6. **State speichern** — anschließend werden alle Einträge entfernt, die nicht mehr im aktuellen Listing stehen.

## Erstlauf

Beim ersten Lauf gelten alle gelisteten Katzen als neu → ~50 Claude-Calls (wenige Cent mit Haiku + Prompt-Caching). Danach bewertet jeder Lauf nur die Neuzugänge.

## Automatischer Betrieb

Der Workflow `.github/workflows/catfinder.yml` läuft einmal täglich per Cron (`30 10` UTC — 12:30 Uhr MESZ) und zusätzlich auf Knopfdruck via *workflow_dispatch*. Ein Lauf:

1. führt `catfinder.py --no-browser` aus,
2. committet `state/seen_cats.json` und `docs/index.html` zurück nach `main` (`chore: state & report aktualisiert [skip ci]`),
3. schickt bei neuen Katzen eine **ntfy-Push-Benachrichtigung** mit Link auf den Report — und ebenso eine, wenn der Lauf fehlschlägt.

Der Report liegt öffentlich unter <https://aleks-muc.github.io/catfinder/> (GitHub Pages aus `docs/`).

Benötigte Repository-Secrets: `ANTHROPIC_API_KEY` und `NTFY_TOPIC`.

## Dateien

- `catfinder.py` — Hauptskript
- `test_*.py` — assert-basierte Selbst-Checks (kein pytest)
- `state/seen_cats.json` — bekannte Katzen (wird automatisch gepflegt)
- `reports/report.html` — letzter lokaler Report (wird überschrieben)
- `docs/index.html` — von der CI veröffentlichter Report (GitHub Pages)
- `.github/workflows/catfinder.yml` — Zeitplan, Commit, Push-Benachrichtigung
