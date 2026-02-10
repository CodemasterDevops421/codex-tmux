# Codex Control Tower (CodexDash)

Production-ready, local-only dashboard for monitoring `tmux`/`codexctl` parallel agents in real time on a headless Raspberry Pi 5.

**What it does**
- Live controller timeline for all `codexctl` dispatches.
- Per-agent status panels (`fast`, `deep`, `test`, `sec`).
- Jobs list with durations, outputs, and token usage (exact or estimated).
- Per-agent chat/transcripts with export.
- Token utilization charts over time.

## Repository Layout
- `backend/` FastAPI + SQLite + WebSocket streamer
- `frontend/` Vite + React + Tailwind + Recharts UI
- `bin/` `codexdash` wrapper for `codexctl`
- `scripts/` helpers
- `systemd/` optional service unit

## Prerequisites
- Python 3.11+
- Node.js 18+ (Node 20 tested)
- `tmux`
- Existing `codexctl` setup in `~/bin/codexctl`

## One-time Setup (any Linux)
```bash
git clone https://github.com/CodemasterDevops421/codex-tmux.git
cd codex-tmux
```

### One-command quickstart (recommended)
```bash
./scripts/quickstart.sh
```

### Install `codexctl`
```bash
mkdir -p ~/bin
cp -a tmux/codexctl/codexctl ~/bin/codexctl
cp -a tmux/codexctl/install.sh ~/bin/codexctl-install.sh
chmod +x ~/bin/codexctl ~/bin/codexctl-install.sh
```

### (Optional) Review tmux notes
```bash
cat tmux/work-tmux/tmux-sugent.md
```

## Install
### Backend
```bash
cd ./backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Frontend
```bash
cd ./frontend
npm install
```

## Run (development)
### Backend dev
```bash
cd ./backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

### Frontend dev
```bash
cd ./frontend
npm run dev
```

Open:
- `http://<pi-ip>:5173`

## Production build + serve
```bash
cd ./frontend
npm run build
npm run preview
```

### Optional systemd backend service
```bash
sudo cp ./systemd/codexdash-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now codexdash-backend
```

## How It Works
### Telemetry bridge
Use `codexdash` instead of `codexctl` when dispatching jobs. It mirrors the call and logs structured events.

```bash
~/bin/codexdash send @fast -- "run tests"
~/bin/codexdash send all --parallel --wait 0 -- "summarize repo"
```

Events are appended to:
- `~/.codexdash/events.ndjson`

The backend tails this file, writes to SQLite (`~/.codexdash/codexdash.db`), and streams events to the UI via WebSocket.

### tmux + Codex architecture (in-depth)
Codex runs inside `tmux` panes created by `codexctl`. CodexDash observes and correlates activity without modifying `tmux`:

**Execution path**
1. You run: `~/bin/codexdash send ...`
2. `codexdash` logs a `dispatch` event and shells out to `~/bin/codexctl send ...`
3. `codexctl` injects the prompt into the target tmux pane(s)
4. Codex runs in each pane and streams output in-place
5. CodexDash continuously `capture-pane`’s output and emits `pane_output` events
6. Backend tails events and updates SQLite + broadcasts to the UI

**Why this works without tmux modifications**
- We rely on `tmux capture-pane` to read the visible buffer.
- We dynamically re-resolve panes every poll to avoid stale IDs.
- We use window names (`fast`, `deep`, `test`, `sec`) or `@codexctl_pane_*` options if present.

**Pane mapping logic**
- **Windows mode**: each agent is a tmux window named `fast`, `deep`, `test`, `sec`
- **Pane mode**: use tmux options `@codexctl_pane_fast`, etc., if set
- **Fallback**: infer from pane title or current command

**Job correlation**
- `codexdash` emits a `dispatch` event with a generated `job_id`.
- `codexctl` injects `JOB:...` markers into pane output.
- The backend extracts `[JOB:...]` from pane output and links those lines to the job.
- This produces per-job transcripts even when Codex prints interleaved output.

**Sub-agent detection**
- If Codex spawns internal sub-agents/tools, it often prints markers like `sub-agent:` or `tool:`.
- CodexDash tags those lines with `sub_agent` for nested thread display.

**Token accounting**
- Exact tokens are parsed if Codex prints them.
- Otherwise estimate: `tiktoken` if available, else `ceil(chars/4)`.

**Operational considerations**
- Large pane buffers can create big `pane_output` events.
- If you want less history, reduce tmux history limit or lower `capture-pane` lines.
- UI updates typically appear within ~250ms of new events.

### tmux discovery
The backend maps agent names to panes every poll:
- **windows mode**: windows named `fast`, `deep`, `test`, `sec`
- **pane mode**: uses `@codexctl_pane_*` tmux options if present
- fallback by pane title or current command

### Token estimation
- If exact token usage lines are found in output, they are stored as exact values.
- Otherwise tokens are estimated with `tiktoken` if available; fallback is `ceil(chars/4)`.

## Environment Overrides
- `CODEXDASH_DIR` change base directory (default `~/.codexdash`)
- `CODEXDASH_EVENTS` override events file path
- `CODEXDASH_DB` override SQLite DB path
- `CODEX_TMUX_SESSION` override tmux session name (default `codexctl`)

## API
- `GET /api/health`
- `GET /api/agents`
- `GET /api/jobs?limit=&status=&agent=`
- `GET /api/jobs/{job_id}`
- `GET /api/events?since=`
- `GET /api/doctor`
- `WS /ws/events`
- `POST /api/dispatch`

## Troubleshooting
- **Frontend doesn’t load**
  - Ensure `npm run dev` is running.
  - Check: `ss -lntp | grep 5173`
- **Backend not responding**
  - Ensure `uvicorn` is running.
  - Check: `curl http://127.0.0.1:8090/api/health`
- **tmux session missing**
  - Start: `~/bin/codexctl up --agents "fast,deep,test,sec" --windows --noattach`
  - Or set `CODEX_TMUX_SESSION`.
- **Pane IDs stale**
  - The probe re-resolves by window/pane names each poll.
- **Codex not authenticated**
  - Doctor panel shows `auth_needed: yes` if login prompts are detected.
- **Jobs stuck in “running”**
  - `codexctl` panes may still be processing; capture output in tmux.

## Security Notes
- No cloud dependencies required.
- Dashboard is LAN-friendly; WAN access requires router port forwarding and is not recommended without auth and TLS.

## License
Local project, internal use. See `LICENSE.txt` if present.
