---
quick_id: 260622-sd4
description: Restliche ponytail-Audit-Punkte (has_unknown, _pair_attr, detect_interested, Rating-Whitelist)
date: 2026-06-22
status: complete
commit: eb0118e
---

# Quick Task 260622-sd4 — Summary

## Was gemacht wurde

Vier verhaltensneutrale Over-Engineering-Cleanups in `catfinder.py`:

1. **delete:** ungenutzter `has_unknown`-Parameter aus `_build_filter_bar`
   (Signatur + Call-Site).
2. **yagni:** `_pair_attr`-Closure entfernt → `data-companions="{cat.companion_count}"`
   direkt im f-string.
3. **shrink:** `detect_interested`-Wrapper entfernt → `bool(INTERESTED_PATTERN.search(text))`
   an der einzigen Aufrufstelle.
4. **shrink:** doppelte Rating-Whitelist (`if r not in (...): r = "unbekannt"`) zu
   Modul-Helper `_safe_rating(value)` zusammengeführt (2 Call-Sites).

## Verifikation

- `ast.parse(catfinder.py)` fehlerfrei.
- `grep`: 0 Vorkommen von `has_unknown` / `_pair_attr` / `detect_interested`;
  `_safe_rating` = 1 Def + 2 Calls.
- Fixture-Render-Diff (5 Cards, alle drei Sektionen, Timestamp gefiltert):
  **leer**, 11661 Bytes vor und nach. HTML-Output unverändert.

## Commit

- `eb0118e` refactor: restliche ponytail-Audit-Punkte aufräumen

## Audit-Status

Damit sind alle Punkte des ponytail-Audits abgearbeitet
(Card-Helper in [[260622-s6i]], diese vier hier). `net: -45 lines` erreicht.
