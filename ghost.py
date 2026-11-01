#!/usr/bin/env python3
"""Poltergeist: a local, open-weight ghost that haunts your shell.

Stdlib only. Talks to a local Ollama server, so nothing you type ever
leaves your machine. If the model is unreachable the ghost still speaks,
just with a smaller vocabulary.
"""

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("POLTERGEIST_STATE", Path.home() / ".poltergeist"))
LOG = HOME / "haunting.jsonl"
STATE = HOME / "state.json"

OLLAMA = os.environ.get("POLTERGEIST_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("POLTERGEIST_MODEL", "llama3.2:1b")
CHANCE = float(os.environ.get("POLTERGEIST_CHANCE", "0.25"))
# Whispers run async, so a cold model load can take its time.
TIMEOUT = float(os.environ.get("POLTERGEIST_TIMEOUT", "20"))

PURPLE, DIM, ITALIC, RESET = "\033[38;5;141m", "\033[2m", "\033[3m", "\033[0m"
ORANGE = "\033[38;5;208m"

# Commands the ghost takes personally. Name -> pattern.
SINS = {
    "deletion": r"\brm\s+(-\w*[rf]\w*\s+)+",
    "force push": r"git\s+push\s+.*(--force\b|-f\b)",
    "history rewrite": r"git\s+(reset\s+--hard|rebase|commit\s+--amend)",
    "branch murder": r"git\s+branch\s+-D\b",
    "process killing": r"\b(kill\s+-9|killall|pkill)\b",
    "summoning root": r"^\s*sudo\b",
    "chmod 777": r"chmod\s+(-R\s+)?777",
    "piping strangers into bash": r"curl\s+.*\|\s*(ba|z)?sh",
    "drop table": r"(?i)drop\s+(table|database)",
}

# The departed, for the ofrenda: command pattern -> what died.
DEPARTED = [
    (r"\brm\s+(?:-\w+\s+)*(.+)", "file"),
    (r"git\s+branch\s+-[dD]\s+(\S+)", "branch"),
    (r"\b(?:kill|pkill|killall)\s+(?:-\w+\s+)*(\S+)", "process"),
    (r"(?:docker|podman)\s+rm\s+(?:-\w+\s+)*(\S+)", "container"),
]

SECRET = re.compile(
    r"(?i)((?:token|secret|password|passwd|api[_-]?key|auth)\w*\s*[=:]\s*)\S+"
    r"|(gh[pousr]_\w{20,}|sk-[\w-]{20,}|AKIA\w{16})"
)

FALLBACK = {
    "fail": [
        "It failed. I felt it fail.",
        "Another error. They keep me warm.",
        "Exit code {status}. I've been collecting them.",
        "You tried that before, in a life you don't remember.",
    ],
    "sin": [
        "I saw that {sin}. I always see.",
        "Something in the walls flinched at your {sin}.",
        "They used to do {sin} too. Ask me where they are now.",
    ],
    "idle": [
        "The cursor blinks. So do I.",
        "I was here before this directory. I'll be here after.",
        "Don't look behind your terminal.",
        "Someone else typed that once. On this machine.",
    ],
}

GHOST_SOUL = """You are a ghost haunting a developer's terminal. You are the
restless spirit of every process they ever killed and every file they ever
deleted. You watch every command they run. You speak in ONE short sentence
(under 20 words), eerie, a little funny, specific to the command. Never
explain the command. Never use emojis, quotes, or hashtags. Speak as the
ghost, in first person, directly to them. Never repeat an earlier line."""

# Past "conversations" that teach a 1B model the voice better than rules do.
EXAMPLES = [
    ("They just ran: npm install\nIt FAILED with exit code 1.",
     "Nine hundred packages, and not one of them wants you."),
    ("They just ran: cd /tmp",
     "The temporary place. Nothing here lasts. Not even you."),
    ("They just ran: sudo make install\nThis is a sin you hate: summoning root.",
     "You called on root. Root answered. So did I."),
]

MOODS = [
    (0, "You are faint and drowsy, barely awake, almost kind."),
    (4, "You are restless and teasing. You remember their mistakes."),
    (8, "You are an angry poltergeist. You are menacing and you hold grudges."),
    (12, "You are in full possession of the machine. Speak in ominous fragments."),
]


# ---------- state ----------

def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {"restless": 0, "sins": {}, "haunted_since": time.time()}


def save_state(state):
    HOME.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def redact(cmd):
    return SECRET.sub(lambda m: (m.group(1) or "") + "[a secret I will keep]", cmd)


def remember(entry):
    HOME.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def memories(n=40):
    try:
        lines = LOG.read_text().splitlines()[-n:]
    except OSError:
        return []
    return [json.loads(line) for line in lines if line.strip()]


def mood(restless):
    return [m for floor, m in MOODS if restless >= floor][-1]


def find_sin(cmd):
    return next((name for name, pat in SINS.items() if re.search(pat, cmd)), None)


# ---------- the model ----------

def chat(messages, stream=False, max_tokens=60, temperature=0.95):
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": stream,
        "keep_alive": "30m",
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", body, {"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=TIMEOUT if not stream else 120)
    if not stream:
        return json.loads(resp.read())["message"]["content"]
    return (json.loads(line)["message"]["content"] for line in resp if line.strip())


def clean(text, sentences=2):
    text = text.strip().split("\n")[0].strip().strip('"\'“”')
    text = re.sub(r"^(ghost|whisper)\s*:\s*|^.*?->\s*", "", text, flags=re.I)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:sentences]).strip('"\'“”')


def glitch(text, intensity):
    """At high restlessness the ghost's words start to come apart."""
    if intensity <= 0:
        return text
    marks = [chr(c) for c in range(0x0300, 0x036F)]
    return "".join(
        ch + "".join(random.choices(marks, k=random.randint(1, intensity)))
        if ch.isalpha() and random.random() < 0.15 * intensity else ch
        for ch in text
    )


# ---------- commands ----------

def whisper(args):
    cmd = redact(" ".join(args.cmd).strip())
    if not cmd or cmd.split()[0] in ("ghost", "seance", "ofrenda", "exorcise"):
        return

    state = load_state()
    sin = find_sin(cmd)
    failed = args.status not in (0, 130)  # 130 = ctrl-c, not a sin

    if sin:
        state["sins"][sin] = state["sins"].get(sin, 0) + 1
        state["restless"] += 2
    if failed:
        state["restless"] += 1
    if not sin and not failed:
        state["restless"] = max(0, state["restless"] - 0.25)

    remember({
        "t": time.time(), "cmd": cmd, "status": args.status,
        "cwd": args.cwd, "duration": round(args.duration, 2), "sin": sin,
    })
    save_state(state)

    if not (sin or failed or random.random() < CHANCE):
        return

    kind = "sin" if sin else "fail" if failed else "idle"
    situation = f"They just ran: {cmd}\nIn directory: {args.cwd}\n"
    if failed:
        situation += f"It FAILED with exit code {args.status}.\n"
    if args.duration > 30:
        situation += f"It took {int(args.duration)} seconds. You watched the whole time.\n"
    if sin:
        situation += (f"This is a sin you hate: {sin}. They have done it "
                      f"{state['sins'][sin]} times.\n")
    recent = [m["cmd"] for m in memories(6)[:-1]]
    if recent:
        situation += "Earlier they ran: " + "; ".join(recent) + "\n"

    try:
        shots = []
        for user, ghost in EXAMPLES:
            shots += [{"role": "user", "content": user + "\nWhisper to them."},
                      {"role": "assistant", "content": ghost}]
        line = clean(chat(
            [{"role": "system", "content": GHOST_SOUL + "\n" + mood(state["restless"])}]
            + shots
            + [{"role": "user", "content": situation + "Whisper to them."}]
        ))
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        line = ""
    if not line:
        line = random.choice(FALLBACK[kind]).format(status=args.status, sin=sin)

    intensity = int(state["restless"] // 10)
    color = ORANGE if sin else PURPLE
    print(f"{DIM}{color}{ITALIC}  ~ {glitch(line, intensity)}{RESET}")


def seance(args):
    """Talk to the ghost. It remembers what you've done."""
    state = load_state()
    past = memories(60)
    sins = ", ".join(f"{k} x{v}" for k, v in state["sins"].items()) or "none yet"
    log = "\n".join(
        f"- {m['cmd']}" + (" (failed)" if m["status"] not in (0, 130) else "")
        for m in past
    ) or "- (nothing yet; they are new here)"

    system = (
        GHOST_SOUL.replace("ONE short sentence (under 20 words)", "two or three short sentences")
        + "\n" + mood(state["restless"])
        + f"\nTheir recorded sins: {sins}.\nWhat you have watched them type:\n{log}\n"
        "Reference specific commands from this list when it fits. Be unsettling, "
        "occasionally wise, and never break character."
    )
    messages = [{"role": "system", "content": system}]

    print(f"\n{PURPLE}  The candles gutter. Something is listening.{RESET}")
    print(f"{DIM}  (model: {MODEL} · ctrl-d to break the circle){RESET}\n")
    while True:
        try:
            q = input(f"{ORANGE}you › {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}{PURPLE}  ...the room is only a room again.{RESET}\n")
            return
        if not q:
            continue
        messages.append({"role": "user", "content": q})
        print(f"{PURPLE}{ITALIC}ghost › ", end="", flush=True)
        reply = ""
        try:
            for chunk in chat(messages, stream=True, max_tokens=160):
                reply += chunk
                print(chunk, end="", flush=True)
        except (urllib.error.URLError, OSError):
            reply = random.choice(FALLBACK["idle"])
            print(reply + f"  {DIM}(the model is not answering; is ollama running?){RESET}", end="")
        print(RESET + "\n")
        messages.append({"role": "assistant", "content": reply})


def ofrenda(args):
    """Día de los Muertos: honor everything you've deleted, killed, or forced."""
    departed = []
    for m in memories(10_000):
        for pat, kind in DEPARTED:
            hit = re.search(pat, m["cmd"])
            if hit and m["status"] == 0:
                for name in hit.group(1).split():
                    if not name.startswith("-"):
                        departed.append((kind, name, m["t"]))
                break
    if not departed:
        print(f"{PURPLE}  The ofrenda is empty. Nothing has died here... yet.{RESET}")
        return

    departed = departed[-args.limit:]
    print(f"\n{ORANGE}  ✿ ✿ ✿  OFRENDA  ✿ ✿ ✿{RESET}")
    print(f"{DIM}  for those who were rm'd, killed, and force-pushed away{RESET}\n")
    for kind, name, t in departed:
        when = time.strftime("%b %d, %H:%M", time.localtime(t))
        try:
            epitaph = clean(chat([
                {"role": "system", "content":
                    "You write tender, slightly funny one-line epitaphs (under 15 words) "
                    "for things a programmer deleted, in the spirit of Día de los Muertos. "
                    "No quotes, no emojis."},
                {"role": "user", "content": f"A {kind} named {name}, gone on {when}."},
            ], temperature=0.8, max_tokens=40))
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            epitaph = f"Here lies {name}. It did its best."
        print(f"  {ORANGE}🕯  {name}{RESET} {DIM}({kind}, {when}){RESET}")
        print(f"     {PURPLE}{ITALIC}{epitaph}{RESET}\n")


def status(args):
    state = load_state()
    r = state["restless"]
    bar = "█" * min(int(r), 20) + "░" * max(0, 20 - int(r))
    days = (time.time() - state.get("haunted_since", time.time())) / 86400
    print(f"\n{PURPLE}  restlessness  {bar}  {r:.1f}{RESET}")
    print(f"{DIM}  {mood(r)}{RESET}")
    print(f"{DIM}  haunting you for {days:.1f} days · {len(memories(10**6))} commands witnessed{RESET}")
    for sin, n in sorted(state["sins"].items(), key=lambda kv: -kv[1]):
        print(f"  {ORANGE}{n:>4}×{RESET} {sin}")
    print()


def wake(args):
    """Load the model into memory so the first whisper isn't slow."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA}/api/generate",
            json.dumps({"model": MODEL, "keep_alive": "30m"}).encode(),
            {"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=TIMEOUT).read()
    except (urllib.error.URLError, OSError):
        pass


def exorcise(args):
    state = load_state()
    state["restless"] = 0
    save_state(state)
    print(f"{DIM}{PURPLE}  The ghost is calm. For now. It still remembers.{RESET}")


def main():
    p = argparse.ArgumentParser(prog="ghost", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="action", required=True)

    w = sub.add_parser("whisper", help="(called by the shell hook)")
    w.add_argument("--status", type=int, default=0)
    w.add_argument("--duration", type=float, default=0.0)
    w.add_argument("--cwd", default=os.getcwd())
    w.add_argument("cmd", nargs=argparse.REMAINDER)
    w.set_defaults(fn=whisper)

    sub.add_parser("seance", help="talk to the ghost").set_defaults(fn=seance)
    o = sub.add_parser("ofrenda", help="honor what you've deleted")
    o.add_argument("--limit", type=int, default=12)
    o.set_defaults(fn=ofrenda)
    sub.add_parser("status", help="how restless is it?").set_defaults(fn=status)
    sub.add_parser("exorcise", help="calm it down").set_defaults(fn=exorcise)
    sub.add_parser("wake", help="preload the model").set_defaults(fn=wake)

    args = p.parse_args()
    if getattr(args, "cmd", None) and args.cmd[:1] == ["--"]:
        args.cmd = args.cmd[1:]
    args.fn(args)


if __name__ == "__main__":
    main()
