# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Edge-AI-Education is not a software application with a build/test pipeline — it is an **infrastructure-as-config** project for deploying a fully local (air-gapped, RGPD-compliant), Docker-based AI tutoring stack for a French lycée technical lab (Laboratoire CIEL, Lycée Claude Chappe). There is no compiler, package manager, linter, or test suite. There are three layers to reason about:

1. **Host provisioning** — `infra/setup-debian.sh`: a one-shot bash script that installs Docker, NVIDIA drivers/CUDA, and the NVIDIA Container Toolkit on Debian 13.
2. **Service orchestration** — `infra/docker-compose.yml` (core: Ollama + Open WebUI) and `infra/docker-compose-voice.yml` (optional overlay adding Whisper/Piper STT/TTS via `openedai-speech`, merged on top of the core compose file).
3. **Agent definitions** — `agents/*.modefile`: Ollama `Modelfile`-format definitions (`FROM`, `PARAMETER`, `SYSTEM`) for the three pedagogical tutor personas, loaded into Ollama by `infra/load-models.sh`.

There is no application source code (no Python/JS/etc. to build or unit-test) — changes to this repo are almost always edits to shell scripts, YAML compose files, or Modelfile prompts.

## Commands

```bash
# 1. Provision a fresh Debian 13 host (drivers, Docker, NVIDIA Container Toolkit)
chmod +x infra/setup-debian.sh && sudo ./infra/setup-debian.sh

# 2a. Start the core stack (Ollama + Open WebUI) — text-only, lower VRAM/RAM
docker compose -f infra/docker-compose.yml up -d

# 2b. Start the core stack plus the voice overlay (STT/TTS for the William agent)
docker compose -f infra/docker-compose.yml -f infra/docker-compose-voice.yml up -d

# 3. Interactively pull base models and compile the three tutor agents into Ollama
chmod +x infra/load-models.sh && ./infra/load-models.sh
```

`load-models.sh` must be run with the working directory set to `infra/` (it references Modelfiles via `../agents/...`), or its relative paths will fail. It prompts for a VRAM tier (1: <12GB → 7B models, 2/3: 12-24GB+ → 12B/14B models) and then runs, per agent:
```bash
docker exec -it ollama-server ollama pull <base_model>
docker exec -i ollama-server ollama create <agent_name> -f - < ../agents/<Agent>.modelfile
```
There is no automated test for this flow — validating a change means actually running the compose stack and confirming `ollama list` / Open WebUI show the expected agents.

## Known filename inconsistencies (do not silently "fix" without checking real state)

- The agent definition files on disk are named `agents/Ada.modefile`, `agents/Jarvis.modefile`, `agents/William.modefile` — **`modefile`, missing the `l`** — while `infra/load-models.sh` and the README reference them as `*.modelfile` (correct Ollama spelling). If you touch the loading script or add a new agent, check the actual filename with `ls agents/` rather than assuming; don't "helpfully" rename existing files without confirming with the user, since this may be an intentional typo the user hasn't noticed yet, or the compose/script side may need the fix instead.
- The manifesto file is named `MENIFESTE.md` on disk (typo for "MANIFESTE"), though it's referred to as `MANIFESTE.md` in commit history and prose. Match the actual filename when linking to it.

## Architecture notes specific to this stack

- **Ollama** (`ollama-server`) is the inference engine, GPU-accelerated via the NVIDIA Container Toolkit, configured with `OLLAMA_MAX_LOADED_MODELS=2` so two agents (typically Jarvis + Ada) stay resident in VRAM simultaneously, and `OLLAMA_NUM_PARALLEL=4` for concurrent student requests.
- **Open WebUI** (`open-webui-interface`) is the student/teacher-facing UI, exposed on host port 80, talking to Ollama over the internal Docker network (`OLLAMA_BASE_URL=http://ollama:11434`). RGPD/RAG-relevant knowledge bases (course PDFs, etc.) are attached to an agent through the Open WebUI admin UI, not through this repo's code.
- **Voice overlay** (`docker-compose-voice.yml`) merges additional env vars into the `open-webui` service (pointing its STT/TTS at `openedai-speech`) and adds the `openedai-speech` container (Whisper STT + Piper TTS), GPU-accelerated. Only needed for the William (English DNL role-play) agent's voice mode.
- **Agent personas are prompt-engineered, not fine-tuned**: each `.modefile` sets a low/moderate `temperature`, a `stop "[USER]"` sequence, and a long `SYSTEM` prompt enforcing Socratic/maieutic tutoring (never handing over a direct answer or corrected code block). When editing a persona's behavior, the `SYSTEM` block is the entire behavior surface — there's no other code path to check. Keep new/edited agents consistent with this constraint (guide via questioning, never emit ready-to-paste solutions) since it's the pedagogical thesis of the whole project, not an incidental style choice.
- Adding a new subject-specific agent means: (1) create `agents/<Name>.modelfile` (following the existing `FROM` / `PARAMETER` / `SYSTEM` structure), (2) add a corresponding `pull` + `ollama create` pair in `infra/load-models.sh`, per the pattern documented at the end of the README.

## RAG module (`rag/` directory, `rag` branch)
 
The `rag/` directory adds an **autonomous RAG pipeline**, separate from Open
WebUI's built-in RAG. It is developed on the `rag` branch and merged into `main`
once validated. Unlike the rest of the repo (infra-as-config, no app code), this
directory **does contain Python application code**.
 
### What it does
Reads the PDF corpus in `corpus_ciel/` (repo root, git-ignored — real documents
never leave the machine), chunks it, embeds it with **BGE-M3** (multilingual
FR/EN, dense + sparse in one pass), stores vectors in **ChromaDB** (persistent),
and exposes a **hybrid dense+lexical** search CLI. A teacher-facing FastAPI layer
to bridge Open WebUI is planned but not yet implemented.
 
### Files
- `config.py` — all params, env-driven (`RAG_DEVICE`, `RAG_CORPUS_DIR`, etc.).
- `chunking.py` — filename-convention parser + type-aware chunking. **CLI blocks
  and tables are kept unsplittable** (`_looks_like_cli`, `_looks_like_table_row`).
- `ingest.py` — orchestration + the anti-cheat guardrail.
- `search.py` — hybrid-search test CLI (this is the dev tool, NOT the student UI).
- `Dockerfile` — two targets: `cpu` (default) and `gpu`.
- `docker-compose-rag.yml` — overlay adding the `rag` service (same pattern as
  the voice overlay).
### Critical invariants — do NOT break these
- **Anti-cheat guardrail is load-bearing.** Documents of type `corrige` and
  `coup-de-pouce` (folders `05_corriges/`, `06_coups_de_pouce/`) MUST stay
  excluded from the queryable `ciel` collection. `config.VISIBILITE_RESTREINTE`
  and the visibility filtering in `ingest.py` enforce this. Never "helpfully"
  index restricted docs into the student-visible collection.
- **Double-check on file type.** `parse_filename` cross-validates the folder's
  implied type against the filename suffix and RAISES on mismatch. This is
  intentional (prevents a misfiled corrigé from leaking). Don't soften it to a
  warning.
- **Unsplittable blocks.** CLI command blocks (Cisco IOS, shell) and address
  tables must never be chunk-split. If you touch `chunking.py`, keep the
  `flush()`-on-boundary logic that isolates code/table blocks as standalone
  chunks.
- **Filename convention** is `<activite>_<seq>_<slug>_<type>` where `<seq>` may
  be a full sequence (`sq3`, typical for `cours`) OR sequence+activity
  (`sq2a6`, typical for `tp`/`corrige`). Both are valid — don't "normalize" one
  into the other.
### Running it (from repo root)
```bash
# build
docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml build rag
# ingest (incremental: just re-run after adding docs; --reset to rebuild)
docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml run --rm rag python ingest.py
# test retrieval
docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml run --rm rag python search.py "pool DHCP ?"
```
There is still no automated test suite: validating a change means running
`ingest.py --dry-run` and a few `search.py` queries and eyeballing the retrieved
chunks. CPU embedding is the default; GPU is opt-in via `RAG_BUILD_TARGET=gpu`
`RAG_DEVICE=cuda`.
 
