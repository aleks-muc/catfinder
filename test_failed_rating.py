"""Selbst-Check: fehlgeschlagene Bewertungen landen nicht im State und werden neu versucht.
Aufruf: python3 test_failed_rating.py — offline, ohne API-Key."""
from catfinder import (EVAL_FAILED_REASON, PROFILE_MISSING_REASON, CatRating,
                       needs_rating, store_ratings)


def main() -> None:
    state = {"1": {"name": "A"}, "2": {"name": "B"}, "3": {"name": "C"}}
    store_ratings(state, {
        "1": CatRating(rating="geeignet", reason="kinderlieb", health="keine"),
        "2": CatRating(rating="unbekannt", reason=EVAL_FAILED_REASON),
        "3": CatRating(rating="unbekannt", reason=PROFILE_MISSING_REASON),
    })
    assert state["1"]["rating"] == "geeignet", "erfolgreiche Bewertung fehlt im State"
    assert "rating" not in state["2"], "API-Fehler wurde als Bewertung gespeichert"
    assert "rating" not in state["3"], "fehlender Steckbrief wurde als Bewertung gespeichert"
    assert not needs_rating(state["1"])
    assert needs_rating(state["2"]) and needs_rating(state["3"]) and needs_rating(None)
    print("test_failed_rating: 3 Faelle ok")


if __name__ == "__main__":
    main()
