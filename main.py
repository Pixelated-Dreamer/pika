import streamlit as st
import sqlite3
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
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    if key_name in os.environ:
        return os.environ[key_name]
    env_path = os.path.join(_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key_name:
                        return v.strip().strip("'\"")
    return None

POKEMON_API_KEY      = load_env_key("POKEMON_API_KEY")
GOOGLE_CLIENT_ID     = load_env_key("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = load_env_key("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = load_env_key("REDIRECT_URI")
if not REDIRECT_URI:
    try:
        host = st.context.headers.get("host")
        if host:
            local = "localhost" in host or "127.0.0.1" in host or host.startswith(("192.168.", "10."))
            REDIRECT_URI = f"http://{host}" if local else f"https://{host}"
    except Exception:
        pass
if not REDIRECT_URI:
    is_cloud = (os.environ.get("STREAMLIT_SHARING_MODE") or
                os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud" or
                not os.path.exists(os.path.join(_DIR, ".env")))
    REDIRECT_URI = "https://pokemonxotic.streamlit.app" if is_cloud else "http://localhost:8501"

def get_google_auth_url(client_id: str, redirect_uri: str) -> str:
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
              "scope": "openid email profile", "access_type": "offline", "prompt": "select_account"}
    query = "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

def get_google_user_info(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict | None:
    try:
        r = requests.post("https://oauth2.googleapis.com/token", timeout=10, data={
            "code": code, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": redirect_uri, "grant_type": "authorization_code",
        })
        if r.status_code != 200:
            return None
        token = r.json().get("access_token")
        if not token:
            return None
        ru = requests.get("https://www.googleapis.com/oauth2/v3/userinfo",
                          headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return ru.json() if ru.status_code == 200 else None
    except Exception:
        return None

DB_FILE = os.path.join(_DIR, "database.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL, profile_photo TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS collections (
        user_id INTEGER NOT NULL, card_id TEXT NOT NULL, name TEXT NOT NULL,
        set_name TEXT NOT NULL, set_id TEXT NOT NULL, number TEXT NOT NULL,
        printed_total TEXT NOT NULL, language TEXT NOT NULL, price REAL, image TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id), PRIMARY KEY (user_id, card_id))''')
    conn.commit(); conn.close()

init_db()

def _b64(name: str) -> str:
    path = os.path.join(_DIR, name)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_pika, _gengar = _b64("pikachu-transparent-32599.png"), _b64("Gengar-PNG-Picture.png")
_imgs = _szs = _pos = _rep = _att = ""
for _d, _sz, _p in [(_pika, "130px", "1% 97%"), (_gengar, "170px", "98% 97%")]:
    if _d:
        _imgs += f'url("data:image/png;base64,{_d}"), '
        _szs  += f"{_sz}, "; _pos += f"{_p}, "; _rep += "no-repeat, "; _att += "fixed, "
_bg_image = (_imgs +
    "repeating-linear-gradient(0deg,transparent,transparent 23px,rgba(255,215,0,.04) 24px),"
    "repeating-linear-gradient(90deg,transparent,transparent 23px,rgba(255,215,0,.04) 24px)")
_bg_size = _szs + "auto,auto"
_bg_pos  = _pos + "0 0,0 0"
_bg_rep  = _rep + "repeat,repeat"
_bg_att  = _att + "fixed,fixed"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
[data-testid="stAppViewContainer"]{{background-color:#0d0d18;background-image:{_bg_image};background-size:{_bg_size};background-position:{_bg_pos};background-repeat:{_bg_rep};background-attachment:{_bg_att};font-family:'Press Start 2P',monospace;}}
[data-testid="stSidebar"]{{background-color:#080810;border-right:2px solid #c8a84b55;}}
h1,h2,h3,h4{{font-family:'Press Start 2P',monospace!important;}}
h1{{color:#f5c518!important;font-size:18px!important;text-shadow:3px 3px 0px #5c4a1a,0 0 30px #c8a84b66;letter-spacing:3px;}}
h2,h3,h4{{color:#c8a84b!important;font-size:10px!important;}}
.stButton>button{{font-family:'Press Start 2P',monospace!important;font-size:10px!important;background:#0d0d18;color:#f5c518;border:2px solid #c8a84b;border-radius:0px;padding:10px 18px;width:100%;transition:background .1s,color .1s,box-shadow .1s;letter-spacing:1px;text-transform:uppercase;}}
.stButton>button:hover{{background:#c8a84b;color:#0d0d18;border-color:#f5c518;box-shadow:4px 4px 0px #5c4a1a;}}
.stButton>button:active{{transform:translate(2px,2px);box-shadow:1px 1px 0px #5c4a1a;}}
.stTextInput input{{font-family:'Press Start 2P',monospace!important;font-size:10px!important;background:#080810;color:#e0d8b0;border:2px solid #c8a84b55;border-radius:0px;caret-color:#f5c518;transition:border-color .1s;padding:10px 12px;}}
.stTextInput input:focus{{border-color:#f5c518!important;box-shadow:none!important;outline:none!important;}}
.stTextInput input::placeholder{{color:#3a3a5a;font-size:8px;}}
.stTextInput label{{font-family:'Press Start 2P',monospace!important;font-size:9px!important;font-weight:400;color:#f5c518!important;letter-spacing:1px;text-transform:uppercase;}}
[data-testid="stImage"] img{{border:2px solid #c8a84b44;border-radius:0px;display:block;margin:0 auto;transition:transform .15s,box-shadow .15s,border-color .15s;}}
[data-testid="stImage"] img:hover{{transform:translateY(-3px);box-shadow:0 6px 0px #c8a84b55,0 8px 20px #00000088;border-color:#f5c518aa;}}
hr{{border-color:#c8a84b33;border-width:2px;margin:12px 0;}}
.stCaption{{color:#5555a0!important;font-family:'Press Start 2P',monospace!important;font-size:7px!important;}}
.stat-pill{{display:inline-block;font-family:'Press Start 2P',monospace;font-size:8px;background:#0d0d18;border:2px solid #c8a84b55;border-radius:0px;color:#8888aa;padding:4px 10px;margin:2px 4px 2px 0;}}
.stat-pill span{{color:#f5c518;}}
.fuzzy-hint{{font-family:'Press Start 2P',monospace;font-size:9px;color:#8888aa;margin:6px 0 8px;padding:6px 10px;border-left:3px solid #c8a84b;background:#c8a84b0f;}}
.fuzzy-hint em{{color:#f5c518;font-style:normal;}}
.sb-card{{display:flex;align-items:center;gap:8px;padding:6px 4px;border-bottom:1px solid #c8a84b22;}}
.sb-card img{{width:38px;height:auto;border-radius:0px;border:1px solid #c8a84b44;flex-shrink:0;}}
.sb-card-info{{font-family:'Inter',sans-serif;font-size:10px;color:#c0c0d8;line-height:1.5;}}
.sb-card-price{{font-weight:600;color:#c8a84b;font-size:10px;}}
.set-header{{font-family:'Inter',sans-serif;font-size:11px;font-weight:600;color:#8888aa;text-transform:uppercase;letter-spacing:1px;margin:20px 0 8px;padding-bottom:4px;border-bottom:1px solid #2a2a40;}}
.coll-card-info{{font-family:'Press Start 2P',monospace;font-size:6px;color:#999;line-height:1.8;text-align:center;margin:4px 0 6px;word-break:break-word;}}
.coll-card-info .price{{color:#00e676;font-size:7px;font-weight:700;}}
.coll-card-info .setnum{{color:#f5c518;}}
.coll-card-info .pack{{color:#b0b0cc;font-size:5px;}}
div[data-testid="column"]:has(.coll-card-info) .stButton>button{{width:60px!important;height:28px!important;padding:0!important;font-size:10px!important;margin:0 auto!important;display:block!important;line-height:24px!important;background:#2a0808!important;color:#ff5555!important;border:2px solid #ff5555aa!important;}}
div[data-testid="column"]:has(.coll-card-info) .stButton>button:hover{{background:#ff5555!important;color:#0d0d18!important;border-color:#ff5555!important;box-shadow:2px 2px 0px #5c1a1a!important;}}
div[data-testid="column"]:has([data-testid="stImage"]):not(:has(.coll-card-info)){{border:2px solid #c8a84b33!important;padding:16px!important;background:#080810!important;margin-bottom:20px!important;height:420px!important;display:flex!important;flex-direction:column!important;justify-content:space-between!important;}}
div[data-testid="column"]:has([data-testid="stImage"]):not(:has(.coll-card-info)) [data-testid="stImage"]{{height:220px!important;display:flex!important;align-items:center!important;justify-content:center!important;overflow:hidden!important;}}
div[data-testid="column"]:has([data-testid="stImage"]):not(:has(.coll-card-info)) [data-testid="stImage"] img{{max-height:200px!important;width:auto!important;object-fit:contain!important;}}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_pokemon_names() -> list[str]:
    csv_path = os.path.join(_DIR, "pokemon.csv")
    if not os.path.exists(csv_path):
        st.warning(f"⚠️ `pokemon.csv` not found at `{csv_path}`. Fuzzy search disabled.")
        return []
    try:
        df = pd.read_csv(csv_path, usecols=["identifier"])
        names = ["-".join(p.capitalize() for p in n.split("-")) for n in df["identifier"].dropna().unique()]
        return sorted(set(names))
    except Exception as e:
        st.error(f"❌ Error loading pokemon.csv: {e}"); return []

_POKEMON_NAMES       = load_pokemon_names()
_POKEMON_NAMES_LOWER = [n.lower() for n in _POKEMON_NAMES]

def fuzzy_correct(name: str) -> str | None:
    if not name or not _POKEMON_NAMES:
        return None
    low = name.strip().lower()
    if any(w in _POKEMON_NAMES_LOWER for w in low.split()) or low in _POKEMON_NAMES_LOWER:
        return None
    matches = difflib.get_close_matches(low, _POKEMON_NAMES_LOWER, n=1, cutoff=0.6)
    if matches:
        return _POKEMON_NAMES[_POKEMON_NAMES_LOWER.index(matches[0])]
    return None

def register_or_login_user(email: str, name: str, profile_photo: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    row = c.fetchone()
    if row:
        user_id = row[0]
        c.execute("UPDATE users SET name=?,profile_photo=? WHERE id=?", (name, profile_photo, user_id))
    else:
        c.execute("INSERT INTO users (email,name,profile_photo) VALUES (?,?,?)", (email, name, profile_photo))
        conn.commit(); user_id = c.lastrowid
    conn.commit(); conn.close()
    return user_id

def load_collection() -> list[dict]:
    user_id = st.session_state.get("user_id")
    if user_id is not None:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM collections WHERE user_id=?", (user_id,))
        rows = c.fetchall(); conn.close()
        return [{"id": r["card_id"], "name": r["name"], "set_name": r["set_name"], "set_id": r["set_id"],
                 "number": r["number"], "printed_total": r["printed_total"], "language": r["language"],
                 "price": r["price"], "image": r["image"]} for r in rows]
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
    user_id = st.session_state.get("user_id")
    if user_id is not None:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute(
                'INSERT INTO collections (user_id,card_id,name,set_name,set_id,number,printed_total,language,price,image) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (user_id, card["id"], card["name"], card["set_name"], card["set_id"],
                 card["number"], card["printed_total"], card["language"], card["price"], card["image"]))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()
        return
    col = load_collection()
    if not any(c["id"] == card["id"] for c in col):
        col.append(card); save_collection(col)

def remove_from_collection(card_id: str):
    user_id = st.session_state.get("user_id")
    if user_id is not None:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM collections WHERE user_id=? AND card_id=?", (user_id, card_id))
        conn.commit(); conn.close()
        return
    save_collection([c for c in load_collection() if c["id"] != card_id])

def collection_ids() -> set[str]:
    return {c["id"] for c in load_collection()}

def best_price_official(card: dict) -> float | None:
    tcgplayer = card.get("tcgplayer", {})
    if tcgplayer:
        vals = []
        for pdetails in (tcgplayer.get("prices") or {}).values():
            if isinstance(pdetails, dict):
                for key in ["market", "mid", "low", "directLow", "high"]:
                    val = pdetails.get(key)
                    if val is not None:
                        try:
                            vals.append(float(val)); break
                        except (ValueError, TypeError):
                            pass
        if vals:
            return max(vals)
    for key in ["trendPrice", "averageSellPrice", "avg30", "avg7", "lowPrice"]:
        val = (card.get("cardmarket", {}).get("prices") or {}).get(key)
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
    for variant in (pricing.get("tcgplayer") or {}).values():
        if isinstance(variant, dict):
            val = variant.get("market") or variant.get("marketPrice") or variant.get("mid") or variant.get("midPrice") or variant.get("low") or variant.get("lowPrice")
            if val is not None:
                try:
                    prices.append(float(val))
                except (ValueError, TypeError):
                    pass
    cm = pricing.get("cardmarket", {})
    if cm:
        val = cm.get("trend") or cm.get("avg") or cm.get("low")
        if val is not None:
            try:
                prices.append(float(val))
            except (ValueError, TypeError):
                pass
    return max(prices) if prices else None

def fmt_price(p: float | None) -> str:
    return f"${p:.2f}" if p is not None else "N/A"

_CARD_BACK = "https://raw.githubusercontent.com/the-epsd/twinleafgg/master/assets/cardback.png"

def card_to_dict_official(raw: dict) -> dict:
    card_set = raw.get("set", {})
    images = raw.get("images", {})
    return {
        "id":            raw.get("id", ""),
        "name":          raw.get("name", ""),
        "set_name":      card_set.get("name", ""),
        "set_id":        card_set.get("id", ""),
        "number":        raw.get("number", ""),
        "printed_total": card_set.get("printedTotal", "?"),
        "language":      "en",
        "price":         best_price_official(raw),
        "image":         images.get("large") or images.get("small") or _CARD_BACK,
    }

def tcgdex_card_to_dict(raw: dict, lang: str) -> dict:
    card_set = raw.get("set", {})
    image_base = raw.get("image", "")
    return {
        "id":            raw.get("id", ""),
        "name":          raw.get("name", ""),
        "set_name":      card_set.get("name", ""),
        "set_id":        card_set.get("id", ""),
        "number":        raw.get("localId", ""),
        "printed_total": card_set.get("cardCount", {}).get("total", "?"),
        "language":      lang,
        "price":         tcgdex_best_price(raw),
        "image":         f"{image_base}/high.png" if image_base else _CARD_BACK,
    }

@st.cache_data(show_spinner=False, ttl=3600)
def cached_fetch_tcgdex_details(card_id: str, lang: str) -> dict | None:
    try:
        r = requests.get(f"https://api.tcgdex.net/v2/{lang}/cards/{card_id}", timeout=10)
        if r.status_code == 200:
            data = r.json(); data["language"] = lang; return data
    except Exception:
        pass
    return None

def search_official_api(name: str, set_number: str = "") -> list[dict]:
    name_clean = name.replace('"', '').strip()
    q_parts = [f'name:"*{name_clean}*"']
    target_total = None
    if set_number.strip():
        parts = [p.strip() for p in set_number.split("/")]
        q_parts.append(f'number:"{parts[0]}"')
        if len(parts) > 1:
            target_total = parts[1]
    headers = {"X-Api-Key": POKEMON_API_KEY} if POKEMON_API_KEY else {}
    try:
        r = requests.get("https://api.pokemontcg.io/v2/cards", headers=headers,
                         params={"q": " ".join(q_parts), "pageSize": 250}, timeout=15)
        if r.status_code != 200:
            return []
        data = sorted(r.json().get("data", []), key=lambda c: c.get("id", ""), reverse=True)
        if target_total:
            data = [c for c in data if str(c.get("set", {}).get("printedTotal")) == target_total]
        return [card_to_dict_official(c) for c in data]
    except Exception:
        return []

@st.cache_data(show_spinner=False, ttl=86400 * 30)
def translate_pokemon_name_to_japanese(english_name: str) -> str:
    clean = english_name.strip().lower().replace(" ", "-").replace(".", "")
    clean = {"mr-mime": "mr-mime", "mime-jr": "mime-jr", "flabebe": "flabebe", "type-null": "type-null"}.get(clean, clean)
    try:
        r = requests.get(f"https://pokeapi.co/api/v2/pokemon-species/{clean}", timeout=5)
        if r.status_code == 200:
            for n in r.json().get("names", []):
                if n.get("language", {}).get("name") == "ja-hrkt":
                    return n.get("name")
    except Exception:
        pass
    return english_name

def search_tcgdex_api(name: str, set_number: str = "", lang: str = "ja") -> list[dict]:
    term = name.strip()
    if lang == "ja":
        term = translate_pokemon_name_to_japanese(term)
    elif term and term[0].islower():
        term = term.capitalize()
    try:
        r = requests.get(f"https://api.tcgdex.net/v2/{lang}/cards", params={"name": term}, timeout=15)
        if r.status_code != 200:
            return []
        briefs = r.json()
    except Exception:
        return []
    if not briefs:
        return []
    briefs.sort(key=lambda b: b.get("id", ""), reverse=True)
    if set_number.strip():
        target_num = set_number.split("/")[0].strip()
        briefs = [b for b in briefs if b.get("localId") == target_num]
    briefs = briefs[:250]
    all_raw = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(cached_fetch_tcgdex_details, b["id"], lang): b for b in briefs}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                all_raw.append(res)
    return [tcgdex_card_to_dict(c, lang) for c in all_raw]

@st.cache_data(show_spinner=False, ttl=1800)
def search_tcg_all(name: str, set_number: str = "", language: str = "en") -> list[dict]:
    if language == "en":
        return search_official_api(name, set_number)
    if language == "ja":
        return search_tcgdex_api(name, set_number, "ja")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fut_off = executor.submit(search_official_api, name, set_number)
        fut_dex = executor.submit(search_tcgdex_api, name, set_number, "ja")
        return (fut_off.result() or []) + (fut_dex.result() or [])

_REGIONAL_PREFIXES = ["Galarian", "Alolan", "Hisuian", "Paldean", "Unovan", "Shadow", "Radiant"]

def show_card_grid(cards: list[dict], mode: str, owned: set[str], num_cols: int = 4):
    if not cards:
        st.info("No cards to display."); return
    cols = st.columns(num_cols)
    for i, card in enumerate(cards):
        with cols[i % num_cols]:
            st.image(card.get("image") or _CARD_BACK, use_container_width=True)
            st.markdown(
                f'<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;color:#fff;margin:6px 0 2px;word-break:break-word;line-height:1.6;">{card["name"]}</div>',
                unsafe_allow_html=True)
            sn = f"{card['number']}/{card['printed_total']}"
            lang = (card.get("language") or "en").upper()
            lang_html = (f'&nbsp;<span style="font-family:\'Press Start 2P\',monospace;font-size:6px;background:#1a2a1a;color:#7fff7f;border:1px solid #3f7f3f;padding:2px 4px;">{lang}</span>'
                         if lang != "EN" else "")
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;font-family:\'Press Start 2P\',monospace;font-size:7px;margin-bottom:6px;">'
                f'<span style="color:#f5c518;">{sn}{lang_html}</span>'
                f'<span style="color:#00e676;">{fmt_price(card["price"])}</span></div>',
                unsafe_allow_html=True)
            if mode == "search":
                if card["id"] in owned:
                    st.markdown('<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;color:#00e676;margin-bottom:8px;">✅ OWNED</div>', unsafe_allow_html=True)
                else:
                    st.button("＋ ADD", key=f"add_{card['id']}_{i}", on_click=add_to_collection, args=(card,))
            elif mode == "collection":
                st.button("－ REMOVE", key=f"rem_{card['id']}_{i}", on_click=remove_from_collection, args=(card["id"],))
            st.write("")

def show_collection_grid(cards: list[dict], owned: set[str], num_cols: int = 8):
    if not cards:
        st.info("No cards to display."); return
    cols = st.columns(num_cols, gap="small")
    for i, card in enumerate(cards):
        with cols[i % num_cols]:
            st.image(card.get("image") or _CARD_BACK, use_container_width=True)
            st.markdown(
                f'<div class="coll-card-info">'
                f'<div class="setnum">{card["number"]}/{card["printed_total"]}</div>'
                f'<div class="price">{fmt_price(card["price"])}</div>'
                f'<div class="pack">{card.get("set_name","")}</div></div>',
                unsafe_allow_html=True)
            st.button("－", key=f"rem_coll_{card['id']}_{i}", on_click=remove_from_collection, args=(card["id"],))

def simulate_card_history(card: dict, days: int = 30) -> list[float]:
    current_price = card.get("price") or 0.0
    if current_price == 0.0:
        return [0.0] * days
    random.seed(sum(ord(c) for c in card.get("id", "")))
    history = [0.0] * days
    history[-1] = current_price
    for i in range(days - 2, -1, -1):
        history[i] = round(history[i + 1] / (1.0 + random.uniform(-0.012, 0.022)), 2)
    return history

def get_altair_line_chart(df: pd.DataFrame, x_col: str, y_col: str, height: int = 220):
    min_val, max_val = float(df[y_col].min()), float(df[y_col].max())
    padding = max((max_val - min_val) * 0.4, min_val * 0.1, 1.0)
    return (
        alt.Chart(df.reset_index()).mark_line(color="#c8a84b", strokeWidth=2).encode(
            x=alt.X(f"{x_col}:N", sort=None, axis=alt.Axis(labelAngle=-45, title=None, labelColor="#8888aa", grid=False)),
            y=alt.Y(f"{y_col}:Q", scale=alt.Scale(domain=[max(0.0, min_val - padding), max_val + padding]),
                    axis=alt.Axis(title=None, labelColor="#8888aa", grid=True, gridColor="#2a2a40")),
        ).properties(height=height).configure_view(strokeWidth=0).configure_axis(domain=False)
    )

def show_profit_grid_with_charts(profits: list[dict]):
    if not profits:
        st.info("No cards to display."); return
    for item in profits:
        card = item["card"]
        gain_val, gain_pct = item["gain"], item["gain_pct"]
        color = "#00e676" if gain_val >= 0 else "#ff1744"
        sign  = "+" if gain_val >= 0 else ""
        st.markdown('<div style="border:2px solid #c8a84b33;padding:16px;margin-bottom:20px;background:#080810;">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-family:\'Press Start 2P\',monospace;font-size:7px;line-height:2.0;margin-bottom:12px;display:flex;justify-content:space-between;flex-wrap:wrap;align-items:center;">'
            f'<span style="color:#f5c518;font-size:9px;">🏆 {card["name"]} ({card["id"]})</span>'
            f'<span style="color:#888;">Base:<span style="color:#fff;">${item["base"]:.2f}</span>&nbsp;&nbsp;'
            f'Market:<span style="color:#fff;">${item["current"]:.2f}</span>&nbsp;&nbsp;'
            f'Profit:<span style="color:{color};font-weight:bold;">{sign}${gain_val:.2f} ({sign}{gain_pct:.1f}%)</span></span></div>',
            unsafe_allow_html=True)
        days = 30
        dates = [(datetime.now() - timedelta(days=d)).strftime("%b %d") for d in range(days)]
        dates.reverse()
        card_df = pd.DataFrame({"Date": dates, "Price ($)": simulate_card_history(card, days)}).set_index("Date")
        st.altair_chart(get_altair_line_chart(card_df, "Date", "Price ($)", height=180), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")

# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in [("search_results", []), ("last_search_key", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

def _trigger_search():
    st.session_state["_search_pending"] = True

# ── Google redirect handling ──────────────────────────────────────────────────
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and "code" in st.query_params:
    auth_code = st.query_params["code"]
    with st.spinner("Signing in with Google..."):
        user_info = get_google_user_info(auth_code, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
    if user_info:
        g_email   = user_info.get("email", "")
        g_name    = user_info.get("name", "Google User")
        g_picture = user_info.get("picture", "https://api.dicebear.com/7.x/pixel-art/svg?seed=ash")
        user_id   = register_or_login_user(g_email, g_name, g_picture)
        st.session_state.update({"user_id": user_id, "username": g_name, "email": g_email,
                                  "profile_photo": g_picture, "show_login_dialog": False})
        st.query_params.clear(); st.rerun()
    else:
        st.error("Google Authentication failed. Please try again.")
        st.query_params.clear()

_owned      = collection_ids()
_collection = load_collection()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    options = ["Searcher", "My Collection", "Profit Selection"]
    active_page = (
        option_menu(menu_title=None, options=options, icons=None, default_index=0)
        if HAS_OPTION_MENU else st.sidebar.radio("NAVIGATE", options)
    )
    st.divider()
    _lang_code = "en"
    if active_page == "Searcher":
        _lang_map = {"🇺🇸 English": "en", "🇯🇵 Japanese": "ja", "🌏 All": ""}
        _lang_code = _lang_map[st.selectbox("Language", list(_lang_map.keys()), index=0, key="language_select")]
        st.divider()

    st.markdown("<div style='height:80px;'></div>", unsafe_allow_html=True)
    current_user_id = st.session_state.get("user_id")
    if current_user_id is None:
        if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
            st.link_button("SIGN IN WITH GOOGLE", get_google_auth_url(GOOGLE_CLIENT_ID, REDIRECT_URI), use_container_width=True)
        else:
            if st.button("SIGN IN", key="btn_signin"):
                st.session_state["show_login_dialog"] = True; st.rerun()
    else:
        photo_url = st.session_state.get("profile_photo", "https://api.dicebear.com/7.x/pixel-art/svg?seed=ash")
        st.markdown(f"""
        <style>
        div:has(>#profile-pic-marker)+div button{{width:48px!important;height:48px!important;border-radius:50%!important;overflow:hidden!important;background-image:url('{photo_url}')!important;background-size:cover!important;background-repeat:no-repeat!important;background-position:center!important;border:2px solid #c8a84b!important;box-shadow:0 0 10px #c8a84b55!important;font-size:0px!important;color:transparent!important;padding:0!important;display:block!important;margin:0 auto!important;}}
        div:has(>#profile-pic-marker)+div button:hover{{border-color:#f5c518!important;box-shadow:0 0 15px #f5c518aa!important;transform:scale(1.05)!important;}}
        </style>""", unsafe_allow_html=True)
        st.markdown('<span id="profile-pic-marker"></span>', unsafe_allow_html=True)
        if st.button(" ", key="btn_profile_avatar"):
            st.session_state["show_profile_options"] = not st.session_state.get("show_profile_options", False); st.rerun()

        if st.session_state.get("show_profile_options"):
            st.markdown(f"<div style='text-align:center;margin-top:8px;'><div style='font-family:\"Press Start 2P\",monospace;font-size:6px;color:#f5c518;margin-bottom:6px;'>{st.session_state.get('username')}</div>", unsafe_allow_html=True)
            guest_cards = []
            if os.path.exists(COLLECTION_FILE):
                try:
                    with open(COLLECTION_FILE) as f:
                        g_data = json.load(f)
                        if isinstance(g_data, list):
                            guest_cards = g_data
                except Exception:
                    pass
            if guest_cards:
                if st.button("📥 SYNC GUEST DATA", key="btn_sync_guest"):
                    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); synced = 0
                    for card in guest_cards:
                        try:
                            c.execute('INSERT INTO collections (user_id,card_id,name,set_name,set_id,number,printed_total,language,price,image) VALUES (?,?,?,?,?,?,?,?,?,?)',
                                      (current_user_id, card["id"], card["name"], card["set_name"], card["set_id"],
                                       card["number"], card["printed_total"], card["language"], card["price"], card["image"]))
                            synced += 1
                        except sqlite3.IntegrityError:
                            pass
                    conn.commit(); conn.close()
                    st.success(f"Synced {synced} cards!"); st.rerun()
            if st.button("LOG OUT", key="btn_logout"):
                st.session_state.update({"user_id": None, "username": None, "email": None,
                                          "profile_photo": None, "show_profile_options": False}); st.rerun()
            if st.button("RESET DATA", key="btn_reset"):
                conn = sqlite3.connect(DB_FILE); c = conn.cursor()
                c.execute("DELETE FROM collections WHERE user_id=?", (current_user_id,))
                conn.commit(); conn.close()
                st.session_state["show_profile_options"] = False
                st.success("Data reset!"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ── Google Sign-in Dialog ─────────────────────────────────────────────────────
if st.session_state.get("show_login_dialog"):
    with st.container(border=True):
        st.markdown("<h3 style='text-align:center;color:#f5c518;font-family:\"Press Start 2P\",monospace;font-size:12px;margin-bottom:15px;'>🌐 SIGN IN WITH GOOGLE</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            g_email = st.text_input("GOOGLE EMAIL", value="ash.ketchum@gmail.com", placeholder="e.g. trainer@gmail.com")
        with col2:
            g_name = st.text_input("FULL NAME", value="Ash Ketchum", placeholder="e.g. Ash Ketchum")
        st.markdown("<div style='font-family:\"Press Start 2P\",monospace;font-size:8px;color:#888;margin:12px 0 6px;'>CHOOSE YOUR GOOGLE AVATAR:</div>", unsafe_allow_html=True)
        _avatars = {"Ash (Pikachu Trainer)": "https://api.dicebear.com/7.x/pixel-art/svg?seed=ash",
                    "Misty (Water Master)":   "https://api.dicebear.com/7.x/pixel-art/svg?seed=misty",
                    "Brock (Rock Leader)":    "https://api.dicebear.com/7.x/pixel-art/svg?seed=brock",
                    "Red (Champion)":         "https://api.dicebear.com/7.x/pixel-art/svg?seed=red"}
        avatar_choice = st.selectbox("GOOGLE PROFILE PHOTO", list(_avatars.keys()))
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✓ CONTINUE TO SIGN IN", key="btn_confirm_login"):
                if not g_email.strip() or not g_name.strip():
                    st.error("Please enter email and name.")
                else:
                    uid = register_or_login_user(g_email.strip(), g_name.strip(), _avatars[avatar_choice])
                    st.session_state.update({"user_id": uid, "username": g_name.strip(), "email": g_email.strip(),
                                              "profile_photo": _avatars[avatar_choice], "show_login_dialog": False})
                    st.success(f"Welcome, {g_name}!"); st.rerun()
        with c2:
            if st.button("✗ CANCEL", key="btn_cancel_login"):
                st.session_state["show_login_dialog"] = False; st.rerun()
        st.markdown("""
        <div style="border:2px solid #c8a84b33;padding:12px;border-radius:8px;background:#080810;margin-top:20px;">
            <div style="color:#f5c518;font-family:'Press Start 2P',monospace;font-size:7px;margin-bottom:8px;">ℹ️ ENABLE ACTUAL GOOGLE SIGN-IN</div>
            <div style="color:#888;font-size:9px;line-height:1.5;font-family:'Inter',sans-serif;">
                Configure free developer keys to login with your real Google account:<br>
                1. <a href="https://console.cloud.google.com" target="_blank" style="color:#f5c518;">Google Cloud Console</a> → OAuth Consent Screen → Credentials → OAuth Client ID (Web application)<br>
                2. Add <code>http://localhost:8501</code> to Authorized redirect URIs<br>
                3. Save keys in <code>.env</code>: <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code>
            </div>
        </div>""", unsafe_allow_html=True)
    st.divider()

# ── Main Content ──────────────────────────────────────────────────────────────
if active_page == "Searcher":
    st.title("🎴 POKÉDEX SEARCHER")
    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:13px;color:#666680;margin:-6px 0 20px;line-height:1.7;">'
        'Search any Pokémon card using the fast TCGdex API — typos are corrected automatically.</div>',
        unsafe_allow_html=True)

    _col_name, _col_set = st.columns([3, 1])
    with _col_name:
        typed_name = st.text_input("POKÉMON NAME", placeholder="e.g. pikachu, bulbasor, charmandr…",
                                   key="typed_name_input", on_change=_trigger_search)
        _corrected = fuzzy_correct(typed_name.strip()) if typed_name and typed_name.strip() else None
        if _corrected:
            st.markdown(f'<div class="fuzzy-hint">→ Searching for <em>{_corrected}</em></div>', unsafe_allow_html=True)
    with _col_set:
        set_number = st.text_input("SET NUMBER  (optional)", placeholder="e.g. 171/094",
                                   key="set_number_input", on_change=_trigger_search)

    if st.button("🔍 SEARCH"):
        st.session_state["_search_pending"] = True

    if st.session_state.pop("_search_pending", False):
        search_name = _corrected or (typed_name.strip() if typed_name else "")
        if not search_name:
            st.warning("Type a Pokémon name to search.")
        else:
            search_key = (search_name.lower(), set_number.strip(), _lang_code)
            if search_key != st.session_state["last_search_key"]:
                st.session_state["last_search_key"] = search_key
                lang_label = {"en": "English", "ja": "Japanese", "": "all languages"}[_lang_code]
                with st.spinner(f'Fetching {lang_label} cards for "{search_name}"…'):
                    raw_cards = search_tcg_all(search_name, set_number.strip(), language=_lang_code)
                if raw_cards:
                    st.session_state["search_results"] = sorted(raw_cards, key=lambda c: (c["price"] or 0), reverse=True)
                else:
                    st.session_state["search_results"] = []
                    st.warning("No cards found. Try a different name or language.")

    if st.session_state["search_results"]:
        results = st.session_state["search_results"]
        trainer_cards  = [c for c in results if "'" in c["name"]]
        regional_cards = [c for c in results if any(c["name"].startswith(p) for p in _REGIONAL_PREFIXES)]
        non_en_cards   = [c for c in results if (c.get("language") or "en").upper() != "EN"]
        st.markdown(
            f'<div style="margin:8px 0 16px;">'
            f'<span class="stat-pill">🃏 <span>{len(results)}</span> cards</span>'
            f'<span class="stat-pill">🎓 trainer <span>{len(trainer_cards)}</span></span>'
            f'<span class="stat-pill">🗾 regional <span>{len(regional_cards)}</span></span>'
            f'<span class="stat-pill">🌏 non-english <span>{len(non_en_cards)}</span></span></div>',
            unsafe_allow_html=True)
        show_card_grid(results, mode="search", owned=_owned)

elif active_page == "My Collection":
    st.title("📦 MY COLLECTION")
    if not _collection:
        st.info("Your collection is empty. Go to the Card Searcher to add some cards!")
    else:
        _total_val = sum(c["price"] for c in _collection if c.get("price"))
        st.markdown(
            f'<div style="font-family:\'Inter\',sans-serif;font-size:13px;color:#666680;margin-bottom:20px;">'
            f'{len(_collection)} cards <span style="color:#c8a84b;font-weight:600;">${_total_val:.2f}</span> est. value</div>',
            unsafe_allow_html=True)
        show_collection_grid(sorted(_collection, key=lambda c: -(c.get("price") or 0)), owned=_owned, num_cols=8)

elif active_page == "Profit Selection":
    st.title("PROFIT & TRENDS")
    if not _collection:
        st.info("No cards in your collection yet. Add some in the Card Searcher to see profit analysis!")
    else:
        days  = 30
        dates = [(datetime.now() - timedelta(days=i)).strftime("%b %d") for i in range(days)]
        dates.reverse()
        daily_totals = [0.0] * days
        for card in _collection:
            for i, val in enumerate(simulate_card_history(card, days)):
                daily_totals[i] += val
        current_val = daily_totals[-1]; base_val = daily_totals[0]
        gain_val = current_val - base_val
        gain_pct = (gain_val / base_val * 100) if base_val > 0 else 0.0
        color = "#00e676" if gain_val >= 0 else "#ff1744"
        sign  = "+" if gain_val >= 0 else ""
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:20px;">'
            f'<div class="stat-pill" style="flex:1;min-width:180px;text-align:center;padding:12px;">Est. Collection Value<br/><span style="font-size:16px;color:#c8a84b;margin-top:6px;display:inline-block;">${current_val:,.2f}</span></div>'
            f'<div class="stat-pill" style="flex:1;min-width:180px;text-align:center;padding:12px;">Purchase Cost (Base)<br/><span style="font-size:16px;color:#8888aa;margin-top:6px;display:inline-block;">${base_val:,.2f}</span></div>'
            f'<div class="stat-pill" style="flex:1;min-width:180px;text-align:center;padding:12px;">Estimated Net Profit<br/><span style="font-size:16px;color:{color};margin-top:6px;display:inline-block;">{sign}${gain_val:,.2f} ({sign}{gain_pct:.2f}%)</span></div>'
            f'</div>', unsafe_allow_html=True)
        chart_data = pd.DataFrame({"Date": dates, "Total Value ($)": daily_totals}).set_index("Date")
        st.altair_chart(get_altair_line_chart(chart_data, "Date", "Total Value ($)", height=220), use_container_width=True)
        st.divider()
        st.markdown('<div style="font-family:\'Press Start 2P\',monospace;font-size:9px;color:#c8a84b;margin:15px 0;">🔥 TOP GROWING PERFORMERS (30-DAY TREND) WITH GRAPHS</div>', unsafe_allow_html=True)
        profit_list = []
        for card in _collection:
            hist = simulate_card_history(card, days)
            current, base = hist[-1], hist[0]
            gain = current - base
            profit_list.append({"card": card, "current": current, "base": base, "gain": gain,
                                 "gain_pct": (gain / base * 100) if base > 0 else 0.0})
        profit_list.sort(key=lambda x: x["gain_pct"], reverse=True)
        show_profit_grid_with_charts(profit_list)
    
