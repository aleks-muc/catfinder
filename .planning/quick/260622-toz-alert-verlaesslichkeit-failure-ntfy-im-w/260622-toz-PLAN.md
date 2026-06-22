---
quick_id: 260622-toz
description: Alert-Verlässlichkeit — Failure-ntfy im Workflow (B) + "seit X Tagen gelistet" im Report (C)
date: 2026-06-22
status: ready
---

# Quick Task 260622-toz — Alert-Verlässlichkeit (B + C)

Zwei unabhängige, kleine Verbesserungen am Core Value ("Familie erfährt zuverlässig
von geeigneten Neuzugängen"). Zwei atomare Commits.

## Task 1 (B): Fehler-Benachrichtigung im CI-Workflow

**files:** `.github/workflows/catfinder.yml`

**Problem:** Schlägt der Lauf fehl (Scrape-Layout-Änderung → `RuntimeError`, API/Netz),
gibt es heute keinen Push. Stille wird als "nichts Neues" fehlinterpretiert (False
Negative auf das Kernversprechen).

**action:** Neuen letzten Step ergänzen, der **nur bei Job-Fehler** einen ntfy-Push
sendet (analog zum bestehenden Erfolgs-Push, gleicher `NTFY_TOPIC`-Secret):

```yaml
      - name: Fehler-Benachrichtigung senden
        if: failure()
        env:
          NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
        run: |
          curl -fsS \
            -H "Title: Catfinder-Lauf fehlgeschlagen" \
            -H "Priority: high" \
            -H "Tags: warning" \
            -H "Click: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}" \
            -d "Der geplante Lauf ist fehlgeschlagen — Listing-Layout, API oder Netz prüfen." \
            "https://ntfy.sh/${NTFY_TOPIC}"
```

`if: failure()` greift unabhängig davon, welcher vorherige Step gefehlt hat.
Title bleibt ASCII (ntfy-Header-Konvention); Emoji nur via `Tags`.

**verify:** `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/catfinder.yml')); print('yaml ok')"`.
Bestehender Erfolgs-Push-Step (`if: steps.catfinder.outputs.new_count > 0`) bleibt unverändert.

**done:** Genau ein neuer Step mit `if: failure()`; YAML valide; keine anderen Steps berührt.

## Task 2 (C): "seit X Tagen gelistet" im Report

**files:** `catfinder.py`

**Problem:** `first_seen` liegt im State (`catfinder.py` State-Write), wird aber nirgends
angezeigt. Eine Dauer-Zeile gibt der Familie ein Dringlichkeitssignal.

**Design (vom Nutzer bestätigt):** Eigene Zeile `📅 seit X Tagen gelistet`, frisch =
`seit heute gelistet`. Sichtbar in "Neu" + "Weiterhin verfügbar", **nicht** in
"Nicht mehr verfügbar" (dort sinnlos).

**action:**
1. Neuer Parameter `first_seen_map: dict[str, str] | None = None` in `render_report`.
2. Innerhalb `render_report` zwei Closures (bei `get_age`):
   - `get_listed_days(cat_id) -> int`: liest `first_seen_map[cat_id]`, parst via
     `datetime.fromisoformat(...).date()`, gibt `max(0, (date.today() - d).days)`;
     fehlend/unparsebar → `0`.
   - `_listed_line(cat) -> str`: `0 → "seit heute gelistet"`, `1 → "seit 1 Tag gelistet"`,
     sonst `f"seit {days} Tagen gelistet"`; gibt `<div class="listed">📅 {txt}</div>`.
3. In `_render_card`: Zeile nach `<div class="meta">…</div>` einsetzen, aber nur wenn
   **nicht** `dimmed` (gone-Sektion bleibt ohne Dauer): `{"" if dimmed else _listed_line(cat)}`.
4. CSS in `HTML_TEMPLATE`-`<style>`: `.card .listed {{ font-size:.85rem; color:#888; }}`.
5. `first_seen_map` an **beiden** `render_report`-Aufrufen in `main` übergeben:
   `{cid: state[cid].get("first_seen", "") for cid in state}`. Neue (noch nicht im State
   gespeicherte) Katzen fehlen in der Map → `get_listed_days` = 0 → "seit heute". Korrekt,
   da neue Katzen genau heute zuerst gesehen werden.

**verify:**
- `python3 -c "import ast; ast.parse(open('catfinder.py').read())"`.
- Fixture-Render (zwei Cats mit unterschiedlichem `first_seen`, eine in "gone"):
  Ausgabe enthält `seit heute gelistet` für eine frische, `seit N Tagen gelistet` für
  eine ältere, und **keine** `listed`-Zeile in der "Nicht mehr verfügbar"-Card.

**done:** Dauer-Zeile in Neu + Weiterhin sichtbar, in Gone nicht; Datum aus `first_seen`;
keine Exceptions bei fehlendem/kaputtem `first_seen`.

## Out of scope
- A/D/E aus dem Direction-Audit. Keine neuen Dependencies (PyYAML nur für lokalen
  Verify-Check, nicht als Runtime-Dep). Rating-Logik/Diff/State-Format unverändert.
