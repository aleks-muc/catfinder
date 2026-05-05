"""Catfinder — neue Katzen beim Tierschutzverein München finden & bewerten.

Scraped https://tierschutzverein-muenchen.de/tiervermittlung/tierheim/katzen,
identifiziert neue Einträge gegenüber dem letzten Lauf, bewertet jedes neue
Profil via Claude API auf Kindertauglichkeit und öffnet einen HTML-Report.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import re
import sys
import tempfile
import time
import webbrowser
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit(
        "Fehler: anthropic SDK nicht installiert.\n"
        "  pip install -r requirements.txt"
    )


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

BASE = "https://tierschutzverein-muenchen.de"
LISTING_URL = f"{BASE}/tiervermittlung/tierheim/katzen"
PROFILE_URL_TMPL = f"{BASE}/tiervermittlung/tierheim/katzen/{{cat_id}}"
USER_AGENT = "Catfinder/1.0 (privater Gebrauch; Katzensuche)"

ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / "state"
STATE_FILE = STATE_DIR / "seen_cats.json"
REPORT_DIR = ROOT / "reports"
REPORT_FILE = REPORT_DIR / "report.html"

MODEL = "claude-haiku-4-5"
MAX_EVAL_WORKERS = 2
API_RETRY_DELAYS = [10, 30, 60]  # Sekunden warten nach 429, je Versuch
PROFILE_FETCH_DELAY_S = 0.4

CAT_ID_PATTERN = re.compile(r"/tiervermittlung/tierheim/katzen/(\d+)")
INTERESTED_PATTERN = re.compile(r"hat bereits feste Interessenten\.")
BIRTH_DATE_PATTERN = re.compile(
    r"(?:geb\.?|[Gg]eburtsdatum|[Gg]eburtstag)[:\s]*"
    r"(?:(\d{1,2})\.)?(\d{1,2})\.(\d{4})"
)

# Ampel-Metadaten
Rating = Literal["geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt"]

RATING_META: dict[str, dict[str, str]] = {
    "geeignet":        {"emoji": "🟢", "label": "Kinder geeignet",       "color": "#2e7d32", "order": "0"},
    "unbekannt":       {"emoji": "⚪", "label": "Keine Angabe",          "color": "#757575", "order": "1"},
    "aeltere_kinder":  {"emoji": "🟡", "label": "Nur ältere Kinder",     "color": "#f9a825", "order": "2"},
    "nicht_geeignet":  {"emoji": "🔴", "label": "Nicht für Kinder",      "color": "#c62828", "order": "3"},
}


# ---------------------------------------------------------------------------
# Datenmodelle
# ---------------------------------------------------------------------------

@dataclass
class Cat:
    cat_id: str
    name: str
    profile_url: str
    image_url: str = ""
    breed: str = ""
    sex: str = ""
    age_hint: str = ""
    has_interested: bool = False
    companion_count: int = 0
    partner_name: str = ""


class CatRating(BaseModel):
    """Strukturierte Claude-Ausgabe zur Kindertauglichkeit einer Katze."""

    rating: Literal["geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt"] = Field(
        description=(
            "geeignet = passt zu Familien mit Kindern jeden Alters. "
            "aeltere_kinder = nur mit älteren / verständnisvollen Kindern. "
            "nicht_geeignet = ausdrücklich keine Kinder / nur Erwachsene. "
            "unbekannt = Text trifft keine Aussage zu Kindern."
        )
    )
    reason: str = Field(
        description="Begründung in max. einem Satz, möglichst wörtliches Zitat aus dem Steckbrief."
    )
SYSTEM_PROMPT = """Du bist ein Klassifikator für deutsche Tierheim-Steckbriefe.

Aufgabe: Bewerte, ob eine Katze laut ihrem Steckbrief für Familien mit Kindern geeignet ist.

Kategorien für 'rating':
- "geeignet": Der Text nennt Kinder ausdrücklich positiv ODER sagt "für Familien" / "kinderlieb" o.ä., ohne Einschränkung auf ein Alter.
- "aeltere_kinder": Nur mit älteren, ruhigen, verständnisvollen oder katzenerfahrenen Kindern (z.B. "Kinder ab 10", "größere Kinder", "ältere Kinder").
- "nicht_geeignet": Der Text schließt Kinder ausdrücklich aus ("keine Kinder", "nur Erwachsene", "nicht in Familien mit Kindern").
- "unbekannt": Der Text trifft KEINE Aussage zu Kindern. WICHTIG: Nicht raten oder aus anderen Merkmalen (scheu, ängstlich, Freigänger) auf Kinderverträglichkeit schließen — wenn nicht explizit erwähnt, ist es "unbekannt".

Gib als Begründung einen knappen Satz, bevorzugt ein wörtliches Zitat aus dem Text.
"""


# ---------------------------------------------------------------------------
# State (JSON)
# ---------------------------------------------------------------------------

def load_state() -> dict[str, dict]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warnung: State-Datei konnte nicht gelesen werden ({e}). Starte frisch.")
        return {}


def save_state(state: dict[str, dict]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    fd, tmp_path = tempfile.mkstemp(prefix="seen_cats_", suffix=".json", dir=str(STATE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def _http_get(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def scrape_listing() -> list[Cat]:
    """Holt die Listenseite und extrahiert alle Katzen-Einträge."""
    html_doc = _http_get(LISTING_URL)
    soup = BeautifulSoup(html_doc, "html.parser")

    # Defensiv: wir suchen alle Links, die auf /tiervermittlung/tierheim/katzen/{id} zeigen.
    cats: dict[str, Cat] = {}
    for a in soup.find_all("a", href=True):
        m = CAT_ID_PATTERN.search(a["href"])
        if not m:
            continue
        cat_id = m.group(1)
        if cat_id in cats:
            continue

        profile_url = a["href"]
        if profile_url.startswith("/"):
            profile_url = BASE + profile_url

        # Der Karte liegen Name + Stammdaten im umschließenden Element bei.
        card = a.find_parent(["article", "li", "div"]) or a
        name = ""
        # Erster überschriftenartiger Text im Card
        for tag in card.find_all(["h1", "h2", "h3", "h4", "span", "strong"]):
            txt = tag.get_text(strip=True)
            if txt and len(txt) < 60 and not txt.lower().startswith("mehr"):
                name = txt
                break
        if not name:
            name = a.get_text(strip=True) or f"Katze {cat_id}"

        img = card.find("img")
        image_url = ""
        if img:
            image_url = img.get("src") or img.get("data-src") or ""
            if image_url.startswith("/"):
                image_url = BASE + image_url

        card_text = card.get_text(" ", strip=True)
        breed = _pick(card_text, ["Rasse", "Mischling", "Hauskatze", "EKH"])
        sex = _pick(card_text, ["weiblich", "männlich", "Kater", "Kätzin"])
        age_hint = _pick(card_text, ["geb.", "Jahre", "Monate", "Alter"])

        cats[cat_id] = Cat(
            cat_id=cat_id,
            name=name,
            profile_url=profile_url,
            image_url=image_url,
            breed=breed,
            sex=sex,
            age_hint=age_hint,
        )

    if not cats:
        raise RuntimeError(
            "Keine Katzen auf der Listenseite gefunden — ist die Seitenstruktur anders?\n"
            f"URL: {LISTING_URL}"
        )

    return list(cats.values())


def _pick(haystack: str, needles: list[str]) -> str:
    for n in needles:
        idx = haystack.find(n)
        if idx >= 0:
            # Nimm das Snippet um den Treffer herum (ungenau, nur als Kontext)
            start = max(0, idx - 10)
            end = min(len(haystack), idx + 40)
            return haystack[start:end].strip()
    return ""


def detect_interested(text: str) -> bool:
    """True wenn der Steckbrief-Text Interessenten-Hinweise enthält."""
    return bool(INTERESTED_PATTERN.search(text))


def find_companion_names(profile_text: str, all_names: list[str]) -> set[str]:
    """Gibt die Menge der Katzennamen aus dem Listing zurück, die im Steckbrief vorkommen.

    Genau 2 Namen → Pärchen. Alles andere → kein Pärchen.
    Gibt die Originalnamen (nicht uppercased) zurück.
    """
    text_up = profile_text.upper()
    found: set[str] = set()
    for name in all_names:
        if name and len(name) >= 2:
            if re.search(r"\b" + re.escape(name.upper()) + r"\b", text_up):
                found.add(name)
    return found


def extract_age_hint(text: str) -> str:
    """Extrahiert Geburtsdatum aus Steckbrief-Text und rechnet in Alter um."""
    m = BIRTH_DATE_PATTERN.search(text)
    if not m:
        return ""
    day_s, month_s, year_s = m.group(1), m.group(2), m.group(3)
    try:
        birth = date(int(year_s), int(month_s), int(day_s) if day_s else 1)
    except (ValueError, TypeError):
        return ""
    today = date.today()
    months_old = (today.year - birth.year) * 12 + (today.month - birth.month)
    if months_old < 0:
        return ""
    if months_old < 12:
        return f"{months_old} Monate alt"
    years = months_old // 12
    return f"{years} Jahr{'e' if years != 1 else ''} alt"


def age_hint_to_months(age_hint: str) -> int | None:
    """Gibt Alter in Monaten zurück, oder None wenn unbekannt."""
    m = re.search(r'(\d+)\s*Jahr', age_hint)
    if m:
        return int(m.group(1)) * 12
    m = re.search(r'(\d+)\s*Monat', age_hint)
    if m:
        return int(m.group(1))
    # Fallback: Geburtsdatum aus Snippet berechnen (z.B. "geb. 15.01.2026")
    enriched = extract_age_hint(age_hint)
    if enriched:
        m = re.search(r'(\d+)\s*Jahr', enriched)
        if m:
            return int(m.group(1)) * 12
        m = re.search(r'(\d+)\s*Monat', enriched)
        if m:
            return int(m.group(1))
    return None


DEFAULT_AGE_LO = 36   # 3 Jahre in Monaten
DEFAULT_AGE_HI = 144  # 12 Jahre in Monaten


def _build_filter_bar(age_min: int, age_max: int, has_unknown: bool) -> str:
    """Baut den HTML/CSS/JS-Block für Altersfilter und Sorgenkinder-Toggle."""
    def fmt(m: int) -> str:
        if m < 12:
            return f"{m} Mon."
        y, r = divmod(m, 12)
        return f"{y}{'.5' if r >= 6 else ''} J."

    # Defaultwerte auf tatsächliche Datenbandbreite klemmen
    default_lo = max(age_min, min(DEFAULT_AGE_LO, age_max))
    default_hi = min(age_max, max(DEFAULT_AGE_HI, age_min))

    slider = ""
    if age_min < age_max:
        slider = f"""
  <div style="display:flex;flex-direction:column;gap:.5rem;flex:1;min-width:220px;max-width:420px;">
    <div style="display:flex;justify-content:space-between;">
      <span style="font-size:.85rem;font-weight:500;color:#555;">Alter filtern</span>
      <span id="ageLabel" style="font-size:.85rem;color:#1976d2;font-weight:600;">{fmt(default_lo)} – {fmt(default_hi)}</span>
    </div>
    <div class="cf-track">
      <div id="sliderFill" class="cf-fill"></div>
      <input type="range" class="cf-range" id="ageMin" min="{age_min}" max="{age_max}" value="{default_lo}">
      <input type="range" class="cf-range" id="ageMax" min="{age_min}" max="{age_max}" value="{default_hi}">
    </div>
  </div>"""

    return f"""<style>
.cf-track{{position:relative;height:6px;background:#e0e0e0;border-radius:3px;margin:.2rem 0;}}
.cf-fill{{position:absolute;height:100%;background:#1976d2;border-radius:3px;pointer-events:none;}}
.cf-range{{position:absolute;width:100%;height:0;top:3px;pointer-events:none;-webkit-appearance:none;appearance:none;background:transparent;outline:none;}}
.cf-range::-webkit-slider-thumb{{-webkit-appearance:none;appearance:none;width:18px;height:18px;border-radius:50%;background:#1976d2;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3);cursor:pointer;pointer-events:all;}}
.cf-range::-moz-range-thumb{{width:18px;height:18px;border-radius:50%;background:#1976d2;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3);cursor:pointer;pointer-events:all;}}
#sorgBtn,#fitBtn,#pairBtn{{padding:.4rem .85rem;border-radius:6px;border:1px solid #ddd;background:#f5f5f5;font-size:.85rem;cursor:pointer;white-space:nowrap;transition:background .15s,border-color .15s;}}
#sorgBtn.hidden{{background:#ffebee;border-color:#ef9a9a;color:#c62828;}}
#fitBtn.active{{background:#e8f5e9;border-color:#a5d6a7;color:#2e7d32;}}
#pairBtn.active{{background:#e3f2fd;border-color:#90caf9;color:#1565c0;}}
</style>
<div id="filterBar" style="position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid #e0e0e0;padding:.9rem 1rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;">{slider}
  <button id="fitBtn" class="active">🟢 Nur geeignet</button>
  <button id="pairBtn" class="active">🐱🐱 Nur Pärchen (aktiv)</button>
  <button id="sorgBtn" class="hidden">🔴 Sorgenkinder einblenden</button>
</div>
<script>
(function(){{
  var minR=document.getElementById('ageMin'),maxR=document.getElementById('ageMax'),
      fill=document.getElementById('sliderFill'),lbl=document.getElementById('ageLabel'),
      sorgBtn=document.getElementById('sorgBtn'),fitBtn=document.getElementById('fitBtn'),
      pairBtn=document.getElementById('pairBtn');
  var LO={age_min},HI={age_max},showSorg=false,showOnlyFit=true,showOnlyPair=true;
  function fmt(m){{if(m<12)return m+' Mon.';var y=Math.floor(m/12),r=m%12;return y+(r>=6?'.5':'')+' J.';}}
  function pct(v){{return HI>LO?(v-LO)/(HI-LO)*100:0;}}
  function update(){{
    var lo=minR?parseInt(minR.value):LO,hi=maxR?parseInt(maxR.value):HI;
    if(lo>hi){{if(document.activeElement===minR){{minR.value=hi;lo=hi;}}else{{maxR.value=lo;hi=lo;}}}}
    if(fill){{fill.style.left=pct(lo)+'%';fill.style.width=Math.max(0,pct(hi)-pct(lo))+'%';}}
    if(lbl)lbl.textContent=fmt(lo)+' \u2013 '+fmt(hi);
    filter(lo,hi);
  }}
  function filter(lo,hi){{
    var visible=0;
    document.querySelectorAll('.card').forEach(function(c){{
      var r=c.dataset.rating,a=c.dataset.ageMonths,show;
      if(showOnlyFit){{show=(r==='geeignet');}}
      else if(r==='nicht_geeignet'&&!showSorg){{show=false;}}
      else{{show=true;}}
      if(show){{show=(!a||a==='unknown')||(parseInt(a)>=lo&&parseInt(a)<=hi);}}
      if(show&&showOnlyPair){{show=c.dataset.companions==='2';}}
      c.style.display=show?'':'none';
      if(show)visible++;
    }});
    var vc=document.getElementById('visibleCount');
    if(vc)vc.textContent=visible;
  }}
  pairBtn.addEventListener('click',function(){{
    showOnlyPair=!showOnlyPair;
    pairBtn.textContent=showOnlyPair?'🐱🐱 Nur Pärchen (aktiv)':'🐱🐱 Nur Pärchen';
    pairBtn.classList.toggle('active',showOnlyPair);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  fitBtn.addEventListener('click',function(){{
    showOnlyFit=!showOnlyFit;
    fitBtn.textContent=showOnlyFit?'🟢 Nur geeignet':'🟢 Alle Bewertungen';
    fitBtn.classList.toggle('active',showOnlyFit);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  sorgBtn.addEventListener('click',function(){{
    showSorg=!showSorg;
    sorgBtn.textContent=showSorg?'🔴 Sorgenkinder ausblenden':'🔴 Sorgenkinder einblenden';
    sorgBtn.classList.toggle('hidden',!showSorg);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  if(minR)minR.addEventListener('input',update);
  if(maxR)maxR.addEventListener('input',update);
  document.addEventListener('DOMContentLoaded',update);
}})();
</script>"""


def fetch_profile_text(cat: Cat) -> str:
    """Holt den Steckbrief und extrahiert den relevanten Beschreibungstext."""
    html_doc = _http_get(cat.profile_url)
    soup = BeautifulSoup(html_doc, "html.parser")

    # Hauptinhalt: <main> falls vorhanden, sonst <article>, sonst gesamter Body.
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""

    # Navigation, Footer, Scripts rauswerfen
    for tag in main.find_all(["nav", "footer", "script", "style", "aside"]):
        tag.decompose()

    text = main.get_text("\n", strip=True)
    # Kompaktieren: viele Leerzeilen → eine
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Längenbegrenzung für den API-Call
    return text[:8000]


# ---------------------------------------------------------------------------
# Claude-Bewertung
# ---------------------------------------------------------------------------

def evaluate_cat(client: Anthropic, cat: Cat, profile_text: str) -> CatRating:
    if not profile_text.strip():
        return CatRating(rating="unbekannt", reason="Steckbriefseite konnte nicht geladen werden.")

    user_prompt = (
        f"Steckbrief von {cat.name} (ID {cat.cat_id}):\n\n"
        f"{profile_text}\n\n"
        "Bewerte die Kindertauglichkeit dieser Katze nach dem oben definierten Schema."
    )

    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + API_RETRY_DELAYS):
        if delay:
            print(f"  Rate-Limit erreicht — warte {delay}s und versuche es erneut …")
            time.sleep(delay)
        try:
            response = client.messages.parse(
                model=MODEL,
                max_tokens=400,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_prompt}],
                output_format=CatRating,
            )
            return response.parsed_output
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                last_exc = e
                continue
            raise
    raise RuntimeError(f"Rate-Limit nach {len(API_RETRY_DELAYS)+1} Versuchen nicht überwunden") from last_exc


def evaluate_all(cats: list[Cat], profile_texts: dict[str, str]) -> dict[str, CatRating]:
    """Parallelisiert Claude-Calls über mehrere Katzen."""
    client = Anthropic()
    results: dict[str, CatRating] = {}

    def work(c: Cat) -> tuple[str, CatRating]:
        try:
            rating = evaluate_cat(client, c, profile_texts.get(c.cat_id, ""))
            return c.cat_id, rating
        except Exception as e:
            print(f"  ! Fehler bei {c.name} ({c.cat_id}): {e}")
            return c.cat_id, CatRating(rating="unbekannt", reason=f"Bewertungsfehler: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_EVAL_WORKERS) as pool:
        futures = [pool.submit(work, c) for c in cats]
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            cid, rating = fut.result()
            results[cid] = rating
            done += 1
            print(f"  [{done}/{len(cats)}] {cid} → {rating.rating}")

    return results


def _card_sort_key(pair: tuple) -> tuple:
    """Primär nach Rating, dann Pärchen vor Einzelkatzen, Partner direkt nebeneinander."""
    cat, rating = pair
    r = RATING_META[rating.rating]["order"]
    if cat.companion_count == 2:
        group = min(cat.name.lower(), cat.partner_name.lower()) if cat.partner_name else cat.name.lower()
        return (r, 0, group, cat.name.lower())
    return (r, 1, "", cat.name.lower())


# ---------------------------------------------------------------------------
# HTML-Report
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catfinder — {timestamp}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #fafafa; color: #222; }}
header {{ background: #fff; border-bottom: 1px solid #e0e0e0; padding: 1rem 1.25rem; }}
header h1 {{ margin: 0 0 .3rem; font-size: 1.4rem; }}
header .stats {{ color: #666; font-size: .85rem; line-height: 1.5; }}
main {{ max-width: 1600px; margin: 1.5rem auto; padding: 0 1rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; }}
.card {{ background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.08); overflow: hidden; display: flex; flex-direction: column; border-left: 6px solid var(--accent); }}
.card img {{ width: 100%; height: 220px; object-fit: cover; display: block; background: #eee; }}
.card .body {{ padding: 1rem 1.1rem 1.2rem; flex: 1; display: flex; flex-direction: column; gap: .5rem; }}
.card h2 {{ margin: 0; font-size: 1.1rem; }}
.card .meta {{ color: #666; font-size: .85rem; }}
.card .rating {{ font-weight: 600; color: var(--accent); }}
.card .reason {{ font-size: .9rem; color: #333; flex: 1; }}
.card a.btn {{ margin-top: .5rem; display: block; background: #1976d2; color: #fff; padding: .65rem .9rem; border-radius: 6px; text-decoration: none; text-align: center; font-weight: 500; font-size: .95rem; }}
.card a.btn:hover {{ background: #1565c0; }}
.empty {{ text-align: center; color: #666; padding: 4rem 1rem; }}
.badge-int {{ display: inline-block; background: #fff3e0; color: #e65100; font-size: .78rem; font-weight: 700; padding: .2rem .55rem; border-radius: 4px; letter-spacing: .01em; }}
.card .partner {{ font-size: .85rem; color: #1565c0; font-style: italic; }}
section + section {{ margin-top: 3rem; }}
section h2.group {{ font-size: 1.1rem; color: #555; border-bottom: 1px solid #ddd; padding-bottom: .4rem; margin-bottom: 1rem; }}
@media (max-width: 480px) {{
  .grid {{ grid-template-columns: 1fr; }}
  header h1 {{ font-size: 1.2rem; }}
}}
</style>
</head>
<body>
<header>
  <h1>🐈 Catfinder — Tierschutzverein München</h1>
  <div class="stats">
    Lauf vom {timestamp} · {total_listed} Katzen gelistet · <strong>{new_count} neu bewertet</strong>{scope_note} · <span id="visibleCount">{new_count}</span> angezeigt
  </div>
</header>
<main>
{filter_bar}
{body}
</main>
</body>
</html>
"""


def render_report(
    evaluated: list[tuple[Cat, CatRating]],
    total_listed: int,
    scope_note: str = "",
    listing_ages: dict[str, int | None] | None = None,
    still_known: list[tuple[Cat, CatRating]] | None = None,
    no_longer_listed: list[tuple[Cat, CatRating]] | None = None,
) -> str:
    still_known = still_known or []
    no_longer_listed = no_longer_listed or []
    evaluated_sorted = sorted(evaluated, key=_card_sort_key)

    def get_age(cat_id: str, hint: str) -> int | None:
        if listing_ages is not None:
            return listing_ages.get(cat_id)
        return age_hint_to_months(hint)

    def _img(cat: Cat) -> str:
        return (
            f'<img src="{html.escape(cat.image_url)}" alt="{html.escape(cat.name)}" loading="lazy">'
            if cat.image_url
            else '<div style="height:220px;background:#e0e0e0;display:flex;align-items:center;justify-content:center;color:#999;">kein Foto</div>'
        )

    def _meta_line(cat: Cat, age_months: int | None = None) -> str:
        if age_months is not None:
            y, mo = divmod(age_months, 12)
            age_str = f"{y} Jahr{'e' if y != 1 else ''}" if y else f"{mo} Monate"
        else:
            age_str = cat.age_hint
        bits = [b for b in (cat.breed, cat.sex, age_str) if b]
        return " · ".join(html.escape(b) for b in bits) if bits else "&nbsp;"

    def _interested_badge(cat: Cat) -> str:
        return '<div class="badge-int">👥 Interessenten vorhanden</div>' if cat.has_interested else ""

    def _pair_attr(cat: Cat) -> str:
        return str(cat.companion_count)

    def _partner_line(cat: Cat) -> str:
        if cat.companion_count == 2 and cat.partner_name:
            return f'<div class="partner">🐱 Pärchen mit <strong>{html.escape(cat.partner_name)}</strong></div>'
        return ""

    # Slider-Grenzen aus allen angezeigten Katzen berechnen
    all_ages = [get_age(c.cat_id, c.age_hint) for c, _ in evaluated_sorted]
    all_ages += [get_age(c.cat_id, c.age_hint) for c, _ in still_known]
    all_ages += [get_age(c.cat_id, c.age_hint) for c, _ in no_longer_listed]
    known_ages = [a for a in all_ages if a is not None]
    age_min = min(known_ages) if known_ages else 0
    age_max = max(known_ages) if known_ages else 0
    filter_bar = _build_filter_bar(age_min, age_max, False) if (evaluated_sorted or still_known) else ""

    two_sections = bool(still_known or no_longer_listed)

    # Sektion 1 — neue Katzen
    if not evaluated_sorted:
        sect1_inner = '<div class="empty">Keine neuen Katzen seit dem letzten Lauf. 🎉</div>'
    else:
        cards = []
        for (cat, rating), age_months in zip(
            evaluated_sorted,
            [get_age(c.cat_id, c.age_hint) for c, _ in evaluated_sorted],
        ):
            meta = RATING_META[rating.rating]
            age_data = str(age_months) if age_months is not None else "unknown"
            cards.append(f"""
    <div class="card" style="--accent: {meta['color']};" data-age-months="{age_data}" data-rating="{rating.rating}" data-companions="{_pair_attr(cat)}">
      {_img(cat)}
      <div class="body">
        <h2>{html.escape(cat.name)} <span style="color:#999;font-weight:400;font-size:.85rem;">#{html.escape(cat.cat_id)}</span></h2>
        <div class="meta">{_meta_line(cat, age_months)}</div>
        {_partner_line(cat)}
        {_interested_badge(cat)}
        <div class="rating">{meta['emoji']} {meta['label']}</div>
        <div class="reason">{html.escape(rating.reason)}</div>
        <a class="btn" href="{html.escape(cat.profile_url)}" target="_blank" rel="noopener">Steckbrief öffnen →</a>
      </div>
    </div>""")
        sect1_inner = f'<div class="grid">{"".join(cards)}</div>'

    if two_sections:
        sect1 = f'<section><h2 class="group">✨ Neu seit letztem Lauf ({len(evaluated_sorted)})</h2>{sect1_inner}</section>'
    else:
        sect1 = f'<section>{sect1_inner}</section>'

    # Sektion 2 — nicht mehr verfügbare Katzen
    sect_gone = ""
    if no_longer_listed:
        cards = []
        for cat, rating in sorted(no_longer_listed, key=_card_sort_key):
            meta = RATING_META[rating.rating]
            age_months = get_age(cat.cat_id, cat.age_hint)
            age_data = str(age_months) if age_months is not None else "unknown"
            cards.append(f"""
    <div class="card" style="--accent: {meta['color']}; opacity: .6;" data-age-months="{age_data}" data-rating="{rating.rating}" data-companions="{_pair_attr(cat)}">
      {_img(cat)}
      <div class="body">
        <h2>{html.escape(cat.name)} <span style="color:#999;font-weight:400;font-size:.85rem;">#{html.escape(cat.cat_id)}</span></h2>
        <div class="meta">{_meta_line(cat, age_months)}</div>
        {_partner_line(cat)}
        {_interested_badge(cat)}
        <div class="rating">{meta['emoji']} {meta['label']}</div>
        <div class="reason">{html.escape(rating.reason)}</div>
        <a class="btn" href="{html.escape(cat.profile_url)}" target="_blank" rel="noopener" style="background:#9e9e9e;">Steckbrief öffnen →</a>
      </div>
    </div>""")
        sect_gone = f'<section><h2 class="group">🚫 Nicht mehr verfügbar ({len(no_longer_listed)})</h2><div class="grid">{"".join(cards)}</div></section>'

    # Sektion 3 — weiterhin verfügbare Katzen (mit gespeicherter Ampelbewertung)
    sect2 = ""
    if still_known:
        cards = []
        for cat, rating in sorted(still_known, key=_card_sort_key):
            meta = RATING_META[rating.rating]
            age_months = get_age(cat.cat_id, cat.age_hint)
            age_data = str(age_months) if age_months is not None else "unknown"
            cards.append(f"""
    <div class="card" style="--accent: {meta['color']};" data-age-months="{age_data}" data-rating="{rating.rating}" data-companions="{_pair_attr(cat)}">
      {_img(cat)}
      <div class="body">
        <h2>{html.escape(cat.name)} <span style="color:#999;font-weight:400;font-size:.85rem;">#{html.escape(cat.cat_id)}</span></h2>
        <div class="meta">{_meta_line(cat, age_months)}</div>
        {_partner_line(cat)}
        {_interested_badge(cat)}
        <div class="rating">{meta['emoji']} {meta['label']}</div>
        <div class="reason">{html.escape(rating.reason)}</div>
        <a class="btn" href="{html.escape(cat.profile_url)}" target="_blank" rel="noopener">Steckbrief öffnen →</a>
      </div>
    </div>""")
        sect2 = f'<section><h2 class="group">📋 Weiterhin verfügbar ({len(still_known)})</h2><div class="grid">{"".join(cards)}</div></section>'

    return HTML_TEMPLATE.format(
        timestamp=datetime.now().strftime("%d.%m.%Y %H:%M"),
        total_listed=total_listed,
        new_count=len(evaluated_sorted),
        scope_note=scope_note,
        filter_bar=filter_bar,
        body=sect1 + sect_gone + sect2,
    )


def write_and_open_report(html_text: str, no_browser: bool = False) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(html_text, encoding="utf-8")
    print(f"\nReport geschrieben: {REPORT_FILE}")
    if not no_browser:
        webbrowser.open(REPORT_FILE.as_uri())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_github_output(new_count: int) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"new_count={new_count}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Catfinder — neue Katzen finden & auf Kindertauglichkeit bewerten.")
    parser.add_argument("--reset", action="store_true", help="State löschen, alles als neu behandeln.")
    parser.add_argument("--all", action="store_true", help="Alle aktuell gelisteten Katzen bewerten (ohne Diff).")
    parser.add_argument("--no-browser", action="store_true", help="Browser nicht öffnen (z.B. für CI).")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Fehler: ANTHROPIC_API_KEY ist nicht gesetzt.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  (z.B. in ~/.zshrc eintragen)"
        )
        return 1

    if args.reset and STATE_FILE.exists():
        STATE_FILE.unlink()
        print("State zurückgesetzt.")

    print(f"Rufe Listenseite ab: {LISTING_URL}")
    cats = scrape_listing()
    all_cat_names = [c.name for c in cats]
    print(f"  {len(cats)} Katzen gelistet.")

    state = load_state()
    had_prior_state = bool(state)  # D-07: Erstlauf vs. regulärer Lauf — voriger State nicht-leer?
    known_ids = set(state.keys())

    if args.all or not state:
        to_evaluate = cats
        still_known: list[Cat] = []
        scope_note = " · alle bewertet" if args.all else " · Erstlauf"
    else:
        to_evaluate = [c for c in cats if c.cat_id not in known_ids]
        still_known = [c for c in cats if c.cat_id in known_ids]
        scope_note = ""

    def _ratings_from_state(cat_list: list[Cat]) -> list[tuple[Cat, CatRating]]:
        result = []
        for c in cat_list:
            entry = state.get(c.cat_id, {})
            r = entry.get("rating", "unbekannt")
            if r not in ("geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt"):
                r = "unbekannt"
            c.has_interested = entry.get("has_interested", False)
            c.companion_count = entry.get("companion_count", 0)
            c.partner_name = entry.get("partner_name", "")
            result.append((c, CatRating(rating=r, reason=entry.get("reason", ""))))
        return result

    # Katzen die letztes Mal gelistet waren, jetzt aber nicht mehr
    current_ids = {c.cat_id for c in cats}
    no_longer_listed: list[tuple[Cat, CatRating]] = []
    for cid in sorted(known_ids - current_ids):
        entry = state[cid]
        c = Cat(
            cat_id=cid,
            name=entry.get("name", cid),
            profile_url=entry.get("profile_url", ""),
            image_url=entry.get("image_url", ""),
            breed=entry.get("breed", ""),
            sex=entry.get("sex", ""),
            age_hint=entry.get("age_hint", ""),
            has_interested=entry.get("has_interested", False),
            companion_count=entry.get("companion_count", 0),
            partner_name=entry.get("partner_name", ""),
        )
        r = entry.get("rating", "unbekannt")
        if r not in ("geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt"):
            r = "unbekannt"
        no_longer_listed.append((c, CatRating(rating=r, reason=entry.get("reason", ""))))

    def _age_months_with_fallback(cat_id: str, age_hint: str) -> int | None:
        return age_hint_to_months(age_hint) or age_hint_to_months(state.get(cat_id, {}).get("age_hint", ""))

    if not to_evaluate:
        print("Keine neuen Katzen seit dem letzten Lauf.")
        la = {c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c in still_known}
        la.update({c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c, _ in no_longer_listed})
        html_text = render_report([], len(cats), listing_ages=la,
                                  still_known=_ratings_from_state(still_known),
                                  no_longer_listed=no_longer_listed,
                                  had_prior_state=had_prior_state)
        write_and_open_report(html_text, no_browser=args.no_browser)
        # Purge: nur Katzen aus dem aktuellen Listing bleiben im State (D-02).
        for cid in list(state.keys()):
            if cid not in current_ids:
                del state[cid]
        save_state(state)
        print(f"State aktualisiert: {len(state)} Katzen bekannt.")
        _write_github_output(0)
        return 0

    print(f"\nLade {len(to_evaluate)} Steckbriefe …")
    profile_texts: dict[str, str] = {}
    for i, cat in enumerate(to_evaluate, 1):
        print(f"  [{i}/{len(to_evaluate)}] {cat.name} ({cat.cat_id})")
        try:
            profile_texts[cat.cat_id] = fetch_profile_text(cat)
        except Exception as e:
            print(f"    ! Fehler: {e}")
            profile_texts[cat.cat_id] = ""
        time.sleep(PROFILE_FETCH_DELAY_S)

    # Interessenten- und Pärchen-Status aus Steckbrief-Text erkennen
    for cat in to_evaluate:
        text = profile_texts.get(cat.cat_id, "")
        cat.has_interested = detect_interested(text)
        companions = find_companion_names(text, all_cat_names)
        if len(companions) == 2:
            cat.companion_count = 2
            cat.partner_name = next(n for n in companions if n.upper() != cat.name.upper())
        else:
            cat.companion_count = 0
            cat.partner_name = ""

    # Alter aus Steckbrief nachpflegen, falls Listing keines hatte
    for cat in to_evaluate:
        if not cat.age_hint:
            age = extract_age_hint(profile_texts.get(cat.cat_id, ""))
            if age:
                cat.age_hint = age

    # Alter-Index für den Slider — bevorzugt Listing-Alter, sonst Profil-Alter
    listing_ages: dict[str, int | None] = {
        cat.cat_id: age_hint_to_months(cat.age_hint) for cat in to_evaluate
    }
    listing_ages.update({c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c in still_known})
    listing_ages.update({c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c, _ in no_longer_listed})

    print(f"\nBewerte {len(to_evaluate)} Katzen via Claude …")
    ratings = evaluate_all(to_evaluate, profile_texts)

    evaluated = [(c, ratings[c.cat_id]) for c in to_evaluate if c.cat_id in ratings]

    html_text = render_report(evaluated, total_listed=len(cats), scope_note=scope_note,
                              listing_ages=listing_ages,
                              still_known=_ratings_from_state(still_known),
                              no_longer_listed=no_longer_listed,
                              had_prior_state=had_prior_state)
    write_and_open_report(html_text, no_browser=args.no_browser)

    # State: alle aktuell gelisteten Katzen eintragen, Bewertungen speichern.
    now_iso = datetime.now().isoformat(timespec="seconds")
    for cat in cats:
        if cat.cat_id not in state:
            entry = asdict(cat)
            entry["first_seen"] = now_iso
            state[cat.cat_id] = entry
    for cat in to_evaluate:
        if cat.cat_id in ratings:
            state[cat.cat_id]["rating"] = ratings[cat.cat_id].rating
            state[cat.cat_id]["reason"] = ratings[cat.cat_id].reason
            state[cat.cat_id]["has_interested"] = cat.has_interested
            state[cat.cat_id]["companion_count"] = cat.companion_count
            state[cat.cat_id]["partner_name"] = cat.partner_name
    # Purge: nur Katzen aus dem aktuellen Listing bleiben im State (D-02).
    for cid in list(state.keys()):
        if cid not in current_ids:
            del state[cid]
    save_state(state)
    print(f"State aktualisiert: {len(state)} Katzen bekannt.")
    _write_github_output(len(evaluated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
