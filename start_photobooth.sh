#!/usr/bin/env bash
# /home/ian/Desktop/printer/start_photobooth.sh
# Starts: Flask, GPIO listener (as root), Chromium (as user “ian”)

set -euo pipefail

APP_DIR="/home/ian/Desktop/printer"
LOG_DIR="/home/ian/photobooth_logs"
BROWSER_USER="ian"

mkdir -p "${LOG_DIR}"
cd "${APP_DIR}"

# ---------- clean shutdown on SIGTERM/SIGINT ----------
cleanup() {
  echo "Stopping child processes..."
  kill "${FLASK_PID}" "${BTN_PID}" "${CHR_PID}" 2>/dev/null || true
  wait || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ---------- Flask server ----------
/usr/bin/python3 app.py \
  >"${LOG_DIR}/flask.log" 2>&1 &
FLASK_PID=$!

# ---------- GPIO listener ----------
/usr/bin/python3 button_listener.py \
  >"${LOG_DIR}/button.log" 2>&1 &
BTN_PID=$!

# ---------- allow Flask to bind to port 5000 ----------
sleep 3

# ---------- Chromium in kiosk mode as non‑root user ----------
export DISPLAY=:0
sudo -u "${BROWSER_USER}" -H \
  /usr/bin/chromium-browser \
    --kiosk http://localhost:5000 \
    --incognito \
    --disable-infobars \
    --noerrdialogs \
    >"${LOG_DIR}/chromium.log" 2>&1 &
CHR_PID=$!

# ---------- keep the service alive until *any* child exits ----------
wait
