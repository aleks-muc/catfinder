#!/usr/bin/env python3
"""Selbst-Check für die Interessenten-Sektion in render_report — Aufruf: python3 test_report_sections.py

Anlass: Katzen mit has_interested bekamen eine eigene Sektion zwischen
"Nicht mehr verfügbar" und "Weiterhin verfügbar" (siehe PLAN.md
260815-j3a). Läuft komplett offline gegen render_report() direkt aus
state/seen_cats.json — python catfinder.py wird bewusst NICHT aufgerufen
(würde einen Live-Scrape der Tierschutzverein-Website plus
Anthropic-API-Calls auslösen). Bewusst ohne Test-Framework — das Projekt
hat keins.
"""
import dataclasses
import json

from catfinder import Cat, CatRating, _rating_from_entry, render_report

STATE_FILE = "state/seen_cats.json"


def _cat(cat_id: str, name: str, interested: bool = False) -> Cat:
    return Cat(cat_id=cat_id, name=name, profile_url="", has_interested=interested)


def _rating() -> CatRating:
    return CatRating(rating="geeignet", reason="Testfall", health="keine")


def _sections(html_text: str) -> list[int]:
    """Zeichenpositionen der vier Sektions-Ueberschriften, falls vorhanden."""
    return [html_text.find(t) for t in (
        "Neu seit letztem Lauf", "Nicht mehr verf", "Interessenten vorhanden (", "Weiterhin verf",
    )]


def _marker(cat_id: str) -> str:
    """Eindeutiges Suchtoken fuer eine Karte — die Card rendert die cat_id nur im
    h2-Span mit class="cid"; die blosse cat_id als Substring kollidiert sonst mit
    CSS-Zahlen und den Sektions-Zaehlern (span.cnt)."""
    return f'class="cid">{cat_id}</span>'


def main() -> None:
    # Fall 1 (D-01): eine Katze mit Interessenten aus evaluated, eine aus still_known —
    # beide landen in der neuen Sektion, die uebrigen Karten bleiben in ihren Sektionen.
    a_int, a_free = _cat("1", "SASCHA", True), _cat("2", "FREYA")
    b_int, b_free = _cat("3", "SVEN", True), _cat("4", "KIM")
    h = render_report(
        [(a_int, _rating()), (a_free, _rating())], 4,
        still_known=[(b_int, _rating()), (b_free, _rating())],
        had_prior_state=True,  # erzwingt den "Nicht mehr verf"-Delimiter fuer den Split unten
    )
    sect_int = h.split("Interessenten vorhanden (")[1].split("Weiterhin verf")[0]
    rest_new = h.split("Neu seit letztem Lauf")[1].split("Nicht mehr verf")[0]
    rest_still = h.split("Weiterhin verf")[1]
    assert _marker("1") in sect_int and _marker("3") in sect_int, "beide Interessenten-Katzen fehlen in der neuen Sektion"
    assert _marker("2") not in sect_int and _marker("4") not in sect_int, "Katzen ohne Interessenten landen faelschlich in der neuen Sektion"
    assert _marker("1") not in rest_new, "SASCHA steht noch in Neu seit letztem Lauf"
    assert _marker("2") in rest_new, "FREYA fehlt in Neu seit letztem Lauf"
    assert _marker("3") not in rest_still, "SVEN steht noch in Weiterhin verfuegbar"
    assert _marker("4") in rest_still, "KIM fehlt in Weiterhin verfuegbar"

    # Fall 2 (D-02): Interessenten-Katze in no_longer_listed bleibt dort, taucht NICHT
    # in der neuen Sektion auf.
    gone = _cat("5", "URSULA", True)
    h = render_report([], 0, no_longer_listed=[(gone, _rating())], had_prior_state=True)
    assert "Interessenten vorhanden (" not in h, "leere Interessenten-Sektion haette nicht rendern duerfen"
    gone_sect = h.split("Nicht mehr verf")[1].split("Weiterhin verf")[0]
    assert _marker("5") in gone_sect, "URSULA fehlt in Nicht mehr verfuegbar"

    # Fall 3 (D-04): Sektionsreihenfolge Neu -> Nicht mehr verfuegbar -> Interessenten -> Weiterhin.
    h = render_report(
        [(_cat("6", "A"), _rating())], 3,
        still_known=[(_cat("7", "B"), _rating()), (_cat("9", "D", True), _rating())],
        no_longer_listed=[(_cat("8", "C"), _rating())],
        had_prior_state=True,
    )
    order = _sections(h)
    assert all(pos != -1 for pos in order), ("nicht alle vier Sektionen vorhanden", order)
    assert order == sorted(order), ("Sektionsreihenfolge falsch", order)
    # alle vier Sektionen klappbar, nur "Neu seit letztem Lauf" per Default offen
    assert h.count('<details class="sect"') == 4, "nicht alle vier Sektionen sind klappbar"
    assert h.count('<details class="sect" open>') == 1, "es darf genau eine Sektion offen starten"
    assert '<details class="sect" open><summary><h2 class="group">Neu seit letztem Lauf' in h, \
        "die offene Sektion muss 'Neu seit letztem Lauf' sein"

    # Fall 4: keine Katze mit Interessenten -> keine Ueberschrift der neuen Sektion.
    h = render_report([(_cat("10", "E"), _rating())], 1, still_known=[(_cat("11", "F"), _rating())])
    assert "Interessenten vorhanden (" not in h, "Empty-State haette nicht rendern duerfen"

    # Fall 5: nur Katzen mit Interessenten -> Filterleiste erscheint trotzdem, "Neu
    # seit letztem Lauf" bleibt als Ueberschrift sichtbar (auch wenn 0 Karten drin sind).
    h = render_report([(_cat("12", "G", True), _rating())], 1)
    assert 'id="filterBar"' in h, "Filterleiste fehlt, obwohl Karten existieren"
    assert "Neu seit letztem Lauf" in h, "Neu-Ueberschrift fehlt"
    assert 'Interessenten vorhanden (<span class="cnt">1</span>)' in h

    # Fall 6: new_count (Header/CI) bleibt die Gesamtzahl UNgefilterter evaluated-Katzen,
    # auch wenn eine davon in die neue Sektion abwandert. Nur die Neu-Ueberschrift schrumpft.
    h = render_report(
        [(_cat("13", "H"), _rating()), (_cat("14", "I", True), _rating()), (_cat("15", "J"), _rating())], 3,
    )
    assert "<strong>3 neu bewertet</strong>" in h, "new_count im Header muss die Gesamtzahl bleiben"
    assert 'Neu seit letztem Lauf (<span class="cnt">2</span>)' in h, "Neu-Ueberschrift muss um die Interessenten-Katze schrumpfen"

    print("test_report_sections: 6 Faelle ok")

    # Smoke-Test gegen den realen State — keine festen Namen/Anzahlen, der State
    # aendert sich zweimal taeglich per CI.
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        print("test_report_sections: Smoke-Test uebersprungen (state/seen_cats.json fehlt)")
        return

    fields = {fld.name for fld in dataclasses.fields(Cat)}
    pairs = [
        (Cat(**{k: v for k, v in entry.items() if k in fields}), _rating_from_entry(entry))
        for entry in state.values()
    ]
    hits = [cid for cid, entry in state.items() if entry.get("has_interested")]
    if not hits:
        print("test_report_sections: Smoke-Test uebersprungen (kein has_interested im State)")
        return

    h = render_report([], len(pairs), still_known=pairs, had_prior_state=True)
    sect_int = h.split("Interessenten vorhanden (")[1].split("Weiterhin verf")[0]
    rest = h.split("Weiterhin verf")[1]
    for cid in hits:
        assert _marker(cid) in sect_int, (cid, "fehlt im Smoke-Test in der neuen Sektion")
        assert _marker(cid) not in rest, (cid, "steht im Smoke-Test noch in Weiterhin verfuegbar")
    print(f"test_report_sections: Smoke-Test ok ({len(hits)} Katzen mit Interessenten im realen State)")


if __name__ == "__main__":
    main()
