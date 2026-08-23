#!/bin/sh

# Always enter the plugin root: a stray "keel" directory in the session
# working tree can shadow the package under python3 -m; a shipped plugin saw a
# 100% hook-failure rate from exactly this.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    plugin_root=$CLAUDE_PLUGIN_ROOT
elif [ -n "${CODEX_PLUGIN_ROOT:-}" ]; then
    plugin_root=$CODEX_PLUGIN_ROOT
else
    plugin_root=$(CDPATH= cd "$(dirname "$0")/.." 2>/dev/null && pwd) || plugin_root=
fi

fail_open() {
    printf '%s\n' "keel hook: $1" >&2
    # Stderr from a hook that exits 0 goes to the DEBUG LOG ONLY -- never the transcript, and the
    # model never sees it. So the "loud" half of loud-stderr-plus-{} was silent: a plugin could be
    # 100% non-functional with nothing surfacing anywhere anyone looks, which is the silent wiring
    # death this shim exists to prevent. `systemMessage` is a universal output field shown to the
    # user, so carriage still fails OPEN but stops failing invisibly.
    #
    # The message text is a fixed literal per branch: interpolating a path or interpreter name
    # would put unescaped bytes inside a JSON string.
    case $1 in
        "could not resolve plugin root") visible_fault="could not resolve plugin root" ;;
        "could not enter plugin root:"*) visible_fault="could not enter plugin root" ;;
        "interpreter not found:"*) visible_fault="interpreter not found" ;;
        *) visible_fault="Python dispatcher failed" ;;
    esac
    printf '{"systemMessage":"keel hook wiring fault: %s"}\n' "$visible_fault"
    # Never exit 2 on a WIRING fault. Verified against the current hooks reference:
    # "Exit 2 means a blocking error. On events that can block, exit 2 blocks whether or
    # not you print JSON." That holds on BOTH hosts -- the older note here claimed it was
    # a codex-only meaning, which is false. Carriage must fail OPEN, so a wiring fault
    # emits {} and exits 0; exit 2 would deny every tool call for the rest of the session.
    exit 0
}

# A bare `cd ""` succeeds in sh, so guard an empty or unresolved root explicitly.
[ -n "$plugin_root" ] || fail_open "could not resolve plugin root"
cd "$plugin_root" 2>/dev/null || fail_open "could not enter plugin root: $plugin_root"

python=${KEEL_PYTHON:-python3}
command -v "$python" >/dev/null 2>&1 || fail_open "interpreter not found: $python"

# Do not exec: it replaces this shell, leaving nothing to emit {} if Python dies;
# the guarantee would stop at the one failure it most needs to cover.
#
# The blanket `|| fail_open` is not restored: it would rewrite a DELIBERATE closed result as
# exit 0 + {}, which on the wire is an allow. Exit 2 is therefore forwarded rather than swallowed.
#
# Nothing emits it today -- dispatch.main() expresses a closed decision as the event's JSON wire
# and falls back to carriage when it cannot, so this branch is currently unreachable. It is kept
# because exit 2 is the ONLY closed signal that survives a payload the host refuses to parse
# ("exit 0 with a parsed object that fails schema validation is a non-blocking error: the action
# proceeds"), so a future decision path that cannot serialize has somewhere to go.
"$python" -m keel.dispatch
status=$?
[ "$status" -eq 0 ] && exit 0
[ "$status" -eq 2 ] && exit 2
fail_open "Python dispatcher failed"
exit 0
