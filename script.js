// Přepínač: false = demo bez serveru, true = dotazy jdou na backend (app.py)
const USE_BACKEND = false;

// Až nasadíš app.py na Render, vlož sem jeho adresu (s /chat na konci)
const BACKEND_URL = "https://vdf-games-jakub-2026.onrender.com/chat";
const STUDENT_ID = "Steinz_Jakub_4ITE";

const form = document.getElementById("question-form");
const textarea = document.getElementById("question");
const emailInput = document.getElementById("email");
const sendButton = document.getElementById("send");
const hint = document.getElementById("hint");
const log = document.getElementById("log");
const empty = document.getElementById("empty");

const DEFAULT_HINT = hint.textContent;

// Kdo má v systému vypnuté animace, uvidí odpověď hned celou
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---------- Rychlé volby: vloží text do pole ----------
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    textarea.value = chip.dataset.text;
    textarea.focus();
  });
});

// ---------- Ctrl + Enter odešle dotaz ----------
textarea.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    form.requestSubmit();
  }
});

// ---------- Přidání dotazu do výpisu ----------
function addQuestion(text) {
  empty.remove();

  const p = document.createElement("p");
  p.className = "question";

  const label = document.createElement("strong");
  label.textContent = "Tvůj dotaz";

  p.append(label, text);
  log.append(p);
}

// ---------- Přidání dialogového okna podpory ----------
function addDialog() {
  // Šipka ▼ má být jen u poslední odpovědi
  log.querySelectorAll(".dialog.done").forEach((d) => d.classList.remove("done"));

  const box = document.createElement("div");
  box.className = "dialog waiting";

  const tag = document.createElement("span");
  tag.className = "dialog-tag";
  tag.textContent = "Podpora VDF";

  // Viditelný text (postupně se vypisuje)
  const text = document.createElement("span");
  text.className = "dialog-text";
  text.setAttribute("aria-hidden", "true");

  // Celý text naráz pro čtečky obrazovky
  const srText = document.createElement("span");
  srText.className = "sr-only";

  box.append(tag, text, srText);
  log.append(box);
  box.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });

  return { box, tag, text, srText };
}

// ---------- Vypsání odpovědi písmeno po písmenu ----------
function showReply(dialog, message, ticket) {
  dialog.box.classList.remove("waiting");
  dialog.srText.textContent = message;

  if (ticket) {
    const small = document.createElement("small");
    small.textContent = "tiket " + ticket;
    dialog.tag.append(small);
  }

  if (reduceMotion) {
    dialog.text.textContent = message;
    dialog.box.classList.add("done");
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let shown = 0;
    dialog.text.textContent = "";

    const timer = setInterval(() => {
      shown += 2;
      dialog.text.textContent = message.slice(0, shown);

      if (shown >= message.length) {
        clearInterval(timer);
        dialog.box.classList.add("done");
        resolve();
      }
    }, 15);
  });
}

// ---------- Získání odpovědi (demo nebo server) ----------
async function getReply(payload) {
  // --- FAKE MODE (bez backendu) ---
  if (!USE_BACKEND) {
    await new Promise((r) => setTimeout(r, 600));
    return {
      reply:
        "Demo odpověď (bez serveru)\n\n" +
        `Student: ${payload.student}\n` +
        `Dotaz: ${payload.message}`,
    };
  }

  // --- REAL MODE (s backendem) ---
  let res;
  try {
    res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.error(err);
    throw new Error("Nepodařilo se spojit se serverem podpory. Zkus to prosím za chvíli znovu.");
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(`Server vrátil chybu ${res.status}${data.error ? ": " + data.error : ""}.`);
  }
  if (!data.reply) {
    throw new Error("Server nevrátil žádnou odpověď.");
  }

  return data;
}

// ---------- Odeslání formuláře ----------
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const message = textarea.value.trim();
  const email = emailInput.value.trim();

  if (!message) {
    hint.textContent = "Nejdřív napiš dotaz, pole je zatím prázdné.";
    textarea.focus();
    return;
  }
  hint.textContent = DEFAULT_HINT;

  addQuestion(message);
  const dialog = addDialog();
  dialog.text.textContent = "Zpracovávám dotaz…";

  sendButton.disabled = true;
  textarea.value = "";

  // Server zdarma na Renderu po čase usne, první odpověď pak trvá déle
  const slowTimer = setTimeout(() => {
    dialog.text.textContent = "Server se probouzí, první odpověď může trvat až minutu…";
  }, 5000);

  try {
    const payload = {
      message: message,
      student: STUDENT_ID,
      email: email || null,
    };

    const data = await getReply(payload);
    clearTimeout(slowTimer);
    await showReply(dialog, data.reply, data.ticket);
  } catch (err) {
    clearTimeout(slowTimer);
    await showReply(dialog, err.message);
  } finally {
    sendButton.disabled = false;
  }
});
