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

## Install
### Backend
```bash
cd /home/chaithupi5/codexdash/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Frontend
```bash
cd /home/chaithupi5/codexdash/frontend
npm install
```

## Run (development)
### Backend dev
```bash
cd /home/chaithupi5/codexdash/backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

### Frontend dev
```bash
cd /home/chaithupi5/codexdash/frontend
npm run dev
```

Open:
- `http://<pi-ip>:5173`

## Production build + serve
```bash
cd /home/chaithupi5/codexdash/frontend
npm run build
npm run preview
```

### Optional systemd backend service
```bash
sudo cp /home/chaithupi5/codexdash/systemd/codexdash-backend.service /etc/systemd/system/
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
