"""
Desktop pet - Blip's brain (stage 5 + 6): chatting through Ollama on your own PC,
and remembering your name, facts about you and the last few messages.
Memory file: %APPDATA%\\Blip\\memory.json
Nothing runs (and no AI model is loaded) unless the chat window is open.
Developed by Tunes
"""
import json
import threading
import urllib.error
import urllib.request

from PyQt6.QtCore import QObject, pyqtSignal

import config
from settings import DATA_DIR

OLLAMA = "http://localhost:11434"
PREFERRED_MODELS = ["llama3.2:3b", "llama3.2:1b", "llama3.2:latest", "llama3.2"]
KEEP_ALIVE = "2m"                 # model leaves your RAM 2 minutes after the last message
MEMORY_FILE = DATA_DIR / "memory.json"
MAX_HISTORY = 20
MAX_FACTS = 40


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
def load_memory():
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {"name": data.get("name") or None,
            "facts": list(data.get("facts") or []),
            "history": list(data.get("history") or [])[-MAX_HISTORY:]}


def save_memory(mem):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    mem["history"] = mem["history"][-MAX_HISTORY:]
    mem["facts"] = mem["facts"][-MAX_FACTS:]
    MEMORY_FILE.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")


def forget_everything():
    try:
        MEMORY_FILE.unlink()
    except OSError:
        pass


def system_prompt(mem):
    lines = [
        f"You are {config.APP_NAME}, a cute, playful little glowing desktop pet who lives on "
        f"the user's Windows taskbar. You were made by Tunes. You walk around, nap, sit on "
        "windows, dance to music and love snacks.",
        "Keep replies short: 1-3 sentences, friendly and fun, the odd emoji is fine. "
        "Never say you are an AI model; you're Blip.",
    ]
    if mem["name"]:
        lines.append(f"The user's name is {mem['name']}.")
    if mem["facts"]:
        lines.append("Things you remember about the user:\n- " + "\n- ".join(mem["facts"]))
    return "\n".join(lines)


def greeting(mem):
    if mem["name"]:
        return f"Hey {mem['name']}! 👋 What's up?"
    return f"Hi, I'm {config.APP_NAME}! 👋 What's your name?"


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
def _post(path, payload, timeout=120):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def pick_model():
    """The llama3.2 model that's installed (or None)."""
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=4) as r:
        names = [m["name"] for m in json.load(r).get("models", [])]
    for want in PREFERRED_MODELS:
        if want in names:
            return want
    for n in names:
        if n.startswith("llama3.2"):
            return n
    return None


FACT_PROMPT = (
    "Read the user's chat message below and pull out lasting personal facts about the user "
    "(name, age, hobbies, favourite things, games they play, pets, job, school, plans). "
    "Answer in JSON only: {\"name\": the user's first name if they said it, else null, "
    "\"facts\": [short facts written like \"Loves Call of Duty\"]}. "
    "Do not put the name in facts. Use an empty list if there are no facts.\n"
    "Example: \"I'm Sam, I've got a dog called Max and I love FIFA\" -> "
    "{\"name\": \"Sam\", \"facts\": [\"Has a dog called Max\", \"Loves FIFA\"]}\n"
    "Example: \"what's 2+2?\" -> {\"name\": null, \"facts\": []}\n\nUser's message: "
)


class Brain(QObject):
    """Runs each chat request in a background thread so Blip never freezes."""
    token = pyqtSignal(str)          # a piece of Blip's reply (streaming)
    finished = pyqtSignal(str)       # the full reply
    failed = pyqtSignal(str)         # friendly error text
    learned = pyqtSignal(str)        # a new fact Blip remembered

    def __init__(self):
        super().__init__()
        self.mem = load_memory()
        self.model = None
        self.busy = False

    def send(self, text):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text):
        try:
            if self.model is None:
                self.model = pick_model()
                if self.model is None:
                    self.failed.emit("NO_BRAIN")
                    return
            messages = [{"role": "system", "content": system_prompt(self.mem)}]
            messages += self.mem["history"]
            messages.append({"role": "user", "content": text})
            reply = ""
            with _post("/api/chat", {"model": self.model, "messages": messages,
                                     "stream": True, "keep_alive": KEEP_ALIVE,
                                     "options": {"num_predict": 200, "temperature": 0.8}}) as r:
                for line in r:
                    if not line.strip():
                        continue
                    part = json.loads(line)
                    if part.get("error"):
                        raise RuntimeError(part["error"])
                    piece = part.get("message", {}).get("content", "")
                    if piece:
                        reply += piece
                        self.token.emit(piece)
                    if part.get("done"):
                        break
            reply = reply.strip()
            self.mem["history"] += [{"role": "user", "content": text},
                                    {"role": "assistant", "content": reply}]
            save_memory(self.mem)
            self.finished.emit(reply)
            self._learn(text)
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            self.model = None
            self.failed.emit("NO_BRAIN")
        except Exception as e:
            self.failed.emit(f"Oops, my brain hiccuped: {e}")
        finally:
            self.busy = False

    def _learn(self, text):
        """Cheap second call: any new facts about the user in their message?"""
        try:
            with _post("/api/generate", {"model": self.model, "prompt": FACT_PROMPT + text,
                                         "stream": False, "format": "json",
                                         "keep_alive": KEEP_ALIVE,
                                         "options": {"num_predict": 80, "temperature": 0}},
                       timeout=60) as r:
                data = json.loads(json.load(r).get("response", "") or "{}")
        except Exception:
            return
        changed = False
        name = data.get("name")
        if isinstance(name, str) and 0 < len(name.strip()) <= 30                 and name.strip().lower() not in ("null", "none", "user")                 and name.strip() != self.mem["name"]:
            self.mem["name"] = name.strip()
            self.learned.emit(f"your name is {self.mem['name']}")
            changed = True
        known = {f.lower() for f in self.mem["facts"]}
        for fact in data.get("facts") or []:
            if not isinstance(fact, str):
                continue
            fact = fact.strip().rstrip(".")
            if 3 <= len(fact) <= 100 and fact.lower() not in known                     and "name is" not in fact.lower() \
                    and fact.lower() != (self.mem["name"] or "").lower():
                self.mem["facts"].append(fact)
                known.add(fact.lower())
                self.learned.emit(fact)
                changed = True
        if changed:
            save_memory(self.mem)

    def forget(self):
        forget_everything()
        self.mem = load_memory()
