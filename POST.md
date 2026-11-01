---
title: Poltergeist — an open-weight ghost that haunts your terminal
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

**Poltergeist** possesses your zsh. A small open-weight model running locally watches every command you type and whispers back under your prompt. It gets restless when you sin (`rm -rf`, `git push --force`, `kill -9`, `curl | sh`), it remembers how many times you've done it, and once it's restless enough its words literally start to glitch apart.

It also has two rituals:

- **`seance`**: a conversation with the ghost, which has read your shell history and *will* bring up that thing you did at 2am.
- **`ofrenda`**: for Día de los Muertos, an altar for everything you've deleted: files, branches, processes, containers. Each one gets an epitaph from the model. `node_modules` finally gets the send-off it deserves.

<!-- TODO: add 2–3 real screenshots / a short terminal recording -->

## Demo

<!-- TODO: asciinema or video link -->

## Code

{% github RathnamS089/poltegerist %}

## How I Built It

- **Model:** `llama3.2:1b` via **Ollama** (swappable with one env var). A 1B model is plenty for one creepy sentence and answers in about a second on a laptop.
- **Zero dependencies:** one stdlib-only Python file that talks to Ollama's local HTTP API, plus one zsh file.
- **Async haunting:** the zsh `precmd` hook spawns the ghost in a background process and registers the output fd with `zle -F`. Your prompt returns instantly, and the whisper drifts in above it when the model finishes. The ghost never slows you down. It just *appears*.
- **Memory and mood:** every command is logged locally with its exit code and a "sin" classification. A restlessness score rises with sins and failures and decays with good behavior. It picks the ghost's persona (drowsy → teasing → poltergeist → full possession) and the intensity of the glitch.
- **Graceful haunting:** if the model is down, a built-in vocabulary takes over, so the ghost works with the internet *and* Ollama off.

## Why Does Open Innovation Matter?

Your shell history is one of the most sensitive files on your machine: hostnames, internal paths, half-typed passwords, tokens pasted into `export`. A terminal ghost backed by a closed API would mean streaming **every command you ever type** to someone else's server. That's not a ghost, it's a keylogger with a personality.

With an open-weight model on localhost:
- **Nothing leaves the laptop.** (Secrets get redacted even from the *local* log.)
- **It costs nothing per whisper.** A hook that fires on every command would be a real bill on a metered API.
- **Latency is local.** A 1B model on Apple Silicon replies faster than a round trip to most APIs.
- **You own the ghost.** Swap in a bigger model for a smarter haunting, or fine-tune your own.

## The Spirit of It

<!-- TODO: the first time it said something that actually made you jump -->
