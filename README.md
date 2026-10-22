# VDF Games – technická podpora

Webová stránka technické podpory pro herní studio VDF Games. Hráč napíše, jaký má problém se hrou, a podpora mu hned odpoví.

Autor: Jakub (4ITE)

## Soubory

- `index.html` – stránka s formulářem a výpisem odpovědí
- `style.css` – vzhled (světlý i tmavý režim)
- `script.js` – odeslání dotazu a vypsání odpovědi
- `app.py` – backend ve Flasku, endpoint `POST /chat`
- `requirements.txt` – knihovny pro backend

## Jak backend odpovídá

`app.py` hledá v dotazu klíčová slova (např. „spustit“, „padá“, „FPS“, „ovladač“) a vrátí odpověď k nejbližšímu tématu. Když nic nesedí, poprosí hráče o víc informací.

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
