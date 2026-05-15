#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGINS_DIR="$SCRIPT_DIR/plugins"   # Claude Code plugins
POWERS_DIR="$SCRIPT_DIR/powers"     # Kiro powers

# Map bundle name → plugin dir under plugins/.
# "all" expands to every plugin.
declare -a BUNDLE_PLUGINS=()
# Map bundle name → power dir names under powers/.
# /nova-migrate is Claude-only for now, so "migration" has no Kiro equivalent.
declare -a BUNDLE_POWERS=()

# ── colours & styles ─────────────────────────────────────────────────────────

BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'

# ── helpers ───────────────────────────────────────────────────────────────────

header() {
  printf '\n%b━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%b\n' "$BLUE" "$RESET"
  printf ' %b  Nova Prompter Installer%b\n' "$WHITE$BOLD" "$RESET"
  printf '%b━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%b\n\n' "$BLUE" "$RESET"
}

section() { printf '\n%b  %s%b\n' "$CYAN$BOLD" "$*" "$RESET"; }
step()    { printf '  %b→%b  %s\n' "$GRAY" "$RESET" "$*"; }
ok()      { printf '  %b✓%b  %s\n' "$GREEN" "$RESET" "$*"; }
warn()    { printf '  %b⚠%b  %s\n' "$YELLOW" "$RESET" "$*"; }
die()     { printf '\n  %b✗  %s%b\n\n' "$RED" "$*" "$RESET" >&2; exit 1; }

prompt() {
  printf '%b  › %b%s%b ' "$CYAN" "$WHITE" "$1" "$RESET" >/dev/tty
}

divider() { printf '  %b%s%b\n' "$GRAY" "──────────────────────────────────────" "$RESET"; }

usage() {
  cat <<EOF

  Usage: $(basename "$0") [OPTIONS]

  Copy Nova plugins / powers into Claude Code or Kiro install dirs.

  Options:
    -g, --global            Install to global user dirs  (~/.claude/skills, ~/.kiro/powers)
    -l, --local             Install to project dirs       (.claude/skills, .kiro/powers)
    -t, --tool <tool>       Target: claude | kiro | both
    -b, --bundle <bundle>   Which plugin(s) to install:
                              prompting   — /nova1-prompt, /nova2-prompt
                              migration   — /nova-migrate (Claude only; pair with prompting)
                              all         — everything
    -h, --help              Show this help

  Claude Code users can also install via the marketplace:
      /plugin marketplace add aws-samples/amazon-nova-samples
      /plugin install nova-prompting@amazon-nova-samples

  This script is the easiest way to install the Kiro powers, since Kiro
  has no central plugin registry yet.

  If flags are omitted the script will ask interactively.

EOF
}

# ── interactive prompts ───────────────────────────────────────────────────────

ask_bundle() {
  section "Which bundle?"
  printf '    %b1)%b  Prompting only %b(/nova1-prompt, /nova2-prompt)%b\n' "$WHITE$BOLD" "$RESET" "$GRAY" "$RESET" >/dev/tty
  printf '    %b2)%b  Migration only %b(/nova-migrate — pair with prompting)%b\n' "$WHITE$BOLD" "$RESET" "$GRAY" "$RESET" >/dev/tty
  printf '    %b3)%b  All\n' "$WHITE$BOLD" "$RESET" >/dev/tty
  printf '\n' >/dev/tty
  prompt "Choice [1/2/3]:"
  local choice
  read -r choice </dev/tty
  case "$choice" in
    1) BUNDLE="prompting" ;;
    2) BUNDLE="migration" ;;
    3) BUNDLE="all"       ;;
    *) die "Invalid choice '$choice'" ;;
  esac
}

resolve_bundle() {
  case "$BUNDLE" in
    prompting)
      BUNDLE_PLUGINS=("nova-prompting")
      BUNDLE_POWERS=("nova1-prompt" "nova2-prompt")
      ;;
    migration)
      BUNDLE_PLUGINS=("nova-migration")
      BUNDLE_POWERS=()  # no Kiro version of /nova-migrate yet
      ;;
    all)
      BUNDLE_PLUGINS=("nova-prompting" "nova-migration")
      BUNDLE_POWERS=("nova1-prompt" "nova2-prompt")
      ;;
    *) die "Invalid --bundle '$BUNDLE'. Must be: prompting | migration | all" ;;
  esac
}

ask_tool() {
  section "Which tool?"
  printf '    %b1)%b  Claude\n' "$WHITE$BOLD" "$RESET" >/dev/tty
  printf '    %b2)%b  Kiro\n'   "$WHITE$BOLD" "$RESET" >/dev/tty
  printf '    %b3)%b  Both\n'   "$WHITE$BOLD" "$RESET" >/dev/tty
  printf '\n' >/dev/tty
  prompt "Choice [1/2/3]:"
  local choice
  read -r choice </dev/tty
  case "$choice" in
    1) TOOL="claude" ;;
    2) TOOL="kiro"   ;;
    3) TOOL="both"   ;;
    *) die "Invalid choice '$choice'" ;;
  esac
}

ask_scope() {
  local hint_local hint_global
  case "$TOOL" in
    claude) hint_local=".claude/skills"               ; hint_global="~/.claude/skills"               ;;
    kiro)   hint_local=".kiro/powers"                 ; hint_global="~/.kiro/powers"                 ;;
    both)   hint_local=".claude/skills + .kiro/powers"; hint_global="~/.claude/skills + ~/.kiro/powers" ;;
  esac

  section "Install scope?"
  printf "    %b1)%b  Local   %b%s%b\n" "$WHITE$BOLD" "$RESET" "$GRAY" "$hint_local"  "$RESET" >/dev/tty
  printf "    %b2)%b  Global  %b%s%b\n" "$WHITE$BOLD" "$RESET" "$GRAY" "$hint_global" "$RESET" >/dev/tty
  printf '\n' >/dev/tty
  prompt "Choice [1/2]:"
  local choice
  read -r choice </dev/tty
  case "$choice" in
    1) SCOPE="local"  ;;
    2) SCOPE="global" ;;
    *) die "Invalid choice '$choice'" ;;
  esac
}

# ── install logic ─────────────────────────────────────────────────────────────

install_claude_skills() {
  local dest_dir="$1"
  local label="$2"

  section "Installing → $label"
  step "$dest_dir"
  divider
  mkdir -p "$dest_dir"

  local count=0
  for plugin in "${BUNDLE_PLUGINS[@]}"; do
    local plugin_skills="$PLUGINS_DIR/$plugin/skills"
    [[ -d "$plugin_skills" ]] || { warn "No skills dir for plugin '$plugin'"; continue; }
    for skill_path in "$plugin_skills"/*/; do
      [[ -d "$skill_path" ]] || continue
      local skill_name
      skill_name="$(basename "$skill_path")"
      local target="$dest_dir/$skill_name"
      mkdir -p "$target"
      cp -r "$skill_path"* "$target/"
      ok "$skill_name  (from $plugin)"
      (( count++ )) || true
    done
  done

  divider
  if [[ $count -eq 0 ]]; then
    warn "No Claude skills for bundle '$BUNDLE'"
  else
    printf '  %b%d skill(s) installed%b\n' "$GREEN" "$count" "$RESET"
  fi
}

install_kiro_powers() {
  local dest_dir="$1"
  local label="$2"

  if [[ ${#BUNDLE_POWERS[@]} -eq 0 ]]; then
    warn "Bundle '$BUNDLE' has no Kiro powers — skipping Kiro install"
    return 0
  fi

  section "Installing → $label"
  step "$dest_dir"
  divider
  mkdir -p "$dest_dir"

  local count=0
  for power_name in "${BUNDLE_POWERS[@]}"; do
    local power_path="$POWERS_DIR/$power_name"
    [[ -d "$power_path" ]] || { warn "Missing power dir: $power_path"; continue; }
    local target="$dest_dir/$power_name"
    mkdir -p "$target"
    cp -r "$power_path"/* "$target/"
    ok "$power_name"
    (( count++ )) || true
  done

  divider
  if [[ $count -eq 0 ]]; then
    warn "No Kiro powers for bundle '$BUNDLE'"
  else
    printf '  %b%d power(s) installed%b\n' "$GREEN" "$count" "$RESET"
  fi
}

# ── parse args ────────────────────────────────────────────────────────────────

SCOPE=""
TOOL=""
BUNDLE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -g|--global) SCOPE="global"; shift ;;
    -l|--local)  SCOPE="local";  shift ;;
    -t|--tool)
      [[ $# -gt 1 ]] || die "--tool requires an argument"
      TOOL="$2"; shift 2
      ;;
    -b|--bundle)
      [[ $# -gt 1 ]] || die "--bundle requires an argument"
      BUNDLE="$2"; shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1  (use --help for usage)" ;;
  esac
done

# ── interactive prompts ───────────────────────────────────────────────────────

header

if [[ -z "$BUNDLE" ]]; then
  ask_bundle
fi
resolve_bundle

if [[ -z "$TOOL" ]]; then
  ask_tool
else
  case "$TOOL" in
    claude|kiro|both) ;;
    *) die "Invalid --tool value '$TOOL'. Must be: claude | kiro | both" ;;
  esac
fi

[[ -z "$SCOPE" ]] && ask_scope

# ── resolve destinations ──────────────────────────────────────────────────────

if [[ "$SCOPE" == "global" ]]; then
  CLAUDE_DEST="$HOME/.claude/skills"
  KIRO_DEST="$HOME/.kiro/powers"
else
  CLAUDE_DEST="$SCRIPT_DIR/.claude/skills"
  KIRO_DEST="$SCRIPT_DIR/.kiro/powers"
fi

# ── run ───────────────────────────────────────────────────────────────────────

case "$TOOL" in
  claude)
    install_claude_skills "$CLAUDE_DEST" "Claude ($SCOPE)"
    ;;
  kiro)
    install_kiro_powers "$KIRO_DEST" "Kiro ($SCOPE)"
    ;;
  both)
    install_claude_skills "$CLAUDE_DEST" "Claude ($SCOPE)"
    install_kiro_powers "$KIRO_DEST" "Kiro ($SCOPE)"
    ;;
esac

printf '\n%b  All done!%b\n\n' "$GREEN$BOLD" "$RESET"
