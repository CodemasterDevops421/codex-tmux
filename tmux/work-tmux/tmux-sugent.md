RFC: tmux Control Channel for Sub-Agent CLIs
===========================================

Status
------
- Status: Draft
- Owner: platform agents
- Target: Any LLM session driving another CLI-based agent (e.g., Codex) through tmux

Context
-------
We often use tmux to host a "primary" pane and a "sub-agent" pane running an LLM CLI. This document defines a safe, repeatable protocol for sending prompts, submitting them, and harvesting output so we do not mis-trigger the sub-agent (e.g., by submitting the wrong prefilled prompt).

Scope and Assumptions
---------------------
- You are inside the same tmux session as the sub-agent pane.
- Pane target examples use `%1`; adjust for your layout.
- The sub-agent CLI (Codex) pre-fills its prompt (e.g., "Write tests for @filename") and only submits when it receives a real Enter key. Carriage returns (C-m) or linefeeds (C-j) typed via `tmux send-keys` do not submit.
- `tmux capture-pane` is available for readback.
- Model selection: by default, do not force a model flag. If explicitly requested, launch the sub-agent with `-m <model>` (e.g., `codex -m gpt-5.1-codex-mini`); otherwise, rely on the CLI default.
- Reasoning effort flags must be compatible with the chosen model; if a profile defaults to an unsupported effort (e.g., `xhigh` on `gpt-5.1-codex-mini`), explicitly select a supported effort (low/medium/high) or avoid overriding it. Some wrappers may still show an unsupported default in the banner; override with `--config model_reasoning_effort=<value>` (e.g., `--config model_reasoning_effort=high`) when launching.

Effort Compatibility (known)
----------------------------
- `gpt-5.1-codex-mini`: supports `low`, `medium`, `high` (not `xhigh`).
- `gpt-5.1-codex-max`: supports `low`, `medium`, `high`, `xhigh` (default profile shows xhigh).
- If unsure, probe with a harmless call to see allowed values (the 400 error lists them), e.g.:
  - `codex exec --skip-git-repo-check -m gpt-5.1-codex-mini --config model_reasoning_effort=xhigh "ping"`
  - Adjust the effort to one of the suggested values and retry.

Protocol Overview
-----------------
1) Create/attach sub-agent pane (within the same session)
   - From the existing session, split the current window (`tmux split-window -h "codex"` or run the relevant CLI). Do **not** start a brand-new tmux session—launch the sub-agent in a fresh pane of your current session so it shares context with the controller pane.

2) Identify the target pane id
   - Run `tmux list-panes` and note the pane id of the sub-agent (do not assume `%1`; e.g., new pane may be `%2`).
   - Use that id for all `tmux send-keys` and `tmux capture-pane` calls.

3) Observe without mutation
   - `tmux capture-pane -p -t <id>`

4) Submit a prompt (safe pattern, single shell invocation)
   - Clear the input line to avoid submitting the prefill:
     - `tmux send-keys -t <id> Home C-k`
   - Type the prompt literally (no key interpretation) and submit Enter as its own send-keys, all within one shell call. A tiny delay before Enter can help avoid immediate-paste misreads:
     ```
     { tmux send-keys -t <id> Home C-k; \
       tmux send-keys -t <id> -l "your prompt here"; \
       sleep 0.1; \
       tmux send-keys -t <id> Enter; }
     ```
   - Do not re-send the prompt if it’s already staged—only send Enter to submit it.

5) Poll for state and completion
   - After submitting, poll with captures until a response arrives:
     ```
     tmux capture-pane -p -t <id>
     sleep 0.2; tmux capture-pane -p -t <id>
     sleep 0.5; tmux capture-pane -p -t <id>
     sleep 1;   tmux capture-pane -p -t <id>
     sleep 5;   tmux capture-pane -p -t <id>
     ```
   - What "working" looks like:
     - The prompt you submitted appears earlier in the pane, followed by a line such as `• Working (0s • esc to interrupt)` or `• Sending Enter key (Xs • esc to interrupt)`; this means the CLI received Enter and is processing.
     - The current prompt line may show a different suggestion (the prefill); ignore it while the working line is present.
   - What completion looks like:
     - A boxed banner like `─ Worked for 8s ────────────────────────────────────────────────` (or similar) appears above the response text. This means the LLM returned output.
   - What failure to submit looks like:
     - Your prompt is still sitting at the bottom prompt with no `Working`/`Sending Enter key` line and no `Worked for` banner. Resend Enter (separately) after clearing the line.

6) Read back output
   - Use `tmux capture-pane -p -t <id>` (optionally with `tail`) after the `Working` line disappears and a `Worked for ...` banner appears.

Observed run (pane %2 example)
------------------------------
- Discovered panes with `tmux list-panes` and targeted the new Codex pane `%2`.
- Cleared the prefill with `Home C-k`, sent `Test prompt: say hello from Codex in this pane.` using `-l`, then a separate `Enter`.
- Saw `─ Worked for 6s ──` and the response `Hello from Codex in this pane!`, then the prompt returned to idle.
- Repeated with `Second attempt prompt: say hello from Codex.` and saw `─ Worked for 13s ──` followed by `Hello from Codex!`.

Critical Behaviors to Remember
------------------------------
- Do NOT rely on `C-m` or `C-j` to submit; they only insert newlines for Codex. A separate `tmux send-keys ... Enter` is required.
- If you use `tmux send-keys -l ... Enter` in one call, the word "Enter" will be typed literally because `-l` forces literal characters. Keep Enter in its own call.
- The CLI prefill is live: hitting Enter on an empty line will submit whatever is preloaded (e.g., `Write tests for @filename`). Always clear before sending.
- `C-u` may not clear the Codex input buffer. Use `Home C-k` to remove the line reliably.
- Verify prior sends: if you do not see a `Worked for ...` banner and do not see `Working`, your prompt likely was not submitted; resend Enter. If you see `Working`, continue polling until it disappears and a `Worked for ...` banner arrives.
- When a multi-part command is sent and captured immediately, scrollback may include prior runs; watch the most recent prompt at the bottom to confirm what was actually submitted.

Common Tasks
------------
- Check pane IDs: `tmux list-panes`
- Send multi-line content: send one line at a time with separate `-l` calls, then a final Enter.
- Interrupt a hanging request: send `tmux send-keys -t <id> C-c` (if the sub-agent supports it) or restart the pane.

Example One-Liner (submit + captures, single shell call)
-------------------------------------------------------
```
{ tmux send-keys -t <id> Home C-k; \
  tmux send-keys -t <id> -l "Summarize the current backlog and risks."; \
  sleep 0.1; \
  tmux send-keys -t <id> Enter; \
  tmux capture-pane -p -t <id>; \
  sleep 0.2; tmux capture-pane -p -t <id>; \
  sleep 0.5; tmux capture-pane -p -t <id>; \
  sleep 1;   tmux capture-pane -p -t <id>; \
  sleep 5;   tmux capture-pane -p -t <id>; }
```

Operational Checklist
---------------------
- [ ] Confirm target pane id via `tmux list-panes` (do not assume `%1`).
- [ ] Clear the prefilled prompt (`Home C-k`).
- [ ] Send prompt with `-l`.
- [ ] Submit with separate Enter.
- [ ] If the prompt is already typed, do NOT retype—just send Enter.
- [ ] Poll captures until you either see `Working` (in progress) or a `Worked for ...` banner (complete).
- [ ] Review bottom-most prompt/output to confirm the request that actually ran.
