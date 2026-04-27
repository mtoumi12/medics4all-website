# Sharing Core Scribe with collaborators

This is the **handoff checklist** you can send as a link or copy into email or Slack. It assumes they receive the project via **Git clone** or a **zip** of the repository.

---

## 1. What you share

| Share | Do not share |
|--------|----------------|
| The repo (remote URL or zip of the tree) | `core_scribe_mvp/.env` (may contain API keys or internal URLs) |
| `core_scribe_mvp/.env.example` (they copy it to `.env`) | `core_scribe_mvp/medics4all.db` (may contain real visit data) |
| This file (`SHARING.md`) and `README.md` | `core_scribe_mvp/storage/` (uploaded audio may contain PHI) |

If you send a **zip**, exclude `.env`, `*.db`, and `storage/` before zipping, or use a clean clone and delete those paths.

---

## 2. What they install

**Option A — Docker (recommended)**  
- [Docker Desktop](https://docs.docker.com/desktop/) (includes Docker Compose v2)

**Option B — Native Python**  
- Python **3.11+** (3.12 is fine) and `pip`  
- For local LLM on the host: [Ollama](https://ollama.com/) if they use `LLM_PROVIDER=ollama`

---

## 3. Path A: Docker (fewest steps)

**Step 1.** Clone the repository (or unzip it).

**Step 2.** Open a terminal and go to the MVP folder:

```bash
cd core_scribe_mvp
```

**Step 3.** Create a local environment file:

```bash
cp .env.example .env
```

**Step 4.** Edit `.env` and choose a mode:

| Goal | What to set in `.env` |
|------|------------------------|
| **Quick demo, no API keys** | Leave defaults; the UI will show **Demo mode** (canned transcript and SOAP). |
| **Cloud (OpenAI)** | `ASR_PROVIDER=openai`, `LLM_PROVIDER=openai`, and `OPENAI_API_KEY=sk-...`. |
| **Local ASR + Ollama inside Docker** | `ASR_PROVIDER=local`, `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434/v1`, and `OLLAMA_MODEL=llama3.1:8b` (or another model they pull). |

**Step 5.** Start services:

- **Without** the Ollama container (cloud or demo):

```bash
docker compose up --build
```

- **With** the Ollama container:

```bash
docker compose --profile ollama up --build
```

The first time they use Ollama in Docker, in **another** terminal:

```bash
cd core_scribe_mvp
docker compose --profile ollama exec ollama ollama pull llama3.1:8b
```

(Replace the model name if they use something else.)

**Step 6.** Open **http://127.0.0.1:8000** in Chrome or Firefox.

**Step 7.** Optional checks:

- API docs: **http://127.0.0.1:8000/docs**  
- Health JSON: **http://127.0.0.1:8000/api/v1/health** — should show `"status": "ok"` and which ASR/LLM profile is active.

**Step 8.** Stop: press `Ctrl+C` in the terminal where Compose is running, or:

```bash
cd core_scribe_mvp
docker compose down
```

SQLite, uploads, and the Hugging Face cache for faster-whisper live on the **named volume** mounted at `/data` in the container; they persist across `docker compose down` unless someone removes the volume on purpose.

---

## 4. Path B: Native (no Docker)

**Step 1.** `cd core_scribe_mvp` and `cp .env.example .env`, then edit `.env` as in the table above.

**Step 2.** Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows:  .venv\Scripts\activate
pip install -r requirements.txt
```

**Step 3.** If they use **Ollama on the machine** (not in Docker), start the Ollama app or `ollama serve`, then `ollama pull <model>`.

**Step 4.** From `core_scribe_mvp/backend`:

```bash
bash run.sh
```

**Step 5.** Open **http://127.0.0.1:8000** (or the host and port they configured).

More detail: [README.md](README.md) (local profiles, model tuning, troubleshooting).

---

## 5. “Did it work?” checklist

1. The **home page** loads at `http://127.0.0.1:8000`.  
2. **`/api/v1/health`** returns JSON with `"status": "ok"`.  
3. The **header pill** matches their intent: Cloud, Local, Hybrid, or Demo mode.  
4. **Create visit → record audio → wait for Ready** completes (Demo mode should finish quickly with sample content).

---

## 6. One-line summary for Slack

> Clone the repo, `cd core_scribe_mvp`, `cp .env.example .env`, add your OpenAI key for cloud mode (or use local + Ollama per `.env.example`), run `docker compose up --build`, open http://127.0.0.1:8000 — full steps in `SHARING.md`.

---

## 7. If something fails

- **`docker compose` complains about `.env`:** Create it with `cp .env.example .env` (Compose expects `.env` to exist in `core_scribe_mvp/`).  
- **Demo mode when they expected real cloud:** `OPENAI_API_KEY` is missing or wrong; check `/api/v1/health` for `asr_ready` / `llm_ready`.  
- **Ollama errors in Docker:** Ensure they used `--profile ollama`, set `OLLAMA_BASE_URL=http://ollama:11434/v1`, and pulled a model into the **ollama** container (not only on the host).  
- **Microphone blocked:** Use **HTTPS** or **localhost**; some browsers block mic on plain HTTP except on `localhost`.

For architecture and product context, see [`../medics4all_architecture_business.md`](../medics4all_architecture_business.md) in the repo root.
