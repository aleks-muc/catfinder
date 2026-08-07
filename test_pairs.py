#!/usr/bin/env python3
"""Selbst-Check für repair_pair_symmetry — Aufruf: python3 test_pairs.py

Anlass: MATILDA wurde nicht als Pärchen erkannt, weil ihr Steckbrief den Partner
nur "Constantin" nennt, das Listing ihn aber als "CONSTANTIN CHRISTOMANOS" führt.
Bewusst ohne Test-Framework — das Projekt hat keins.
"""
from catfinder import Cat, repair_pair_symmetry


def _cat(cat_id: str, name: str, partner: str = "", companions: int = 0) -> Cat:
    return Cat(cat_id=cat_id, name=name, profile_url="",
               partner_name=partner, companion_count=companions)


def main() -> None:
    # Der Auslöser: beide neu, nur eine Seite hat den Partner erkannt.
    a, b = _cat("1", "CONSTANTIN CHRISTOMANOS", "MATILDA", 2), _cat("2", "MATILDA")
    repair_pair_symmetry([a, b], {"1", "2"}, {})
    assert (b.partner_name, b.companion_count) == ("CONSTANTIN CHRISTOMANOS", 2)

    # Partner war schon bekannt: Korrektur muss auch in den State, sonst
    # überschreibt _ratings_from_state das Cat-Objekt beim Rendern wieder.
    a, b = _cat("1", "CONSTANTIN CHRISTOMANOS", "MATILDA", 2), _cat("2", "MATILDA")
    state = {"2": {"name": "MATILDA", "partner_name": "", "companion_count": 0}}
    repair_pair_symmetry([a, b], {"1"}, state)
    assert state["2"] == {"name": "MATILDA", "partner_name": "CONSTANTIN CHRISTOMANOS",
                          "companion_count": 2}
    assert b.partner_name == "CONSTANTIN CHRISTOMANOS"

    # Bereits symmetrische Paare bleiben unangetastet.
    a, b = _cat("1", "SVEN", "KIM", 2), _cat("2", "KIM", "SVEN", 2)
    repair_pair_symmetry([a, b], {"1", "2"}, {})
    assert (a.partner_name, b.partner_name) == ("KIM", "SVEN")

    # Partner nicht mehr im Listing: ignorieren statt abstürzen.
    a = _cat("1", "SVEN", "WEGKATZE", 2)
    repair_pair_symmetry([a], {"1"}, {})
    assert a.partner_name == "WEGKATZE"

    # Einzelkatzen dürfen nicht zu Pärchen werden.
    a, b = _cat("1", "SUCUK"), _cat("2", "PEPPI")
    repair_pair_symmetry([a, b], {"1", "2"}, {})
    assert (a.companion_count, b.companion_count) == (0, 0)

    # Eine Katze ist kein Pärchen mit sich selbst.
    a = _cat("1", "MINI", "MINI", 2)
    repair_pair_symmetry([a], {"1"}, {})

    print("test_pairs: 6 Fälle ok")


if __name__ == "__main__":
    main()
