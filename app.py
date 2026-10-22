import json
import os
import random
import time
import unicodedata
import urllib.error
import urllib.request

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Pro školní projekt povolíme CORS všude (později se dá zpřísnit)
CORS(app)


# Témata podpory. Klíčová slova jsou bez diakritiky a malými písmeny.
# Jedno slovo = začátek slova v dotazu ("spust" najde "spustit", "spuštění").
# Víc slov = hledá se celá fráze ("cerna obrazovka").
TOPICS = [
    {
        "keywords": ["spust", "nespust", "nezapn", "nenac", "cerna obrazovka", "nejde zapnout"],
        "reply": (
            "Když se hra nespustí, zkus prosím tohle:\n"
            "1. Restartuj počítač a spusť hru znovu.\n"
            "2. V launcheru zvol „Ověřit soubory hry“, opraví poškozené soubory po aktualizaci.\n"
            "3. Aktualizuj ovladače grafické karty.\n"
            "4. Dočasně vypni antivirus, někdy hru blokuje.\n"
            "Pokud to nepomůže, napiš nám, jestli se objeví nějaká chybová hláška."
        ),
    },
    {
        "keywords": ["pada", "spadn", "spadl", "crash", "zamrz", "vypadn", "zasekl", "zasekn"],
        "reply": (
            "Pády hry většinou způsobí ovladače nebo poškozené soubory:\n"
            "1. Aktualizuj ovladače grafické karty.\n"
            "2. V launcheru zvol „Ověřit soubory hry“.\n"
            "3. Zavři programy na pozadí (overlaye, nahrávání obrazovky).\n"
            "4. Sniž v nastavení kvalitu grafiky.\n"
            "Pomůže nám, když napíšeš, kdy přesně hra padá, třeba při načítání nebo v boji."
        ),
    },
    {
        "keywords": ["fps", "lag", "seka", "trha", "pomal", "ping", "zpozd"],
        "reply": (
            "Na lepší výkon zkus:\n"
            "1. Snížit rozlišení nebo kvalitu stínů a efektů.\n"
            "2. Zapnout V-Sync, pokud se obraz trhá.\n"
            "3. Zavřít prohlížeč a další programy na pozadí.\n"
            "4. U notebooku připojit nabíječku a zapnout režim vysokého výkonu.\n"
            "Pokud se seká jen hra online, jde spíš o připojení: zkus kabel místo Wi-Fi."
        ),
    },
    {
        "keywords": ["ovladac", "gamepad", "controller", "joystick", "klavesnic"],
        "reply": (
            "Když nefunguje ovladač:\n"
            "1. Odpoj ho a připoj znovu, ideálně do jiného USB portu.\n"
            "2. U bezdrátového ovladače zkontroluj baterii a znovu ho spáruj.\n"
            "3. V nastavení hry zkontroluj, jestli je zapnutá podpora ovladače.\n"
            "4. Ve Steamu vypni nebo zapni „Steam Input“ pro tuhle hru."
        ),
    },
    {
        "keywords": ["ucet", "uct", "prihlas", "hesl", "login", "zablokov", "zabanov"],
        "reply": (
            "S účtem ti pomůžeme:\n"
            "1. Heslo obnovíš přes „Zapomenuté heslo“ na přihlašovací obrazovce.\n"
            "2. Zkontroluj, že se přihlašuješ stejným e-mailem, jaký jsi použil/a při registraci.\n"
            "3. Pokud je účet zablokovaný, vyplň výše svůj e-mail a popiš, co se stalo."
        ),
    },
    {
        "keywords": ["platb", "zaplat", "koupil", "nakup", "penize", "refund", "dlc", "predplat"],
        "reply": (
            "U problémů s nákupem:\n"
            "1. Platba se někdy zpracovává až 24 hodin, zkus se odhlásit a přihlásit znovu.\n"
            "2. Zkontroluj, že jsi přihlášený/á na stejný účet, na který jsi nakupoval/a.\n"
            "3. Pokud chceš vrátit peníze, napiš datum nákupu a co jsi kupoval/a."
        ),
    },
    {
        "keywords": ["aktualiz", "update", "patch", "verze", "stahov", "stahuj", "nestahuj", "instal", "nainstal"],
        "reply": (
            "Když se aktualizace nestáhne nebo nenainstaluje:\n"
            "1. Zkontroluj, že máš na disku dost volného místa.\n"
            "2. Restartuj launcher a spusť stahování znovu.\n"
            "3. Když to nepomůže, hru odinstaluj a nainstaluj znovu, uložené pozice zůstanou."
        ),
    },
    {
        "keywords": ["zvuk", "neslys", "hudb", "audio", "mikrofon", "sluchat", "repro"],
        "reply": (
            "Když nejde zvuk:\n"
            "1. Zkontroluj hlasitost ve hře i ve Windows (Mixér hlasitosti).\n"
            "2. Ve Windows nastav správné výstupní zařízení, třeba sluchátka.\n"
            "3. Odpoj a znovu připoj sluchátka, pak hru restartuj."
        ),
    },
    {
        "keywords": ["dekuj", "dik", "funguje to", "uz to jde"],
        "reply": "Rádo se stalo! Kdyby se problém vrátil, napiš nám znovu. Hodně štěstí ve hře.",
    },
]

# ---------- Gemini (umělá inteligence) ----------
# Klíč NIKDY nepatří do kódu ani na GitHub. Na Renderu ho nastav v záložce
# Environment jako proměnnou GEMINI_API_KEY. Bez klíče backend odpovídá
# podle klíčových slov níže, takže stránka funguje pořád.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

SYSTEM_PROMPT = (
    "Jsi technická podpora herního studia VDF Games. Odpovídej česky, přátelsky a stručně: "
    "nejvýš 6 krátkých kroků nebo pár vět, bez nadpisů a bez formátování Markdown. "
    "Pomáhej jen s problémy kolem her: spuštění, pády, výkon a FPS, ovladače, účet, "
    "platby, aktualizace a zvuk. Nikdy nechtěj hesla, čísla karet ani jiné citlivé údaje. "
    "Když dotaz nesouvisí s hrami, slušně řekni, že pomáháš jen s hrami VDF Games. "
    "Když nevíš, popros o víc informací (jaká hra, na čem hraje, co přesně se děje)."
)

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


def ask_gemini(message):
    """Pošle dotaz do Gemini a vrátí text odpovědi (nebo None, když se to nepovede)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
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
    "Díky za dotaz. Abychom ti mohli poradit, napiš nám prosím víc:\n"
    "- o jakou hru jde,\n"
    "- na čem hraješ (PC, konzole, mobil),\n"
    "- co přesně se děje a jestli se objeví chybová hláška."
)


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
        return jsonify({"error": f"dotaz je moc dlouhý (max {MAX_MESSAGE_LENGTH} znaků)"}), 400

    # Render posílá skutečnou adresu návštěvníka v hlavičce X-Forwarded-For
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
    if too_many_requests(ip):
        return jsonify({"error": "moc dotazů najednou, zkus to prosím za minutu"}), 429

    # Výpis do logu (na Renderu ho uvidíš v záložce Logs)
    print(f"[{student}] {email or 'bez e-mailu'}: {message}")

    reply = ask_gemini(message) if GEMINI_API_KEY else None
    if not reply:
        reply = find_reply(message)  # bez klíče nebo při chybě: odpověď podle klíčových slov
    ticket = f"VDF-{random.randint(1000, 9999)}"

    return jsonify({"reply": reply, "ticket": ticket})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
