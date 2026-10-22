# VDF Games – technická podpora

Webová stránka technické podpory pro herní studio VDF Games. Hráč napíše, jaký má problém se hrou, a podpora mu hned odpoví.

**Online:** https://vdf-games-jakub-2026.onrender.com/ (stránku i backend posílá jeden server na Renderu; stav serveru je na `/status`)

Autor: Jakub (4ITE)

## Soubory

- `index.html` – stránka s formulářem a výpisem odpovědí
- `style.css` – vzhled (světlý i tmavý režim)
- `script.js` – odeslání dotazu a vypsání odpovědi
- `app.py` – backend ve Flasku: posílá stránku (`/`) a odpovídá na dotazy (`POST /chat`)
- `requirements.txt` – knihovny pro backend

## Jak backend odpovídá

Když je na serveru nastavený klíč `GEMINI_API_KEY`, `app.py` pošle dotaz do Gemini (model `gemini-3.5-flash-lite`, jde změnit proměnnou `GEMINI_MODEL`) s pokynem odpovídat jako podpora VDF Games.

Bez klíče, nebo když Gemini neodpoví, hledá `app.py` v dotazu klíčová slova (např. „spustit“, „padá“, „FPS“, „ovladač“) a vrátí odpověď k nejbližšímu tématu. Když nic nesedí, poprosí hráče o víc informací.

Ochrana: dotaz může mít nejvýš 1000 znaků a z jedné IP adresy jde poslat nejvýš 8 dotazů za minutu.

Požadavek:

```json
{ "message": "Hra mi padá", "student": "Steinz_Jakub_4ITE", "email": null }
```

Odpověď:

```json
{ "reply": "Pády hry většinou způsobí…", "ticket": "VDF-1234" }
```

## Spuštění na počítači

```bash
pip install -r requirements.txt
python app.py
```

Backend poběží na `http://localhost:8000`. V `script.js` pak nastav `USE_BACKEND = true` a `BACKEND_URL = "http://localhost:8000/chat"`.

## Nasazení na Render

1. New → Web Service → vybrat tento repozitář.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Adresu služby (s `/chat` na konci) vlož do `BACKEND_URL` v `script.js` a nastav `USE_BACKEND = true`.
5. Volitelně: v záložce **Environment** přidej proměnnou `GEMINI_API_KEY` se svým klíčem z Google AI Studia. Klíč nikdy nedávej do kódu ani na GitHub.
