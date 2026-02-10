#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$HOME/bin"
install -m 0755 "$HOME/codexctl/codexctl" "$HOME/bin/codexctl"

if ! grep -qs 'export PATH="$HOME/bin:$PATH"' "$HOME/.bashrc"; then
  printf '\nexport PATH="$HOME/bin:$PATH"\n' >> "$HOME/.bashrc"
fi

echo "Installed: $HOME/bin/codexctl"
echo "Open a NEW shell or run: source ~/.bashrc"
