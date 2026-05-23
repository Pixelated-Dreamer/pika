import streamlit as st
import requests
import json
import os
import base64
import pandas as pd
import difflib

st.set_page_config(page_title="PokéDex Collector", layout="wide", page_icon="🎴")

_DIR            = os.path.dirname(__file__)
COLLECTION_FILE = os.path.join(_DIR, "collection.json")
TCG_API         = "https://api.pokemontcg.io/v2/cards"


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
def best_price(card: dict) -> float | None:
    prices = card.get("tcgplayer", {}).get("prices", {})
    vals   = [v.get("market") for v in prices.values() if v.get("market")]
    return max(vals) if vals else None


def fmt_price(p: float | None) -> str:
    return f"${p:.2f}" if p is not None else "N/A"


def card_to_dict(raw: dict) -> dict:
    return {
        "id":            raw.get("id", ""),
        "name":          raw.get("name", ""),
        "set_name":      raw.get("set", {}).get("name", ""),
        "set_id":        raw.get("set", {}).get("id", ""),
        "number":        raw.get("number", ""),
        "printed_total": raw.get("set", {}).get("printedTotal", "?"),
        "language":      raw.get("set", {}).get("language", "en"),
        "price":         best_price(raw),
        "image":         raw.get("images", {}).get("large")
                         or raw.get("images", {}).get("small", ""),
    }


# ── API search ────────────────────────────────────────────────────────────────
def search_tcg_all(name: str, set_number: str = "", language: str = "en") -> list[dict]:
    """
    Fetch every card whose name contains `name`.
    The pokemontcg.io API only hosts English cards, so language filtering
    is not available server-side; we always search by name only.
    """
    q = f"name:*{name}*"

    if set_number and "/" in set_number:
        parts = set_number.split("/")
        num   = parts[0].strip()
        total = parts[1].strip()
        q    += f" number:{num}"
        if total:
            q += f" set.printedTotal:{total}"
    elif set_number.strip():
        q += f" number:{set_number.strip()}"

    PAGE_SIZE     = 250
    all_raw: list = []
    seen_ids: set = set()
    page          = 1
    api_total     = 0

    while True:
        try:
            r = requests.get(
                TCG_API,
                params={
                    "q":        q,
                    "pageSize": PAGE_SIZE,
                    "page":     page,
                    "orderBy":  "-set.releaseDate",
                },
                timeout=20,
            )
        except requests.exceptions.Timeout:
            st.error("Request timed out — try again.")
            break
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {e}")
            break

        if r.status_code != 200:
            st.error(f"API error {r.status_code}")
            break

        payload   = r.json()
        api_total = payload.get("totalCount", 0)
        batch     = payload.get("data", [])

        for card in batch:
            cid = card.get("id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_raw.append(card)

        if len(batch) < PAGE_SIZE or len(all_raw) >= api_total:
            break
        page += 1

    return all_raw


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
            if card.get("image"):
                st.image(card["image"], use_container_width=True)

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
            if card.get("image"):
                st.image(card["image"], use_container_width=True)

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


# ── Session state ─────────────────────────────────────────────────────────────
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []
if "show_collection_overlay" not in st.session_state:
    st.session_state["show_collection_overlay"] = False
if "fuzzy_suggestion" not in st.session_state:
    st.session_state["fuzzy_suggestion"] = None
if "accepted_fuzzy" not in st.session_state:
    st.session_state["accepted_fuzzy"] = False


_owned      = collection_ids()
_collection = load_collection()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Language selector at the very top ─────────────────────────────────────
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

    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:13px;font-weight:600;'
        'color:#c8a84b;margin-bottom:4px;">My Collection</div>',
        unsafe_allow_html=True,
    )

    if not _collection:
        st.caption("No cards yet — search and add some!")
    else:
        _total = sum(c["price"] for c in _collection if c.get("price"))
        st.markdown(
            f'<div style="font-family:\'Inter\',sans-serif;font-size:11px;color:#666680;'
            f'margin-bottom:10px;">{len(_collection)} cards · '
            f'<span style="color:#c8a84b;font-weight:600;">${_total:.2f}</span></div>',
            unsafe_allow_html=True,
        )

        if st.button("View Full Collection", key="expand_collection_btn"):
            st.session_state["show_collection_overlay"] = True
            st.rerun()

        st.divider()

        # Show up to 12 cards as thumbnails
        _sb_sorted = sorted(_collection, key=lambda c: (c.get("set_name", ""), -(c.get("price") or 0)))
        for _sb_card in _sb_sorted[:12]:
            img_tag = ""
            if _sb_card.get("image"):
                img_tag = f'<img src="{_sb_card["image"]}" style="width:38px;border-radius:4px;flex-shrink:0;">'
            price_str = f'${_sb_card["price"]:.2f}' if _sb_card.get("price") else ""
            st.markdown(
                f'<div class="sb-card">'
                f'{img_tag}'
                f'<div class="sb-card-info">'
                f'<div>{_sb_card["name"]}</div>'
                f'<div class="sb-card-price">{price_str}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        if len(_sb_sorted) > 12:
            st.caption(f"+ {len(_sb_sorted) - 12} more")

if st.session_state["show_collection_overlay"]:
    _bk_col, _ttl_col = st.columns([1, 5])
    with _bk_col:
        if st.button("← Back", key="close_overlay_btn"):
            st.session_state["show_collection_overlay"] = False
            st.rerun()
    with _ttl_col:
        st.title("📦 MY COLLECTION")

    if not _collection:
        st.info("Your collection is empty.")
    else:
        _total_val = sum(c["price"] for c in _collection if c.get("price"))
        st.markdown(
            f'<div style="font-family:\'Inter\',sans-serif;font-size:13px;color:#666680;'
            f'margin-bottom:20px;">{len(_collection)} cards · '
            f'<span style="color:#c8a84b;font-weight:600;">${_total_val:.2f}</span> est. value</div>',
            unsafe_allow_html=True,
        )
        # Sort entire collection by price high to low, no grouping
        _coll_by_price = sorted(_collection, key=lambda c: -(c.get("price") or 0))
        show_collection_grid(_coll_by_price, owned=_owned, num_cols=8)

else:
    # ── Main Search Screen ────────────────────────────────────────────────────
    st.title("🎴 POKÉDEX COLLECTOR")

    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:13px;color:#666680;'
        'margin:-6px 0 20px;line-height:1.7;">Search any Pokémon card — typos are '
        'auto-corrected automatically.</div>',
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
                found = [card_to_dict(c) for c in raw_cards]
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
