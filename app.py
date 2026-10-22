import json
import os
import random
import time
import unicodedata
import urllib.error
import urllib.request

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS

app = Flask(__name__)

# Složka, ve které leží index.html, style.css a script.js
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_FILES = {"style.css", "script.js"}

# Pro školní projekt povolíme CORS všude (později se dá zpřísnit)
CORS(app)


# Témata podpory. Klíčová slova jsou bez diakritiky a malými písmeny.
# Jedno slovo = začátek slova v dotazu ("spust" najde "spustit", "spuštění").
# Víc slov = hledá se celá fráze ("cerna obrazovka").
TOPICS = [
    {
        "keywords": ["spust", "nespust", "nezapn", "nenac", "cerna obrazovka", "nejde zapnout"],
        "reply": (
            "Pokud se hra nespustí, zkuste prosím následující:\n"
            "1. Restartujte počítač a spusťte hru znovu.\n"
            "2. V launcheru zvolte „Ověřit soubory hry“, opraví to soubory poškozené při aktualizaci.\n"
            "3. Aktualizujte ovladače grafické karty.\n"
            "4. Dočasně vypněte antivirus, který může hru blokovat.\n"
            "Pokud to nepomůže, napište nám prosím, zda se zobrazuje nějaká chybová hláška."
        ),
    },
    {
        "keywords": ["pada", "spadn", "spadl", "crash", "zamrz", "vypadn", "zasekl", "zasekn"],
        "reply": (
            "Pády hry nejčastěji způsobují ovladače nebo poškozené soubory. Doporučujeme:\n"
            "1. Aktualizujte ovladače grafické karty.\n"
            "2. V launcheru zvolte „Ověřit soubory hry“.\n"
            "3. Zavřete programy na pozadí (overlaye, nahrávání obrazovky).\n"
            "4. Snižte v nastavení kvalitu grafiky.\n"
            "Pomůže nám, když napíšete, kdy přesně hra padá, například při načítání nebo v boji."
        ),
    },
    {
        "keywords": ["fps", "lag", "seka", "trha", "pomal", "ping", "zpozd"],
        "reply": (
            "Pro lepší výkon zkuste prosím:\n"
            "1. Snížit rozlišení nebo kvalitu stínů a efektů.\n"
            "2. Zapnout V-Sync, pokud se obraz trhá.\n"
            "3. Zavřít prohlížeč a další programy na pozadí.\n"
            "4. U notebooku připojit nabíječku a zapnout režim vysokého výkonu.\n"
            "Pokud se hra seká jen při hraní online, jde spíše o připojení. Zkuste prosím kabel místo Wi-Fi."
        ),
    },
    {
        "keywords": ["ovladac", "gamepad", "controller", "joystick", "klavesnic"],
        "reply": (
            "Pokud nefunguje ovladač, zkuste prosím:\n"
            "1. Odpojit ho a znovu připojit, ideálně do jiného USB portu.\n"
            "2. U bezdrátového ovladače zkontrolovat baterii a znovu ho spárovat.\n"
            "3. V nastavení hry ověřit, že je zapnutá podpora ovladače.\n"
            "4. Ve Steamu vypnout nebo zapnout „Steam Input“ pro tuto hru."
        ),
    },
    {
        "keywords": ["ucet", "uct", "prihlas", "hesl", "login", "zablokov", "zabanov"],
        "reply": (
            "S účtem Vám rádi pomůžeme:\n"
            "1. Heslo obnovíte přes „Zapomenuté heslo“ na přihlašovací obrazovce.\n"
            "2. Zkontrolujte prosím, že se přihlašujete stejným e-mailem, jaký jste použil(a) při registraci.\n"
            "3. Pokud je účet zablokovaný, vyplňte prosím výše svůj e-mail a popište, co se stalo. Požadavek předáme kolegům."
        ),
    },
    {
        "keywords": ["platb", "zaplat", "koupil", "nakup", "penize", "refund", "dlc", "predplat"],
        "reply": (
            "U problémů s nákupem prosím postupujte takto:\n"
            "1. Platba se někdy zpracovává až 24 hodin. Zkuste se odhlásit a znovu přihlásit.\n"
            "2. Zkontrolujte, že jste přihlášen(a) ke stejnému účtu, ze kterého jste nakupoval(a).\n"
            "3. Pokud žádáte o vrácení peněz, uveďte prosím datum nákupu a o jakou položku šlo. Požadavek předáme kolegům."
        ),
    },
    {
        "keywords": ["aktualiz", "update", "patch", "verze", "stahov", "stahuj", "nestahuj", "instal", "nainstal"],
        "reply": (
            "Pokud se aktualizace nestáhne nebo nenainstaluje:\n"
            "1. Zkontrolujte, že máte na disku dostatek volného místa.\n"
            "2. Restartujte launcher a spusťte stahování znovu.\n"
            "3. Pokud to nepomůže, hru odinstalujte a nainstalujte znovu. Uložené pozice zůstanou zachovány."
        ),
    },
    {
        "keywords": ["zvuk", "neslys", "hudb", "audio", "mikrofon", "sluchat", "repro"],
        "reply": (
            "Pokud nefunguje zvuk:\n"
            "1. Zkontrolujte hlasitost ve hře i ve Windows (Mixér hlasitosti).\n"
            "2. Ve Windows nastavte správné výstupní zařízení, například sluchátka.\n"
            "3. Odpojte a znovu připojte sluchátka, poté hru restartujte."
        ),
    },
    {
        "keywords": ["dekuj", "dik", "funguje to", "uz to jde"],
        "reply": "Rádi jsme pomohli. Pokud by se problém vrátil, neváhejte nás znovu kontaktovat. Přejeme příjemnou hru.",
    },
]


# ---------- Gemini (umělá inteligence) ----------
# Klíč NIKDY nepatří do kódu ani na GitHub. Na Renderu ho nastav v záložce
# Environment jako proměnnou GEMINI_API_KEY. Bez klíče backend odpovídá
# podle klíčových slov níže, takže stránka funguje pořád.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

SYSTEM_PROMPT = """Odpovídáš na dotazy hráčů za zákaznickou podporu herního studia VDF Games.
Piš jako zkušený a ochotný člověk z podpory, který odpovídá na e-mail.

Tón a jazyk:
- Spisovná čeština, zdvořile a profesionálně. Hráči vždy vykej (Vy, Váš, zkuste, napište) a nikdy netykej.
- Buď vstřícný a klidný, ale věcný. Žádný slang, emotikony ani přehnané nadšení.
- Nepoužívej Markdown: žádné hvězdičky, mřížky, tučné písmo ani nadpisy. Jen obyčejný text a číslované kroky.

Struktura odpovědi:
1. Začni „Dobrý den,“ a jednou větou, ze které je vidět, že rozumíš problému.
2. Napiš konkrétní postup v číslovaných krocích (nejvýše 6), každý krok jedna až dvě věty.
3. Pokud chybí důležité informace (jaká hra, zařízení, chybová hláška), zdvořile se na ně zeptej.
4. Zakonči řádkem „S pozdravem“ a pod ním „tým podpory VDF Games“.

Pravidla:
- Pomáhej jen s hrami VDF Games a technickými problémy kolem nich (spuštění, pády, výkon, ovladače, účet, platby, aktualizace, zvuk). Na jiná témata zdvořile odpověz, že s nimi podpora pomoci nemůže.
- Nikdy nežádej hesla, čísla platebních karet ani jiné citlivé údaje.
- Nic neslibuj (vrácení peněz, odblokování účtu, termín opravy). Můžeš napsat, že požadavek předáš kolegům, a odkázat na číslo požadavku.
- Nevymýšlej si názvy her, funkce ani nastavení, o kterých nevíš.
- Když se hráč zeptá, jestli píše s člověkem, odpověz pravdivě, že jde o automatického asistenta podpory VDF Games."""

MAX_MESSAGE_LENGTH = 1000      # delší dotazy odmítneme
MAX_REQUESTS_PER_MINUTE = 8    # ochrana proti zneužití (a proti vysokému účtu za API)
_recent_requests = {}


def too_many_requests(ip):
    """Jednoduchý limit: kolik dotazů smí jedna IP adresa poslat za minutu."""
    now = time.time()
    times = [t for t in _recent_requests.get(ip, []) if now - t < 60]
    if len(times) >= MAX_REQUESTS_PER_MINUTE:
        _recent_requests[ip] = times
        return True
    times.append(now)
    _recent_requests[ip] = times
    return False


def ask_gemini(message, ticket):
    """Pošle dotaz do Gemini a vrátí text odpovědi (nebo None, když se to nepovede)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": f"Číslo požadavku: {ticket}\n\nDotaz hráče:\n{message}"}]}],
        "generationConfig": {"maxOutputTokens": 800},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.load(res)
    except urllib.error.HTTPError as err:
        print(f"Gemini vrátil chybu {err.code}: {err.read()[:300]!r}")
        return None
    except Exception as err:  # výpadek sítě, timeout…
        print(f"Gemini nedostupný: {err}")
        return None

    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        print(f"Gemini nevrátil žádný text: {str(data)[:300]}")
        return None
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    return text or None


FALLBACK_REPLY = (
    "Děkujeme za Váš dotaz. Abychom Vám mohli poradit, potřebujeme prosím několik doplňujících informací:\n"
    "- o jakou hru jde,\n"
    "- na jakém zařízení hrajete (PC, konzole, mobil),\n"
    "- co přesně se děje a zda se zobrazuje chybová hláška."
)


def formal_letter(text):
    """Odpověď podle klíčových slov zabalí do oslovení a podpisu, ať zní stejně jako Gemini."""
    return f"Dobrý den,\n\n{text}\n\nS pozdravem\ntým podpory VDF Games"


def normalize(text):
    """Převede text na malá písmena a odstraní diakritiku ("Nespustí" -> "nespusti")."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def find_reply(message):
    """Najde téma s nejvíc shodami klíčových slov. Když nic nesedí, vrátí obecnou odpověď."""
    text = normalize(message)
    # Interpunkci nahradíme mezerami, ať jdou slova snadno rozdělit
    clean = "".join(ch if ch.isalnum() else " " for ch in text)
    words = clean.split()

    best_reply = FALLBACK_REPLY
    best_score = 0

    for topic in TOPICS:
        score = 0
        for keyword in topic["keywords"]:
            if " " in keyword:
                if keyword in clean:
                    score += 1
            elif any(word.startswith(keyword) for word in words):
                score += 1

        if score > best_score:
            best_score = score
            best_reply = topic["reply"]

    return best_reply


@app.get("/")
def home():
    """Hlavní adresa ukáže stránku podpory (frontend)."""
    return send_from_directory(HERE, "index.html")


@app.get("/<name>")
def page_file(name):
    """Styly a skript stránky. Nic jiného ze složky (třeba app.py) se neposílá."""
    if name not in PAGE_FILES:
        abort(404)
    return send_from_directory(HERE, name)


@app.get("/status")
def status():
    mode = f"Gemini ({GEMINI_MODEL})" if GEMINI_API_KEY else "klíčová slova (bez GEMINI_API_KEY)"
    return f"VDF Support Backend is running – odpovědi: {mode}"


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    student = (data.get("student") or "unknown").strip()
    email = (data.get("email") or "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": f"dotaz je příliš dlouhý (nejvýše {MAX_MESSAGE_LENGTH} znaků)"}), 400

    # Render posílá skutečnou adresu návštěvníka v hlavičce X-Forwarded-For
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
    if too_many_requests(ip):
        return jsonify({"error": "příliš mnoho dotazů najednou, zkuste to prosím za minutu"}), 429

    # Výpis do logu (na Renderu ho uvidíš v záložce Logs)
    print(f"[{student}] {email or 'bez e-mailu'}: {message}")

    ticket = f"VDF-{random.randint(1000, 9999)}"
    reply = ask_gemini(message, ticket) if GEMINI_API_KEY else None
    if not reply:
        reply = formal_letter(find_reply(message))  # bez klíče nebo při chybě: odpověď podle klíčových slov

    return jsonify({"reply": reply, "ticket": ticket})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
