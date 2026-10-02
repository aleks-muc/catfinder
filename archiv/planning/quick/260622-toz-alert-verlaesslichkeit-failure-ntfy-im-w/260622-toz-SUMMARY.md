---
quick_id: 260622-toz
description: Alert-Verlässlichkeit — Failure-ntfy (B) + "seit X Tagen gelistet" (C)
date: 2026-06-22
status: complete
commits: [2da54d1, 5b8d6bc]
---

# Quick Task 260622-toz — Summary

Zwei Direction-Findings aus `/improve next` umgesetzt, je ein atomarer Commit.

## Task 1 (B) — Fehler-Benachrichtigung im CI

`.github/workflows/catfinder.yml`: neuer Step `Fehler-Benachrichtigung senden`
mit `if: failure()`, der bei jedem fehlgeschlagenen Lauf einen ntfy-Push sendet
(gleicher `NTFY_TOPIC`-Secret, Click-Link auf den Actions-Run). Schließt die
False-Negative-Lücke — Stille wird nicht mehr fälschlich als "nichts Neues" gelesen.
Erfolgs-Push (`new_count>0`) unverändert.

- Verify: YAML valide (`yaml.safe_load`), genau ein neuer Step.
- Commit `2da54d1`.

## Task 2 (C) — "seit X Tagen gelistet" im Report

`catfinder.py`: neuer Parameter `first_seen_map` in `render_report`, plus Closures
`get_listed_days` (parst `first_seen` via `datetime.fromisoformat`) und `_listed_line`.
Eigene Card-Zeile `📅 seit X Tagen gelistet` (frisch → "seit heute"), gerendert in
"Neu" + "Weiterhin verfügbar", **nicht** in "Nicht mehr verfügbar" (`dimmed`-Gate).
CSS `.card .listed` ergänzt. Beide `render_report`-Aufrufe in `main` übergeben die
Map aus dem State. Robust gegen fehlendes/kaputtes `first_seen` (→ 0 Tage).

- Verify (Fixture-Render): frisch/neu → "seit heute" (2×), 5 Tage → "seit 5 Tagen" (1×),
  Gone-Card ohne Dauer-Zeile, CSS vorhanden, `ast.parse` ok.
- Commit `5b8d6bc`.

## Quelle

Direction-Audit `/improve next` — Optionen B + C (vom Nutzer gewählt).
Offen aus dem Audit: A (Relevanz-Push), D (Eignungs-Achsen), E (Dismiss) — nicht verfolgt.
