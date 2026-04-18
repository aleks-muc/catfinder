# Catfinder

Findet neue Katzen beim [Tierschutzverein München](https://tierschutzverein-muenchen.de/tiervermittlung/tierheim/katzen) und bewertet sie via Claude API automatisch auf **Kindertauglichkeit**. Ergebnis: HTML-Report mit Ampel (🟢 geeignet · 🟡 nur ältere Kinder · 🔴 nicht geeignet · ⚪ unbekannt) und Direkt-Link zum Steckbrief.

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
python catfinder.py            # Standard: nur neue Katzen seit letztem Lauf bewerten
python catfinder.py --all      # Alle aktuell gelisteten Katzen bewerten
python catfinder.py --reset    # State löschen → alle wieder als "neu" behandeln
```

Der Report wird nach `reports/report.html` geschrieben und automatisch im Default-Browser geöffnet.

## Wie es funktioniert

1. **Scrape** der Listenseite → alle ~50 Katzen mit ID, Name, Foto, Stammdaten.
2. **Diff** gegen `state/seen_cats.json` → nur neue Einträge werden bewertet.
3. **Fetch** jeder Steckbriefseite (mit 400 ms Pause, höflicher User-Agent).
4. **Bewertung via Claude Haiku 4.5** — strukturierte Ausgabe (Pydantic), System-Prompt gecacht → ab Katze 2 billiger.
5. **HTML-Report** mit Ampel-Sortierung (grün zuerst, rot zuletzt).
6. **State speichern** — nur neue Einträge; vermittelte Katzen bleiben im State, damit wiederkehrende Einträge nicht fälschlich als „neu" erscheinen.

## Erstlauf

Beim ersten Lauf gelten alle gelisteten Katzen als neu → ~50 Claude-Calls (wenige Cent mit Haiku + Prompt-Caching). Danach bewertet jeder Lauf nur die Neuzugänge.

## Dateien

- `catfinder.py` — Hauptskript
- `state/seen_cats.json` — bekannte Katzen (wird automatisch gepflegt)
- `reports/report.html` — letzter Report (wird überschrieben)
