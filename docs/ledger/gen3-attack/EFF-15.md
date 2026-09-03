# EFF-15 UNVERIFIED [agnostic/unverified] dispatch._open_effect_denial (`cl.id in committed`) and post_tool_use (`still = {row['clause_id'] ...}`); clauses U02 (keyed on --target), U10 (keyed on the .json path)

## claim
'The guard must name what the demand is keyed on: a Read of other.json does not pay for the traversal of payload.json.' -- that rule is enforced on the effect path but not on the commitment path.

## reproducer
Code path shown by the executed bypass in EFF-07: /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/hook2.py (setsid python3 hook2.py > h2.out 2>&1 </dev/null). The header check that let the unrelated act through is `if cl.id in committed: progress = True`, evaluated before any subject comparison; the keyed-subject variant (two open U10 rows for different .json files, header naming U10) was NOT executed.

## observed
Executed part: a header naming U20 waived open U12/U13/U19 demands as well (h2.out rounds 0-2: 'pre=allow owed=[U12,U13,U19,U20]'). The subject-blindness for keyed clauses (U02/U10) follows from the same two lines but was not driven end to end, so it is reported as unverified.
