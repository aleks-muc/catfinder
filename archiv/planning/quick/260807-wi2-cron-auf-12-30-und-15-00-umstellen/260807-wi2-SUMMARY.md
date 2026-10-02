---
quick_id: 260807-wi2
description: Cron-Zeiten des CI-Laufs auf 12:30 und 15:00 Uhr lokal umstellen
date: 2026-08-07
status: complete
commits: [11b7811]
---

# Quick Task 260807-wi2 — Summary

`.github/workflows/catfinder.yml`: beide `cron`-Ausdrücke ersetzt.

| | vorher | nachher |
|---|---|---|
| Lauf 1 | `0 7 * * *` → 09:00 CEST | `30 10 * * *` → 12:30 CEST |
| Lauf 2 | `0 14 * * *` → 16:00 CEST | `0 13 * * *` → 15:00 CEST |

Kommentare auf die neuen Klartext-Zeiten gezogen (inkl. Winterzeit-Angabe).
`workflow_dispatch` und alle 8 Job-Steps unberührt.

## Entscheidung: Zeitzone

Auf **Sommerzeit (CEST = UTC+2)** fixiert. GitHub-Actions-Cron kennt kein
`TZ:`-Feld, nur UTC — im Winter laufen die Jobs dadurch eine Stunde früher
lokal (11:30 / 14:00 CET). Bewusst akzeptiert; die Alternative (vier
Cron-Einträge plus Skip-Guard-Step, der die lokale Stunde prüft) rechtfertigt
sich nicht, da GitHub geplante Runs unter Last ohnehin routinemäßig 10–30 min
verspätet startet.

- Verify: `yaml.safe_load` → `['30 10 * * *', '0 13 * * *']`, `workflow_dispatch` vorhanden, 8 Steps.
- Diff: 2 Zeilen geändert.
- Commit `11b7811`.

## Kontext

Erste von drei Ideen aus der Session-Planung. Offen: Krankheits-Feld
(`/gsd-plan-phase`) und Design-Auffrischung ohne Emojis (`/gsd-sketch`).
