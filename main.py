import streamlit as st
import requests
import json
import os
import base64

st.set_page_config(page_title="PokéDex Collector", layout="wide", page_icon="🎴")

_DIR            = os.path.dirname(__file__)
COLLECTION_FILE = os.path.join(_DIR, "collection.json")
TCG_API         = "https://api.pokemontcg.io/v2/cards"


# ── Background images (graceful if files missing) ─────────────────────────────
def _b64(name: str) -> str:
    path = os.path.join(_DIR, name)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_pika   = _b64("pikachu-transparent-32599.png")
_gengar = _b64("Gengar-PNG-Picture.png")

_extra_imgs = ""
_extra_sz   = ""
_extra_pos  = ""
_extra_rep  = ""
_extra_att  = ""
if _pika:
    _extra_imgs += f'url("data:image/png;base64,{_pika}"), '
    _extra_sz   += "130px, "
    _extra_pos  += "1% 97%, "
    _extra_rep  += "no-repeat, "
    _extra_att  += "fixed, "
if _gengar:
    _extra_imgs += f'url("data:image/png;base64,{_gengar}"), '
    _extra_sz   += "170px, "
    _extra_pos  += "98% 97%, "
    _extra_rep  += "no-repeat, "
    _extra_att  += "fixed, "

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

[data-testid="stAppViewContainer"] {{
    background-color: #0d0d1a;
    background-image: {_bg_image};
    background-size: {_bg_size};
    background-position: {_bg_pos};
    background-repeat: {_bg_rep};
    background-attachment: {_bg_att};
}}
[data-testid="stSidebar"] {{
    background-color: #080812;
    border-right: 3px solid #f5c51833;
}}
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
[data-testid="stImage"] img {{
    border: 2px solid #f5c51844;
    display: block;
    margin: 0 auto;
}}
hr {{ border-color: #f5c51833; }}
.stCaption {{ color: #888 !important; }}
.stat-pill {{
    display: inline-block;
    font-family: 'Press Start 2P', monospace;
    font-size: 7px;
    background: #111;
    border: 1px solid #f5c51844;
    color: #f5c518;
    padding: 4px 8px;
    margin: 2px 3px 2px 0;
}}
.stat-pill span {{ color: #00e676; }}
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


# ── API — paginated wildcard search, no language restriction ──────────────────
def search_tcg_all(name: str, set_number: str = "") -> list[dict]:
    """
    Fetch every card whose name *contains* `name`.

    Using `name:*{name}*` (wildcard on both sides) means:
      - Base cards           → "Jolteon"
      - Variant cards        → "Jolteon VMAX", "Jolteon GX" …
      - Regional forms       → "Galarian Jolteon", "Alolan Jolteon" …
      - Trainer/owner cards  → "Misty's Jolteon", "Team Rocket's Jolteon" …
      - All languages        → no language filter = API returns en + ja + ko + …
        (pokemontcg.io's non-English index is small but anything it has comes through)

    Paginates until all pages are consumed so no card is ever missed.
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

    PAGE_SIZE      = 250          # API maximum per page
    all_raw: list  = []
    seen_ids: set  = set()
    page           = 1
    api_total      = 0

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

        # Done when we have all cards or the batch was smaller than a full page
        if len(batch) < PAGE_SIZE or len(all_raw) >= api_total:
            break
        page += 1

    return all_raw


# ── Card grid ─────────────────────────────────────────────────────────────────
_REGIONAL_PREFIXES = [
    "Galarian", "Alolan", "Hisuian", "Paldean", "Unovan", "Shadow", "Radiant",
]

def show_card_grid(cards: list[dict], mode: str, owned: set[str]):
    if not cards:
        st.info("No cards to display.")
        return

    cols = st.columns(4)
    for i, card in enumerate(cards):
        with cols[i % 4]:
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

            # Non-English badge
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


# ── Session state ─────────────────────────────────────────────────────────────
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

_owned      = collection_ids()
_collection = load_collection()


# ── Sidebar — collection only ──────────────────────────────────────────────────
with st.sidebar:
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
st.title("🎴 POKÉDEX COLLECTOR")

st.markdown(
    '<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;color:#888;'
    'margin:-10px 0 18px;line-height:2;">Type any Pokémon — trainer cards, regional forms '
    '&amp; all languages included automatically.</div>',
    unsafe_allow_html=True,
)

col_a, col_b = st.columns([2, 1])
with col_a:
    pokemon_name = st.text_input("POKÉMON NAME", placeholder="e.g. Jolteon, Charizard, Pikachu…")
with col_b:
    set_number = st.text_input("SET NUMBER  (optional)", placeholder="e.g. 171/094")

if st.button("🔍 SEARCH"):
    if not pokemon_name.strip():
        st.warning("Enter a Pokémon name to search.")
    else:
        with st.spinner(f"Fetching every card for \"{pokemon_name.strip()}\"…"):
            raw_cards = search_tcg_all(pokemon_name.strip(), set_number.strip())

        if raw_cards:
            found = [card_to_dict(c) for c in raw_cards]
            found.sort(key=lambda c: (c["price"] or 0), reverse=True)
            st.session_state["search_results"] = found
        else:
            st.session_state["search_results"] = []
            st.warning("No cards found. Check the spelling and try again.")

# ── Results ───────────────────────────────────────────────────────────────────
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
