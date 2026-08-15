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

# Je Kategorie drei Farbwerte:
#   color = Fläche, Kartenkante und Rahmen
#   text  = abgedunkelter Ton derselben Familie, für Text auf Weiß
#   on    = Schriftfarbe im gefüllten Label (Gelb trägt kein Weiß, nur 2.9:1)
# Alle Kombinationen liegen über WCAG AA (4.5:1); fest hinterlegt statt zur Laufzeit
# aus der Helligkeit gerechnet — es sind vier Werte, die sich nicht ändern.
RATING_META: dict[str, dict[str, str]] = {
    "geeignet":        {"label": "Kinder geeignet",   "color": "#1e7a35", "text": "#145c26", "on": "#ffffff", "order": "0"},
    "unbekannt":       {"label": "Keine Angabe",      "color": "#6b6560", "text": "#4d4843", "on": "#ffffff", "order": "1"},
    "aeltere_kinder":  {"label": "Nur ältere Kinder", "color": "#c9880a", "text": "#8a5c00", "on": "#17150f", "order": "2"},
    "nicht_geeignet":  {"label": "Nicht für Kinder",  "color": "#c62020", "text": "#971616", "on": "#ffffff", "order": "3"},
}

# Alle vier Health-Kategorien sind sichtbar — auch der Negativfall, weil ein fehlender
# Marker sonst nicht von "nicht bewertet" zu unterscheiden wäre. "keine" (geprüft, nichts
# gefunden) und "unbekannt" (Steckbrief nicht ladbar) tragen deshalb verschiedene Farben.
HEALTH_META: dict[str, dict[str, str]] = {
    "keine":           {"label": "Keine Erkrankung bekannt", "color": "#1e7a35", "text": "#145c26"},
    "erwaehnt":        {"label": "Gesundheit beachten",      "color": "#c9880a", "text": "#8a5c00"},
    "dauerbehandlung": {"label": "Dauerbehandlung nötig",    "color": "#c62020", "text": "#971616"},
    "unbekannt":       {"label": "Gesundheit unbekannt",     "color": "#6b6560", "text": "#4d4843"},
}

# Bestfall: für Kinder geeignet und ohne bekannte Erkrankung. Statt zweier grüner Labels
# wird eine zusammengezogene Aussage gerendert (Sketch 006, Vorschlag 2).
BEST_LABEL = "Geeignet und gesund"


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
    health: Literal["keine", "erwaehnt", "dauerbehandlung", "unbekannt"] = Field(
        default="unbekannt",
        description=(
            "keine = Steckbrief nennt keine gesundheitliche Einschränkung. "
            "erwaehnt = Einschränkung genannt, aber ohne dauerhafte Behandlung "
            "(z.B. Übergewicht, ausgeheilte Sache, nur beobachten). "
            "dauerbehandlung = braucht dauerhaft Medikamente, Spezialfutter oder Gabe zu festen Zeiten. "
            "unbekannt = kein Steckbrieftext vorhanden."
        ),
    )
    health_note: str = Field(
        default="",
        description=(
            "Die Erkrankung in max. einem Halbsatz, bevorzugt wörtlich aus dem Steckbrief "
            "(z.B. 'Epilepsie, 2x täglich Medikamente'). Leer lassen bei 'keine' und 'unbekannt'."
        ),
    )


SYSTEM_PROMPT = """Du bist ein Klassifikator für deutsche Tierheim-Steckbriefe.

Aufgabe: Bewerte, ob eine Katze laut ihrem Steckbrief für Familien mit Kindern geeignet ist.

Kategorien für 'rating':
- "geeignet": Der Text nennt Kinder ausdrücklich positiv ODER sagt "für Familien" / "kinderlieb" o.ä., ohne Einschränkung auf ein Alter.
- "aeltere_kinder": Nur mit älteren, ruhigen, verständnisvollen oder katzenerfahrenen Kindern (z.B. "Kinder ab 10", "größere Kinder", "ältere Kinder").
- "nicht_geeignet": Der Text schließt Kinder ausdrücklich aus ("keine Kinder", "nur Erwachsene", "nicht in Familien mit Kindern").
- "unbekannt": Der Text trifft KEINE Aussage zu Kindern. WICHTIG: Nicht raten oder aus anderen Merkmalen (scheu, ängstlich, Freigänger) auf Kinderverträglichkeit schließen — wenn nicht explizit erwähnt, ist es "unbekannt".

Gib als Begründung einen knappen Satz, bevorzugt ein wörtliches Zitat aus dem Text.

Zweite Aufgabe: Bewerte über 'health' den gesundheitlichen Pflegeaufwand GENAU DIESER Katze.
Die Angaben stehen meist im Abschnitt "Besonderheiten".

Es zählt ausschließlich ein diagnostizierter körperlicher Befund oder ein dauerhafter
Versorgungsbedarf. Alles andere ist "keine" — auch wenn der Text es ausführlich erwähnt.

Kategorien für 'health':
- "keine": Kein körperlicher Befund genannt.
- "erwaehnt": Befund genannt, aber ohne dauerhafte Behandlung (ausgeheilte Verletzung, Übergewicht, Wert unter Beobachtung).
- "dauerbehandlung": Braucht dauerhaft Medikamente, Spezialfutter oder Gaben zu festen Zeiten.
- "unbekannt": Es liegt kein Steckbrieftext vor.

NICHT als Erkrankung werten — das sind die häufigsten Fehlerquellen:
- Kastration, Impfung, Chippen. Auch dann nicht, wenn sie noch ausstehen: "noch nicht
  kastriert", "Kastration muss nachgeholt werden", "noch zu jung für die Kastration".
  Das ist Routine bei jedem Vermittlungstier, kein Befund.
- Verhalten und Entwicklung: Unsauberkeit bei Jungtieren ("altersbedingt ab und zu noch
  etwas unsauber"), Hyperaktivität, Beißvorfälle, Anknabbern von Gegenständen, Scheu,
  Unverträglichkeit mit Artgenossen. Auch dann nicht, wenn der Text ausdrücklich sagt,
  dass die medizinische Untersuchung ohne Befund blieb.
- "Sorgentier" und "Nur für erfahrene Halter" sind Vermittlungsmarker, keine Diagnose.
- Allgemeine Rassehinweise ohne konkreten Befund ("als British Kurzhaar besteht ein
  erhöhtes Risiko für rassetypische Erkrankungen").

Der Abschnitt "Besonderheiten" enthält häufig genau solche nicht-medizinischen Hinweise.
Dass er existiert und etwas erwähnt, ist für sich genommen KEIN Befund.

Pärchen-Steckbriefe beschreiben BEIDE Katzen im selben Text, oft im ganzen Abschnitt nur
die Partnerkatze. Bewerte ausschließlich die Katze, nach der im User-Prompt gefragt wird.
Ist der Befund einer anderen Katze zugeschrieben — erkennbar am Namen oder an "er"/"sie"
mit Bezug auf sie — dann ist 'health' für die gefragte Katze "keine".

'health_note': der Befund DIESER Katze in max. einem Halbsatz, bevorzugt wörtlich.
Bei "keine" und "unbekannt" leer lassen.

Letzte Prüfung vor der Antwort: Wählst du "erwaehnt" oder "dauerbehandlung", muss
'health_note' einen konkreten körperlichen Befund benennen — Diagnose, Organwert,
Verletzung, Allergie, Infektion, Über- oder Untergewicht. Kannst du keinen benennen, weil
es um Verhalten, Entwicklung, Erziehung, Kastration oder die Partnerkatze geht, dann ist
'health' = "keine" und 'health_note' leer. Ein Satz wie "keine diagnostizierte Erkrankung"
in der Notiz bedeutet immer "keine".
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


def _safe_rating(value: str) -> str:
    """Klemmt einen aus dem State gelesenen Rating-Wert auf eine gültige Kategorie."""
    return value if value in ("geeignet", "aeltere_kinder", "nicht_geeignet", "unbekannt") else "unbekannt"


def _rating_from_entry(entry: dict) -> CatRating:
    """Baut ein CatRating aus einem State-Eintrag; Alt-Einträge ohne health bleiben gültig."""
    health = entry.get("health", "unbekannt")
    if health not in ("keine", "erwaehnt", "dauerbehandlung", "unbekannt"):
        health = "unbekannt"
    return CatRating(
        rating=_safe_rating(entry.get("rating", "unbekannt")),
        reason=entry.get("reason", ""),
        health=health,
        health_note=entry.get("health_note", ""),
    )


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


def repair_pair_symmetry(cats: list[Cat], evaluated_ids: set[str], state: dict[str, dict]) -> None:
    """Ergänzt die fehlende Gegenrichtung bei einseitig erkannten Pärchen.

    Ein Pärchen gilt beidseitig, aber Steckbriefe nennen die Partnerkatze oft nur in
    Kurzform ("Constantin" statt Listing-Name "CONSTANTIN CHRISTOMANOS"). Dann schlägt
    find_companion_names nur auf einer Seite an und die andere Karte zeigt keinen Partner.

    Katzen aus evaluated_ids tragen ihren Stand am Cat-Objekt, alle anderen im State —
    letztere werden dort mitkorrigiert, weil _ratings_from_state ihre Werte von dort
    liest und das Cat-Objekt sonst wieder überschreiben würde.
    """
    def partner_of(c: Cat) -> str:
        if c.cat_id in evaluated_ids:
            return c.partner_name
        return state.get(c.cat_id, {}).get("partner_name", "")

    by_name = {c.name.upper(): c for c in cats}
    for cat in cats:
        pname = partner_of(cat)
        if not pname:
            continue
        partner = by_name.get(pname.upper())
        if partner is None or partner.cat_id == cat.cat_id or partner_of(partner):
            continue
        partner.companion_count = 2
        partner.partner_name = cat.name
        if partner.cat_id in state:
            state[partner.cat_id]["companion_count"] = 2
            state[partner.cat_id]["partner_name"] = cat.name


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


def _build_filter_bar(age_min: int, age_max: int) -> str:
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
  <div style="display:flex;align-items:center;gap:.6rem;">
    <span class="cf-cap">Alter</span>
    <div class="cf-track">
      <div id="sliderFill" class="cf-fill"></div>
      <input type="range" class="cf-range" id="ageMin" min="{age_min}" max="{age_max}" value="{default_lo}">
      <input type="range" class="cf-range" id="ageMax" min="{age_min}" max="{age_max}" value="{default_hi}">
    </div>
    <span id="ageLabel" class="cf-cap">{fmt(default_lo)} – {fmt(default_hi)}</span>
  </div>"""

    return f"""<style>
.cf-cap{{font-size:.8rem;color:#5c574f;white-space:nowrap;}}
.cf-track{{position:relative;width:130px;height:1px;background:#c9c3b8;margin:.2rem 0;}}
.cf-fill{{position:absolute;top:-1px;height:3px;background:#141310;pointer-events:none;}}
.cf-range{{position:absolute;width:100%;height:0;top:0;pointer-events:none;-webkit-appearance:none;appearance:none;background:transparent;outline:none;}}
.cf-range::-webkit-slider-thumb{{-webkit-appearance:none;appearance:none;width:14px;height:14px;border-radius:50%;background:#141310;border:2px solid #f5f3ef;cursor:pointer;pointer-events:all;}}
.cf-range::-moz-range-thumb{{width:14px;height:14px;border-radius:50%;background:#141310;border:2px solid #f5f3ef;cursor:pointer;pointer-events:all;}}
#sorgBtn,#fitBtn,#pairBtn,#healthBtn{{background:none;border:none;padding:.2rem 0;font:inherit;font-size:.85rem;color:#5c574f;cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent;}}
#fitBtn.active,#pairBtn.active,#healthBtn.active{{color:#141310;border-bottom-color:#141310;font-weight:600;}}
#sorgBtn{{color:#971616;}}
#sorgBtn.hidden{{color:#5c574f;}}
#resetBtn{{margin-left:auto;background:none;border:none;padding:.2rem 0;color:#5c574f;cursor:pointer;font:inherit;font-size:.85rem;text-decoration:underline;text-underline-offset:3px;}}
#resetBtn:hover{{color:#141310;}}
</style>
<div id="filterBar" style="position:sticky;top:0;z-index:100;background:#f5f3ef;border-bottom:1px solid #d2cbc0;padding:1rem 0;display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;">{slider}
  <button id="fitBtn" class="active">Nur geeignet</button>
  <button id="pairBtn" class="active">Nur Pärchen (aktiv)</button>
  <button id="sorgBtn" class="hidden">Sorgenkinder einblenden</button>
  <button id="healthBtn">Dauerbehandlung ausblenden</button>
  <button id="resetBtn">Alle Katzen zeigen</button>
</div>
<script>
(function(){{
  var minR=document.getElementById('ageMin'),maxR=document.getElementById('ageMax'),
      fill=document.getElementById('sliderFill'),lbl=document.getElementById('ageLabel'),
      sorgBtn=document.getElementById('sorgBtn'),fitBtn=document.getElementById('fitBtn'),
      pairBtn=document.getElementById('pairBtn'),resetBtn=document.getElementById('resetBtn'),
      healthBtn=document.getElementById('healthBtn');
  var LO={age_min},HI={age_max},showSorg=false,showOnlyFit=true,showOnlyPair=true,hideTreat=false;
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
      if(show&&hideTreat){{show=c.dataset.health!=='dauerbehandlung';}}
      c.style.display=show?'':'none';
      if(show)visible++;
    }});
    var vc=document.getElementById('visibleCount');
    if(vc)vc.textContent=visible;
  }}
  pairBtn.addEventListener('click',function(){{
    showOnlyPair=!showOnlyPair;
    pairBtn.textContent=showOnlyPair?'Nur Pärchen (aktiv)':'Nur Pärchen';
    pairBtn.classList.toggle('active',showOnlyPair);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  fitBtn.addEventListener('click',function(){{
    showOnlyFit=!showOnlyFit;
    fitBtn.textContent=showOnlyFit?'Nur geeignet':'Alle Bewertungen';
    fitBtn.classList.toggle('active',showOnlyFit);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  healthBtn.addEventListener('click',function(){{
    hideTreat=!hideTreat;
    healthBtn.textContent=hideTreat?'Dauerbehandlung ausgeblendet':'Dauerbehandlung ausblenden';
    healthBtn.classList.toggle('active',hideTreat);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  sorgBtn.addEventListener('click',function(){{
    showSorg=!showSorg;
    sorgBtn.textContent=showSorg?'Sorgenkinder ausblenden':'Sorgenkinder einblenden';
    sorgBtn.classList.toggle('hidden',!showSorg);
    filter(minR?parseInt(minR.value):LO,maxR?parseInt(maxR.value):HI);
  }});
  resetBtn.addEventListener('click',function(){{
    showSorg=true;showOnlyFit=false;showOnlyPair=false;hideTreat=false;
    if(minR)minR.value=LO;
    if(maxR)maxR.value=HI;
    fitBtn.textContent='Nur geeignet';
    fitBtn.classList.remove('active');
    pairBtn.textContent='Nur Pärchen';
    pairBtn.classList.remove('active');
    sorgBtn.textContent='Sorgenkinder ausblenden';
    sorgBtn.classList.remove('hidden');
    healthBtn.textContent='Dauerbehandlung ausblenden';
    healthBtn.classList.remove('active');
    update();
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

    # Partnername steht aus dem Listing bereits fest (main setzt ihn vor der Bewertung) —
    # dem Modell nennen statt es aus dem Fließtext raten zu lassen.
    partner_hint = (
        f" Der Text beschreibt auch die Partnerkatze {cat.partner_name}. Befunde, die "
        f"{cat.partner_name} betreffen, zählen für {cat.name} nicht."
        if cat.partner_name
        else ""
    )
    user_prompt = (
        f"Steckbrief von {cat.name} (ID {cat.cat_id}):\n\n"
        f"{profile_text}\n\n"
        f"Bewerte Kindertauglichkeit und Gesundheit von {cat.name} nach dem oben "
        f"definierten Schema.{partner_hint}"
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
:root {{
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --paper: #f5f3ef; --ink: #141310; --soft: #3a3630; --mute: #5c574f; --hair: #d2cbc0;
}}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0;
        background: var(--paper); color: var(--ink); -webkit-font-smoothing: antialiased; }}
header {{ max-width: 1500px; margin: 0 auto; padding: 2.5rem 1.5rem 1.4rem; }}
header h1 {{ font-family: var(--serif); font-weight: 400; font-size: 2.4rem; margin: 0 0 .35rem;
             letter-spacing: -.01em; }}
header .stats {{ color: var(--mute); font-size: .85rem; line-height: 1.5;
                 border-top: 2px solid var(--ink); padding-top: .9rem; }}
main {{ max-width: 1500px; margin: 0 auto; padding: 0 1.5rem 5rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 2rem 1.75rem; }}
.card {{ background: #fff; display: flex; flex-direction: column;
         border: 1px solid var(--hair); border-left: 4px solid var(--accent); }}
.card img {{ width: 100%; height: 220px; object-fit: cover; display: block; background: #e6e3dd; }}
.card .body {{ padding: 1rem 1.1rem 1.1rem; flex: 1; display: flex; flex-direction: column; gap: .5rem; }}
.card h2 {{ font-family: var(--serif); font-weight: 400; font-size: 1.3rem; margin: 0; line-height: 1.25; }}
.card .meta {{ color: var(--mute); font-size: .82rem; }}
.card .status {{ display: flex; flex-direction: column; gap: .2rem; }}
.card .partner {{ font-size: .85rem; color: #1f4453; }}
.badge-int {{ font-size: .74rem; letter-spacing: .06em; text-transform: uppercase;
              font-weight: 700; color: #971616; }}
.card .labels {{ display: flex; flex-direction: column; align-items: flex-start; gap: .3rem; margin-top: .15rem; }}
.card .lab {{ font-size: .78rem; font-weight: 600; padding: .26rem .65rem; border-radius: 2px;
              border: 1px solid; line-height: 1.25; }}
.card .lab-best {{ font-size: .85rem; padding: .35rem .8rem; }}
.card .reason {{ font-size: .88rem; line-height: 1.55; color: var(--soft); flex: 1; margin-top: .3rem; }}
.card .health {{ font-size: .85rem; line-height: 1.5; padding-left: .7rem; border-left: 2px solid; }}
.card .foot {{ padding-top: .75rem; border-top: 1px solid var(--hair); display: flex;
               justify-content: space-between; align-items: baseline; gap: .75rem;
               font-size: .78rem; color: var(--mute); }}
.card .foot a {{ color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--soft);
                 font-weight: 500; white-space: nowrap; }}
.card .foot a:hover {{ color: #1f4453; border-color: #1f4453; }}
.card.gone {{ opacity: .6; }}
.empty {{ text-align: center; color: var(--mute); padding: 4rem 1rem; background: #fff;
          border: 1px solid var(--hair); }}
section {{ margin-top: 3rem; }}
section h2.group {{ font-family: var(--serif); font-weight: 400; font-size: 1.4rem;
                    color: var(--soft); margin: 0 0 1.4rem; }}
@media (max-width: 520px) {{
  .grid {{ grid-template-columns: 1fr; }}
  header h1 {{ font-size: 1.9rem; }}
}}
</style>
</head>
<body>
<header>
  <h1>Catfinder</h1>
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
    had_prior_state: bool = False,
    first_seen_map: dict[str, str] | None = None,
) -> str:
    still_known = still_known or []
    no_longer_listed = no_longer_listed or []
    evaluated_sorted = sorted(evaluated, key=_card_sort_key)

    # Katzen mit festen Interessenten sind faktisch vergeben, sollen aber sichtbar
    # bleiben — eigene Sektion statt Verwässerung der beiden Hauptlisten.
    # Verschwundene Katzen (no_longer_listed) sind hiervon bewusst ausgenommen.
    interested = sorted(
        [p for p in evaluated_sorted + still_known if p[0].has_interested],
        key=_card_sort_key,
    )
    evaluated_sorted = [p for p in evaluated_sorted if not p[0].has_interested]
    still_known = [p for p in still_known if not p[0].has_interested]

    def get_age(cat_id: str, hint: str) -> int | None:
        if listing_ages is not None:
            return listing_ages.get(cat_id)
        return age_hint_to_months(hint)

    def get_listed_days(cat_id: str) -> int:
        fs = first_seen_map.get(cat_id) if first_seen_map else None
        if not fs:
            return 0
        try:
            seen = datetime.fromisoformat(fs).date()
        except ValueError:
            return 0
        return max(0, (date.today() - seen).days)

    def _listed_line(cat: Cat) -> str:
        days = get_listed_days(cat.cat_id)
        if days == 0:
            txt = "seit heute gelistet"
        elif days == 1:
            txt = "seit 1 Tag gelistet"
        else:
            txt = f"seit {days} Tagen gelistet"
        return txt

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

    def _status_line(cat: Cat) -> str:
        """Partner und Interessenten — steht direkt unter Name und Metazeile."""
        bits = []
        if cat.companion_count == 2 and cat.partner_name:
            bits.append(f'<span class="partner">Pärchen mit <strong>{html.escape(cat.partner_name)}</strong></span>')
        if cat.has_interested:
            bits.append('<span class="badge-int">Interessenten vorhanden</span>')
        return f'<div class="status">{"".join(bits)}</div>' if bits else ""

    def _labels(rating: CatRating) -> str:
        """Bewertung gefüllt, Gesundheit umrandet darunter.

        Bestfall (geeignet + keine Erkrankung) wird zu einem Label zusammengezogen —
        zwei grüne Labels übereinander tragen dieselbe Aussage doppelt.
        """
        rm = RATING_META[rating.rating]
        filled = (
            f'<span class="lab{{cls}}" style="background:{rm["color"]};'
            f'border-color:{rm["color"]};color:{rm["on"]}">{{text}}</span>'
        )
        if rating.rating == "geeignet" and rating.health == "keine":
            return f'<div class="labels">{filled.format(cls=" lab-best", text=BEST_LABEL)}</div>'

        hm = HEALTH_META.get(rating.health, HEALTH_META["unbekannt"])
        outlined = (
            f'<span class="lab" style="background:#fff;'
            f'border-color:{hm["color"]};color:{hm["text"]}">{hm["label"]}</span>'
        )
        return f'<div class="labels">{filled.format(cls="", text=rm["label"])}{outlined}</div>'

    def _health_note(rating: CatRating) -> str:
        """Beschreibung aus Gesundheitssicht, im Ton der Kategorie. Leer wenn nichts vorliegt."""
        if not rating.health_note:
            return ""
        hm = HEALTH_META.get(rating.health, HEALTH_META["unbekannt"])
        return (f'<div class="health" style="color:{hm["text"]};border-color:{hm["color"]}">'
                f'{html.escape(rating.health_note)}</div>')

    def _render_card(cat: Cat, rating: CatRating, *, dimmed: bool = False) -> str:
        """Erzeugt das HTML-Markup für eine Katzen-Card; dimmed=True für nicht mehr verfügbare Katzen."""
        meta = RATING_META[rating.rating]
        age_months = get_age(cat.cat_id, cat.age_hint)
        age_data = str(age_months) if age_months is not None else "unknown"
        listed = "" if dimmed else _listed_line(cat)
        return f"""
    <div class="card{' gone' if dimmed else ''}" style="--accent: {meta['color']};" data-age-months="{age_data}" data-rating="{rating.rating}" data-companions="{cat.companion_count}" data-health="{rating.health}">
      {_img(cat)}
      <div class="body">
        <h2>{html.escape(cat.name)} <span style="font-family:-apple-system,sans-serif;color:#5c574f;font-size:.72rem;">{html.escape(cat.cat_id)}</span></h2>
        <div class="meta">{_meta_line(cat, age_months)}</div>
        {_status_line(cat)}
        {_labels(rating)}
        <div class="reason">{html.escape(rating.reason)}</div>
        {_health_note(rating)}
        <div class="foot"><span>{listed}</span>
          <a href="{html.escape(cat.profile_url)}" target="_blank" rel="noopener">Steckbrief &rarr;</a></div>
      </div>
    </div>"""

    # Slider-Grenzen aus allen angezeigten Katzen berechnen
    all_ages = [get_age(c.cat_id, c.age_hint) for c, _ in evaluated_sorted]
    all_ages += [get_age(c.cat_id, c.age_hint) for c, _ in still_known]
    all_ages += [get_age(c.cat_id, c.age_hint) for c, _ in no_longer_listed]
    all_ages += [get_age(c.cat_id, c.age_hint) for c, _ in interested]
    known_ages = [a for a in all_ages if a is not None]
    age_min = min(known_ages) if known_ages else 0
    age_max = max(known_ages) if known_ages else 0
    filter_bar = _build_filter_bar(age_min, age_max) if (evaluated_sorted or still_known or interested) else ""

    two_sections = bool(still_known or no_longer_listed or interested)

    # Sektion 1 — neue Katzen
    if not evaluated_sorted:
        sect1_inner = '<div class="empty">Keine neuen Katzen seit dem letzten Lauf.</div>'
    else:
        cards = [_render_card(cat, rating) for cat, rating in evaluated_sorted]
        sect1_inner = f'<div class="grid">{"".join(cards)}</div>'

    if two_sections:
        sect1 = f'<section><h2 class="group">Neu seit letztem Lauf ({len(evaluated_sorted)})</h2>{sect1_inner}</section>'
    else:
        sect1 = f'<section>{sect1_inner}</section>'

    # Sektion 2 — nicht mehr verfügbare Katzen
    sect_gone = ""
    if no_longer_listed:
        cards = [_render_card(cat, rating, dimmed=True) for cat, rating in sorted(no_longer_listed, key=_card_sort_key)]
        sect_gone = f'<section><h2 class="group">Nicht mehr verfügbar ({len(no_longer_listed)})</h2><div class="grid">{"".join(cards)}</div></section>'
    elif had_prior_state:
        # D-05/D-06/D-07: voriger State nicht-leer, aber nichts verschwunden — Empty-State-Hint mit bestehendem .empty-Pattern.
        sect_gone = (
            '<section><h2 class="group">Nicht mehr verfügbar (0)</h2>'
            '<div class="empty">Seit dem letzten Lauf sind keine Katzen verschwunden.</div>'
            '</section>'
        )
    # else: had_prior_state == False (Erstlauf / --reset / Cold-Start) — sect_gone bleibt "" (D-07: Sektion komplett ausblenden).

    # Sektion 3 — Katzen mit festen Interessenten (faktisch vergeben, aber sichtbar)
    sect_int = ""
    if interested:
        cards = [_render_card(cat, rating) for cat, rating in interested]
        sect_int = f'<section><h2 class="group">Interessenten vorhanden ({len(interested)})</h2><div class="grid">{"".join(cards)}</div></section>'

    # Sektion 4 — weiterhin verfügbare Katzen (mit gespeicherter Ampelbewertung)
    sect2 = ""
    if still_known:
        cards = [_render_card(cat, rating) for cat, rating in sorted(still_known, key=_card_sort_key)]
        sect2 = f'<section><h2 class="group">Weiterhin verfügbar ({len(still_known)})</h2><div class="grid">{"".join(cards)}</div></section>'

    return HTML_TEMPLATE.format(
        timestamp=datetime.now().strftime("%d.%m.%Y %H:%M"),
        total_listed=total_listed,
        new_count=len(evaluated),
        scope_note=scope_note,
        filter_bar=filter_bar,
        body=sect1 + sect_gone + sect_int + sect2,
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
    # voriger State nicht-leer und kein --all? Bei --all behandeln wir den Lauf als frisch (kein Delta-Hint).
    had_prior_state = bool(state) and not args.all
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
            c.has_interested = entry.get("has_interested", False)
            c.companion_count = entry.get("companion_count", 0)
            c.partner_name = entry.get("partner_name", "")
            result.append((c, _rating_from_entry(entry)))
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
        no_longer_listed.append((c, _rating_from_entry(entry)))

    def _age_months_with_fallback(cat_id: str, age_hint: str) -> int | None:
        return age_hint_to_months(age_hint) or age_hint_to_months(state.get(cat_id, {}).get("age_hint", ""))

    if not to_evaluate:
        print("Keine neuen Katzen seit dem letzten Lauf.")
        la = {c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c in still_known}
        la.update({c.cat_id: _age_months_with_fallback(c.cat_id, c.age_hint) for c, _ in no_longer_listed})
        html_text = render_report([], len(cats), listing_ages=la,
                                  still_known=_ratings_from_state(still_known),
                                  no_longer_listed=no_longer_listed,
                                  had_prior_state=had_prior_state,
                                  first_seen_map={cid: state[cid].get("first_seen", "") for cid in state})
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
        cat.has_interested = bool(INTERESTED_PATTERN.search(text))
        companions = find_companion_names(text, all_cat_names)
        if len(companions) == 2:
            cat.companion_count = 2
            cat.partner_name = next(n for n in companions if n.upper() != cat.name.upper())
        else:
            cat.companion_count = 0
            cat.partner_name = ""

    repair_pair_symmetry(cats, {c.cat_id for c in to_evaluate}, state)

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
                              had_prior_state=had_prior_state,
                              first_seen_map={cid: state[cid].get("first_seen", "") for cid in state})
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
            state[cat.cat_id]["health"] = ratings[cat.cat_id].health
            state[cat.cat_id]["health_note"] = ratings[cat.cat_id].health_note
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
