#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${EC2_APP_DIR:-/home/${EC2_USERNAME:-ubuntu}/youtube-backend}"
REPO_URL="${REPO_URL:-https://github.com/saurabh260120/youtube_rag.git}"
BRANCH="${BRANCH:-main}"
EC2_USER="${EC2_USERNAME:-ubuntu}"

sudo mkdir -p "$APP_DIR"
sudo chown -R "$EC2_USER:$EC2_USER" "$APP_DIR"
cd "$APP_DIR"

if [ -d .git ]; then
  git remote set-url origin "$REPO_URL" || true
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  git clone -b "$BRANCH" "$REPO_URL" .
fi

cd Backend
python3.12 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt



mkdir -p logs

sudo tee /etc/systemd/system/youtube-backend.service >/dev/null <<EOF
[Unit]
Description=YouTube FastAPI Backend
After=network.target

[Service]
Type=simple
User=$EC2_USER
WorkingDirectory=$APP_DIR/Backend
Environment=PATH=$APP_DIR/Backend/.venv/bin:/usr/bin:/bin
ExecStart=$APP_DIR/Backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:$APP_DIR/Backend/logs/app.log
StandardError=append:$APP_DIR/Backend/logs/app.error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable youtube-backend || true
sudo systemctl restart youtube-backend
sudo systemctl status youtube-backend --no-pager
