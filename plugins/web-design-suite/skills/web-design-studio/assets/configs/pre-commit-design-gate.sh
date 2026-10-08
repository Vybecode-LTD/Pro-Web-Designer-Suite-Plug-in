#!/bin/sh
# =============================================================================
# pre-commit-design-gate.sh — Law 9: nothing ships un-audited
# =============================================================================
#
# Runs the design gates over STAGED FILES ONLY and refuses the commit if any
# of them fails:
#
#   1. stylelint  — the project's stylelint config        (CSS side)
#   2. eslint     — the project's ESLint config            (JSX/TSX side)
#   3. python -m scripts.audit_design                      (cross-cutting)
#   4. python -m scripts.a11y_static    (the accessibility floor — runs only
#      when a11y-audit-runner's a11y_static.py is vendored into scripts/)
#   5. python -m scripts.check_roles    (role-pair contrast per theme — runs
#      only when a tokens.css is staged and check_roles.py is vendored into
#      scripts/, together with generate_color_ramp.py, which it imports)
#
#   Configs are found where handoff-conventions.md puts them, at the repo
#   root (stylelint.config.*, .stylelintrc*, eslint.config.*), then in
#   assets/configs/; DESIGN_GATE_STYLELINT_CONFIG and
#   DESIGN_GATE_ESLINT_CONFIG name them outright. The shipped configs import
#   project_config.mjs from their own folder, so copy it with them. A stage that cannot run —
#   no config, no audit script, no Python — FAILS the commit, because a gate
#   that skips quietly passes everything. DESIGN_GATE_ALLOW_SKIP=1 turns
#   that into a warning, for a repo that has not adopted the stage yet.
#
# INSTALL — the same file, as two hooks
#   cp assets/configs/pre-commit-design-gate.sh .git/hooks/pre-commit
#   cp assets/configs/pre-commit-design-gate.sh .git/hooks/commit-msg
#   chmod +x .git/hooks/pre-commit .git/hooks/commit-msg
#
#   Or, if the project uses husky:
#     echo 'sh assets/configs/pre-commit-design-gate.sh' > .husky/pre-commit
#     echo 'sh assets/configs/pre-commit-design-gate.sh "$1"' > .husky/commit-msg
#
#   Run with no arguments it is the pre-commit gate. Handed the message file
#   (as git hands it to commit-msg) it records a bypass in the commit.
#
# BYPASS — deliberately visible
#   DESIGN_GATE_BYPASS=1 DESIGN_GATE_BYPASS_REASON="why" git commit -m "..."
#
#   The variable is required to be exactly `1`. `--no-verify` also works
#   because git offers it and no hook can prevent it, but it leaves no
#   record. This variable does, twice. A line goes to design-gate.log in the
#   repository's git directory, with the time, the user, the reason and the
#   staged files. And with the commit-msg hook installed, the commit itself
#   carries a `Design-Gate-Bypass: <reason>` trailer, so the bypass travels
#   with the history instead of staying in one clone. Review both in the
#   weekly design review; a bypass that nobody can explain is a missing token
#   or a missing escape hatch, and both are fixable.
#
# WHAT IS CHECKED — the working tree, or the index
#   By default the gates read the working tree. DESIGN_GATE_INDEX=1 runs the
#   Python stages on the STAGED content instead (copied out with git
#   checkout-index), so a change staged with `git add -p` is judged as it
#   will be committed. stylelint and ESLint still read the working tree:
#   their configs resolve against real paths. The cross-file pass sees the
#   staged files either way; run the full audit in CI for the whole tree.
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

# --- commit-msg mode ---------------------------------------------------------
# Installed as the commit-msg hook, this script is handed the message file. If
# the pre-commit run was bypassed, write the bypass into the commit.
if [ $# -ge 1 ] && [ -f "$1" ]; then
  MARKER="$(git rev-parse --git-dir 2>/dev/null || echo .git)/design-gate-bypass"
  if [ -f "$MARKER" ]; then
    git interpret-trailers --in-place \
      --trailer "Design-Gate-Bypass: $(head -n 1 "$MARKER")" "$1" || exit 1
    rm -f "$MARKER"
  fi
  exit 0
fi

# --- Configuration -----------------------------------------------------------

AUDIT_MODULE="${DESIGN_GATE_AUDIT_MODULE:-scripts.audit_design}"
AUDIT_FILE="$(printf '%s' "$AUDIT_MODULE" | tr . /).py"
A11Y_MODULE="${DESIGN_GATE_A11Y_MODULE:-scripts.a11y_static}"
A11Y_FILE="$(printf '%s' "$A11Y_MODULE" | tr . /).py"
ROLES_MODULE="${DESIGN_GATE_ROLES_MODULE:-scripts.check_roles}"
ROLES_FILE="$(printf '%s' "$ROLES_MODULE" | tr . /).py"
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

# The log lives in the COMMON git directory, shared by every worktree; in a
# linked worktree .git is a file, not a directory. The bypass marker is per
# worktree, because the commit-msg run that reads it is.
COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null) || COMMON_DIR=.git
LOG_FILE="$COMMON_DIR/design-gate.log"
MARKER="$(git rev-parse --git-dir 2>/dev/null || echo .git)/design-gate-bypass"

# first_file <path...>: the first of these that exists.
first_file() {
  for candidate in "$@"; do
    if [ -f "$candidate" ]; then printf '%s' "$candidate"; return 0; fi
  done
  return 1
}
STYLELINT_CONFIG="${DESIGN_GATE_STYLELINT_CONFIG:-$(first_file stylelint.config.mjs \
  stylelint.config.js stylelint.config.cjs .stylelintrc.json .stylelintrc.yaml \
  .stylelintrc.yml .stylelintrc.js .stylelintrc assets/configs/stylelint.config.mjs || true)}"
STYLELINT_IN_PACKAGE=0
if [ -z "$STYLELINT_CONFIG" ] && [ -f package.json ] \
    && grep -q '"stylelint"[[:space:]]*:[[:space:]]*{' package.json; then
  STYLELINT_IN_PACKAGE=1            # a "stylelint" config object; stylelint finds it
fi
ESLINT_CONFIG="${DESIGN_GATE_ESLINT_CONFIG:-$(first_file eslint.design.config.mjs \
  assets/configs/eslint.design.config.mjs || true)}"
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
  reason=$(printf '%s' "${DESIGN_GATE_BYPASS_REASON:-no reason given}" | tr '\n\t' '  ')
  who=$(git config user.email 2>/dev/null || echo unknown)
  when=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  printf '%s\tBYPASS\t%s\t%s\t%s\n' "$when" "$who" "$reason" "$staged_list" >> "$LOG_FILE" || {
    echo "design-gate: cannot write $LOG_FILE, so the bypass would leave no record" >&2
    exit 1
  }
  printf '%s (%s, %s)\n' "$reason" "$who" "$when" > "$MARKER" || exit 1
  printf '%s design-gate BYPASSED%s — recorded in %s, and in the commit as a trailer when the commit-msg hook is installed\n' \
    "$C_YEL" "$C_OFF" "$LOG_FILE" >&2
  exit 0
fi
rm -f "$MARKER"          # a bypass marker from an aborted commit must not leak into this one

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
  if [ "${DESIGN_GATE_INDEX:-0}" = "1" ]; then
    printf '%sdesign-gate: these files are partially staged; the Python stages checked the staged content, stylelint and ESLint the working tree:%s\n' \
      "$C_YEL" "$C_OFF" >&2
  else
    printf '%sdesign-gate: these files are partially staged; the gate checked the working tree, not the index (DESIGN_GATE_INDEX=1 checks the index):%s\n' \
      "$C_YEL" "$C_OFF" >&2
  fi
  printf '%s\n' "$PARTIAL" | sed 's/^/  /' >&2
  printf '\n' >&2
fi

# --- Optional: audit what will be committed ----------------------------------
# DESIGN_GATE_INDEX=1 copies the STAGED content of the staged files into a
# scratch tree and runs the Python stages there, with the repo root on
# PYTHONPATH so `-m scripts.audit_design` still resolves.
AUDIT_ROOT="$REPO_ROOT"
if [ "${DESIGN_GATE_INDEX:-0}" = "1" ]; then
  AUDIT_ROOT="$TMP_DIR/index"
  mkdir -p "$AUDIT_ROOT" || exit 1
  tr '\n' '\0' < "$STAGED" | git checkout-index -z --stdin --prefix="$AUDIT_ROOT/" || exit 1
fi

# py_stage <args...>: run Python where the stage should look.
py_stage() {
  if [ "$AUDIT_ROOT" = "$REPO_ROOT" ]; then
    "$PYTHON" "$@"
  else
    (cd "$AUDIT_ROOT" && PYTHONPATH="$REPO_ROOT" "$PYTHON" "$@")
  fi
}

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

# missing <label> <why>: a stage that cannot run fails the commit, unless
# DESIGN_GATE_ALLOW_SKIP=1 says to go on without it.
missing() {
  if [ "${DESIGN_GATE_ALLOW_SKIP:-0}" = "1" ]; then
    printf '  %s!%s %s — %s — SKIPPED (DESIGN_GATE_ALLOW_SKIP=1)\n' "$C_YEL" "$C_OFF" "$1" "$2"
  else
    FAILED="$FAILED $1"
    printf '  %s✗%s %s — %s\n' "$C_RED" "$C_OFF" "$1" "$2"
    printf '\n%s%s cannot run:%s %s. Add it, point its DESIGN_GATE_* variable at it, or set DESIGN_GATE_ALLOW_SKIP=1 to commit without this stage.\n' \
      "$C_BOLD$C_RED" "$1" "$C_OFF" "$2" >> "$REPORT"
  fi
}

printf '%sdesign-gate%s  %s staged file(s)\n' "$C_BOLD" "$C_OFF" "$(wc -l < "$STAGED" | tr -d ' ')"

# 1. Stylelint — Laws 1, 2, 3, 5, 6 in CSS.
if [ -s "$TMP_DIR/css" ]; then
  set --
  while IFS= read -r f; do [ -n "$f" ] && set -- "$@" "$f"; done < "$TMP_DIR/css"
  if [ -n "$STYLELINT_CONFIG" ]; then
    run_gate "stylelint" "Laws 1, 2, 3, 5, 6 — tokens, gaps, scale, layers, roles" \
      "$TMP_DIR/out.stylelint" \
      npx --no-install stylelint --config "$STYLELINT_CONFIG" \
        --formatter string "$@"
  elif [ "$STYLELINT_IN_PACKAGE" = "1" ]; then
    run_gate "stylelint" "Laws 1, 2, 3, 5, 6 — tokens, gaps, scale, layers, roles" \
      "$TMP_DIR/out.stylelint" \
      npx --no-install stylelint --formatter string "$@"
  else
    missing "stylelint" "no stylelint config (looked for stylelint.config.*, .stylelintrc*, a \"stylelint\" object in package.json, and assets/configs/stylelint.config.mjs)"
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
  # --no-warn-ignored: a staged file the project's config ignores is passed
  # here by name, and ESLint warns "File ignored because of a matching ignore
  # pattern", which --max-warnings 0 would turn into a refused commit.
  if [ "${DESIGN_GATE_ESLINT_STANDALONE:-0}" = "1" ]; then
    if [ -n "$ESLINT_CONFIG" ]; then
      run_gate "eslint (design laws only)" "Laws 1, 2, 3, 4, 5, 6, 8" \
        "$TMP_DIR/out.eslint" \
        npx --no-install eslint --no-config-lookup --config "$ESLINT_CONFIG" \
          --no-warn-ignored --max-warnings 0 "$@"
    else
      missing "eslint (design laws only)" "no eslint.design.config.mjs at the repo root or in assets/configs/"
    fi
  else
    run_gate "eslint" "Laws 1, 2, 3, 4, 5, 6, 8 — tokens, gaps, scale, one home, layers, roles, a11y" \
      "$TMP_DIR/out.eslint" \
      npx --no-install eslint --no-warn-ignored --max-warnings 0 "$@"
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
      py_stage -m "$AUDIT_MODULE" "$@"
  else
    missing "audit_design" "$AUDIT_FILE not found (vendor web-design-studio's scripts, or set DESIGN_GATE_AUDIT_MODULE)"
  fi
else
  missing "audit_design" "no working Python (set DESIGN_GATE_PYTHON)"
fi

# 4. The accessibility floor — source-level WCAG checks from a11y-audit-runner.
#    Opt-in by presence: it runs when scripts/a11y_static.py is vendored (or
#    DESIGN_GATE_A11Y_MODULE names it), so a repo that has not adopted it is
#    not nagged. Same staged files, same verdict: either gate refuses. Files
#    that are not markup, JSX or CSS are skipped by the script itself.
if [ -n "$PYTHON" ] && command -v "$PYTHON" >/dev/null 2>&1 && [ -f "$A11Y_FILE" ]; then
  set --
  while IFS= read -r f; do [ -n "$f" ] && set -- "$@" "$f"; done < "$STAGED"
  run_gate "a11y_static" "WCAG 2.2 — the accessibility floor" \
    "$TMP_DIR/out.a11y" \
    py_stage -m "$A11Y_MODULE" "$@"
fi

# 5. Role-pair contrast — check_roles resolves the Tier-2 roles in every theme
#    and checks the pairs components put together: text 4.5:1, control
#    borders and the focus ring 3:1. Opt-in by presence, like stage 4, and
#    only when a tokens file is part of this commit.
grep -E '(^|/)([^/]*-)?tokens\.css$' "$STAGED" > "$TMP_DIR/tokens" 2>/dev/null || true
if [ -n "$PYTHON" ] && command -v "$PYTHON" >/dev/null 2>&1 && [ -f "$ROLES_FILE" ] \
    && [ -s "$TMP_DIR/tokens" ]; then
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    run_gate "check_roles $f" "Laws 6 and 8 — role pairs clear WCAG 1.4.3 and 1.4.11 in every theme" \
      "$TMP_DIR/out.roles" \
      py_stage -m "$ROLES_MODULE" "$f"
  done < "$TMP_DIR/tokens"
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

To bypass and leave a record:  ${C_DIM}DESIGN_GATE_BYPASS=1 DESIGN_GATE_BYPASS_REASON="why" git commit ...${C_OFF}
EOF

exit 1
