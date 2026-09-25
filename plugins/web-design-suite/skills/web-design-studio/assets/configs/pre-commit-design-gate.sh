#!/bin/sh
# =============================================================================
# pre-commit-design-gate.sh — Law 9: nothing ships un-audited
# =============================================================================
#
# Runs the three design gates over STAGED FILES ONLY and refuses the commit
# if any of them fails:
#
#   1. stylelint  — assets/configs/stylelint.config.mjs   (CSS side)
#   2. eslint     — assets/configs/eslint.design.config.mjs (JSX/TSX side)
#   3. python -m scripts.audit_design                      (cross-cutting)
#
# INSTALL
#   cp assets/configs/pre-commit-design-gate.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
#   Or, if the project uses husky:
#     echo "sh assets/configs/pre-commit-design-gate.sh" > .husky/pre-commit
#
# BYPASS — deliberately visible
#   DESIGN_GATE_BYPASS=1 git commit -m "..."
#
#   The variable is required to be exactly `1`. `--no-verify` also works
#   because git offers it and no hook can prevent it, but it leaves no
#   record. This variable does: the hook writes a line to .git/design-gate.log
#   with the timestamp, the user and the staged file list BEFORE it exits,
#   so a bypass is a fact in the repo rather than a rumour. Review that log
#   in the weekly design review; a bypass that nobody can explain is a
#   missing token or a missing escape hatch, and both are fixable.
#
# WHY STAGED-ONLY
#   A gate that lints the whole tree is a gate that fails for reasons the
#   committer did not cause, on their first commit in a legacy repo. It gets
#   bypassed once, then always. Linting only what is being committed means
#   the gate is always about THIS change, always fast, and always fair —
#   which is the only way it survives contact with a deadline.
#
# POSIX sh. No bashisms: this runs in whatever /bin/sh the developer's
# machine, the CI image and the Windows git-bash shim provide.
# =============================================================================

set -u

# --- Configuration -----------------------------------------------------------

STYLELINT_CONFIG="${DESIGN_GATE_STYLELINT_CONFIG:-assets/configs/stylelint.config.mjs}"
ESLINT_CONFIG="${DESIGN_GATE_ESLINT_CONFIG:-assets/configs/eslint.design.config.mjs}"
AUDIT_MODULE="${DESIGN_GATE_AUDIT_MODULE:-scripts.audit_design}"
AUDIT_FILE="$(printf '%s' "$AUDIT_MODULE" | tr . /).py"
PYTHON="${DESIGN_GATE_PYTHON:-}"
if [ -z "$PYTHON" ]; then
  # `python3` on Windows is often the Microsoft Store placeholder: it is on
  # PATH but only prints an install hint. Take the first interpreter that runs.
  for candidate in python3 python py; do
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
      PYTHON=$candidate
      break
    fi
  done
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "design-gate: not inside a git repository" >&2
  exit 1
}
cd "$REPO_ROOT" || exit 1

LOG_FILE="$REPO_ROOT/.git/design-gate.log"
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/design-gate.XXXXXX") || exit 1
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM HUP

# Colour only when stdout is a terminal; a CI log full of escape codes is
# harder to read than one without.
if [ -t 1 ]; then
  C_RED=$(printf '\033[31m'); C_YEL=$(printf '\033[33m')
  C_DIM=$(printf '\033[2m');  C_BOLD=$(printf '\033[1m'); C_OFF=$(printf '\033[0m')
else
  C_RED=''; C_YEL=''; C_DIM=''; C_BOLD=''; C_OFF=''
fi

# --- Bypass ------------------------------------------------------------------

if [ "${DESIGN_GATE_BYPASS:-0}" = "1" ]; then
  staged_list=$(git diff --cached --name-only --diff-filter=ACMR | tr '\n' ' ')
  printf '%s\tBYPASS\t%s\t%s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "$(git config user.email 2>/dev/null || echo unknown)" \
    "$staged_list" >> "$LOG_FILE"
  printf '%s design-gate BYPASSED%s — recorded in .git/design-gate.log\n' \
    "$C_YEL" "$C_OFF" >&2
  exit 0
fi

# --- Collect staged files ----------------------------------------------------
# --diff-filter=ACMR: Added, Copied, Modified, Renamed. Deleted files are
# excluded, or the hook fails trying to lint a path that no longer exists.
#
# -z then `while IFS= read -r`: filenames containing SPACES are a fact of
# design work ("Hero Section.tsx" happens the first week of every project),
# and `cmd $(cat list)` word-splits them into two nonexistent paths. The
# `set --` loops below build the argument list one element at a time, which
# is the POSIX way to do this without arrays.
#
# Known limit: a filename containing a literal NEWLINE still breaks this,
# because the list is newline-delimited after the `tr`. Git allows it; no
# real project does it; the failure is loud (a path not found) rather than
# silent, which is the acceptable trade.

STAGED="$TMP_DIR/staged"
git diff --cached --name-only --diff-filter=ACMR -z \
  | tr '\0' '\n' > "$STAGED"

if [ ! -s "$STAGED" ]; then
  exit 0
fi

grep -E '\.css$'            "$STAGED" > "$TMP_DIR/css"  2>/dev/null || true
grep -E '\.(js|jsx|ts|tsx|mjs)$' "$STAGED" > "$TMP_DIR/js"   2>/dev/null || true

# --- Warn about partially staged files ---------------------------------------
# The linters read the WORKING TREE, not the index. When a file is only
# partially staged (`git add -p`), what is linted is not what is committed.
# Reconstructing the index content into a temp tree would make config
# resolution, relative imports and `files:` globs all resolve against the
# wrong paths — which breaks the very overrides this system depends on. So:
# lint the working tree, and say plainly when the two differ. Silence here
# would be a lie.

PARTIAL=$(git diff --name-only --diff-filter=ACMR -z 2>/dev/null \
  | tr '\0' '\n' \
  | grep -Fxf "$STAGED" 2>/dev/null || true)

if [ -n "$PARTIAL" ]; then
  printf '%sdesign-gate: these files are partially staged; the gate checked the working tree, not the index:%s\n' \
    "$C_YEL" "$C_OFF" >&2
  printf '%s\n' "$PARTIAL" | sed 's/^/  /' >&2
  printf '\n' >&2
fi

# --- Runners -----------------------------------------------------------------

FAILED=''
REPORT="$TMP_DIR/report"
: > "$REPORT"

# run_gate <label> <law-summary> <output-file> <command...>
run_gate() {
  label="$1"; shift
  laws="$1"; shift
  out="$1"; shift
  if "$@" > "$out" 2>&1; then
    printf '  %s✓%s %s\n' "$C_DIM" "$C_OFF" "$label"
  else
    FAILED="$FAILED $label"
    {
      printf '\n%s──────────────────────────────────────────────────────────────%s\n' "$C_RED" "$C_OFF"
      printf '%s%s FAILED%s   %s\n' "$C_BOLD$C_RED" "$label" "$C_OFF" "$laws"
      printf '%s──────────────────────────────────────────────────────────────%s\n' "$C_RED" "$C_OFF"
      cat "$out"
    } >> "$REPORT"
    printf '  %s✗%s %s\n' "$C_RED" "$C_OFF" "$label"
  fi
}

printf '%sdesign-gate%s  %s staged file(s)\n' "$C_BOLD" "$C_OFF" "$(wc -l < "$STAGED" | tr -d ' ')"

# 1. Stylelint — Laws 1, 2, 3, 5, 6 in CSS.
if [ -s "$TMP_DIR/css" ]; then
  if [ -f "$STYLELINT_CONFIG" ]; then
    set --
    while IFS= read -r f; do [ -n "$f" ] && set -- "$@" "$f"; done < "$TMP_DIR/css"
    run_gate "stylelint" "Laws 1, 2, 3, 5, 6 — tokens, gaps, scale, layers, roles" \
      "$TMP_DIR/out.stylelint" \
      npx --no-install stylelint --config "$STYLELINT_CONFIG" \
        --formatter string "$@"
  else
    printf '  %s!%s stylelint config not found at %s — SKIPPED\n' "$C_YEL" "$C_OFF" "$STYLELINT_CONFIG"
  fi
fi

# 2. ESLint — Laws 1, 2, 3, 4, 5, 6, 8 in JSX/TSX.
#    By default the PROJECT config is used, because it carries the parser.
#    The design fragment deliberately ships without one (see the header of
#    eslint.design.config.mjs) so it can compose into any setup.
#
#    DESIGN_GATE_ESLINT_STANDALONE=1 runs the fragment alone. Useful in a
#    repo that has not wired it in yet — but with the caveat that follows
#    from the fragment having no parser: .ts and .tsx files will fail with
#    "Parsing error: Unexpected token :" because the default espree parser
#    does not read type annotations. Standalone mode is a smoke test for
#    .js/.jsx, not a substitute for composing the fragment properly.
if [ -s "$TMP_DIR/js" ]; then
  set --
  while IFS= read -r f; do [ -n "$f" ] && set -- "$@" "$f"; done < "$TMP_DIR/js"
  if [ "${DESIGN_GATE_ESLINT_STANDALONE:-0}" = "1" ]; then
    run_gate "eslint (design laws only)" "Laws 1, 2, 3, 4, 5, 6, 8" \
      "$TMP_DIR/out.eslint" \
      npx --no-install eslint --no-config-lookup --config "$ESLINT_CONFIG" \
        --max-warnings 0 "$@"
  else
    run_gate "eslint" "Laws 1, 2, 3, 4, 5, 6, 8 — tokens, gaps, scale, one home, layers, roles, a11y" \
      "$TMP_DIR/out.eslint" \
      npx --no-install eslint --max-warnings 0 "$@"
  fi
fi

# 3. The design audit — Law 9, and the checks no linter can express: literals
#    disguised inside Tier-3 socket declarations, the cross-file pass (one
#    class styled from two files, one property owned twice), layer order, and
#    the baseline that freezes existing debt instead of failing on it.
#    Run from the repo root so `-m scripts.audit_design` resolves. The staged
#    paths are passed as arguments; the audit reads them from the working tree.
if [ -n "$PYTHON" ] && command -v "$PYTHON" >/dev/null 2>&1; then
  if [ -f "$AUDIT_FILE" ]; then
    set --
    while IFS= read -r f; do [ -n "$f" ] && set -- "$@" "$f"; done < "$STAGED"
    run_gate "audit_design" "Law 9 — nothing ships un-audited" \
      "$TMP_DIR/out.audit" \
      "$PYTHON" -m "$AUDIT_MODULE" "$@"
  else
    printf '  %s!%s %s not found — SKIPPED\n' "$C_YEL" "$C_OFF" "$AUDIT_FILE"
  fi
else
  printf '  %s!%s no working Python (set DESIGN_GATE_PYTHON) — audit SKIPPED\n' "$C_YEL" "$C_OFF"
fi

# --- Verdict -----------------------------------------------------------------

if [ -z "$FAILED" ]; then
  exit 0
fi

cat "$REPORT" >&2

cat >&2 <<EOF

${C_BOLD}${C_RED}Commit refused by the design gate.${C_OFF}
Failed:${FAILED}

Each message above names the Law it enforces and the token or role to use
instead. Three ways forward, in order of preference:

  1. ${C_BOLD}Use the role.${C_OFF} Nine times out of ten the message already names it
     (p-card, gap-related, bg-surface, text-muted, rounded-panel).

  2. ${C_BOLD}Add the token.${C_OFF} If no role fits, the design needs a vocabulary it
     does not have. Add a Tier-2 role to assets/starter/styles/tokens.css,
     bind it in assets/configs/theme.css, and the class exists everywhere.
     This takes four minutes and it is the correct answer more often than
     people expect.

  3. ${C_BOLD}Document the escape.${C_OFF} A genuine one-off — optical alignment, a
     browser bug, third-party DOM you do not control — gets a disable
     comment with a justification and a name:

       /* stylelint-disable-next-line declaration-property-value-allowed-list --
          Law 2 escape: the arrow's bounding box sits 1px below its visual
          centre because of the border join. Reviewed by <name>, <date>. */

     "It looked better" is not a justification; it is a layout that has not
     been thought through, and the fix is in the parent.

To bypass and leave a record:  ${C_DIM}DESIGN_GATE_BYPASS=1 git commit ...${C_OFF}
EOF

exit 1
