import streamlit as st
import requests
import json
import os
import base64

st.set_page_config(page_title="PokéDex Collector", layout="wide", page_icon="🎴")

_DIR = os.path.dirname(__file__)
COLLECTION_FILE = os.path.join(_DIR, "collection.json")
TCG_API = "https://api.pokemontcg.io/v2/cards"

LANGUAGE_MAP = {
    "All Nations": None,
    "USA":         "en",
    "Japan":       "ja",
    "South Korea": "ko",
}


# ── Background images ─────────────────────────────────────────────────────────
def _b64(name: str) -> str:
    with open(os.path.join(_DIR, name), "rb") as f:
        return base64.b64encode(f.read()).decode()

_pika   = _b64("pikachu-transparent-32599.png")
_gengar = _b64("Gengar-PNG-Picture.png")


# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

/* ── Background ── */
[data-testid="stAppViewContainer"] {{
    background-color: #0d0d1a;
    background-image:
        url("data:image/png;base64,{_pika}"),
        url("data:image/png;base64,{_gengar}"),
        repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(255,215,0,.04) 24px),
        repeating-linear-gradient(90deg, transparent, transparent 23px, rgba(255,215,0,.04) 24px);
    background-size: 130px, 170px, auto, auto;
    background-position: 1% 97%, 98% 97%, 0 0, 0 0;
    background-repeat: no-repeat, no-repeat, repeat, repeat;
    background-attachment: fixed, fixed, fixed, fixed;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: #080812;
    border-right: 3px solid #f5c51833;
}}

/* ── Pixel font for headings ── */
h1, h2, h3, h4 {{
    font-family: 'Press Start 2P', monospace !important;
}}
h1 {{
    color: #f5c518 !important;
    font-size: 18px !important;
    text-shadow: 3px 3px 0px #7a6200, 0 0 24px #f5c51866;
    letter-spacing: 2px;
}}
h2, h3, h4 {{
    color: #d4a820 !important;
    font-size: 11px !important;
}}

/* ── Buttons ── */
.stButton > button {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 8px !important;
    background: #0d0d1a;
    color: #f5c518;
    border: 2px solid #f5c518;
    border-radius: 0px;
    padding: 8px 10px;
    width: 100%;
    transition: background 0.1s, color 0.1s, box-shadow 0.1s;
}}
.stButton > button:hover {{
    background: #f5c518;
    color: #0d0d1a;
    box-shadow: 4px 4px 0px #7a6200;
}}
.stButton > button:active {{
    box-shadow: 1px 1px 0px #7a6200;
    transform: translate(2px, 2px);
}}

/* ── Inputs ── */
.stTextInput input {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 9px !important;
    background: #080812;
    color: #00e676;
    border: 2px solid #f5c51844;
    border-radius: 0;
    caret-color: #f5c518;
}}
.stTextInput label {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 8px !important;
    color: #f5c518 !important;
}}

/* ── Selectbox ── */
.stSelectbox label {{
    font-family: 'Press Start 2P', monospace !important;
    font-size: 8px !important;
    color: #f5c518 !important;
}}
.stSelectbox > div > div {{
    background: #080812;
    border: 2px solid #f5c51844;
    border-radius: 0;
    font-family: 'Press Start 2P', monospace !important;
    font-size: 8px !important;
    color: #00e676;
}}

/* ── Card images ── */
[data-testid="stImage"] img {{
    border: 2px solid #f5c51844;
    display: block;
    margin: 0 auto;
}}

/* ── Divider ── */
hr {{
    border-color: #f5c51833;
}}

/* ── Caption ── */
.stCaption {{
    color: #888 !important;
}}
</style>
""", unsafe_allow_html=True)


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
    vals = [v.get("market") for v in prices.values() if v.get("market")]
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
        "price":         best_price(raw),
        "image":         raw.get("images", {}).get("large")
                         or raw.get("images", {}).get("small", ""),
    }


# ── API ───────────────────────────────────────────────────────────────────────
def search_tcg(name: str, set_number: str = "", language: str | None = None) -> list[dict]:
    q = f'name:"{name}"'

    if set_number and "/" in set_number:
        parts = set_number.split("/")
        num   = parts[0].strip()
        total = parts[1].strip()
        q += f" number:{num}"
        if total:
            q += f" set.printedTotal:{total}"
    elif set_number.strip():
        q += f" number:{set_number.strip()}"

    if language:
        q += f" set.language:{language}"

    try:
        r = requests.get(TCG_API, params={"q": q, "pageSize": 100}, timeout=15)
        if r.status_code == 200:
            return r.json().get("data", [])
        else:
            st.error(f"API error {r.status_code}")
    except requests.exceptions.Timeout:
        st.error("Request timed out — try again.")
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
    return []


# ── Card grid ─────────────────────────────────────────────────────────────────
def show_card_grid(cards: list[dict], mode: str, owned: set[str]):
    if not cards:
        st.info("No cards to display.")
        return

    cols = st.columns(4)
    for i, card in enumerate(cards):
        with cols[i % 4]:
            if card.get("image"):
                st.image(card["image"], use_container_width=True)

            # Pixel-styled name
            st.markdown(
                f'<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;'
                f'color:#fff;margin:6px 0 4px;word-break:break-word;line-height:1.6;">'
                f'{card["name"]}</div>',
                unsafe_allow_html=True,
            )

            # Set number + price on one horizontal line
            sn = f"{card['number']}/{card['printed_total']}"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'font-family:\'Press Start 2P\',monospace;font-size:7px;margin-bottom:6px;">'
                f'<span style="color:#f5c518;">{sn}</span>'
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


# ── Session state ─────────────────────────────────────────────────────────────
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

# Load once per render — on_click callbacks fire before this, so disk is already updated
_owned      = collection_ids()
_collection = load_collection()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.selectbox("Language", list(LANGUAGE_MAP.keys()), key="language")

    st.divider()
    st.markdown("### My Collection")

    if not _collection:
        st.caption("No cards yet. Search and add some!")
    else:
        _total = sum(c["price"] for c in _collection if c.get("price"))
        st.caption(f"{len(_collection)} cards · ${_total:.2f} total")
        st.divider()

        _collection.sort(key=lambda c: (c.get("set_name", ""), -(c.get("price") or 0)))

        _grouped: dict[str, list[dict]] = {}
        for _card in _collection:
            _grouped.setdefault(_card.get("set_name", "Unknown Set"), []).append(_card)

        for _set_name, _set_cards in _grouped.items():
            st.markdown(f"**{_set_name}**")
            for _card in _set_cards:
                _c1, _c2 = st.columns([1, 2])
                with _c1:
                    if _card.get("image"):
                        st.image(_card["image"], use_container_width=True)
                with _c2:
                    st.markdown(
                        f'<div style="font-family:\'Press Start 2P\',monospace;'
                        f'font-size:7px;color:#fff;word-break:break-word;line-height:1.6;">'
                        f'{_card["name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"{_card['number']}/{_card['printed_total']}")
                    st.caption(fmt_price(_card["price"]))
                    st.button(
                        "－",
                        key=f"sb_rem_{_card['id']}",
                        on_click=remove_from_collection,
                        args=(_card["id"],),
                    )
            st.write("")


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🎴POKESEARCH")

col_a, col_b = st.columns([2, 1])
with col_a:
    pokemon_name = st.text_input("POKÉMON NAME", placeholder="e.g. Charizard, Pikachu VMAX…")
with col_b:
    set_number = st.text_input("SET NUMBER", placeholder="e.g. 171/094")
    st.caption("Leave empty to see all cards with that name.")

if st.button("🔍 SEARCH"):
    if not pokemon_name.strip():
        st.warning("Enter a Pokémon name to search.")
    else:
        lang = LANGUAGE_MAP[st.session_state.get("language", "All Nations")]
        with st.spinner("Searching…"):
            raw = search_tcg(pokemon_name.strip(), set_number.strip(), lang)

        if raw:
            found = [card_to_dict(c) for c in raw]
            found.sort(key=lambda c: (c["price"] or 0), reverse=True)
            st.session_state["search_results"] = found
        else:
            st.session_state["search_results"] = []
            st.warning("No cards found. Try adjusting the name or set number.")

if st.session_state["search_results"]:
    _results = st.session_state["search_results"]
    st.markdown(f"**{len(_results)} result(s)** — sorted by price")
    show_card_grid(_results, mode="search", owned=_owned)
