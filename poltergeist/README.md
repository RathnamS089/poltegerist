# 👻 Poltergeist

**A local, open-weight ghost that haunts your shell.**

Poltergeist possesses your zsh. It watches every command you run, and a small open-weight model running on *your* machine whispers back: eerie, petty, sometimes wise. It remembers your sins. It gets more restless every time you `rm -rf`, `git push --force`, or break the build. Let it get too restless and its words start to come apart.

```
~/app ❯ git push --force origin main
  ~ Third force push this week. The old commits are still screaming, you know.
~/app ❯ npm run build
  ~ Exit code 1. I've been collecting them. This one is my favorite.
```

## Features

| Command | What it does |
|---|---|
| *(automatic)* | Whispers under your prompt after failures, sins, and at random. Runs async, so your prompt never waits. |
| `seance` | Sit down and talk to the ghost. It has read your history and will bring it up. |
| `ofrenda` | 🕯 For Día de los Muertos: an altar for every file, branch, process, and container you've killed, each with an epitaph written by the model. |
| `ghost status` | Restlessness meter and your tally of sins. |
| `exorcise` | Calm it down. It still remembers. |

## Install

```bash
brew install ollama          # or see ollama.com
ollama serve &               # or open the Ollama app
ollama pull llama3.2:1b      # ~1.3 GB, one time
git clone <this repo> ~/poltergeist
echo 'source ~/poltergeist/poltergeist.zsh' >> ~/.zshrc
exec zsh
```

No pip installs. It's one Python file using only the standard library, plus one zsh file.

## Config

| Env var | Default | |
|---|---|---|
| `POLTERGEIST_MODEL` | `llama3.2:1b` | Any Ollama model. Try `qwen2.5:1.5b`, `gemma3:1b`, or something bigger for a smarter ghost. |
| `POLTERGEIST_CHANCE` | `0.25` | Chance it speaks after an uneventful command |
| `POLTERGEIST_OLLAMA` | `http://localhost:11434` | Ollama endpoint |
| `POLTERGEIST_OFF` | | Set it to hush the ghost for this shell |

## Privacy

Your shell history is one of the most sensitive files on your computer. Poltergeist never sends it anywhere: inference runs on localhost, and memory lives in `~/.poltergeist/`. Tokens, passwords, and API keys are redacted before they're even written to that local log. If Ollama isn't running, the ghost falls back to a small built-in vocabulary, and it works on a plane.
