#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu 22.04 arm64 EC2 (t4g.large) for ag-webGL.
#
# Run ONCE, from the repo root, after `git clone`. Idempotent -- safe to re-run.
#
#   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -    # done below
#   ./scripts/ec2-bootstrap.sh
#
# Companion runbook: /Users/eddie/.claude/plans/i-want-to-make-nested-hennessy.md

set -euo pipefail

if [ ! -f pyproject.toml ] || [ ! -d frontend ]; then
  echo "Run from the ag-webGL repo root (where pyproject.toml and frontend/ live)." >&2
  exit 1
fi

echo "==> 1/5 apt packages"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  python3.11 python3.11-venv python3.11-dev \
  git tmux build-essential curl ca-certificates

echo "==> 2/5 node 20 (NodeSource)"
if ! command -v node >/dev/null || [ "$(node --version | cut -dv -f2 | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
node --version
npm --version

echo "==> 3/5 4GB swapfile (helps the Next build on an 8GB box)"
if [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  fi
fi
free -h

echo "==> 4/5 backend venv + dependencies"
if [ ! -d .venv ]; then
  python3.11 -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"

echo "==> 5/5 frontend npm install (~3 min)"
( cd frontend && npm install )

cat <<'EOF'

==============================================================================
  Bootstrap complete.
==============================================================================

Next:

  1.  Add your API key
        cp .env.example .env
        nano .env                  # paste ANTHROPIC_API_KEY=sk-ant-...

  2.  Build the frontend (~10-15 min on t4g.large; watch swap with `vmstat 5`)
        cd frontend && npm run build && cd -

  3.  Run both servers in tmux
        tmux new -s scene
        # Pane 1:
        .venv/bin/uvicorn agent.main:app --host 127.0.0.1 --port 8000
        # Ctrl-B " to split, then in pane 2:
        cd frontend && npm run start -- --hostname 127.0.0.1 --port 3000

  4.  From your Mac (new local terminal)
        ssh -i KEY.pem -N \
            -L 3000:127.0.0.1:3000 \
            -L 8000:127.0.0.1:8000 \
            ubuntu@EC2_PUBLIC_DNS

  5.  Browser -> http://localhost:3000

==============================================================================
EOF
