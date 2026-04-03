#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_DIR="${SCRIPT_DIR}/.ai-team/prompts"

SESSION_NAME="${1:-fqxs-team}"
WORK_DIR="${2:-$SCRIPT_DIR}"
ATTACH_MODE="${3:-attach}"

CLAUDE_PROMPT="${PROMPT_DIR}/claude-planner.md"
CODEX_PROMPT="${PROMPT_DIR}/codex-backend.md"
GEMINI_PROMPT="${PROMPT_DIR}/gemini-frontend.md"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 is not installed or not on PATH." >&2
    exit 1
  fi
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 1
  fi
}

require_cmd tmux
require_cmd claude
require_cmd codex
require_cmd gemini

require_file "$CLAUDE_PROMPT"
require_file "$CODEX_PROMPT"
require_file "$GEMINI_PROMPT"

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  if [[ "${ATTACH_MODE}" == "--no-attach" ]]; then
    echo "tmux session already exists: ${SESSION_NAME}"
    exit 0
  fi
  exec tmux attach -t "${SESSION_NAME}"
fi

tmux new-session -d -s "${SESSION_NAME}" -c "${WORK_DIR}"
PANE_CLAUDE="$(tmux list-panes -t "${SESSION_NAME}" -F '#{pane_id}' | head -n 1)"
PANE_CODEX="$(tmux split-window -h -t "${PANE_CLAUDE}" -c "${WORK_DIR}" -P -F '#{pane_id}')"
PANE_GEMINI="$(tmux split-window -h -t "${PANE_CODEX}" -c "${WORK_DIR}" -P -F '#{pane_id}')"

tmux select-layout -t "${SESSION_NAME}" even-horizontal

tmux select-pane -t "${PANE_CLAUDE}" -T "Claude Planner"
tmux select-pane -t "${PANE_CODEX}" -T "Codex Backend"
tmux select-pane -t "${PANE_GEMINI}" -T "Gemini Frontend"

tmux send-keys -t "${PANE_CLAUDE}" "claude \"\$(cat ${CLAUDE_PROMPT})\"" C-m
tmux send-keys -t "${PANE_CODEX}" "codex \"\$(cat ${CODEX_PROMPT})\"" C-m
tmux send-keys -t "${PANE_GEMINI}" "gemini" C-m

if [[ "${ATTACH_MODE}" == "--no-attach" ]]; then
  echo "tmux session created: ${SESSION_NAME}"
  echo "attach with: tmux attach -t ${SESSION_NAME}"
  exit 0
fi

exec tmux attach -t "${SESSION_NAME}"
