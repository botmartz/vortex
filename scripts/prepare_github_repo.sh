#!/usr/bin/env bash
set -e

REPO_DIR="/run/media/soham/D Drive/botmartz/botmartz-engine"
cd "$REPO_DIR"

if [ ! -d ".git" ]; then
  git init
  echo "Initialized git repository in $REPO_DIR"
fi

# Ensure secrets and runtime data are strictly ignored
cat << 'GITIGNORE' > .gitignore
.env
.venv/
__pycache__/
*.pyc
target/
data/
*.db
*.sqlite3*
*.duckdb
*.wal
.DS_Store
dist/
node_modules/
GITIGNORE

git add Cargo.toml Cargo.lock pyproject.toml README.md AGENTS.md configs/ crates/ docs/ python/ scripts/ web/ .gitignore
git status --short | head -n 30
echo "Staged clean open-source repository assets."
