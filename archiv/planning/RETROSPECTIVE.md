# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Delta + Filter-Reset

**Shipped:** 2026-05-06
**Phases:** 2 | **Plans:** 2 | **Sessions:** 2 (Phase 1 + Phase 2 jeweils ein Session-Durchlauf)

### What Was Built

- Delta-Modus für die "Nicht mehr verfügbar"-Sektion: Report zeigt nur Run-zu-Run-Verschwinden statt Vollhistorie (REPORT-01).
- Hard-Purge des State-Files: verschwundene Katzen fliegen sofort raus, keine Zombies (REPORT-02).
- Empty-State-Hinweis "Seit dem letzten Lauf sind keine Katzen verschwunden" wenn nichts verschwunden ist (REPORT-03).
- Reset-Button "↺ Filter zurücksetzen" rechts in der Filterleiste mit atomarem single-`update()`-Reset (FILTER-01, FILTER-02).
- Single-File-Disziplin gehalten: 31 Zeilen netto in `catfinder.py`, kein neues Modul, keine neuen Dependencies.

### What Worked

- **CONTEXT.md mit gelockten Decisions vor dem Plan**: D-01..D-07 in Phase 2 hat den Planner und Executor durchgängig konkret gehalten — keine vagen Entscheidungen, keine Re-Plan-Iterationen. Plan-Checker hat first-iteration `VERIFICATION PASSED` zurückgegeben.
- **Pattern-Mapper vor dem Planner**: `02-PATTERNS.md` mit line-anchored Excerpts aus `_build_filter_bar` (pairBtn/fitBtn/sorgBtn-Handler als Analoga) hat den Executor präzise gemacht — der Reset-Handler folgt 1:1 der existierenden IIFE-Struktur.
- **Checkpoint-Pattern (Task 5 = checkpoint:human-verify)**: Manueller Browser-Smoke-Test für visuell-CSS-abhängige Akzeptanz (D-02 Link-Stil) — günstiger als automatischer Visual-Regression-Setup. User-Approval an genau einer Stelle, Continuation-Agent schreibt SUMMARY.md.
- **`--skip-research` für kleine, gut-verstandene Phasen**: Phase 2 brauchte keine externe Recherche — Domänenwissen lag in CONTEXT.md.

### What Was Inefficient

- **Phase 2 Roadmap-Notes "Kein UI-SPEC nötig" wurde vom Workflow nicht erkannt** — gsd-plan-phase hat trotzdem den UI-Gate ausgelöst und gefragt. User-Question war OK, aber ein flag (`--skip-ui` automatisch aus ROADMAP-Note ableiten?) wäre eleganter.
- **REQUIREMENTS.md-Update beim Phase-Complete unzuverlässig**: `gsd-tools phase complete` hat `requirements_updated: true` zurückgegeben, aber FILTER-01/02 standen weiter auf "Pending". Manueller Edit war nötig vor dem Milestone-Close.
- **Branch-Push-Reihenfolge**: Tag wurde vor Main gepusht → erste Push-Iteration scheiterte (remote ahead durch CI-Bot-Commit), retag + force-push nötig. Reihenfolge "fetch → rebase → push main → push tag" wäre clean von Anfang an gewesen.

### Patterns Established

- **CONTEXT.md mit nummerierten D-IDs als Locked-Decisions**: D-01..D-07 als atomare Entscheidungs-Anker im Plan und in jedem Task-`<read_first>` referenziert. Reduziert Drift.
- **Single-Plan-Phasen für atomare Single-File-Edits**: Phase 2 (4 Sub-Edits + 1 Checkpoint = 5 Tasks in 1 Plan) statt 4 Micro-Plans. Decision-Rationale: alle Sub-Edits müssen zusammen getestet werden.
- **Slider-Null-Tolerance als Domain-Pattern**: `if(minR)minR.value=...` für conditional-rendered Slider-Block. Wird wieder kommen, wenn andere conditional-rendered Inputs hinzukommen.
- **F-string-Brace-Escaping als bekannte Falle**: doubled `{{ }}` für CSS/JS-Literals, einfaches `{name}` für Python-Interpolation. Bei jeder `_build_filter_bar`-Änderung explizit checken.

### Key Lessons

1. **Pattern-Mapping vor Planning lohnt sich auch bei kleinen Änderungen**: Phase 2 hat in ~80 Sekunden Pattern-Mapper-Lauf alle Analoga aufgelistet — der Planner war dann minutenlang konkreter.
2. **Manueller Browser-Smoke-Test als Checkpoint ist legitim für visuell-zentrische UIs**: Wenn das Projekt keine Visual-Regression-Tests hat, ist `checkpoint:human-verify` sauberer als heuristische Pseudo-Verifikation. Der Cost ist 1 Klick + 1 Augen-Check.
3. **CI-Bot-Commits in den Workflow einplanen**: GitHub-Actions pushen `state/seen_cats.json` und `docs/index.html` zwischen lokalen Sessions zurück. Vor jedem `git push` ein `git fetch + rebase` einplanen.
4. **`--skip-research` nicht aus Faulheit, sondern wenn CONTEXT.md komplett ist**: Bei Phase 2 war alles in 7 D-IDs gelockt — Recherche hätte nichts hinzugefügt. Bei Phasen mit echtem Domain-Unbekannten weiter Research nutzen.

### Cost Observations

- Model mix für die Planning/Execution-Pipeline: Pattern-Mapper sonnet, Planner opus, Plan-Checker sonnet, Executor sonnet, Verifier sonnet, Code-Reviewer sonnet. Opus nur dort eingesetzt, wo Reasoning über Decisions+Constraints stattfindet.
- Sessions: 2 produktive (1 pro Phase). Phase 2 inklusive Plan + Execute + Verify in einer Session.
- Notable: Phase 2 hat 0 Revisions-Iterationen gebraucht (Plan-Checker passed first try) — Indiz, dass CONTEXT.md mit gelockten Decisions Planning-Iterationen fast komplett eliminiert.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 2 | 2 | Initial GSD-Adoption: CONTEXT.md → Pattern-Mapper → Plan → Execute → Verify-Pipeline durchläuft sauber für Single-File-Python-Projekt. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 0 (no test framework — explicit Out-of-Scope) | n/a | 0 (`requests` + `bs4` + `anthropic` + `pydantic` unverändert) |

### Top Lessons (Verified Across Milestones)

(Erst nach v1.1+ verfügbar — v1.0 ist der erste Milestone.)
