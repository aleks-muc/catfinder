# Phase 1: Delta-basiertes "Nicht mehr verfügbar" - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Der HTML-Report zeigt in der "Nicht mehr verfügbar"-Sektion ausschließlich Katzen, die seit dem unmittelbar vorigen Lauf vom Listing verschwunden sind. `state/seen_cats.json` enthält nach jedem Lauf nur noch Katzen, die im aktuellen Listing standen — keine Zombies. Wenn nichts verschwunden ist, zeigt die Sektion einen klaren Hinweistext (außer bei Erstlauf / `--reset`, wo sie ausgeblendet bleibt).

Deckt REPORT-01, REPORT-02, REPORT-03 vollständig ab.

</domain>

<decisions>
## Implementation Decisions

### State-Schema & Delta-Quelle
- **D-01:** State bleibt **flat dict** `{cat_id → entry}` — keine Schema-Erweiterung, kein neues `_meta`-Feld. Die Semantik ändert sich: State repräsentiert ab jetzt "Katzen aus dem unmittelbar vorigen Lauf", nicht mehr "alle je gesehenen Katzen".
- **D-02:** **Hard-Purge** als Teil des Save-Schritts — nach Rendering werden alle State-Einträge entfernt, deren `cat_id` nicht im aktuellen Listing steht. Delta für die "Nicht mehr verfügbar"-Sektion = `previous_state.keys() − current_listing_ids` (berechnet vor dem Purge, gerendert in den Report).
- **D-03:** **Kein Sicherheitsnetz** gegen versehentliches Massen-Purge bei sehr kleinem Listing. Der bestehende `RuntimeError` in `scrape_listing` (catfinder.py:213-217) bei 0 gefundenen Katzen ist die einzige Schutzlinie und reicht für den privaten Use-Case (`--reset` ist trivialer Recovery-Pfad).

### Zombie-Migration beim Erstlauf
- **D-04:** **Big-Bang Approach** — kein Migrations-Sondercode. Beim ersten Lauf nach Deploy wird der bestehende, mit Zombies gefüllte State semantisch wie ein "voriger Lauf" behandelt. Das Delta gegen das aktuelle Listing erzeugt eine einmalig sehr lange "Nicht mehr verfügbar"-Sektion; danach ist der State sauber und das Verhalten regulär. Akzeptabler einmaliger Lärm — keine Marker-Felder, keine Schema-Versions-Logik.
- **Implikation für die E-Mail:** Subject bleibt `Catfinder – 0 neue Katzen` falls keine Neuen evaluiert werden, aber der Body-Report enthält die Zombie-Liste. CI-Commit (`chore: state & report aktualisiert`) bleibt identisch — nur der State-Diff ist beim Erstlauf groß. Konsistent mit PROJECT.md-Constraint zur Bot-Commit-Stabilität.

### Empty-State Wording & Visual
- **D-05:** Hinweistext: **"Seit dem letzten Lauf sind keine Katzen verschwunden. ✨"**
- **D-06:** Visueller Stil: **Wiederverwendung des bestehenden `<div class="empty">…</div>` Patterns**, das aktuell für die "Neu seit letztem Lauf"-Sektion verwendet wird (catfinder.py:605, Style im inline CSS in `HTML_TEMPLATE` ab catfinder.py:498). Kein neues CSS, keine neuen Klassen. Gleiches Muster, gleiches Look-and-Feel.

### Sektion bei Erstlauf / --reset
- **D-07:** **Sektion komplett ausblenden** wenn der State zu Beginn des Laufs leer war — also bei Erstlauf, nach `--reset`, oder beim Cold-Start in CI. Die `scope_note`-Logik (catfinder.py:736-739, "· Erstlauf" / "· alle bewertet") wird als Erkennungs-Hook genutzt, oder direkter Check `not state` vor dem Rendering. Empty-State-Hinweis (D-05/D-06) erscheint **nur** wenn voriger State nicht-leer war und im aktuellen Lauf nichts verschwand.
- **`--all`-Verhalten:** Bei `--all` mit nicht-leerem State bleibt die Sektion verhaltensgleich zum regulären Lauf — `--all` betrifft Re-Evaluation, nicht das Delta. Zombies werden auch hier gepurged.

### Claude's Discretion
- Genaue Reihenfolge und Atomicity der Schritte "compute disappeared" → "render report" → "mutate state" → "save_state" innerhalb von `main()` — atomic save reicht (heutiges `tempfile.mkstemp` + `os.replace`-Pattern in catfinder.py:139-147 bleibt).
- Position der "Nicht mehr verfügbar"-Sektion im Report — heute zwischen "Neu" und "Weiterhin verfügbar" (catfinder.py:686), bleibt so außer der Planner findet einen Grund zum Tausch.
- Sortierung in der Sektion bleibt `_card_sort_key` (catfinder.py:484-491) — gleiche Logik wie heute.
- Gegenwärtige Visual-Treatment der Zombie-Cards (graue Buttons, `opacity:.6`, catfinder.py:643-654) bleibt unverändert.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Phase Specifications
- `.planning/PROJECT.md` — Constraints (Single-File-Code, kein neues Runtime-Dep, State-Format-Stabilität, CI-Commit-Stabilität), Out-of-Scope (keine Modularisierung, keine Tests, keine Backwards-Compat-Wrapper), Key Decisions (kein Zeitfenster, kein Soft-Delete).
- `.planning/REQUIREMENTS.md` — REPORT-01..03 als die in dieser Phase abgedeckten REQs; explizite Out-of-Scope-Liste (u.a. konfigurierbares Zeitfenster, State-Migration-Wrapper).
- `.planning/ROADMAP.md` §"Phase 1" — Goal-Statement und 5 Erfolgskriterien (insb. Krit. 4: Zombies dürfen still gepurged ODER per Delta gemeldet werden — beides erlaubt; Krit. 5: CI-Commit-Form bleibt).

### Codebase Maps
- `.planning/codebase/ARCHITECTURE.md` — Pipeline-Überblick, Persistence Layer, Data Flow incl. heutige `known_ids - current_ids`-Semantik (Zeile 114), Anti-Patterns (insb. "Mixing rendering and business logic" — beachten beim Vergrößern von `render_report`).
- `.planning/codebase/STRUCTURE.md` §"Where to Add New Code" — Wo neue State-Logik landet (catfinder.py:126-147), wo Report-Sektionen hinzugefügt werden (catfinder.py:603-678).

### Implementation Touchpoints
- `catfinder.py:126-147` — `load_state` / `save_state` (atomic write Pattern bleibt). Purge-Logik integriert sich hier oder in `main()`.
- `catfinder.py:733-779` — `main()`-Block, in dem heute `known_ids - current_ids` für `no_longer_listed` gebildet wird; zentraler Edit-Punkt für Delta-Logik.
- `catfinder.py:498-545` — `HTML_TEMPLATE` mit inline CSS, inkl. `.empty`-Klasse für Empty-State.
- `catfinder.py:603-678` — Sektion-Rendering in `render_report`; Zombie-Section bei catfinder.py:636-655.
- `catfinder.py:842-856` — heutiges State-Update am Lauf-Ende; Hier muss der Purge eingreifen.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`<div class="empty">…</div>`-Pattern** (catfinder.py:605): exakter Empty-State-Stil für "Keine neuen Katzen seit dem letzten Lauf. 🎉" wird 1:1 für die neue "Nichts verschwunden"-Anzeige übernommen. Kein neues CSS.
- **`tempfile.mkstemp` + `os.replace`-Pattern** in `save_state` (catfinder.py:136-147): atomic write bleibt für den State-Schreib-Pfad nach Purge. Garantie: kein halb-geschriebener State auch wenn Crash zwischen Purge und Disk-Write.
- **`_card_sort_key`** (catfinder.py:484-491): Sortierung der Verschwundenen bleibt deterministisch (Rating, Pärchen, Partner-Adjazenz).
- **`_ratings_from_state`** (catfinder.py:745-756) und der Rebuild-Block (catfinder.py:761-778) für `no_longer_listed`: Liefern heute schon `(Cat, CatRating)`-Tupel aus dem State; gleiche Mechanik wird für die Delta-Berechnung beibehalten — nur die Quellmenge ändert sich nicht semantisch (state-vor-Lauf), aber das Subset-Verhältnis ändert sich, weil State nun pro Lauf komprimiert wird.

### Established Patterns
- **Single-file convention** (siehe `.planning/codebase/CONVENTIONS.md`): Neue Logik landet als Funktion im passenden Section-Banner-Block (`# --- State ---` für Persistenz-Helfer; `# --- Main ---` für Orchestration).
- **German user-facing strings**: Alle Logs (`Warnung:`, `Fehler:`), HTML-Texte und Section-Titel in Deutsch — Empty-State-Text "Seit dem letzten Lauf sind keine Katzen verschwunden. ✨" folgt diesem Konvention.
- **Defensive Default für `RATING_META.unbekannt`-Fallback** (catfinder.py:750-751, 776-777): Auch verschwundene Katzen mit unklarem Rating werden ohne Crash gerendert.
- **Type Hints durchgehend** (PEP 604 mit `from __future__ import annotations`): Neue Helper bekommen vollständige Annotations; Return-Types `set[str]`, `list[tuple[Cat, CatRating]]` sind etabliert.

### Integration Points
- **Delta-Berechnung sitzt in `main()`** zwischen `state = load_state()` (catfinder.py:733) und dem State-Update-Block (catfinder.py:842-856). Konkret: nach dem `known_ids - current_ids`-Block (catfinder.py:760-778) — dort wird `no_longer_listed` heute schon erzeugt; das bleibt der Anchor.
- **Purge-Schritt** wird im selben `main()`-Block am Ende eingebaut, vor dem letzten `save_state(state)`. Variante: vor save_state alle `cat_id` aus `state` entfernen, deren Key nicht in `current_ids` steht.
- **Empty-State-Rendering** geschieht in `render_report` neben dem bestehenden `sect_gone`-Block (catfinder.py:636-655). Wenn `no_longer_listed` leer ist UND State vor Lauf nicht-leer war: rendere `<section><h2 class="group">🚫 Nicht mehr verfügbar (0)</h2><div class="empty">Seit dem letzten Lauf sind keine Katzen verschwunden. ✨</div></section>`. Wenn State leer war: gar nichts rendern (Sektion komplett ausblenden).
- **`render_report` braucht ein neues Signal**, ob der State zu Beginn des Laufs leer war — damit es zwischen "Erstlauf, ausblenden" und "regulärer Lauf, Empty-Hint" unterscheiden kann. Möglichkeiten: zusätzlicher Parameter `had_prior_state: bool` oder Inferenz aus Kombination der existierenden Parameter (`scope_note` enthält "Erstlauf"). Planner entscheidet.
- **CI-Pfad**: `.github/workflows/catfinder.yml` wird **nicht** angefasst. Commit-Message, Pages-URL, E-Mail-Subject bleiben strukturell gleich. Nur der Inhalt von `state/seen_cats.json` und `docs/index.html` ändert sich pro Lauf.

</code_context>

<specifics>
## Specific Ideas

- **Empty-State-Text exakt:** "Seit dem letzten Lauf sind keine Katzen verschwunden. ✨" — in dieser Wortwahl, mit Sparkles-Emoji am Ende, im `.empty`-CSS-Stil.
- **Sektion-Titel bei Empty-State:** Bleibt bei "🚫 Nicht mehr verfügbar" — Count-Suffix `(0)` oder Auslassen ist Detail-Frage des Planners. Konsistenz zu "Neu seit letztem Lauf (N)" und "Weiterhin verfügbar (N)" spricht für `(0)`.
- **Big-Bang-Akzeptanz:** Die User-Familie weiß, dass der erste Report nach Deploy lang sein wird (alle Zombies werden 1x gemeldet). Kein Banner, kein Sondertext nötig — Vertrauen in den Mechanismus.

</specifics>

<deferred>
## Deferred Ideas

- **Konfigurierbares Zeitfenster** für "Nicht mehr verfügbar" (z.B. "weg seit ≤ 7 Tagen") — explizit in Out-of-Scope (REQUIREMENTS.md) und PROJECT.md gelisetet. Nicht jetzt.
- **State-Statistik / Verlauf** ("Wann verschwand Katze X?", "Wie lange war sie sichtbar?") — würde ein zusätzliches `_meta`-Feld oder eine zweite State-Datei brauchen; bewusst nicht Teil dieses Milestones (Single-File, kein zusätzliches Schema).
- **Plausibilitäts-Check / Mass-Purge-Sicherung** — wenn Catfinder mal in einem Multi-User-Kontext laufen müsste, wäre eine Schutzlogik sinnvoll. Privat reicht `--reset` als Recovery.
- **Banner für den Big-Bang-Erstlauf** ("Achtung, einmaliger Bereinigungslauf — diese Liste schrumpft beim nächsten Mal") — verworfen als unnötig, kann später hinzugefügt werden falls die User:innen verwirrt sind.
- **Modularisierung von `catfinder.py`** — separate `state.py`, `report.py` etc. — explizit Out-of-Scope für diesen Milestone (PROJECT.md, ROADMAP.md Notes).

</deferred>

---

*Phase: 1-Delta-basiertes "Nicht mehr verfügbar"*
*Context gathered: 2026-05-05*
