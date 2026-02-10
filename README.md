# Codex Control Tower (CodexDash)

A local-only dashboard for monitoring tmux/codexctl parallel agents in real time on a headless Raspberry Pi 5.

## Layout
- `backend/` FastAPI + SQLite + WebSocket streamer
- `frontend/` Vite + React + Tailwind + Recharts UI
- `bin/` `codexdash` wrapper for `codexctl` logging
- `scripts/` helpers
- `systemd/` optional service

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

## Run (dev)
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

## Production build + serve
```bash
cd /home/chaithupi5/codexdash/frontend
npm run build
npm run preview
```

Optional systemd service:
```bash
sudo cp /home/chaithupi5/codexdash/systemd/codexdash-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now codexdash-backend
```

## Integration with `codexctl`
Replace your dispatch calls:
```bash
~/bin/codexctl send ...
```
with:
```bash
~/bin/codexdash send ...
```

`codexdash` writes structured NDJSON events to `~/.codexdash/events.ndjson`. The backend tails this file, writes to SQLite (`~/.codexdash/codexdash.db`), and streams events over WebSocket.

Environment overrides:
- `CODEXDASH_DIR` to change base directory (default `~/.codexdash`)
- `CODEXDASH_EVENTS` to override events file path
- `CODEXDASH_DB` to override SQLite path

## Token estimation
- If token usage lines are found in output (e.g. `prompt tokens: 123`), they are stored as exact values.
- Otherwise tokens are estimated with `tiktoken` if available; fallback is `ceil(chars/4)`.

## Troubleshooting
- **tmux session missing**: set `CODEX_TMUX_SESSION=your_session` when running backend.
- **pane IDs stale**: the tmux probe re-resolves by window/pane names each poll.
- **can’t find pane**: ensure pane titles or tmux options `@codexctl_pane_fast` etc. are set.
- **Codex not authenticated**: Doctor panel will show `auth_needed: yes` if login prompt is detected.
- **approvals still appear**: Codex may still require local approvals even in unsafe mode; use tmux to approve.

## API
- `GET /api/health`
- `GET /api/agents`
- `GET /api/jobs?limit=&status=&agent=`
- `GET /api/jobs/{job_id}`
- `GET /api/events?since=`
- `GET /api/doctor`
- `WS /ws/events`
- `POST /api/dispatch`
