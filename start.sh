#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
NPM_BIN="${NPM_BIN:-npm}"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend_api.log"
WORKER_LOG="$LOG_DIR/worker.log"
WORKER_PID_FILE="$LOG_DIR/worker.pid"

NEXT_HOST="${NEXT_HOST:-0.0.0.0}"
NEXT_PORT="${NEXT_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-}"
KEEP_BACKEND_RUNNING="${KEEP_BACKEND_RUNNING:-0}"
FORCE_RESTART_BACKEND="${FORCE_RESTART_BACKEND:-0}"
FORCE_RESTART_FRONTEND="${FORCE_RESTART_FRONTEND:-0}"
START_WORKER="${START_WORKER:-0}"

BACKEND_PID=""
WORKER_PID=""
STARTED_BACKEND="0"
STARTED_WORKER="0"

log() {
  printf '%s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

die() {
  printf '[XATO] %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Foydalanish:
  ./start.sh
  ./start.sh --check

Ixtiyoriy env o'zgaruvchilar:
  NEXT_HOST=0.0.0.0
  NEXT_PORT=3000
  BACKEND_PORT=8000
  APP_BACKEND_API_BIND_HOST=0.0.0.0
  APP_BACKEND_API_BASE_URL=http://127.0.0.1:8000
  KEEP_BACKEND_RUNNING=1
  FORCE_RESTART_BACKEND=1
  FORCE_RESTART_FRONTEND=1
  START_WORKER=1
EOF
}

dotenv_get() {
  local key="$1"
  local env_file="$ROOT_DIR/.env"
  if [[ ! -f "$env_file" ]]; then
    return 0
  fi

  local line=""
  line="$(grep -E "^${key}=" "$env_file" 2>/dev/null | tail -n 1 || true)"
  line="${line#*=}"
  line="${line%$'\r'}"

  if [[ "${line:0:1}" == '"' && "${line: -1}" == '"' ]]; then
    line="${line:1:${#line}-2}"
  elif [[ "${line:0:1}" == "'" && "${line: -1}" == "'" ]]; then
    line="${line:1:${#line}-2}"
  fi

  printf '%s' "$line"
}

looks_like_windows_path() {
  case "$1" in
    [A-Za-z]:[\\/]*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

resolve_backend_base_url() {
  local configured_url="$1"
  local configured_port="$2"
  if [[ -n "$configured_url" ]]; then
    printf '%s' "${configured_url%/}"
    return 0
  fi
  printf 'http://127.0.0.1:%s' "$configured_port"
}

extract_url_port() {
  local url="$1"
  URL_TO_PARSE="$url" "$PYTHON_BIN" - <<'PY'
import os
from urllib.parse import urlsplit

url = os.environ.get("URL_TO_PARSE", "").strip()
if not url:
    raise SystemExit(1)

parsed = urlsplit(url)
if parsed.port is not None:
    print(parsed.port)
elif parsed.scheme == "https":
    print(443)
else:
    print(80)
PY
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

require_file() {
  local path="$1"
  local message="$2"
  [[ -e "$path" ]] || die "$message"
}

pid_for_port() {
  local port="$1"
  if ! command_exists lsof; then
    return 0
  fi
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

wait_for_pid_exit() {
  local pid="$1"
  local retries="${2:-20}"
  local i
  for ((i=1; i<=retries; i+=1)); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

stop_port_process_if_requested() {
  local label="$1"
  local port="$2"
  local force_restart="$3"
  local pids=()
  local pid=""

  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pid_for_port "$port")
  if [[ "${#pids[@]}" -eq 0 ]]; then
    return 0
  fi

  if [[ "$force_restart" != "1" ]]; then
    die "${label} porti band: ${port}. Qayta ishga tushirish uchun FORCE_RESTART_${label}=1 bilan urinib ko'ring."
  fi

  log "[${label}] Port $port band, mavjud process to'xtatilmoqda..."
  kill "${pids[@]}" >/dev/null 2>&1 || true

  for pid in "${pids[@]}"; do
    if ! wait_for_pid_exit "$pid" 30; then
      die "${label} processi to'xtamadi (PID: $pid, port: $port)"
    fi
  done
}

http_ready() {
  local url="$1"
  START_URL="$url" "$PYTHON_BIN" - <<'PY'
import os
import sys
import urllib.request

url = os.environ["START_URL"]
try:
    with urllib.request.urlopen(url, timeout=1.5) as response:
        raise SystemExit(0 if response.status < 500 else 1)
except Exception:
    raise SystemExit(1)
PY
}

wait_for_backend() {
  local url="$1"
  local retries="${2:-80}"
  local i
  for ((i=1; i<=retries; i+=1)); do
    if http_ready "$url"; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

cleanup() {
  if [[ "$STARTED_WORKER" == "1" && "$KEEP_BACKEND_RUNNING" != "1" && -n "$WORKER_PID" ]]; then
    if kill -0 "$WORKER_PID" >/dev/null 2>&1; then
      log
      log "[CLEANUP] Worker to'xtatilmoqda (PID: $WORKER_PID)..."
      kill "$WORKER_PID" >/dev/null 2>&1 || true
      wait "$WORKER_PID" 2>/dev/null || true
    fi
    rm -f "$WORKER_PID_FILE"
  fi

  if [[ "$STARTED_BACKEND" == "1" && "$KEEP_BACKEND_RUNNING" != "1" && -n "$BACKEND_PID" ]]; then
    if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      log
      log "[CLEANUP] Backend to'xtatilmoqda (PID: $BACKEND_PID)..."
      kill "$BACKEND_PID" >/dev/null 2>&1 || true
      wait "$BACKEND_PID" 2>/dev/null || true
    fi
  fi
}

prepare_local_runtime_paths() {
  local data_dir_value="${DATA_DIR:-$(dotenv_get DATA_DIR)}"
  local excel_dir_value="${EXCEL_DIR:-$(dotenv_get EXCEL_DIR)}"
  local vector_db_value="${VECTOR_DB_PATH:-$(dotenv_get VECTOR_DB_PATH)}"
  local models_dir_value="${MODELS_DIR:-$(dotenv_get MODELS_DIR)}"

  if [[ -z "$data_dir_value" ]] || looks_like_windows_path "$data_dir_value"; then
    export DATA_DIR="$ROOT_DIR/data"
  else
    export DATA_DIR="$data_dir_value"
  fi

  if [[ -z "$excel_dir_value" ]] || looks_like_windows_path "$excel_dir_value"; then
    export EXCEL_DIR="$DATA_DIR/excel_reports"
  else
    export EXCEL_DIR="$excel_dir_value"
  fi

  if [[ -z "$vector_db_value" ]] || looks_like_windows_path "$vector_db_value"; then
    export VECTOR_DB_PATH="$DATA_DIR/vector_db"
  else
    export VECTOR_DB_PATH="$vector_db_value"
  fi

  if [[ -z "$models_dir_value" ]] || looks_like_windows_path "$models_dir_value"; then
    export MODELS_DIR="$ROOT_DIR/models"
  else
    export MODELS_DIR="$models_dir_value"
  fi

  mkdir -p "$DATA_DIR" "$EXCEL_DIR" "$VECTOR_DB_PATH" "$MODELS_DIR"
}

postgres_ready() {
  local dsn="$1"
  APP_POSTGRES_DSN="$dsn" "$PYTHON_BIN" - <<'PY'
import importlib.util
import os
import sys

dsn = os.environ.get("APP_POSTGRES_DSN", "").strip()
if not dsn:
    raise SystemExit(2)

if importlib.util.find_spec("psycopg") is None:
    print("psycopg topilmadi", file=sys.stderr)
    raise SystemExit(3)

try:
    import psycopg

    conn = psycopg.connect(dsn, connect_timeout=2)
    try:
        conn.execute("SELECT 1")
    finally:
        conn.close()
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1)
PY
}

choose_database_backend() {
  local configured_backend="${APP_DB_BACKEND:-$(dotenv_get APP_DB_BACKEND)}"
  local configured_dsn="${APP_POSTGRES_DSN:-$(dotenv_get APP_POSTGRES_DSN)}"

  configured_backend="$(printf '%s' "${configured_backend:-postgres}" | tr '[:upper:]' '[:lower:]')"
  if [[ "$configured_backend" != "postgres" ]]; then
    die "Faqat PostgreSQL qo'llab-quvvatlanadi. APP_DB_BACKEND=postgres bo'lishi shart."
  fi

  if postgres_ready "$configured_dsn" >/dev/null 2>&1; then
    export APP_DB_BACKEND="postgres"
    export APP_POSTGRES_DSN="$configured_dsn"
    return 0
  fi

  die "APP_DB_BACKEND=postgres, lekin PostgreSQL ulanmayapti. SQLite fallback o'chirilgan."
}

bootstrap_local_databases() {
  "$PYTHON_BIN" - <<'PY'
from utils.auth.auth_db import init_auth_db
from utils.database.task_db import init_db

init_auth_db()
init_db()
PY
}

print_banner() {
  log
  log "============================================================"
  log "  JIRA AI Analyzer - Local Startup"
  log "============================================================"
  log
}

trap cleanup EXIT INT TERM

MODE="${1:-run}"
if [[ "$MODE" == "--help" || "$MODE" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "$MODE" != "run" && "$MODE" != "--check" ]]; then
  die "Noma'lum argument: $MODE"
fi

require_file "$PYTHON_BIN" "Virtual environment topilmadi: $PYTHON_BIN"
require_file "$ROOT_DIR/.env" ".env fayl topilmadi. Avval .env ni to'ldiring."
require_file "$FRONTEND_DIR/package.json" "Frontend package.json topilmadi: $FRONTEND_DIR/package.json"
require_file "$FRONTEND_DIR/node_modules" "Frontend dependency topilmadi. Avval 'cd frontend && npm install' ni bajaring."

mkdir -p "$LOG_DIR"
prepare_local_runtime_paths
choose_database_backend

WEBHOOK_EXECUTION_MODE="${APP_WEBHOOK_EXECUTION_MODE:-$(dotenv_get APP_WEBHOOK_EXECUTION_MODE)}"
WEBHOOK_EXECUTION_MODE="${WEBHOOK_EXECUTION_MODE:-inline}"
if [[ "$WEBHOOK_EXECUTION_MODE" == "queue" ]]; then
  START_WORKER="1"
fi

BACKEND_BIND_HOST="${APP_BACKEND_API_BIND_HOST:-$(dotenv_get APP_BACKEND_API_BIND_HOST)}"
BACKEND_BIND_HOST="${BACKEND_BIND_HOST:-0.0.0.0}"

RAW_BACKEND_BASE_URL="${APP_BACKEND_API_BASE_URL:-$(dotenv_get APP_BACKEND_API_BASE_URL)}"
if [[ -z "$BACKEND_PORT" ]]; then
  if [[ -n "$RAW_BACKEND_BASE_URL" ]]; then
    BACKEND_PORT="$(extract_url_port "$RAW_BACKEND_BASE_URL")"
  else
    BACKEND_PORT="8000"
  fi
fi
BACKEND_BASE_URL="$(resolve_backend_base_url "$RAW_BACKEND_BASE_URL" "$BACKEND_PORT")"
BACKEND_ROOT_URL="${BACKEND_BASE_URL%/}/"

export APP_USE_BACKEND_API="true"

print_banner

log "UI  (Next.js)   : http://127.0.0.1:${NEXT_PORT}"
log "API (FastAPI)   : ${BACKEND_BASE_URL}"
log "Mode            : ${WEBHOOK_EXECUTION_MODE}"
log "DB backend      : ${APP_DB_BACKEND}"
log "DATA_DIR        : ${DATA_DIR}"
log "VECTOR_DB_PATH  : ${VECTOR_DB_PATH}"
log "MODELS_DIR      : ${MODELS_DIR}"
log "Backend log     : ${BACKEND_LOG}"
if [[ "$START_WORKER" == "1" ]]; then
  log "Worker log      : ${WORKER_LOG}"
fi
log

log "[PRECHECK] Local bazalar tayyorlanmoqda..."
bootstrap_local_databases
log "[PRECHECK] OK"

if [[ "$MODE" == "--check" ]]; then
  log
  log "[OK] Startup precheck muvaffaqiyatli o'tdi."
  exit 0
fi

stop_port_process_if_requested "BACKEND" "$BACKEND_PORT" "$FORCE_RESTART_BACKEND"

if [[ -n "$(pid_for_port "$BACKEND_PORT")" ]]; then
  log "[API] Backend allaqachon ishlayapti: ${BACKEND_BASE_URL}"
else
  log "[API] Backend ishga tushirilmoqda..."
  nohup env \
    DATA_DIR="$DATA_DIR" \
    EXCEL_DIR="$EXCEL_DIR" \
    VECTOR_DB_PATH="$VECTOR_DB_PATH" \
    MODELS_DIR="$MODELS_DIR" \
    APP_DB_BACKEND="$APP_DB_BACKEND" \
    APP_POSTGRES_DSN="$APP_POSTGRES_DSN" \
    APP_USE_BACKEND_API="$APP_USE_BACKEND_API" \
    APP_WEBHOOK_EXECUTION_MODE="$WEBHOOK_EXECUTION_MODE" \
    "$PYTHON_BIN" -m uvicorn \
      services.webhook.jira_webhook_handler:app \
      --host "$BACKEND_BIND_HOST" \
      --port "$BACKEND_PORT" \
      >>"$BACKEND_LOG" 2>&1 &
  BACKEND_PID="$!"
  STARTED_BACKEND="1"

  if wait_for_backend "$BACKEND_ROOT_URL" 80; then
    log "[API] Backend tayyor bo'ldi (PID: $BACKEND_PID)"
  else
    die "Backend ko'tarilmadi. Logni tekshiring: $BACKEND_LOG"
  fi
fi

if [[ "$START_WORKER" == "1" ]]; then
  if [[ -f "$WORKER_PID_FILE" ]]; then
    existing_worker_pid="$(cat "$WORKER_PID_FILE" 2>/dev/null || true)"
    if [[ -n "$existing_worker_pid" ]] && kill -0 "$existing_worker_pid" >/dev/null 2>&1; then
      WORKER_PID="$existing_worker_pid"
      log "[WORKER] Worker allaqachon ishlayapti (PID: $WORKER_PID)"
    else
      rm -f "$WORKER_PID_FILE"
    fi
  fi

  if [[ -z "$WORKER_PID" ]]; then
    log "[WORKER] Background worker ishga tushirilmoqda..."
    nohup env \
      DATA_DIR="$DATA_DIR" \
      EXCEL_DIR="$EXCEL_DIR" \
      VECTOR_DB_PATH="$VECTOR_DB_PATH" \
      MODELS_DIR="$MODELS_DIR" \
      APP_DB_BACKEND="$APP_DB_BACKEND" \
      APP_POSTGRES_DSN="$APP_POSTGRES_DSN" \
      APP_USE_BACKEND_API="$APP_USE_BACKEND_API" \
      APP_WEBHOOK_EXECUTION_MODE="$WEBHOOK_EXECUTION_MODE" \
      "$PYTHON_BIN" -m services.worker.main \
      >>"$WORKER_LOG" 2>&1 &
    WORKER_PID="$!"
    STARTED_WORKER="1"
    printf '%s' "$WORKER_PID" > "$WORKER_PID_FILE"
    sleep 1

    if kill -0 "$WORKER_PID" >/dev/null 2>&1; then
      log "[WORKER] Worker tayyor bo'ldi (PID: $WORKER_PID)"
    else
      die "Worker ko'tarilmadi. Logni tekshiring: $WORKER_LOG"
    fi
  fi
fi

stop_port_process_if_requested "FRONTEND" "$NEXT_PORT" "$FORCE_RESTART_FRONTEND"

log "[WEB] Next.js portal ishga tushmoqda..."
log

cd "$FRONTEND_DIR"
BACKEND_API_BASE_URL="$BACKEND_BASE_URL" \
NEXT_PUBLIC_BACKEND_API_BASE_URL="$BACKEND_BASE_URL" \
"$NPM_BIN" run dev -- --hostname "$NEXT_HOST" --port "$NEXT_PORT"
