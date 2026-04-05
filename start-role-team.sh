#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-3-pro-preview}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_DIR="${SCRIPT_DIR}/.ai-team/prompts"
WORK_DIR="${SCRIPT_DIR}"
RESUME_MODE=0
AUTO_MODE=0
LEGACY_MODE=0
SESSION_NAME="fqxs-team"
ATTACH_MODE="attach"

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

usage() {
  cat <<'EOF'
Usage:
  ./start-role-team.sh [workdir] [-r|--resume] [-a|--auto] [--legacy] [--no-attach]

Default behavior:
  Start the fqxs collaboration team through CCB using .ccb/ccb.config.

Options:
  -r, --resume     Resume previous CCB context
  -a, --auto       Start CCB in auto permission mode
  --legacy         Use the old plain tmux launcher instead of CCB
  --no-attach      Legacy mode only; create the tmux session without attaching
  -h, --help       Show this help message
EOF
}

tmux_session_has_ccb_markers() {
  local session_name="$1"

  if ! tmux has-session -t "${session_name}" 2>/dev/null; then
    return 1
  fi

  tmux list-panes -t "${session_name}" -F '#{pane_title}' 2>/dev/null | grep -q 'CCB-'
}

cleanup_stale_tmux_session() {
  local session_name="$1"

  if ! tmux has-session -t "${session_name}" 2>/dev/null; then
    return
  fi

  if tmux_session_has_ccb_markers "${session_name}"; then
    return
  fi

  echo "Removing stale non-CCB tmux session: ${session_name}"
  tmux kill-session -t "${session_name}"
}

ensure_tmux_for_ccb() {
  local relaunch=("${SCRIPT_DIR}/start-role-team.sh")

  if [[ ${LEGACY_MODE} -eq 1 ]]; then
    return
  fi

  if [[ -n "${TMUX:-}" ]]; then
    return
  fi

  require_cmd tmux
  cleanup_stale_tmux_session "${SESSION_NAME}"

  if [[ "${WORK_DIR}" != "${SCRIPT_DIR}" ]]; then
    relaunch+=("${WORK_DIR}")
  fi
  if [[ ${RESUME_MODE} -eq 1 ]]; then
    relaunch+=("--resume")
  fi
  if [[ ${AUTO_MODE} -eq 1 ]]; then
    relaunch+=("--auto")
  fi

  if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
    exec tmux attach -t "${SESSION_NAME}"
  fi

  exec tmux new-session -s "${SESSION_NAME}" -c "${WORK_DIR}" "$(printf '%q ' "${relaunch[@]}")"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--resume|--restore)
      RESUME_MODE=1
      shift
      ;;
    -a|--auto)
      AUTO_MODE=1
      shift
      ;;
    --legacy)
      LEGACY_MODE=1
      shift
      ;;
    --no-attach)
      ATTACH_MODE="--no-attach"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -d "$1" ]]; then
        WORK_DIR="$(cd "$1" && pwd)"
        shift
      else
        echo "unknown argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

start_legacy_tmux() {
  local claude_prompt="${PROMPT_DIR}/claude-planner.md"
  local codex_prompt="${PROMPT_DIR}/codex-backend.md"
  local gemini_prompt="${PROMPT_DIR}/gemini-frontend.md"

  require_cmd tmux
  require_cmd claude
  require_cmd codex
  require_cmd gemini

  require_file "${claude_prompt}"
  require_file "${codex_prompt}"
  require_file "${gemini_prompt}"

  if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
    if [[ "${ATTACH_MODE}" == "--no-attach" ]]; then
      echo "tmux session already exists: ${SESSION_NAME}"
      exit 0
    fi
    exec tmux attach -t "${SESSION_NAME}"
  fi

  tmux new-session -d -s "${SESSION_NAME}" -c "${WORK_DIR}"
  local pane_claude
  local pane_codex
  local pane_gemini
  pane_claude="$(tmux list-panes -t "${SESSION_NAME}" -F '#{pane_id}' | head -n 1)"
  pane_codex="$(tmux split-window -h -t "${pane_claude}" -c "${WORK_DIR}" -P -F '#{pane_id}')"
  pane_gemini="$(tmux split-window -h -t "${pane_codex}" -c "${WORK_DIR}" -P -F '#{pane_id}')"

  tmux select-layout -t "${SESSION_NAME}" even-horizontal

  tmux select-pane -t "${pane_claude}" -T "Claude Planner"
  tmux select-pane -t "${pane_codex}" -T "Codex Backend"
  tmux select-pane -t "${pane_gemini}" -T "Gemini Frontend"

  tmux send-keys -t "${pane_claude}" "claude \"\$(cat ${claude_prompt})\"" C-m
  tmux send-keys -t "${pane_codex}" "codex \"\$(cat ${codex_prompt})\"" C-m
  tmux send-keys -t "${pane_gemini}" "gemini" C-m

  if [[ "${ATTACH_MODE}" == "--no-attach" ]]; then
    echo "tmux session created: ${SESSION_NAME}"
    echo "attach with: tmux attach -t ${SESSION_NAME}"
    exit 0
  fi

  exec tmux attach -t "${SESSION_NAME}"
}

start_ccb() {
  local cmd=(ccb)

  require_cmd ccb
  require_file "${WORK_DIR}/AGENTS.md"
  require_file "${WORK_DIR}/CLAUDE.md"
  require_file "${WORK_DIR}/CODEX.md"
  require_file "${WORK_DIR}/GEMINI.md"

  cd "${WORK_DIR}"

  if [[ ${RESUME_MODE} -eq 1 ]]; then
    cmd+=(-r)
  fi
  if [[ ${AUTO_MODE} -eq 1 ]]; then
    cmd+=(-a)
  fi
  if [[ ! -f ".ccb/ccb.config" ]]; then
    cmd+=(codex gemini claude)
  fi

  echo "Starting fqxs collaboration via CCB in ${WORK_DIR}"
  exec "${cmd[@]}"
}

if [[ ${LEGACY_MODE} -eq 1 ]]; then
  start_legacy_tmux
fi

ensure_tmux_for_ccb
start_ccb
