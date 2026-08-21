#!/usr/bin/env python3
"""Regressionstest für den Interessenten-Status-Refresh — Aufruf: python3 test_interested_refresh.py

Anlass: has_interested wurde nur beim Erstkontakt aus dem Steckbrief gelesen und veraltete
danach für immer, weil main() für bereits bekannte Katzen (still_known) nie ein Profil neu
lud (Debug-Session interessenten-status-veraltet). Deckt beide main()-Pfade ab: den
Früh-Ausstieg ohne neue Katzen (häufigster CI-Fall, 2x/Tag) und den Hauptpfad mit einer
neuen Katze daneben. Läuft komplett offline gegen main() selbst statt nur gegen
render_report — genau diese Lücke hat den Bug durch die grünen Tests schlüpfen lassen.
scrape_listing, fetch_profile_text und evaluate_all sind gestubbt, State-/Report-Pfade
zeigen auf ein Temp-Verzeichnis; kein Netzwerk, kein echter API-Key nötig. Bewusst ohne
Test-Framework — das Projekt hat keins.
"""
import contextlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import catfinder
from catfinder import Cat, CatRating


def _cat(cat_id: str, name: str) -> Cat:
    return Cat(cat_id=cat_id, name=name, profile_url=f"https://example.invalid/{cat_id}")


def _sascha_entry() -> dict:
    """State-Eintrag einer bekannten Katze mit bereits vorhandener Claude-Bewertung und
    veraltetem has_interested=False."""
    return {
        "cat_id": "1", "name": "SASCHA", "profile_url": "https://example.invalid/1",
        "image_url": "", "breed": "", "sex": "", "age_hint": "",
        "has_interested": False, "companion_count": 0, "partner_name": "",
        "first_seen": "2026-01-01T00:00:00",
        "rating": "geeignet", "reason": "Testfall", "health": "keine", "health_note": "",
    }


@contextlib.contextmanager
def _stubbed_main(state: dict, cats: list, fetch_fn, evaluate_all_fn):
    """Patcht main()'s I/O-Grenzen (State-/Report-Pfad, Scrape, Steckbrief-Fetch, Claude)
    gegen ein Temp-Verzeichnis und Stubs, damit main() offline und ohne echten API-Key läuft.
    """
    tmp = Path(tempfile.mkdtemp(prefix="catfinder_test_"))
    state_file = tmp / "seen_cats.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    report_file = tmp / "report.html"

    patched = {
        "STATE_FILE": state_file, "STATE_DIR": tmp,
        "REPORT_FILE": report_file, "REPORT_DIR": tmp,
        "scrape_listing": lambda: cats,
        "fetch_profile_text": fetch_fn,
        "evaluate_all": evaluate_all_fn,
    }
    originals = {name: getattr(catfinder, name) for name in patched}
    orig_argv, orig_api_key = sys.argv, os.environ.get("ANTHROPIC_API_KEY")
    orig_gh_output = os.environ.pop("GITHUB_OUTPUT", None)
    try:
        for name, value in patched.items():
            setattr(catfinder, name, value)
        sys.argv = ["catfinder.py", "--no-browser"]
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        yield state_file, report_file
    finally:
        for name, value in originals.items():
            setattr(catfinder, name, value)
        sys.argv = orig_argv
        if orig_api_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = orig_api_key
        if orig_gh_output is not None:
            os.environ["GITHUB_OUTPUT"] = orig_gh_output
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    # Fall 1: keine neuen Katzen -> Früh-Ausstieg (catfinder.py, "if not to_evaluate").
    # Häufigster Fall, hat den Profil-Refresh vor dem Fix nie erreicht.
    state = {"1": _sascha_entry()}
    cats = [_cat("1", "SASCHA")]

    def fetch_interested(cat: Cat) -> str:
        return "Katze SASCHA hat bereits feste Interessenten."

    def evaluate_all_must_not_run(cs, texts):
        raise AssertionError("evaluate_all haette im Fruehausstieg nicht laufen duerfen")

    with _stubbed_main(state, cats, fetch_interested, evaluate_all_must_not_run) as (state_file, report_file):
        assert catfinder.main() == 0
        saved = json.loads(state_file.read_text(encoding="utf-8"))
        assert saved["1"]["has_interested"] is True, "has_interested im Fruehausstieg nicht aktualisiert"
        assert saved["1"]["rating"] == "geeignet", "rating haette unangetastet bleiben muessen"
        assert saved["1"]["reason"] == "Testfall", "reason haette unangetastet bleiben muessen"
        report_html = report_file.read_text(encoding="utf-8")
        assert 'Interessenten vorhanden (<span class="cnt">1</span>)' in report_html, "Interessenten-Sektion fehlt im Report"

    # Fall 2: eine neue Katze daneben -> Hauptpfad. Auch hier muss die bereits bekannte
    # Katze frisch refetcht werden, nicht nur die neue.
    state = {"1": _sascha_entry()}
    cats = [_cat("1", "SASCHA"), _cat("2", "NEUKATZE")]

    def fetch_by_id(cat: Cat) -> str:
        if cat.cat_id == "1":
            return "Katze SASCHA hat bereits feste Interessenten."
        return "Katze NEUKATZE ist verspielt und neugierig."

    def evaluate_all_stub(cs, texts):
        return {"2": CatRating(rating="unbekannt", reason="Testbewertung", health="unbekannt")}

    with _stubbed_main(state, cats, fetch_by_id, evaluate_all_stub) as (state_file, _report_file):
        assert catfinder.main() == 0
        saved = json.loads(state_file.read_text(encoding="utf-8"))
        assert saved["1"]["has_interested"] is True, "still_known im Hauptpfad nicht refetcht"
        assert saved["1"]["rating"] == "geeignet", "rating der bekannten Katze haette unangetastet bleiben muessen"
        assert saved["2"]["rating"] == "unbekannt", "neue Katze wurde nicht normal bewertet"
        assert saved["2"]["has_interested"] is False

    print("test_interested_refresh: 2 Faelle ok")


if __name__ == "__main__":
    main()
