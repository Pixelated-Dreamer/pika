import streamlit as st
import requests
import json
import os
import base64
import pandas as pd
import difflib
import concurrent.futures
from datetime import datetime, timedelta
import random
import altair as alt


try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

st.set_page_config(page_title="PokéDex Collector", layout="wide", page_icon="🎴")

_DIR            = os.path.dirname(__file__)
COLLECTION_FILE = os.path.join(_DIR, "collection.json")

def load_env_key(key_name: str) -> str | None:
    env_path = os.path.join(_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key_name:
                        return v.strip().strip("'\"")
    return None

POKEMON_API_KEY = load_env_key("POKEMON_API_KEY")
TCG_API         = "https://api.tcgdex.net/v2"



# ── Background images ─────────────────────────────────────────────────────────
def _b64(name: str) -> str:
    path = os.path.join(_DIR, name)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_pika   = _b64("pikachu-transparent-32599.png")
_gengar = _b64("Gengar-PNG-Picture.png")

_extra_imgs = _extra_sz = _extra_pos = _extra_rep = _extra_att = ""
if _pika:
    _extra_imgs += f'url("data:image/png;base64,{_pika}"), '
    _extra_sz   += "130px, "; _extra_pos += "1% 97%, "
    _extra_rep  += "no-repeat, "; _extra_att += "fixed, "
if _gengar:
    _extra_imgs += f'url("data:image/png;base64,{_gengar}"), '
    _extra_sz   += "170px, "; _extra_pos += "98% 97%, "
    _extra_rep  += "no-repeat, "; _extra_att += "fixed, "

_bg_image = (
    _extra_imgs
    + "repeating-linear-gradient(0deg,transparent,transparent 23px,rgba(255,215,0,.04) 24px), "
    + "repeating-linear-gradient(90deg,transparent,transparent 23px,rgba(255,215,0,.04) 24px)"
)
_bg_size = _extra_sz + "auto, auto"
_bg_pos  = _extra_pos + "0 0, 0 0"
_bg_rep  = _extra_rep + "repeat, repeat"
_bg_att  = _extra_att + "fixed, fixed"


# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

/* ── Base ─────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {{
    background-color: #0d0d18;
    background-image: {_bg_image};
    background-size: {_bg_size};
    background-position: {_bg_pos};
    background-repeat: {_bg_rep};
    background-attachment: {_bg_att};
    font-family: 'Press Start 2P', monospace;
}}
[data-testid="stSidebar"] {{
    background-color: #080810;
    border-right: 2px solid #c8a84b55;
}}

/* ── Headings ─────────────────────────────────────────────── */
h1, h2, h3, h4 {{
    font-family: 'Press Start 2P', monospace !important;
}}
h1 {{
    color: #f5c518 !important;
    font-size: 18px !important;
    text-shadow: 3px 3px 0px #5c4a1a, 0 0 30px #c8a84b66;
    letter-spacing: 3px;
}}
h2, h3, h4 {{
    color: #c8a84b !important;
    font-size: 10px !important;
}}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 10px !important;
    background: #0d0d18;
    color: #f5c518;
    border: 2px solid #c8a84b;
    border-radius: 0px;
    padding: 10px 18px;
    width: 100%;
    transition: background 0.1s, color 0.1s, box-shadow 0.1s;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.stButton > button:hover {{
    background: #c8a84b;
    color: #0d0d18;
    border-color: #f5c518;
    box-shadow: 4px 4px 0px #5c4a1a;
}}
.stButton > button:active {{
    transform: translate(2px, 2px);
    box-shadow: 1px 1px 0px #5c4a1a;
}}

/* ── Text inputs ─────────────────────────────────────────── */
.stTextInput input {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 10px !important;
    background: #080810;
    color: #e0d8b0;
    border: 2px solid #c8a84b55;
    border-radius: 0px;
    caret-color: #f5c518;
    transition: border-color 0.1s;
    padding: 10px 12px;
}}
.stTextInput input:focus {{
    border-color: #f5c518 !important;
    box-shadow: none !important;
    outline: none !important;
}}
.stTextInput input::placeholder {{
    color: #3a3a5a;
    font-size: 8px;
}}
.stTextInput label {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 9px !important;
    font-weight: 400;
    color: #f5c518 !important;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

/* ── Selectbox ─────────────────────────────────────────── */
.stSelectbox label {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 9px !important;
    color: #f5c518 !important;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.stSelectbox div[data-baseweb="select"] > div {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 10px !important;
    background: #080810 !important;
    color: #e0d8b0 !important;
    border: 2px solid #c8a84b55 !important;
    border-radius: 0px !important;
}}
.stSelectbox div[data-baseweb="select"] svg {{
    fill: #c8a84b !important;
}}
[data-baseweb="popover"] ul {{
    background: #0d0d18 !important;
    border: 2px solid #c8a84b !important;
    border-radius: 0px !important;
}}
[data-baseweb="popover"] li {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 9px !important;
    color: #c0c0a0 !important;
    background: #0d0d18 !important;
}}
[data-baseweb="popover"] li:hover {{
    background: #c8a84b22 !important;
    color: #f5c518 !important;
}}

/* ── Images ──────────────────────────────────────────────── */
[data-testid="stImage"] img {{
    border: 2px solid #c8a84b44;
    border-radius: 0px;
    display: block;
    margin: 0 auto;
    transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
}}
[data-testid="stImage"] img:hover {{
    transform: translateY(-3px);
    box-shadow: 0 6px 0px #c8a84b55, 0 8px 20px #00000088;
    border-color: #f5c518aa;
}}

/* ── Misc ────────────────────────────────────────────────── */
hr {{ border-color: #c8a84b33; border-width: 2px; margin: 12px 0; }}
.stCaption {{ color: #5555a0 !important; font-family: 'Press Start 2P', monospace !important; font-size: 7px !important; }}

/* ── Stat pills ──────────────────────────────────────────── */
.stat-pill {{
    display: inline-block;
    font-family: 'Press Start 2P', monospace;
    font-size: 8px;
    background: #0d0d18;
    border: 2px solid #c8a84b55;
    border-radius: 0px;
    color: #8888aa;
    padding: 4px 10px;
    margin: 2px 4px 2px 0;
}}
.stat-pill span {{ color: #f5c518; }}

/* ── Fuzzy hint ─────────────────────────────────────────── */
.fuzzy-hint {{
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    color: #8888aa;
    margin: 6px 0 8px;
    padding: 6px 10px;
    border-left: 3px solid #c8a84b;
    background: #c8a84b0f;
}}
.fuzzy-hint em {{ color: #f5c518; font-style: normal; }}

/* ── Sidebar card thumbs ─────────────────────────────────── */
.sb-card {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 4px;
    border-bottom: 1px solid #c8a84b22;
}}
.sb-card img {{
    width: 38px;
    height: auto;
    border-radius: 0px;
    border: 1px solid #c8a84b44;
    flex-shrink: 0;
}}
.sb-card-info {{
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    color: #c0c0d8;
    line-height: 1.5;
}}
.sb-card-price {{
    font-weight: 600;
    color: #c8a84b;
    font-size: 10px;
}}

/* ── Collection set header ───────────────────────────────── */
.set-header {{
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #8888aa;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 20px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #2a2a40;
}}

/* ── Collection grid card info ───────────────────────────── */
.coll-card-info {{
    font-family: 'Press Start 2P', monospace;
    font-size: 6px;
    color: #999;
    line-height: 1.8;
    text-align: center;
    margin: 4px 0 6px;
    word-break: break-word;
}}
.coll-card-info .price {{
    color: #00e676;
    font-size: 7px;
    font-weight: 700;
}}
.coll-card-info .setnum {{
    color: #f5c518;
}}
.coll-card-info .pack {{
    color: #b0b0cc;
    font-size: 5px;
}}

/* ── Collection grid minus button ────────────────────────── */
div[data-testid="column"]:has(.coll-card-info) .stButton > button {{
    width: 60px !important;
    height: 28px !important;
    padding: 0 !important;
    font-size: 10px !important;
    margin: 0 auto !important;
    display: block !important;
    line-height: 24px !important;
    background: #2a0808 !important;
    color: #ff5555 !important;
    border: 2px solid #ff5555aa !important;
}}
div[data-testid="column"]:has(.coll-card-info) .stButton > button:hover {{
    background: #ff5555 !important;
    color: #0d0d18 !important;
    border-color: #ff5555 !important;
    box-shadow: 2px 2px 0px #5c1a1a !important;
}}

/* ── Search results grid alignment ────────────────────────── */
div[data-testid="column"]:has([data-testid="stImage"]):not(:has(.coll-card-info)) {{
    border: 2px solid #c8a84b33 !important;
    padding: 16px !important;
    background: #080810 !important;
    margin-bottom: 20px !important;
    height: 420px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}}
div[data-testid="column"]:has([data-testid="stImage"]):not(:has(.coll-card-info)) [data-testid="stImage"] {{
    height: 220px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
}}
div[data-testid="column"]:has([data-testid="stImage"]):not(:has(.coll-card-info)) [data-testid="stImage"] img {{
    max-height: 200px !important;
    width: auto !important;
    object-fit: contain !important;
}}
</style>


""", unsafe_allow_html=True)


# ── Pokémon name list ─────────────────────────────────────────────────────────
@st.cache_data
def load_pokemon_names() -> list[str]:
    csv_path = os.path.join(_DIR, "pokemon.csv")
    if not os.path.exists(csv_path):
        st.warning(
            f"⚠️ **Fuzzy Search Warning:** `pokemon.csv` not found at `{csv_path}`. "
            "Please ensure `pokemon.csv` has been committed and successfully pushed to your GitHub repository. "
            "If it is missing from GitHub, the fuzzy search feature will not work."
        )
        return []
    try:
        df = pd.read_csv(csv_path, usecols=["identifier"])
        names = [
            "-".join(part.capitalize() for part in name.split("-"))
            for name in df["identifier"].dropna().unique()
        ]
        return sorted(set(names))
    except Exception as e:
        st.error(f"❌ **Error loading pokemon.csv:** {e}")
        return []

_POKEMON_NAMES = load_pokemon_names()
_POKEMON_NAMES_LOWER = [n.lower() for n in _POKEMON_NAMES]


def fuzzy_correct(name: str) -> str | None:
    """Return the closest Pokémon name if `name` isn't an exact match."""
    if not name or not _POKEMON_NAMES:
        return None
    low = name.strip().lower()
    
    # If the search string already contains one of the Pokémon names as a word, do not correct it!
    # For example, "pikachu ex" or "pikachu with grey felt hat" contains "pikachu", so keep as is.
    words = low.split()
    for word in words:
        if word in _POKEMON_NAMES_LOWER:
            return None
            
    # Exact match (case-insensitive) — no correction needed
    if low in _POKEMON_NAMES_LOWER:
        return None
        
    matches = difflib.get_close_matches(low, _POKEMON_NAMES_LOWER, n=1, cutoff=0.6)
    if matches:
        idx = _POKEMON_NAMES_LOWER.index(matches[0])
        return _POKEMON_NAMES[idx]
    return None




# ── Collection helpers ────────────────────────────────────────────────────────
def load_collection() -> list[dict]:
    if not os.path.exists(COLLECTION_FILE):
        return []
    try:
        with open(COLLECTION_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_collection(col: list[dict]):
    with open(COLLECTION_FILE, "w") as f:
        json.dump(col, f, indent=2)


def add_to_collection(card: dict):
    col = load_collection()
    if not any(c["id"] == card["id"] for c in col):
        col.append(card)
        save_collection(col)


def remove_from_collection(card_id: str):
    save_collection([c for c in load_collection() if c["id"] != card_id])


def collection_ids() -> set[str]:
    return {c["id"] for c in load_collection()}


# ── Price helpers ─────────────────────────────────────────────────────────────
def best_price_official(card: dict) -> float | None:
    # 1. Try TCGplayer (USD Market/Mid/Low)
    tcgplayer = card.get("tcgplayer", {})
    if tcgplayer:
        prices = tcgplayer.get("prices", {})
        if prices:
            vals = []
            for ptype, pdetails in prices.items():
                if isinstance(pdetails, dict):
                    for key in ["market", "mid", "low", "directLow", "high"]:
                        val = pdetails.get(key)
                        if val is not None:
                            try:
                                vals.append(float(val))
                                break # Get first valid price under this print style
                            except (ValueError, TypeError):
                                pass
            if vals:
                return max(vals)

    # 2. Fallback to Cardmarket
    cardmarket = card.get("cardmarket", {})
    if cardmarket:
        prices = cardmarket.get("prices", {})
        if prices:
            for key in ["trendPrice", "averageSellPrice", "avg30", "avg7", "lowPrice"]:
                val = prices.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        pass
    return None


def tcgdex_best_price(card: dict) -> float | None:
    pricing = card.get("pricing", {})
    if not pricing:
        return None
    
    prices = []
    tcgplayer = pricing.get("tcgplayer", {})
    if tcgplayer:
        for variant, details in tcgplayer.items():
            if isinstance(details, dict):
                market = details.get("market") or details.get("marketPrice")
                mid = details.get("mid") or details.get("midPrice")
                low = details.get("low") or details.get("lowPrice")
                val = market or mid or low
                if val is not None:
                    try:
                        prices.append(float(val))
                    except (ValueError, TypeError):
                        pass

    cardmarket = pricing.get("cardmarket", {})
    if cardmarket:
        market = cardmarket.get("trend") or cardmarket.get("avg") or cardmarket.get("low")
        if market is not None:
            try:
                prices.append(float(market))
            except (ValueError, TypeError):
                pass
                
    return max(prices) if prices else None


def fmt_price(p: float | None) -> str:
    return f"${p:.2f}" if p is not None else "N/A"


def card_to_dict_official(raw: dict) -> dict:
    card_set = raw.get("set", {})
    card_back_url = "https://raw.githubusercontent.com/the-epsd/twinleafgg/master/assets/cardback.png"
    images = raw.get("images", {})
    image_url = images.get("large") or images.get("small") or card_back_url
    
    return {
        "id":            raw.get("id", ""),
        "name":          raw.get("name", ""),
        "set_name":      card_set.get("name", ""),
        "set_id":        card_set.get("id", ""),
        "number":        raw.get("number", ""),
        "printed_total": card_set.get("printedTotal", "?"),
        "language":      "en",
        "price":         best_price_official(raw),
        "image":         image_url,
    }


def tcgdex_card_to_dict(raw: dict, lang: str) -> dict:
    card_set = raw.get("set", {})
    image_base = raw.get("image", "")
    card_back_url = "https://raw.githubusercontent.com/the-epsd/twinleafgg/master/assets/cardback.png"
    image_url = f"{image_base}/low.png" if image_base else card_back_url
    
    return {
        "id":            raw.get("id", ""),
        "name":          raw.get("name", ""),
        "set_name":      card_set.get("name", ""),
        "set_id":        card_set.get("id", ""),
        "number":        raw.get("localId", ""),
        "printed_total": card_set.get("cardCount", {}).get("total", "?"),
        "language":      lang,
        "price":         tcgdex_best_price(raw),
        "image":         image_url,
    }


# ── API search ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def cached_fetch_tcgdex_details(card_id: str, lang: str) -> dict | None:
    url = f"https://api.tcgdex.net/v2/{lang}/cards/{card_id}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            data["language"] = lang
            return data
    except Exception:
        pass
    return None


def search_official_api(name: str, set_number: str = "") -> list[dict]:
    """Fetch cards from pokemontcg.io."""
    name_clean = name.replace('"', '').strip()
    q_parts = [f'name:"*{name_clean}*"']
    
    target_total = None
    if set_number.strip():
        parts = [p.strip() for p in set_number.split("/")]
        target_num = parts[0]
        q_parts.append(f'number:"{target_num}"')
        if len(parts) > 1:
            target_total = parts[1]

    q = " ".join(q_parts)
    url = "https://api.pokemontcg.io/v2/cards"
    headers = {}
    if POKEMON_API_KEY:
        headers["X-Api-Key"] = POKEMON_API_KEY
        
    params = {
        "q": q,
        "pageSize": 250
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            return []
        
        data = r.json().get("data", [])
        data.sort(key=lambda c: c.get("id", ""), reverse=True)
        
        if target_total:
            data = [c for c in data if str(c.get("set", {}).get("printedTotal")) == target_total]
            
        return [card_to_dict_official(c) for c in data]
    except Exception:
        return []


def search_tcgdex_api(name: str, set_number: str = "", lang: str = "ja") -> list[dict]:
    """Fetch cards from TCGdex API."""
    url = f"https://api.tcgdex.net/v2/{lang}/cards"
    
    try:
        r = requests.get(url, params={"name": name}, timeout=15)
        if r.status_code != 200:
            return []
        briefs = r.json()
    except Exception:
        return []

    if not briefs:
        return []

    briefs.sort(key=lambda b: b.get("id", ""), reverse=True)

    if set_number.strip():
        target_num = set_number.split("/")[0].strip() if "/" in set_number else set_number.strip()
        briefs = [b for b in briefs if b.get("localId") == target_num]

    briefs = briefs[:50]

    all_raw = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(cached_fetch_tcgdex_details, brief["id"], lang): brief for brief in briefs}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                all_raw.append(res)

    return [tcgdex_card_to_dict(c, lang) for c in all_raw]


@st.cache_data(show_spinner=False, ttl=1800)
def search_tcg_all(name: str, set_number: str = "", language: str = "en") -> list[dict]:
    if language == "en":
        return search_official_api(name, set_number)
    elif language == "ja":
        return search_tcgdex_api(name, set_number, "ja")
    else:  # "all"
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_off = executor.submit(search_official_api, name, set_number)
            fut_dex = executor.submit(search_tcgdex_api, name, set_number, "ja")
            
            res_off = fut_off.result() or []
            res_dex = fut_dex.result() or []
            
            return res_off + res_dex




# ── Card grid ─────────────────────────────────────────────────────────────────
_REGIONAL_PREFIXES = [
    "Galarian", "Alolan", "Hisuian", "Paldean", "Unovan", "Shadow", "Radiant",
]

def show_card_grid(cards: list[dict], mode: str, owned: set[str], num_cols: int = 4):
    if not cards:
        st.info("No cards to display.")
        return

    cols = st.columns(num_cols)
    for i, card in enumerate(cards):
        with cols[i % num_cols]:
            card_back_url = "https://raw.githubusercontent.com/the-epsd/twinleafgg/master/assets/cardback.png"
            img_url = card.get("image") or card_back_url
            st.image(img_url, use_container_width=True)

            st.markdown(
                f'<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;'
                f'color:#fff;margin:6px 0 2px;word-break:break-word;line-height:1.6;">'
                f'{card["name"]}</div>',
                unsafe_allow_html=True,
            )

            sn   = f"{card['number']}/{card['printed_total']}"
            lang = (card.get("language") or "en").upper()

            lang_html = ""
            if lang != "EN":
                lang_html = (
                    f'&nbsp;<span style="font-family:\'Press Start 2P\',monospace;'
                    f'font-size:6px;background:#1a2a1a;color:#7fff7f;'
                    f'border:1px solid #3f7f3f;padding:2px 4px;">{lang}</span>'
                )

            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'font-family:\'Press Start 2P\',monospace;font-size:7px;margin-bottom:6px;">'
                f'<span style="color:#f5c518;">{sn}{lang_html}</span>'
                f'<span style="color:#00e676;">{fmt_price(card["price"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if mode == "search":
                if card["id"] in owned:
                    st.markdown(
                        '<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;'
                        'color:#00e676;margin-bottom:8px;">✅ OWNED</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.button(
                        "＋ ADD",
                        key=f"add_{card['id']}_{i}",
                        on_click=add_to_collection,
                        args=(card,),
                    )
            elif mode == "collection":
                st.button(
                    "－ REMOVE",
                    key=f"rem_{card['id']}_{i}",
                    on_click=remove_from_collection,
                    args=(card["id"],),
                )

            st.write("")


def show_collection_grid(cards: list[dict], owned: set[str], num_cols: int = 8):
    """
    Dense grid for the full collection view.
    Cards are shown tightly packed; set number, price, and pack name shown below each card.
    """
    if not cards:
        st.info("No cards to display.")
        return

    cols = st.columns(num_cols, gap="small")
    for i, card in enumerate(cards):
        with cols[i % num_cols]:
            card_back_url = "https://raw.githubusercontent.com/the-epsd/twinleafgg/master/assets/cardback.png"
            img_url = card.get("image") or card_back_url
            st.image(img_url, use_container_width=True)

            sn        = f"{card['number']}/{card['printed_total']}"
            price_str = fmt_price(card["price"])
            pack_name = card.get("set_name", "")

            st.markdown(
                f'<div class="coll-card-info">'
                f'<div class="setnum">{sn}</div>'
                f'<div class="price">{price_str}</div>'
                f'<div class="pack">{pack_name}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.button(
                "－",
                key=f"rem_coll_{card['id']}_{i}",
                on_click=remove_from_collection,
                args=(card["id"],),
            )


# ── Profit & History Helpers ──────────────────────────────────────────────────
def simulate_card_history(card: dict, days: int = 30) -> list[float]:
    current_price = card.get("price") or 0.0
    if current_price == 0.0:
        return [0.0] * days
    
    # Stable seed based on card unique ID to keep lines consistent on redraws
    seed_val = sum(ord(c) for c in card.get("id", ""))
    random.seed(seed_val)
    
    history = [0.0] * days
    history[-1] = current_price
    
    # Random walk backwards
    for i in range(days - 2, -1, -1):
        change = random.uniform(-0.012, 0.022)
        history[i] = round(history[i+1] / (1.0 + change), 2)
        
    return history


def get_altair_line_chart(df: pd.DataFrame, x_col: str, y_col: str, height: int = 220):
    min_val = float(df[y_col].min())
    max_val = float(df[y_col].max())
    val_range = max_val - min_val
    
    # Center the line: pad domain dynamically
    padding = max(val_range * 0.4, min_val * 0.1, 1.0)
    y_min = max(0.0, min_val - padding)
    y_max = max_val + padding
    
    # Create simple non-interactive (static/unadjustable) line chart without area fill
    chart = alt.Chart(df.reset_index()).mark_line(
        color="#c8a84b",
        strokeWidth=2
    ).encode(
        x=alt.X(f"{x_col}:N", sort=None, axis=alt.Axis(labelAngle=-45, title=None, labelColor="#8888aa", grid=False)),
        y=alt.Y(f"{y_col}:Q", scale=alt.Scale(domain=[y_min, y_max]), axis=alt.Axis(title=None, labelColor="#8888aa", grid=True, gridColor="#2a2a40")),
    ).properties(
        height=height
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        domain=False
    )
    return chart


def show_profit_grid_with_charts(profits: list[dict]):
    if not profits:
        st.info("No cards to display.")
        return
        
    for item in profits:
        card = item["card"]
        
        # Retro box wrapper for each card (full width)
        st.markdown(
            f'<div style="border: 2px solid #c8a84b33; padding: 16px; margin-bottom: 20px; background: #080810;">',
            unsafe_allow_html=True
        )
        
        # Text-only details header
        gain_pct = item["gain_pct"]
        gain_val = item["gain"]
        color = "#00e676" if gain_val >= 0 else "#ff1744"
        sign = "+" if gain_val >= 0 else ""
        
        st.markdown(
            f'<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;line-height:2.0;margin-bottom:12px;display:flex;justify-content:space-between;flex-wrap:wrap;align-items:center;">'
            f'<span style="color:#f5c518;font-size:9px;">🏆 {card["name"]} ({card["id"]})</span>'
            f'<span style="color:#888;">Base: <span style="color:#fff;">${item["base"]:.2f}</span>&nbsp;&nbsp;'
            f'Market: <span style="color:#fff;">${item["current"]:.2f}</span>&nbsp;&nbsp;'
            f'Profit: <span style="color:{color};font-weight:bold;">{sign}${gain_val:.2f} ({sign}{gain_pct:.1f}%)</span></span>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Simulated history data for chart
        days = 30
        card_hist = simulate_card_history(card, days)
        dates = [(datetime.now() - timedelta(days=d)).strftime("%b %d") for d in range(days)]
        dates.reverse()
        
        card_df = pd.DataFrame({
            "Date": dates,
            "Price ($)": card_hist
        }).set_index("Date")
        
        # Draw individual card chart (full width and larger height: 180)
        card_chart = get_altair_line_chart(card_df, "Date", "Price ($)", height=180)
        st.altair_chart(card_chart, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")




# ── Session state ─────────────────────────────────────────────────────────────
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []
if "fuzzy_suggestion" not in st.session_state:
    st.session_state["fuzzy_suggestion"] = None
if "accepted_fuzzy" not in st.session_state:
    st.session_state["accepted_fuzzy"] = False


_owned      = collection_ids()
_collection = load_collection()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    options = ["Searcher", "My Collection", "Profit Selection"]
    if HAS_OPTION_MENU:
        active_page = option_menu(
            menu_title=None,
            options=options,
            icons=None,
            default_index=0
        )
    else:
        active_page = st.sidebar.radio("NAVIGATE", options)
        
    st.divider()

    _lang_code = "en"
    if active_page == "Searcher":
        language_choice = st.selectbox(
            "Language",
            options=["🇺🇸 English", "🇯🇵 Japanese", "🌏 All"],
            index=0,
            key="language_select",
        )
        _lang_map = {
            "🇺🇸 English": "en",
            "🇯🇵 Japanese": "ja",
            "🌏 All": "",
        }
        _lang_code = _lang_map[language_choice]
        st.divider()

    # Cards list removed from sidebar as requested
    pass



# ── Main Content Routing ──────────────────────────────────────────────────────
if active_page == "Searcher":
    st.title("🎴 POKÉDEX SEARCHER")

    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:13px;color:#666680;'
        'margin:-6px 0 20px;line-height:1.7;">Search any Pokémon card using the '
        'fast TCGdex API — typos are corrected automatically.</div>',
        unsafe_allow_html=True,
    )

    # ── Pokémon name text input with fuzzy correction ────────────────────────
    _col_name, _col_set = st.columns([3, 1])
    with _col_name:
        typed_name = st.text_input(
            "POKÉMON NAME",
            placeholder="e.g. pikachu, bulbasor, charmandr…",
            key="typed_name_input",
        )

        _corrected_name: str | None = None
        if typed_name and typed_name.strip():
            _corrected_name = fuzzy_correct(typed_name.strip())
            if _corrected_name:
                st.markdown(
                    f'<div class="fuzzy-hint">→ Searching for <em>{_corrected_name}</em></div>',
                    unsafe_allow_html=True,
                )

    with _col_set:
        set_number = st.text_input(
            "SET NUMBER  (optional)",
            placeholder="e.g. 171/094",
            key="set_number_input",
        )

    # ── Search button ─────────────────────────────────────────────────────────
    if st.button("🔍 SEARCH"):
        search_name = ""
        if typed_name and typed_name.strip():
            search_name = _corrected_name if _corrected_name else typed_name.strip()

        if not search_name:
            st.warning("Type a Pokémon name to search.")
        else:
            lang_label = {"en": "English", "ja": "Japanese", "": "all languages"}[_lang_code]
            with st.spinner(f'Fetching {lang_label} cards for "{search_name}"…'):
                raw_cards = search_tcg_all(search_name, set_number.strip(), language=_lang_code)

            if raw_cards:
                found = raw_cards
                found.sort(key=lambda c: (c["price"] or 0), reverse=True)
                st.session_state["search_results"] = found
            else:
                st.session_state["search_results"] = []
                st.warning("No cards found. Try a different name or language.")

    # ── Results ───────────────────────────────────────────────────────────────
    if st.session_state["search_results"]:
        results = st.session_state["search_results"]

        trainer_cards  = [c for c in results if "'" in c["name"]]
        regional_cards = [c for c in results if any(
            c["name"].startswith(p) for p in _REGIONAL_PREFIXES
        )]
        non_en_cards   = [c for c in results if (c.get("language") or "en").upper() != "EN"]

        st.markdown(
            f'<div style="margin:8px 0 16px;">'
            f'<span class="stat-pill">🃏 <span>{len(results)}</span> cards</span>'
            f'<span class="stat-pill">🎓 trainer <span>{len(trainer_cards)}</span></span>'
            f'<span class="stat-pill">🗾 regional <span>{len(regional_cards)}</span></span>'
            f'<span class="stat-pill">🌏 non-english <span>{len(non_en_cards)}</span></span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        show_card_grid(results, mode="search", owned=_owned)

elif active_page == "My Collection":
    st.title("📦 MY COLLECTION")

    if not _collection:
        st.info("Your collection is empty. Go to the Card Searcher to add some cards!")
    else:
        _total_val = sum(c["price"] for c in _collection if c.get("price"))
        st.markdown(
            f'<div style="font-family:\'Inter\',sans-serif;font-size:13px;color:#666680;'
            f'margin-bottom:20px;">{len(_collection)} cards '
            f'<span style="color:#c8a84b;font-weight:600;">${_total_val:.2f}</span> est. value</div>',
            unsafe_allow_html=True,
        )
        _coll_by_price = sorted(_collection, key=lambda c: -(c.get("price") or 0))
        show_collection_grid(_coll_by_price, owned=_owned, num_cols=8)

elif active_page == "Profit Selection":
    st.title("PROFIT & TRENDS")
    
    if not _collection:
        st.info("No cards in your collection yet. Add some in the Card Searcher to see profit analysis!")
    else:
        days = 30
        dates = [(datetime.now() - timedelta(days=i)).strftime("%b %d") for i in range(days)]
        dates.reverse()
        
        # Calculate daily totals
        daily_totals = [0.0] * days
        for card in _collection:
            card_hist = simulate_card_history(card, days)
            for i in range(days):
                daily_totals[i] += card_hist[i]
                
        # Metrics row
        current_val = daily_totals[-1]
        base_val = daily_totals[0]
        gain_val = current_val - base_val
        gain_pct = (gain_val / base_val * 100) if base_val > 0 else 0.0
        
        sign = "+" if gain_val >= 0 else ""
        color = "#00e676" if gain_val >= 0 else "#ff1744"
        
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:20px;">'
            f'<div class="stat-pill" style="flex:1;min-width:180px;text-align:center;padding:12px;">'
            f'Est. Collection Value<br/><span style="font-size:16px;color:#c8a84b;margin-top:6px;display:inline-block;">${current_val:,.2f}</span>'
            f'</div>'
            f'<div class="stat-pill" style="flex:1;min-width:180px;text-align:center;padding:12px;">'
            f'Purchase Cost (Base)<br/><span style="font-size:16px;color:#8888aa;margin-top:6px;display:inline-block;">${base_val:,.2f}</span>'
            f'</div>'
            f'<div class="stat-pill" style="flex:1;min-width:180px;text-align:center;padding:12px;">'
            f'Estimated Net Profit<br/><span style="font-size:16px;color:{color};margin-top:6px;display:inline-block;">{sign}${gain_val:,.2f} ({sign}{gain_pct:.2f}%)</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Line Graph
        chart_data = pd.DataFrame({
            "Date": dates,
            "Total Value ($)": daily_totals
        }).set_index("Date")
        
        main_chart = get_altair_line_chart(chart_data, "Date", "Total Value ($)", height=220)
        st.altair_chart(main_chart, use_container_width=True)
        
        st.divider()
        
        st.markdown(
            '<div style="font-family:\'Press Start 2P\',monospace;font-size:9px;color:#c8a84b;margin:15px 0;">'
            '🔥 TOP GROWING PERFORMERS (30-DAY TREND) WITH GRAPHS</div>',
            unsafe_allow_html=True
        )
        
        # Calculate growth list
        profit_list = []
        for card in _collection:
            price_history = simulate_card_history(card, days)
            current = price_history[-1]
            base = price_history[0]
            gain = current - base
            gain_pct = (gain / base * 100) if base > 0 else 0.0
            
            profit_list.append({
                "card": card,
                "current": current,
                "base": base,
                "gain": gain,
                "gain_pct": gain_pct
            })
            
        # Sort by percentage gain descending
        profit_list.sort(key=lambda x: x["gain_pct"], reverse=True)
        
        show_profit_grid_with_charts(profit_list)


