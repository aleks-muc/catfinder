---
status: awaiting_human_verify
trigger: "Katzen mit festen Interessenten erscheinen weiterhin in der Sektion 'Weiterhin verfügbar', statt ausschließlich in der neuen Sektion 'Interessenten vorhanden'."
created: 2026-08-15
updated: 2026-08-15
---

# Debug: Interessenten-Status veraltet nie nach

## Symptome

**Expected behavior:** Jede aktuell gelistete Katze, die laut ihrem Steckbrief auf
tierschutzverein-muenchen.de feste Interessenten hat, erscheint im Report in der Sektion
"Interessenten vorhanden" — nicht in "Weiterhin verfügbar".

**Actual behavior:** Unter "Weiterhin verfügbar" stehen weiterhin Katzen, die auf der
Website Interessenten haben. Sie tragen im Report auch keinen Badge "Interessenten
vorhanden", d.h. das Programm hält sie für interessentenfrei.

**Error messages:** Keine. Kein Crash, kein Traceback — stiller Datenfehler.

**Timeline:** Fällt seit Quick-Task 260815-j3a (Commits c60cbce/9b03931, 2026-08-15) auf,
weil die neue Sektion den Zustand erstmals sichtbar macht. Der zugrunde liegende
Datenfehler ist ÄLTER als der Quick-Task — er betraf vorher nur den Badge, den niemand
vermisst hat.

**Reproduction:** Offline, ohne Netz und ohne API-Key:
```bash
.venv/bin/python - <<'EOF'
import re
h = open("docs/index.html", encoding="utf-8").read()
parts = re.split(r'<h2 class="group">([^<]+)</h2>', h)
for i in range(1, len(parts), 2):
    titel, body = parts[i], parts[i+1]
    print(titel, "->", body.count('class="card'), "Cards,", body.count('badge-int'), "mit Badge")
EOF
```

## Evidence

- timestamp: 2026-08-15
  finding: Der report-seitige Filter FUNKTIONIERT. Im aktuellen `docs/index.html` (nach dem
  Cron-Lauf) steht kein einziger `badge-int` unter "Weiterhin verfügbar":
  `Interessenten vorhanden (5) -> 5 Cards, 5 mit Badge` /
  `Weiterhin verfügbar (44) -> 44 Cards, 0 mit Badge`.
  Damit sind drei ursprüngliche Hypothesen WIDERLEGT: die Partitionierung in
  `render_report`, ein Unterschied zwischen den zwei `render_report`-Aufrufen in `main()`,
  und eine abweichende Datenquelle zwischen Badge und Sektionsfilter. Badge und Filter
  lesen beide `cat.has_interested` und sind konsistent.

- timestamp: 2026-08-15
  finding: `state/seen_cats.json` hat 49 Einträge, davon exakt 5 mit `has_interested: true`
  (SASCHA, SVEN, KIM, URSULA, BRAUNIE). Das Feld fehlt bei 0 Einträgen — es ist also
  überall gesetzt, nur eben teilweise mit einem veralteten Wert.

- timestamp: 2026-08-15
  finding: **Vermutliche Root Cause.** In `main()` (catfinder.py ca. 1020-1043) werden
  Steckbriefe NUR für `to_evaluate` gefetcht — das sind ausschließlich die neu entdeckten
  Katzen. Direkt danach setzt die Schleife `for cat in to_evaluate:`
  `cat.has_interested = bool(INTERESTED_PATTERN.search(text))` (catfinder.py:1035).
  Für bereits bekannte Katzen (`still_known`) wird kein Profil geladen und
  `has_interested` nie neu bestimmt; der Wert kommt via `entry.get("has_interested", False)`
  unverändert aus dem State zurück. Eine Katze, die beim Erstkontakt keine Interessenten
  hatte und später welche bekommt, bleibt damit dauerhaft auf `False`.

- timestamp: 2026-08-15
  finding: **Listing-basierter Fix geprüft — nicht tragfähig.** `detect_interested` als
  eigenständige Funktion existiert im aktuellen Code NICHT (grep über ganz `catfinder.py`:
  0 Treffer für `def detect_interested`). Die Referenz aus der Vorbefüllung auf
  "ca. Zeile 233" ist veraltet — dort steht heute `_rating_from_entry`/`save_state`.
  `INTERESTED_PATTERN` (catfinder.py:59) wird im gesamten Code genau EINMAL verwendet:
  Zeile 1035, gegen `profile_texts[cat.cat_id]` — das ist der Text aus
  `fetch_profile_text()` (catfinder.py:546-564), die die INDIVIDUELLE Steckbriefseite
  (`cat.profile_url`) holt, `<main>`/`<article>` extrahiert und auf 8000 Zeichen kappt.
  Kein einziger Call-Site prüft `INTERESTED_PATTERN` gegen `card_text` aus `scrape_listing`.
  `card_text` (catfinder.py:297) stammt dagegen aus einem viel engeren DOM-Element
  (`a.find_parent(["article","li","div"])`) und wird ausschließlich über `_pick()` auf
  kurze Stichworte durchsucht (Rasse/Geschlecht/Alter — catfinder.py:298-300); niemand im
  Code liest daraus Satz-Text. Es existiert lokal keine rohe Listing-HTML-Fixture (weder im
  Repo noch in der Git-History von `*.html`-Dateien, weder in `.planning/` noch in
  `state/seen_cats.json`), um den tatsächlichen Live-Markup direkt zu prüfen — ein
  Live-Fetch ist laut Randbedingung ausgeschlossen. Schlussfolgerung: strukturelle Evidenz
  spricht GEGEN einen zuverlässigen Interessenten-Hinweis im Listing-Card-Text (keine
  Satz-Ebene, nur Stichwort-Extraktion); eine 100%ige Verneinung ist ohne Live-Fetch nicht
  möglich, aber es gibt keinerlei Code- oder Datenhinweis DAFÜR. Der billige Listing-Fix
  ist damit NICHT bestätigt — Fix muss über Profil-Refetch für `still_known` laufen.

- timestamp: 2026-08-15
  finding: Kostenabschätzung Profil-Refetch. State: 49 Einträge, davon 5 mit
  `has_interested: true` (siehe oben). Zusätzlich läuft `to_evaluate` im Normalfall (keine
  neuen Katzen) über den Frühausstieg in `main()` (catfinder.py:1002-1019) — dieser Pfad
  ruft `render_report` direkt mit `_ratings_from_state(still_known)` auf und erreicht den
  Profil-Fetch-Block (Zeile 1021+) NIE. Ein Refetch-Fix muss also an ZWEI Stellen greifen:
  im Frühausstieg (keine neuen Katzen) UND im Hauptpfad (still_known neben to_evaluate).
  Variante (a) alle 44-49 still_known-Steckbriefe jeden Lauf neu laden: ~44-49 Requests ×
  `PROFILE_FETCH_DELAY_S` (0.4s) ≈ 18-20s Zusatzlaufzeit, 2×/Tag ⇒ ~88-98 Zusatz-Requests/Tag
  an die Vereins-Website. Variante (b) nur Katzen ohne `has_interested: true` neu laden:
  aktuell 44 von 49 (90%) sind unflagged und würden bei JEDEM Lauf weiter neu geladen —
  die Ersparnis ggü. (a) liegt beim aktuellen Datenstand nur bei ~10% (die bereits
  geflaggten 5). Der Ersparnis-Effekt wächst NICHT beliebig über Zeit: Katzen mit
  Interessenten werden typischerweise bald vermittelt und fallen dann aus dem Listing (State
  wird laut D-02 gepurgt), während unvermittelte Katzen dauerhaft ungeflaggt bleiben und
  bei (b) für immer mit-refetcht werden. (b) ist also günstiger, aber nicht dramatisch —
  Größenordnung 10-30%, nicht "deutlich weniger" wie ursprünglich vermutet.

- timestamp: 2026-08-15
  finding: **CHECKPOINT-Antwort: Variante A gewählt** (alle bekannten Steckbriefe bei jedem
  Lauf neu laden). Begründung Nutzer: (b) spart beim aktuellen Datenstand nur ~10% und
  fügt eine ungeprüfte Dauerhaftigkeitsannahme hinzu; (c)/Sampling ist der meiste Code bei
  schlechtester Aktualität; (a) ist zugleich die einfachste Implementierung ohne
  Sonderfallunterscheidung.

- timestamp: 2026-08-15
  finding: **Fix implementiert.** Zwei neue, testbare Modul-Funktionen ersetzen die
  bisherige to_evaluate-only-Logik: `refresh_interested_and_pairs(cats, all_cat_names,
  state)` (catfinder.py, im Scraper-Abschnitt nach `fetch_profile_text`) lädt für JEDE
  übergebene Katze den Steckbrief neu und setzt has_interested/companion_count/
  partner_name direkt am Cat-Objekt — mit State-Fallback bei Fetch-Fehler statt Reset auf
  False. `sync_state_entries(cats, state, now_iso)` (State-Abschnitt, nach `save_state`)
  legt neue State-Einträge an und pflegt dieselben drei Felder für ALLE Katzen nach, ohne
  rating/reason/health/health_note anzufassen. In `main()` läuft
  `refresh_interested_and_pairs(cats, ...)` jetzt VOR dem Früh-Ausstieg (`if not
  to_evaluate`) und deckt damit beide Pfade über eine einzige Aufrufstelle ab —
  `_ratings_from_state` liest has_interested/companion/partner nicht mehr aus dem State
  (nur noch die Claude-Bewertung), da diese Felder bereits frisch am Cat-Objekt stehen.
  `evaluate_all`/Anthropic-Aufrufe unverändert, weiterhin nur für `to_evaluate`.

- timestamp: 2026-08-15
  finding: **Verifikation.** (1) Revert-Test: `git stash` auf catfinder.py, neuer
  Regressionstest `test_interested_refresh.py` lief gegen den ALTEN Code und schlug exakt
  mit "has_interested im Fruehausstieg nicht aktualisiert" fehl (Bug reproduziert) —
  `git stash pop`, erneuter Lauf grün (Fix bestätigt ursächlich, nicht zufällig). (2)
  Bestehende Suite unverändert grün: `test_pairs.py` (6/6), `test_report_sections.py`
  (6/6 + Smoke-Test gegen echten State, 5 Katzen mit has_interested). (3) Neuer Test deckt
  BEIDE main()-Pfade End-to-End ab (nicht nur render_report isoliert) — Fall 1:
  Früh-Ausstieg (keine neuen Katzen), Fall 2: Hauptpfad (still_known + eine neue Katze
  nebeneinander) — jeweils inkl. Assertion, dass rating/reason der bekannten Katze
  UNVERÄNDERT bleiben und (Fall 1) `evaluate_all` gar nicht erst aufgerufen wird. (4)
  `git diff --stat`: nur `catfinder.py` geändert (+75/-43), `state/`, `reports/`, `docs/`
  von allen Testläufen unberührt (Tests schreiben ausschließlich in `tempfile.mkdtemp()`).
  Kein Netzwerkzugriff, kein API-Key nötig — alle I/O-Grenzen (State-/Report-Pfad,
  scrape_listing, fetch_profile_text, evaluate_all) gestubbt.

## Eliminated

- hypothesis: Die Partitionierung in `render_report` (catfinder.py:747-751) filtert falsch.
  evidence: Live-Report zeigt 0 Badges unter "Weiterhin verfügbar" — der Filter greift.

- hypothesis: Die zwei `render_report`-Aufrufe in `main()` (Zeile ~1007 und ~1067) füttern
  unterschiedliche Daten, weil `c.has_interested = entry.get(...)` nur in einem Pfad steht.
  evidence: Widerlegt durch denselben Live-Report-Befund. Beide Pfade rendern konsistent.

- hypothesis: `has_interested` fehlt bei manchen State-Einträgen.
  evidence: Feld ist bei allen 49 Einträgen vorhanden.

## Current Focus

```yaml
reasoning_checkpoint:
  hypothesis: >
    has_interested/companion_count/partner_name veralten für bereits bekannte Katzen
    (still_known), weil main() für sie nie einen Steckbrief nachlädt — der Wert kommt
    stattdessen dauerhaft unverändert aus dem letzten State-Snapshot.
  confirming_evidence:
    - "Live-Report: 0 badge-int unter 'Weiterhin verfügbar', Filter/Badge selbst korrekt."
    - "State: 5/49 Einträge has_interested=true, 0 fehlende Felder — reiner Aktualitäts-,
      kein Struktur-/Filterfehler."
    - "Codepfad bestätigt: profile_texts wurde nur für to_evaluate befüllt, INTERESTED_PATTERN
      nur an dieser einen Stelle verwendet, still_known bezog has_interested ausschließlich
      aus _ratings_from_state (State-Fallback)."
    - "Reproduziert per Revert-Test: git stash auf catfinder.py, test_interested_refresh.py
      lief GEGEN den alten Code und schlug exakt mit 'has_interested im Fruehausstieg nicht
      aktualisiert' fehl; git stash pop + erneuter Lauf -> grün."
  falsification_test: >
    Wäre has_interested für still_known bereits frisch aus einem Refetch gesetzt worden
    (z.B. via _ratings_from_state ODER eine andere main()-Stelle), hätte der Revert-Test
    NICHT fehlschlagen dürfen. Er schlug fehl -> Hypothese bestätigt.
  fix_rationale: >
    Root Cause ist der fehlende Refetch, nicht die Report-Logik — Fix muss die Datenquelle
    für still_known auffrischen, nicht render_report/Filter anfassen (die waren nie kaputt).
  blind_spots: >
    Kein Live-Zugriff auf die echte Listing-Seite möglich (Randbedingung) — der Ausschluss
    des billigen Listing-Fixes stützt sich auf strukturelle Code-Evidenz, nicht auf einen
    Live-Fetch-Beweis. Bleibt vertretbar, da User-Entscheidung (Variante A) ohnehin einen
    Profil-Refetch verlangt, unabhängig vom Listing-Befund.
  candidate_causes:
    - "code: main() ruft den has_interested-Refresh nur für to_evaluate auf, nie für
      still_known (bestätigte Ursache)."
    - "data: State selbst ist strukturell intakt (kein fehlendes Feld) — als Ursache
      ausgeschlossen, siehe Evidence."
  and_gate: >
    nein — ein einzelner Code-Fehlpfad erklärt den kompletten Befund vollständig, kein
    zweiter gleichzeitig nötiger Faktor identifiziert.
```

hypothesis: BESTÄTIGT UND GEFIXT (siehe Resolution).

test: Fix implementiert, gegen echten Repro-Fall verifiziert (Revert-Test), Regressionstest
  ergänzt, bestehende Test-Suite grün geblieben.

expecting: Nutzer bestätigt den Fix im nächsten CI-Lauf / bei manueller Prüfung des Reports.

next_action: CHECKPOINT an Nutzer — Bestätigung abwarten, dann `archive_session`.

## Resolution

root_cause: `main()` bestimmte `has_interested`/`companion_count`/`partner_name` nur für
  neu entdeckte Katzen (`to_evaluate`) aus einem frisch geladenen Steckbrief. Für bereits
  bekannte Katzen (`still_known`) wurde nie ein Steckbrief nachgeladen — der Wert kam über
  `_ratings_from_state` dauerhaft unverändert aus dem letzten State-Snapshot. Eine Katze,
  die beim Erstkontakt interessentenfrei war und später Interessenten bekam, blieb damit
  für immer auf `has_interested: false` eingefroren. Der häufigste main()-Pfad (Frühausstieg
  bei "keine neuen Katzen", 2×/Tag) erreichte den einzigen Profil-Fetch-Block im Code
  überhaupt nie.

fix: Variante A (Nutzerentscheidung) — zwei neue Modul-Funktionen in `catfinder.py`:
  `refresh_interested_and_pairs(cats, all_cat_names, state)` lädt für ALLE aktuell
  gelisteten Katzen (nicht nur `to_evaluate`) den Steckbrief neu und setzt
  has_interested/companion_count/partner_name direkt am Cat-Objekt (State-Fallback bei
  Fetch-Fehler, damit ein Netzwerk-Hänger den Status nicht auf `false` zurücksetzt).
  `sync_state_entries(cats, state, now_iso)` legt neue State-Einträge an und pflegt
  dieselben drei Felder für alle Katzen nach, ohne rating/reason/health/health_note
  anzufassen. In `main()` läuft der Refresh jetzt VOR dem `if not to_evaluate`-Ausstieg —
  eine einzige Aufrufstelle deckt beide Pfade ab, keine duplizierte Logik.
  `_ratings_from_state` liest die drei Felder nicht mehr aus dem State (nur noch die
  Claude-Bewertung), da sie bereits frisch am Cat-Objekt stehen. `evaluate_all`/
  Anthropic-Aufrufe unverändert, weiterhin ausschließlich für `to_evaluate`.

verification:
```yaml
verification:
  target_test:
    result: pass
    detail: >
      test_interested_refresh.py, beide Fälle (Früh-Ausstieg + Hauptpfad) grün gegen den
      Fix; gegen den alten Code (git stash) schlug Fall 1 exakt mit "has_interested im
      Fruehausstieg nicht aktualisiert" fehl.
  mutation_check:
    result: skipped
    reason_if_skipped: >
      Kein Stryker/Mutationstest-Tool im Projekt konfiguriert (reines Python, Single-File,
      keine neuen Dependencies erlaubt) — Stryker ist JS-spezifisch und hätte hier keine
      Entsprechung ohne neue Tooling-Abhängigkeit einzuführen.
    mutant_killed: null
  no_op_deletion:
    result: pass
    deletion_justified_by_rca: true
    detail: >
      git diff ist NICHT deletion-only: entfernt wurde der State-Clobber in
      _ratings_from_state (die eigentliche Bug-Ursache, durch reasoning_checkpoint
      begründet) UND der alte to_evaluate-only Fetch-Block — ersetzt durch zwei neue
      Funktionen (refresh_interested_and_pairs, sync_state_entries), die denselben Umfang
      jetzt für ALLE Katzen statt nur to_evaluate abdecken. Netto: mehr abgedeckte Fälle,
      keine stillschweigend entfernte Prüfung.
  adjacent_tests:
    result: pass
    suites_run: [test_pairs.py, test_report_sections.py]
    detail: "test_pairs.py 6/6, test_report_sections.py 6/6 + Smoke-Test gegen echten State."
  revert_and_reconfirm:
    result: pass
    bug_returned_on_revert: true
    fixed_on_reapply: true
    detail: "git stash / stash pop auf catfinder.py — siehe Evidence-Eintrag oben."
  guardrail_verdict: accepted
```

  Kein Netzwerk, kein API-Key, `state/`/`reports/`/`docs/` unberührt (Tests laufen gegen
  `tempfile.mkdtemp()`). Ausstehend: End-to-End-Bestätigung durch Nutzer im echten CI-Lauf.

files_changed:
  - catfinder.py (Fix: refresh_interested_and_pairs, sync_state_entries, main()-Umbau)
  - test_interested_refresh.py (neuer Regressionstest, Datenfluss-Ebene)

## Randbedingungen (aus CLAUDE.md — bindend)

- KEIN Netzwerkzugriff, KEINE Anthropic-API-Calls, kein ANTHROPIC_API_KEY verfügbar.
  `python catfinder.py` NIEMALS ausführen (Live-Scrape + API-Calls). Verifikation
  ausschließlich offline über `render_report(...)` aus `state/seen_cats.json`;
  `test_report_sections.py` und `test_pairs.py` zeigen das Muster.
- Interpreter: `.venv/bin/python` (3.9.6).
- Single-File bleibt Single-File, keine neuen Runtime-Dependencies.
- `state/seen_cats.json`, `reports/report.html`, `docs/index.html` NICHT verändern oder
  committen — die gehören der CI. Temporäre Ausgaben in ein temp-Verzeichnis.
- `new_count` (Report-Header, `$GITHUB_OUTPUT`, ntfy) muss bitgleich bleiben.
  CI-Verhalten unverändert: gleicher Bot-Commit, gleiche Pfade, gleiche Pages-URL.
- Alle User-facing-Strings, Log-Ausgaben, Docstrings und Kommentare auf DEUTSCH.
  Code-Stil an catfinder.py: snake_case, 4 Spaces, deutsche Einzeiler-Docstrings,
  `_`-Präfix für interne Helper.
- Der Regressionstest muss den DATENFLUSS abdecken, nicht nur `render_report` isoliert —
  genau diese Lücke hat den Bug durch die grünen Tests schlüpfen lassen.
