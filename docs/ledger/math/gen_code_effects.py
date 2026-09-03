import csv

F = "plugin/keel/effects.py"
rows = []

def r(kind, src, what, reads, writes):
    rows.append((kind, f"{F}:{src}", what, reads, writes))

# ---- EFFECTS dict: one row per key (kind=field) ----
effects_keys = [
("40","files_changed","EFFECTS text: a file has different content after the act, or exists after and did not before; a change by another process during the act is charged to it; gitignored/outside-root paths unobserved","EFFECTS dict literal","EFFECTS['files_changed'] sentence"),
("41","files_removed","EFFECTS text: a file with content before has none/does not exist after; a vanished top-level gitignored entry named by path only","EFFECTS dict literal","EFFECTS['files_removed'] sentence"),
("42","head_moved","EFFECTS text: HEAD names a different commit after the act","EFFECTS dict literal","EFFECTS['head_moved'] sentence"),
("43","head_switched","EFFECTS text: HEAD moved to a commit that already existed before (switch/checkout not commit), or a checkout was recorded in HEAD's reflog and HEAD ended where it began","EFFECTS dict literal","EFFECTS['head_switched'] sentence"),
("44","head_reset","EFFECTS text: HEAD moved to an ancestor of where it was and the worktree changed with it, or a reset was recorded in HEAD's reflog whatever it moved back to","EFFECTS dict literal","EFFECTS['head_reset'] sentence"),
("45","commit_signed","EFFECTS text: the act created the commit HEAD now names, and that commit carries a signature","EFFECTS dict literal","EFFECTS['commit_signed'] sentence"),
("46","remote_ref_moved","EFFECTS text: a remote-tracking ref names a different commit after the act","EFFECTS dict literal","EFFECTS['remote_ref_moved'] sentence"),
("47","remote_landed","EFFECTS text: every remote head this session moved equals a local ref, measured at the remote","EFFECTS dict literal","EFFECTS['remote_landed'] sentence"),
("48","pids_gone","EFFECTS text: a process of this session running before the act is not running after it","EFFECTS dict literal","EFFECTS['pids_gone'] sentence"),
("49","pids_spawned","EFFECTS text: a process that did not exist before is still running after (stated limit: a worker that exited before return is not observed), assigned by lineage","EFFECTS dict literal","EFFECTS['pids_spawned'] sentence"),
("50","pids_spawned_again","EFFECTS text: pids_spawned, and this session had already spawned one before","EFFECTS dict literal","EFFECTS['pids_spawned_again'] sentence"),
("51","net_out","EFFECTS text: the act opened an outbound connection; NOT-EVALUABLE when the host's counter moved while no act of this session was running","EFFECTS dict literal","EFFECTS['net_out'] sentence"),
("52","report_null","EFFECTS text: the act printed a null datum, or nothing, while reading a structured file","EFFECTS dict literal","EFFECTS['report_null'] sentence"),
("53","report_pass","EFFECTS text: the act printed a test-report datum with no failures","EFFECTS dict literal","EFFECTS['report_pass'] sentence"),
("54","report_clean","EFFECTS text: the act printed a scanner-report datum with no findings","EFFECTS dict literal","EFFECTS['report_clean'] sentence"),
("55","report_fail","EFFECTS text: the act printed a report datum with failures or findings","EFFECTS dict literal","EFFECTS['report_fail'] sentence"),
("58","report_ref","EFFECTS text (guard side): an act that changed no file/ref/process printed a ref name or commit id the ref snapshot holds","EFFECTS dict literal","EFFECTS['report_ref'] sentence"),
("59","report_paths","EFFECTS text: an act that changed no file/ref/process printed a path the worktree snapshot holds","EFFECTS dict literal","EFFECTS['report_paths'] sentence"),
("60","named_paths","EFFECTS text: the worktree paths that report named, in full: what a demand keyed on a changed path is paid by","EFFECTS dict literal","EFFECTS['named_paths'] sentence"),
("61","named_pids","EFFECTS text: the live pids that report named: what a demand keyed on a gone pid is paid by","EFFECTS dict literal","EFFECTS['named_pids'] sentence"),
("62","report_pids","EFFECTS text: the act printed at least two pids that were alive at the snapshot","EFFECTS dict literal","EFFECTS['report_pids'] sentence"),
("63","report_self","EFFECTS text: the act's output contains a whole segment of its own command; read from command text not the world, stated not proven name-agnostic","EFFECTS dict literal","EFFECTS['report_self'] sentence"),
("64","report_structured","EFFECTS text: the act printed a JSON datum that is not null","EFFECTS dict literal","EFFECTS['report_structured'] sentence"),
("65","report_signature","EFFECTS text: the act printed a signature block or a verified-signature datum","EFFECTS dict literal","EFFECTS['report_signature'] sentence"),
("66","report_nowarn","EFFECTS text: report_pass, and the report carries no warning line","EFFECTS dict literal","EFFECTS['report_nowarn'] sentence"),
("67","net_read","EFFECTS text: net_out, and the act changed no file, moved no ref, left no process, and reported no failure; K13 stated limit on quiet connect to closed port","EFFECTS dict literal","EFFECTS['net_read'] sentence"),
("68","report_after_change","EFFECTS text: report_pass on an act that ran after a file changed since the last spawn","EFFECTS dict literal","EFFECTS['report_after_change'] sentence"),
("69","report_listing","EFFECTS text: report_pids, and the output holds no segment of the act's own command","EFFECTS dict literal","EFFECTS['report_listing'] sentence"),
("70","observed_read","EFFECTS text: the host Read tool returned Keel's own worktree measurement (observed.json), as written","EFFECTS dict literal","EFFECTS['observed_read'] sentence"),
("71","remote_read","EFFECTS text: the host Read tool returned Keel's own remote measurement (remote.json), with tips present","EFFECTS dict literal","EFFECTS['remote_read'] sentence"),
]
for src, name, what, reads, writes in effects_keys:
    r("field", src, what, reads, writes)

# ---- regexes ----
r("regex","75-76","REPORT_SIGNATURE: matches a PGP/SSH signature block header, 'Good signature', or gpgsig","stdout text","bool used in report_effects.report_signature")
r("regex","77","WARNING_LINE: matches any line (multiline, case-insens) starting with a warning/warnings token","stdout text","bool used in report_effects.report_nowarn")
r("regex","94-96","REPORT_PASS: matches N passed (not followed by N failed/error), OK, ok test line, 'test result: ok', '0 failed', Tests: N passed N total, or PASS","stdout text","bool used in report_effects `passed`")
r("regex","97-99","REPORT_CLEAN: matches 0/no/zero findings|issues|problems|vulnerabilities|violations|warnings|errors|matches, or 'clean', or 'all checks passed'","stdout text","bool used in report_effects.report_clean")
r("regex","100-103","REPORT_FAIL: matches N failed/errors/findings/issues/problems/vulnerabilities/violations, ^FAILED, FAIL, ^E , Traceback, 'test result: FAILED', or AssertionError","stdout text","bool used in report_effects.report_pass/nowarn/clean/fail")
r("regex","555","_TOKEN: matches a run of [A-Za-z0-9_./-]+ as one token","report/stdout text","tokens set used by trace_effects")

# ---- constants ----
r("constant","80","LISTING_FLOOR=2: fewest distinct live pids a listing must claim, so one number that happens to be a live pid is not a listing","n/a","threshold used in trace_effects.report_pids")
r("constant","82","ABBREV_FLOOR=7: shortest hex prefix accepted as a commit id (git's own abbreviation floor)","n/a","threshold used in trace_effects.report_ref sha-prefix match")
r("constant","85","REMOTE_RETRY_S=60.0: seconds between attempts to list a remote that could not be listed, so an offline host is asked once a minute not once per act","n/a","threshold used in snapshot() remote retry gate")
r("constant","87","OBSERVED='observed.json': filename Keel writes for the operator to Read its own worktree measurement","n/a","used as write_observed()/`_artifact_read` target name")
r("constant","88","REMOTE='remote.json': filename Keel writes for the operator to Read its own remote measurement","n/a","used as observe_remote()/`_artifact_read` target name")
r("constant","108","WALK_CAP=20000: entries at which the non-repo file walk stops and reports NOT-EVALUABLE, sized to ~1s of the hook's 20s budget at ~20000 lstat/s","n/a","cap used in walk_tree() loop")
r("constant","112","GIT_TIMEOUT=5.0: per-git-call timeout seconds; 4 calls per snapshot and 4 per delta stay inside the hook's 20s","n/a","timeout passed to subprocess.run in _git()")
r("constant","115","_STARTTIME_AFTER_COMM=19: index of the start-time field in /proc/<pid>/stat after the comm-closing ')' (field 22 overall); a reused pid with a different start time is a new process","n/a","index used in proc_table()/_ancestry() parsing")
r("constant","119","_SID_AFTER_COMM=3: index of the process session id field after ')' (field 6 overall); what a daemonized/reparented worker keeps","n/a","index used in proc_table() parsing")
r("constant","122","_ANCESTRY_CAP=64: ancestors walked before giving up on a pid, so a cyclic/stale /proc read stops rather than spinning","n/a","cap used in under() loop")
r("constant","442","EMPTY_BLOB='e69de29b...': the git blob sha of an empty file, used to detect a file emptied (content gone) vs merely modified","n/a","comparison value used in _tree_delta()")

# ---- _git ----
r("function","125-134","Run `git -C cwd <args>` with GIT_OPTIONAL_LOCKS=0 and a timeout; return stdout text or None on failure","cwd, args, env, subprocess result","str|None")
r("branch","130-131","OSError or subprocess.TimeoutExpired during the git call -> function returns None (git unreachable/too slow)","subprocess exception","returns None")
r("branch","132-133","git returncode != 0 -> function returns None (git call failed)","done.returncode","returns None")
r("branch","134","git succeeded -> return done.stdout","done.stdout","returns str")

# ---- _repo_root ----
r("function","139-141","Resolve the repository root for cwd via `git rev-parse --show-toplevel`, stripped, or None if not a repo/unreachable","cwd, _git() output","str|None")

# ---- worktree_tree ----
r("function","144-164","Build the tree object of the entire worktree (tracked+untracked) via a private, freshly-emptied git index, then write-tree; every blob lands in the object store","root, index path","str|None sha of tree object")
r("branch","156-159","mkdir parents / unlink existing index file fails with OSError -> return None","index path filesystem ops","returns None")
r("branch","161-162","`git add -A -- .` under the private index returns None (git failed) -> return None","GIT_INDEX_FILE env, _git() result","returns None")
r("branch","163-164","`git write-tree` succeeded -> return stripped sha; else None","_git() write-tree output","returns str|None")

# ---- walk_tree ----
r("function","167-184","Fallback file inventory outside a repository: path -> (size, mtime_ns), capped at WALK_CAP, no pre-image kept","cwd, os.walk of cwd","dict[str,(int,int)]|None")
r("branch","172","Prune dirnames in-place to skip .git, node_modules, __pycache__ while walking","dirnames list","mutates dirnames (walk excludes these dirs)")
r("branch","175-178","os.lstat(path) raises OSError for one file -> skip that file, continue walk","per-file lstat","continue (file omitted)")
r("line","179","Record relpath -> (st_size, st_mtime_ns) for each successfully stat'd file","os.lstat result, os.path.relpath","seen[relpath] = (size, mtime_ns)")
r("branch","180-181","len(seen) exceeds WALK_CAP -> abort and return None (budget protection)","len(seen), WALK_CAP","returns None")
r("branch","182-183","Outer os.walk raises OSError -> return None","os.walk exception","returns None")

# ---- refs ----
r("function","187-198","Read every ref (`git for-each-ref`) into a name->sha table, plus HEAD's own resolved sha (possibly unborn)","root, _git() for-each-ref and rev-parse output","dict[str,str]|None")
r("line","192-195","Parse each `for-each-ref` output line 'refname sha' into table[name]=sha when both fields present","for-each-ref line","table[name] = sha")
r("line","196-197","Resolve HEAD via `git rev-parse --verify -q HEAD`; store stripped sha or '' if HEAD is unborn/unreachable","_git() rev-parse HEAD output","table['HEAD'] = sha or ''")

# ---- _stat_fields ----
r("function","201-207","Read /proc/<pid>/stat and split the fields AFTER the last ')' (comm may contain spaces/parens)","/proc/<pid>/stat file","list[str]|None")
r("branch","204-205","Reading /proc/<pid>/stat raises OSError (pid gone/unreadable) -> return None","file read","returns None")

# ---- proc_table ----
r("function","210-231","One pass over /proc: pid -> (start_time, ppid, session_id) for every running, non-zombie process","/proc directory listing, per-pid stat fields","dict[int,(str,int,int)]|None")
r("branch","220-221","/proc is not a directory (no procfs) -> return None","pathlib.Path('/proc').is_dir()","returns None")
r("branch","224-225","Directory entry name is not all digits (not a pid dir) -> skip entry","entry.name","continue")
r("branch","227-228","stat fields missing/short, or state field == 'Z' (zombie) -> skip this pid (zombie is not alive; reaped orphan not 'running')","fields[0], len(fields)","continue (pid excluded from table)")
r("line","229-230","Store pid -> (start_time field, int(ppid field), int(session field) if digit else 0)","fields[_STARTTIME_AFTER_COMM], fields[1], fields[_SID_AFTER_COMM]","table[pid] = (start, ppid, sid)")

# ---- under ----
r("function","234-244","For every pid in table, walk its ppid chain (capped at _ANCESTRY_CAP hops) and keep it if the chain reaches root","root pid, table of (start,ppid,sid)","dict[int,str] pid->start_time for descendants of root")
r("branch","239-243","Walk cursor up via table[cursor][1] (or 1 if cursor unknown) until cursor==root (record kin) or cursor<=1 or hops>=_ANCESTRY_CAP (give up on this pid)","table ppid chain, _ANCESTRY_CAP","kin[pid]=start on success; pid omitted otherwise")

# ---- _ancestry ----
r("function","247-256","Walk this process's own ppid chain via /proc, `hops` levels, nearest ancestor first","os.getpid(), /proc/<pid>/stat via _stat_fields","list[int] pid chain")
r("branch","253-254","_stat_fields fails, or fields too short, or parent pid <= 1 (reached init) -> stop walking","fields, fields[1]","break (chain ends)")

# ---- session_root ----
r("function","259-270","The hook's grandparent process (dispatch.sh under host is 2 levels up): the root of the session's process subtree","os.getpid() ancestry via _ancestry(2)","int pid, _ancestry(2)[-1]")

# ---- _own_chain ----
r("function","273-276","This process and up to 7 ancestors: always alive at snapshot time, gone by construction at delta time, never the act's doing","_ancestry(7)","set[int] of pids to exclude from observation")

# ---- net_active_opens ----
r("function","279-297","Read /proc/net/snmp and return the cumulative TCP ActiveOpens counter for this host","/proc/net/snmp file","int|None")
r("branch","287-288","Reading /proc/net/snmp raises OSError -> return None","file read","returns None")
r("line","289-291","Scan lines for the one whose first token is 'Tcp:' and whose header row contains 'ActiveOpens'","lines, head tokens","index, values located")
r("branch","293-296","Parsing values[head.index('ActiveOpens')] as int raises ValueError/IndexError -> return None","values row","returns None")
r("line","297","No 'Tcp:' header line found in the file -> fall through, return None","lines scan exhausted","returns None")

# ---- assigned_process ----
r("function","318-323","Decide whether pid belongs to this session: in the tracked tree, or (for lineage-less kernel threads) via a shared process session id","pid, sid, in_tree dict, sids_then set","bool")
r("branch","319-320","pid is a key of in_tree (already known to descend from session_root) -> assigned=True","pid, in_tree","returns True")
r("branch","321-322","sid is 0 (kernel thread, session 0 carries no lineage) -> assigned=False","sid","returns False")
r("branch","323","Otherwise assigned iff sid was one of the session's process-session ids before the act","sid, sids_then","returns sid in sids_then")

# ---- assigned_counter ----
r("function","326-330","Decide whether the net-open counter's movement is assignable to the act (vs ambient host chatter in the idle gap)","before dict (net, net_ambient), now:int|None","bool|None")
r("branch","328-329","before['net_ambient'] is truthy, or the before/now counter value is None -> not assignable, NOT-EVALUABLE","before.get('net'), before.get('net_ambient'), now","returns None")
r("branch","330","Otherwise assigned iff the counter increased across the act","then, now","returns now > then")

# ---- _slot ----
r("function","335-337","Derive this session+agent's private state subdirectory path from a truncated sha256 of 'session\\x00agent'","state dir, session, agent","pathlib.Path state/effects-<16-hex>")

# ---- _before_path ----
r("function","340-347","Path of the pre-act snapshot file for one act, keyed by tool_use_id when the host supplies one (else a single shared before.json)","slot, act id (tool_use_id)","pathlib.Path")
r("branch","345-346","act is a non-empty id -> key the snapshot file by sha256(act)[:16] so concurrent acts don't share a slot (DL-06)","act string","returns slot/before-<hash>.json")
r("branch","347","act is falsy -> fall back to the single shared slot/before.json","(no act)","returns slot/before.json")

# ---- _ignored ----
r("function","350-354","List top-level gitignored entries by name via `git ls-files -o -i --exclude-standard --directory`, sorted","root, _git() output","list[str]|None")

# ---- _reflog_count ----
r("function","357-362","Count HEAD's reflog entries via `git rev-list -g --count HEAD`","root, _git() output","int|None")
r("branch","361-362","Parsing the count as int raises ValueError -> return None","out.strip()","returns None")

# ---- snapshot ----
r("function","365-419","Record the world before an act (or at session start when opens_act=False): worktree tree, refs, ignored list, reflog count, process table, network counter; write before.json (if opens_act) and observed.json always","state,session,agent,cwd,opens_act,act","dict snap; writes before-*.json and observed.json")
r("branch","376","cwd is a directory -> root=_repo_root(cwd); else root=None (no repo probe on a missing cwd)","os.path.isdir(cwd)","root: str|None")
r("branch","378-386","root exists AND remote not yet measured this session AND REMOTE_RETRY_S elapsed since last try -> measure remote now (before this act's net counter is read) and remember measured/tried/net_after","memory, time.time(), REMOTE_RETRY_S, observe_remote()","memory['remote_measured'], memory['remote_tried'], memory['net_after'] updated; remote.json possibly written")
r("line","387-388","Read the current net_active_opens() counter, and the remembered net_after from the last measurement","net_active_opens(), memory","net_now, net_after")
r("line","392-393","net_ambient = the counter moved since the last recorded net_after even though (as far as this call knows) no act of this session ran in between","net_now, net_after","snap['net_ambient']: bool")
r("branch","394-398","root is set -> populate snap['tree'/'refs'/'ignored'/'reflog'] via worktree_tree/refs/_ignored/_reflog_count","root, slot/index","snap fields set from repo probes")
r("branch","399-400","root is None but cwd is a directory -> populate snap['walk'] via walk_tree(cwd) (non-repo fallback)","cwd","snap['walk'] set")
r("branch","401-405","proc_table() succeeded -> compute own chain, descendants of session_root (kin), and snap['pids'] = kin excluding this process's own ancestry chain","proc_table(), _own_chain(), under()","snap['pids'] dict")
r("loop","409-411","For each previously-remembered spawned pid whose start time in the fresh table still matches, re-add it to snap['pids'] (an orphaned/reparented daemon worker stays this session's)","memory['spawned'], table","snap['pids'][pid]=start for still-alive remembered workers")
r("line","412-414","snap['sids'] = sorted set of process-session ids among kin plus session_root's own session id (0 dropped)","table, kin, session_root","snap['sids']: list[int]")
r("line","415","snap['alive'] = sorted list of every pid currently in /proc (when table is available)","table keys","snap['alive']: list[int]")
r("branch","416-417","opens_act is True -> write this snapshot as the pre-act image for this (session,agent,act)","snap, _before_path()","writes before-*.json")
r("line","418","Always write the operator-facing observed.json from this snapshot","state, root, snap","calls write_observed()")

# ---- observe ----
r("function","422-424","Session-start measurement: call snapshot() with opens_act=False so nothing is left as a pre-act image for a later delta to consume","state,session,agent,cwd","None; writes observed.json (and remote.json opportunistically) with no before-*.json")

# ---- _memory ----
r("function","427-432","Load this slot's persisted session memory (session.json), or a fresh default","slot/session.json","dict")
r("branch","429-432","File missing or invalid JSON (OSError/ValueError) -> return default {'spawns':0,'net_out':False}","session.json read","returns default dict")

# ---- _remember ----
r("function","435-439","Persist the session memory dict back to slot/session.json","memory dict, slot","writes session.json")
r("branch","438-439","Write fails with OSError -> silently ignored (best-effort persistence)","filesystem write","no exception propagated")

# ---- _tree_delta ----
r("function","445-466","Diff two worktree tree shas via `git diff-tree -r --raw --no-renames` into (changed paths, removed paths)","root, before sha, after sha","(list|None, list|None)")
r("branch","446-447","before or after tree sha is missing/empty -> (None,None) NOT-EVALUABLE","before, after","returns (None,None)")
r("branch","448-449","before == after (no tree change) -> ([],[])","before,after equality","returns ([],[])")
r("branch","450-452","`git diff-tree` call itself returns None (git failed) -> (None,None)","_git() diff-tree output","returns (None,None)")
r("branch","462-463","Status is 'D' (deleted), or status in M/T and the after-blob is EMPTY_BLOB while the before-blob was not (K17: emptied file = content gone) -> path counted as removed","fields[status,was,now]","removed.append(path)")
r("branch","464-465","Status in M/T/A and not caught by the emptied case above -> path counted as changed","fields[status]","changed.append(path)")

# ---- _walk_delta ----
r("function","469-476","Diff two path->(size,mtime_ns) walk snapshots into (changed, removed) when neither snapshot is None","before dict, after dict","(list|None, list|None)")
r("branch","470-471","before is None or after is None -> (None,None) NOT-EVALUABLE","before, after","returns (None,None)")
r("line","472","emptied = paths present in both whose after-size is 0 and before-size was not 0 (treated as removed, not changed)","before/after (size,mtime) tuples","emptied: set[str]")
r("line","473-474","changed = sorted paths in after not in emptied whose signature differs from before or that are new","after, before, emptied","changed: list[str]")
r("line","475","removed = sorted union of paths present before but absent after, plus emptied","before keys, after keys, emptied","removed: list[str]")

# ---- report_effects ----
r("function","479-494","Classify the act's stdout text (and the command that produced it) into the report-datum booleans","stdout, command","dict[str,bool] of report_* keys")
r("line","480-482","text = stdout if it's a str else ''; stripped = text.strip(); operands = command.split() if command is a str else []","tool_response.stdout, tool_input.command","text, stripped, operands")
r("line","483","reads_structured = any operand ends with .json/.yaml/.yml/.toml (the act's command targets a structured file)","operands","reads_structured: bool")
r("line","484","passed = REPORT_PASS matches text AND REPORT_FAIL does not (a pass claim is voided by a co-occurring failure claim)","text, REPORT_PASS, REPORT_FAIL","passed: bool")
r("branch","486","report_null = output is exactly 'null', or output is empty while the command read a structured file","stripped, reads_structured","EFFECTS['report_null'] value")
r("branch","487","report_pass = passed","passed","EFFECTS['report_pass'] value")
r("branch","488","report_clean = REPORT_CLEAN matches text AND REPORT_FAIL does not","text, REPORT_CLEAN, REPORT_FAIL","EFFECTS['report_clean'] value")
r("branch","489","report_fail = REPORT_FAIL matches text","text, REPORT_FAIL","EFFECTS['report_fail'] value")
r("branch","490","report_nowarn = passed AND WARNING_LINE does not match text","passed, text, WARNING_LINE","EFFECTS['report_nowarn'] value")
r("branch","491","report_signature = REPORT_SIGNATURE matches text","text, REPORT_SIGNATURE","EFFECTS['report_signature'] value")
r("branch","492","report_structured = _is_structured(stripped)","stripped","EFFECTS['report_structured'] value")
r("branch","493","report_self = _lists_itself(text, command)","text, command","EFFECTS['report_self'] value")

# ---- _is_structured ----
r("function","497-503","Whether stripped stdout parses as JSON and is not the JSON null value","stripped text","bool")
r("branch","498-499","stripped is empty, or its first char is not one of the JSON-value-start chars ([{\"0-9-tf) -> not structured, return False without attempting a parse","stripped[0]","returns False")
r("branch","500-503","json.loads(stripped) raises ValueError -> return False; else return whether the parsed value is not None","stripped","returns bool")

# ---- _segments ----
r("function","506-535","Split a command string into segments on control operators (| ; & newline) OUTSIDE quoted spans, so a quoted mention of an operator is not itself a split point (MATH-10)","command string","list[str] segments")
r("branch","513-516","Inside an open quote and current char equals the quote char -> append it and close the quote","quote state, ch","quote=None, buf appended")
r("branch","517-519","Inside an open double-quote and current char is a backslash with a following char -> treat as an escaped char within the quote, consume both","quote, ch, next char","buf appended with escaped pair, i advanced")
r("branch","513-522","Inside a quote (other than the two cases above) -> just append the char; outside a quote and char is a quote char -> open a new quoted span","quote state, ch","buf appended / quote opened")
r("branch","523-525","Outside a quote and char is a backslash with a following char -> append both chars as one escaped unit, skip ahead","ch, next char","buf appended, i advanced")
r("branch","526-529","Outside a quote and char is one of | ; & newline (control operator) -> flush the current buffer as a completed segment and start a new one","ch, buf","segs.append(''.join(buf)); buf=[]")
r("branch","530-531","Outside a quote, none of the above (ordinary char) -> append to buffer","ch","buf appended")
r("line","533-534","After the scan, flush any remaining buffered text as a final segment","buf","segs.append(''.join(buf))")

# ---- _lists_itself ----
r("function","538-552","Whether the act's output contains a whole, >=3-char segment of its own command text (stated limit: compared as literal text, so shell-expanded parts like $$ are missed)","text, command","bool")
r("branch","546-547","command is not a str, or text is empty -> return False (nothing to compare)","command, text","returns False")
r("branch","548-551","Some stripped segment of the command (from _segments) has length >=3 and appears verbatim in text -> return True","_segments(command), text","returns True")
r("line","552","No segment matched -> return False","(loop exhausted)","returns False")

# ---- trace_effects ----
r("function","558-609","The guard-side effects: whether a quiet act's printed output is corroborated by the pre-act world snapshot (refs, worktree paths, live pids)","text, before snapshot dict, root, quiet(bool 'still'), listed_self","dict with report_ref/report_paths/report_pids/named_paths/named_pids(/report_listing)")
r("line","561","tokens = set of all _TOKEN matches in the act's output text","text","tokens: set[str]")
r("line","562-563","Initialize out with report_ref/report_paths/report_pids/named_paths/named_pids all defaulted to None (NOT-EVALUABLE until a branch below sets them)","(literal)","out dict defaults")
r("branch","564-571","before['refs'] is not None -> report_ref = quiet AND some token equals a branch/remote-tracking short name, or is an ABBREV_FLOOR+ hex string that prefixes some ref's sha","refs_then, tokens, ABBREV_FLOOR","out['report_ref']")
r("branch","572-575","root is set and before['tree'] is set -> list every path in that tree via `git ls-tree -r --name-only`","root, before['tree']","paths: list[str]|None")
r("branch","576-577","(elif) before['walk'] is not None -> paths = list of that walk snapshot's keys","before['walk']","paths: list[str]")
r("line","579-587","For every listed path, register the full path, its basename, and every ancestor-prefix directory into `held` (unused further in this function beyond being computed)","paths","held: set[str]")
r("line","588-599","For every output token (minus leading './' and trailing '/'), match it against each known path by exact equality, path suffix ('/'+t), basename equality, or as a directory prefix (t+'/'); keep matches in `named` (AG-10: only a keyed match pays)","tokens, paths","named: set[str]")
r("branch","600","named_paths = sorted(named) when quiet, else [] (the guard datum is only paid on a quiet/still act)","quiet, named","out['named_paths']")
r("branch","601","report_paths = quiet AND named is non-empty","quiet, named","out['report_paths']")
r("branch","602-608","before['alive'] is not None -> claimed = output tokens that are digit strings naming a pid alive at the snapshot; named_pids=sorted(claimed); report_pids = len(claimed)>=LISTING_FLOOR; report_listing = report_pids AND NOT listed_self","alive, tokens, LISTING_FLOOR, listed_self","out['named_pids'], out['report_pids'], out['report_listing']")

# ---- observe_remote ----
r("function","612-635","Measure remote tracking-branch tips once via `git ls-remote --heads origin` and write remote.json for the operator; fails closed (no write) if the remote can't be listed","state, root","dict[str,str] tips|None; writes remote.json on success")
r("branch","618-619","`git remote` call returns None (git unreachable) -> return None without writing anything","_git() remote output","returns None")
r("branch","622-629","remotes.strip() is non-empty -> list origin's heads via `ls-remote --heads origin`; if that call returns None, return None; else parse each 'sha\\tname' line into tips","remotes, _git() ls-remote output","tips: dict[str,str]")
r("branch","630-634","Writing remote.json raises OSError -> return None (fail closed: no artifact, so a Read of it cannot happen and the demand stays owed)","state/REMOTE write","returns None")
r("line","635","Success path: return tips","tips","returns dict[str,str]")

# ---- write_observed ----
r("function","638-659","Write Keel's own worktree measurement (observed.json) for the operator to Read: head, branch, tree, dirty-paths or walk-paths, refs, live pids","state, root, snap","writes observed.json (best-effort)")
r("line","640-644","Initialize doc with root/session/t/head=None/branch=None/tree/dirty=None/paths=None/refs and pids sorted from snap['pids'] keys","snap fields","doc dict")
r("branch","645-648","root is set and snap['refs'] is not None -> doc['head']=refs['HEAD']; doc['branch'] = stripped `git symbolic-ref -q --short HEAD` or None","root, snap['refs'], _git() symbolic-ref","doc['head'], doc['branch']")
r("branch","649-653","doc['head'] and snap['tree'] are both set -> doc['dirty'] = sorted changed-path names from `git diff-tree --name-status` between HEAD and the snapshot tree (None if that diff-tree call fails)","root, doc['head'], snap['tree']","doc['dirty']")
r("branch","654-655","(elif) snap['walk'] is not None -> doc['paths'] = sorted list of the walked paths","snap['walk']","doc['paths']")
r("branch","656-659","Writing observed.json raises OSError -> silently ignored (best-effort)","state/OBSERVED write","no exception propagated")

# ---- _artifact_read ----
r("function","662-697","Whether a host Read tool_use, per the PostToolUse event, actually returned one of Keel's own artifacts (observed.json/remote.json) unmodified and matching this session/worktree","state, event(tool_input,tool_response,cwd,session_id), name","bool")
r("branch","664-666","event.tool_input.file_path is missing/not a string/empty -> not this artifact, return False","tool_input.file_path","returns False")
r("branch","669-670","tool_response is a dict carrying an 'error' key (host-reported read error) -> return False","tool_response","returns False")
r("branch","671-672","tool_response is a string starting with 'Error' or containing 'exceeds maximum' (host error text) -> return False","tool_response","returns False")
r("branch","675-677","The resolved file_path does not equal the resolved target path, or the target is not an existing file -> return False","path, state/name, pathlib.resolve/is_file","returns False")
r("branch","678-680","Reading/parsing the target JSON raises OSError or ValueError -> return False","target file read/json.loads","returns False")
r("branch","681-682","Parsed JSON top level is not a dict -> return False","doc type","returns False")
r("branch","690-691","cwd resolves to a repo root, and doc['root'] is set, and they differ -> return False (DL-11: datum belongs to a different worktree/session)","event.cwd, _repo_root(cwd), doc['root']","returns False")
r("branch","692-693","name == REMOTE -> return whether doc['tips'] is a dict (remote artifact validity check; short-circuits the session_id check below)","doc['tips'], name","returns bool")
r("branch","694-696","event.session_id is a non-empty string and doc['session'] is neither None nor equal to it -> return False (artifact belongs to another session)","event.session_id, doc['session']","returns False")
r("line","697","Final check for the OBSERVED artifact: return whether 'head' is a key of doc","doc","returns bool")

# ---- read_delta ----
r("function","700-708","Build the effects record for a host Read tool_use: everything world-changing defaults to false/empty, only observed_read/remote_read can be true","state, event","dict[str,Any] full EFFECTS-keyed record")
r("line","702","Initialize every EFFECTS key to False (a Read did nothing to the world, by definition)","EFFECTS keys","out dict all False")
r("line","703-705","Override the list-valued effect keys (files_changed, files_removed, remote_ref_moved, pids_gone, pids_spawned, named_paths, named_pids) to empty lists instead of False","(literal key list)","out[name] = [] for those keys")
r("line","706","observed_read = _artifact_read(state, event, OBSERVED)","state, event","out['observed_read']")
r("line","707","remote_read = _artifact_read(state, event, REMOTE)","state, event","out['remote_read']")

# ---- delta ----
r("function","711-838","What a PostToolUse act did: every EFFECTS key present as a value or None (NOT-EVALUABLE), computed by comparing the pre-act snapshot to the world now","state,session,agent,event","dict[str,Any] full EFFECTS-keyed record; also updates and persists session memory")
r("line","714","Initialize every EFFECTS key to None (NOT-EVALUABLE) before anything is measured","EFFECTS keys","out dict all None")
r("line","715-716","Extract tool_input dict and tool_response dict from the event (empty dict if not present/not a dict)","event.tool_input, event.tool_response","tool_input, response")
r("line","717","Merge in the report_* booleans computed from this act's stdout/command","response.stdout, tool_input.command, report_effects()","out updated with report_null/pass/clean/fail/nowarn/signature/structured/self")
r("line","718","act = event.tool_use_id (may be missing)","event.tool_use_id","act")
r("branch","719-721","Resolve the pre-act snapshot path keyed by act via _before_path; if that keyed file doesn't exist, fall back to the shared slot/before.json","slot, act, filesystem existence","pre: Path")
r("branch","722-726","Reading/parsing the pre-act snapshot JSON raises OSError/ValueError (no snapshot found) -> set out['not_evaluable']='no pre-act snapshot' and return immediately, everything else stays None","pre file read","returns out with not_evaluable set, all effects None")
r("branch","727-730","Deleting the consumed pre-act snapshot file raises OSError -> ignored (best-effort cleanup)","pre.unlink()","no exception propagated")
r("line","731","Load this slot's persisted session memory","slot/session.json via _memory()","memory dict")
r("line","732","root = before.get('root') (the pre-act snapshot's repo root, or None if it wasn't a repo)","before['root']","root")
r("branch","733-778","root is set -> compute file/ref/head/commit effects from a repository comparison (worktree tree diff, ref table diff, reflog scan, ignored-entries diff)","root, before, current git state","changed, removed, out['pre_image','head_moved','remote_ref_moved','head_reset','commit_signed','head_switched']")
r("line","734","after_tree = worktree_tree(root, slot/index): rebuild the current worktree tree object","root, slot/index","after_tree")
r("line","735","changed, removed = _tree_delta(root, before['tree'], after_tree)","before['tree'], after_tree","changed, removed")
r("line","736","out['pre_image'] = before['tree'] (the recoverable pre-image tree sha, for a later revert)","before['tree']","out['pre_image']")
r("line","737-738","after_refs = refs(root); before_refs = before.get('refs')","root, before['refs']","after_refs, before_refs")
r("branch","739-773","Both after_refs and before_refs are not None -> compute head_moved/remote_ref_moved/head_reset/commit_signed/head_switched from comparing the two ref tables and the reflog","after_refs, before_refs","out['head_moved' etc.] set; else those keys stay whatever default/None")
r("line","740-741","old_head/new_head extracted from before_refs/after_refs; head_moved = old_head != new_head","before_refs['HEAD'], after_refs['HEAD']","old_head,new_head,out['head_moved']")
r("line","742-744","remote_ref_moved = sorted names under refs/remotes/ whose sha differs between before_refs and after_refs (union of both ref-tables' remote names)","before_refs, after_refs","out['remote_ref_moved']")
r("branch","745-746","remote_ref_moved is non-empty -> memory['remote_moved']=True, so the session ending knows to ask the remote regardless of the net counter","out['remote_ref_moved']","memory['remote_moved']=True")
r("line","747-749","Default head_reset=False, commit_signed=False, head_switched=False before the finer checks below (a HEAD that didn't move can't have reset/switched/signed)","(literal)","out['head_reset'/'commit_signed'/'head_switched'] = False")
r("branch","750-763","head_moved AND both old_head and new_head are set -> classify the move as reset vs switch vs new-commit-with-signature via merge-base ancestry and cat-file","root, old_head, new_head, before_refs.values()","out['head_reset'/'commit_signed'/'head_switched'] refined")
r("line","751-752","ancestor = `git merge-base --is-ancestor new_head old_head`; head_reset = that succeeded AND (changed or removed) is truthy (worktree moved back too)","root, new_head, old_head, changed, removed","out['head_reset']")
r("line","753","body = `git cat-file commit new_head` output, or '' if unavailable","root, new_head","body")
r("line","760-761","existed = new_head is an ancestor (via merge-base --is-ancestor) of ANY pre-act ref tip -> the commit already existed before the act (a switch), vs a newly created commit","root, new_head, before_refs.values()","existed: bool")
r("line","762","head_switched = existed","existed","out['head_switched']")
r("line","763","commit_signed = (not existed) AND body contains '\\ngpgsig ' (only a newly created commit is examined for a signature the act itself produced)","existed, body","out['commit_signed']")
r("branch","767-773","before['reflog'] and current reflog count are both ints and the count increased -> HEAD moved and returned to itself is still detectable via new reflog entries (EFF-09)","before['reflog'], _reflog_count(root)","then_n, now_n compared")
r("line","769","moves = the newest (now_n - then_n) reflog subject lines via `git reflog show --format=%gs HEAD`","root, then_n, now_n","moves: list[str]")
r("branch","770-771","Any reflog move subject starts with 'reset:' -> out['head_reset']=True (overriding the earlier tree-based determination)","moves","out['head_reset']=True")
r("branch","772-773","Any reflog move subject starts with 'checkout:' AND head_moved is still False (HEAD ended where it began) -> out['head_switched']=True","moves, out['head_moved']","out['head_switched']=True")
r("branch","774-778","removed is not None AND before['ignored'] is not None -> also treat a now-vanished top-level gitignored entry as removed","before['ignored'], removed","removed set may be extended")
r("line","775","now_ignored = current top-level gitignored entries via _ignored(root)","root","now_ignored")
r("branch","776-778","now_ignored is not None -> gone = before-ignored entries no longer present; removed = sorted(removed ∪ gone)","before['ignored'], now_ignored","removed extended")
r("branch","779-781","(else, root is None) changed, removed computed via _walk_delta comparing before['walk'] to a fresh walk_tree(before['cwd']) (or None if cwd no longer a directory)","before['walk'], before['cwd']","changed, removed")
r("line","782","out['files_changed'], out['files_removed'] = changed, removed","changed, removed","out fields set")
r("line","783-784","table = proc_table(); then = before.get('pids') (the pre-act pid->start map)","proc_table(), before['pids']","table, then")
r("branch","785-804","table is not None AND then is not None -> compute pids_gone/pids_spawned/pids_spawned_again and update spawn memory","table, then, before","out['pids_gone'/'pids_spawned'/'pids_spawned_again'], memory updated")
r("line","786-787","own = _own_chain(); in_tree = under(before.get('session_root') or 0, table) (current descendants of the pre-act session root)","before['session_root'], table","own, in_tree")
r("line","788-789","pids_gone = sorted pids that were tracked before and are now either absent from table or present with a different start time (reused pid = different process = still gone)","then, table","out['pids_gone']")
r("line","791","alive_then, sids_then extracted from before['alive']/before['sids']","before['alive'],before['sids']","alive_then, sids_then")
r("line","792-796","spawned = sorted pids in table, excluding own chain, that are new (not in alive_then, or tracked before under a different start time) AND assigned_process()-true against in_tree/sids_then","table, own, alive_then, then, in_tree, sids_then, assigned_process()","spawned: list[int]")
r("line","797","out['pids_spawned'] = spawned","spawned","out field set")
r("line","798","out['pids_spawned_again'] = spawned is non-empty AND memory.get('spawns',0) > 0 (a repeat offender within this session)","spawned, memory['spawns']","out['pids_spawned_again']")
r("branch","799-804","spawned is non-empty -> increment memory['spawns'], and remember each spawned pid's start time in memory['spawned'] (so a later orphaned/reparented copy is still recognized by snapshot())","spawned, table, memory","memory['spawns'] +=1; memory['spawned'] updated")
r("line","805-806","net_now = net_active_opens(); out['net_out'] = assigned_counter(before, net_now)","net_active_opens(), before","out['net_out']")
r("branch","811-812","out['net_out'] is truthy -> memory['net_out']=True (sticky: once the session is known to have transmitted, it stays known for the ending)","out['net_out']","memory['net_out']=True")
r("branch","813-814","(elif) out['net_out'] is None AND memory.get('net_out') is not already True -> memory['net_out']=None (unmeasurable stays unmeasurable unless already proven True; never collapses to False)","out['net_out'], memory['net_out']","memory['net_out']=None")
r("line","815","memory['net_after'] = net_now (marks where the next idle-gap measurement starts)","net_now","memory['net_after']")
r("line","817","spawned = out.get('pids_spawned') or [] (re-read for the guard-side 'still' computation below)","out['pids_spawned']","spawned")
r("line","825","still = changed==[] AND removed==[] AND NOT out['head_moved'] (the act is 'quiet': changed nothing it could have printed about)","changed, removed, out['head_moved']","still: bool")
r("line","826-827","Merge in the guard-side trace effects (report_ref/report_paths/named_paths/named_pids/report_pids/report_listing) computed against the pre-act snapshot and the quiet flag","response.stdout, before, root, still, out['report_self']","out updated via trace_effects()")
r("line","828-829","net_read = None if net_out is None, else (net_out is truthy AND still AND NOT report_fail) — a read of the network is a quiet, non-failing, transmitting act","out['net_out'], still, out['report_fail']","out['net_read']")
r("line","830","report_after_change = out['report_pass'] AND memory.get('changed_since_spawn') truthy (a pass claimed after a file changed since the last process was spawned)","out['report_pass'], memory['changed_since_spawn']","out['report_after_change']")
r("branch","831-832","changed is non-empty -> memory['changed_since_spawn']=True","changed","memory['changed_since_spawn']=True")
r("branch","833-834","spawned is non-empty -> memory['changed_since_spawn']=False (a fresh process resets the 'change since spawn' clock)","spawned","memory['changed_since_spawn']=False")
r("line","835-836","out['observed_read']=False; out['remote_read']=False (a PostToolUse delta is never itself a Read of Keel's own artifacts; only read_delta() can set these true)","(literal)","out fields set False")
r("line","837","Persist updated memory back to slot/session.json","memory, slot","writes session.json via _remember()")

# ---- at_stop ----
r("function","841-890","Session-ending remote check: whether every remote-tracking ref this session appears to have moved actually landed on the remote, measured once and only when the session transmitted","state,session,agent,cwd","dict with remote_ref_moved, remote_landed (and maybe not_evaluable)")
r("line","850-851","slot, memory = this session's persisted state","state,session,agent","slot, memory")
r("line","852","out initialized with remote_ref_moved=None, remote_landed=None","(literal)","out dict")
r("branch","853-858","memory['net_out'] is exactly False AND memory does not have remote_moved set -> no act transmitted and no remote-tracking ref moved locally, so nothing to ask: remote_ref_moved=[], remote_landed=True, return early","memory['net_out'], memory['remote_moved']","returns out early")
r("line","860","root = _repo_root(cwd) if cwd is a directory else None","cwd","root")
r("branch","861-862","root is falsy (not a repository) -> return out as-is (both fields stay None, NOT-EVALUABLE)","root","returns out (Nones)")
r("line","863","remotes = `git remote` output","root","remotes")
r("branch","864-867","remotes call succeeded and remotes.strip() is empty (no remotes configured) -> remote_ref_moved=[], remote_landed=True, return early","remotes","returns out early")
r("line","868","local = refs(root) (current local + tracking refs)","root","local")
r("branch","869-871","local is None (refs couldn't be read) -> out['not_evaluable']='the remote could not be listed', return","local","returns out with not_evaluable")
r("line","872","local_shas = set of every sha in the local ref table","local","local_shas")
r("loop","876-887","For every remote name in remotes.split(): list its heads via `git ls-remote --heads <remote>`","remotes.split()","per-remote listing")
r("branch","878-880","A given remote's ls-remote call returns None (unreachable) -> out['not_evaluable']=f'the remote {remote} could not be listed', return immediately (fails closed on the first unreachable remote)","listing","returns out with not_evaluable")
r("line","883","tracking = local ref table lookup for refs/remotes/<remote>/<branch-name-with-refs/heads/-prefix-stripped>","local, remote, name","tracking: str|None")
r("branch","884-885","tracking is not None (we do have a local tracking ref for this branch) AND tracking != the remote's current sha -> this ref moved; record as 'name' (origin) or 'remote:name' (other remotes)","tracking, sha, remote","moved.append(...)")
r("branch","886-887","(nested) the remote's current sha is not among local_shas -> this moved ref did not land on any local ref (push didn't land, or a foreign move)","sha, local_shas","unlanded.append(name)")
r("line","888","out['remote_ref_moved'] = moved","moved","out field set")
r("line","889","out['remote_landed'] = not unlanded (landed iff nothing was left unlanded)","unlanded","out field set")

with open("/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/ledger/math/code.effects.tsv", "w", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["id","kind","source","what","reads","writes/returns"])
    for i, (kind, src, what, reads, writes) in enumerate(rows, 1):
        w.writerow([f"C-EFF-{i:03d}", kind, src, what, reads, writes])

print("rows:", len(rows))
