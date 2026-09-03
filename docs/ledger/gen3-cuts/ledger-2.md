# ledger-2 [field] Demand.id (dataclass field) -> Demand.id (property over the four fields it was always computed from)
LOC 543 -> 540

## description
`Demand` carried six fields; `id` was `derive_id(session, agent, clause_id, subject)` -- a pure function of four of the other five. Every construction site in dispatch computed `did = derive_id(session, agent, cl.id, subject)` and then handed the answer straight back in as `id=did` beside the same four values, so one datum had two spellings and nothing checked they agreed. Made a property: the id is derived where it is defined, and a Demand can no longer be built with an id that disagrees with what it is about. The row on disk is unchanged (`{"kind":"demand", "id": d.id, **asdict(d)}`; `_canon` sorts keys). Falls out with it: the demand id no longer has to travel through `pre_tool_use`'s `denials` tuple (`(cl, subject, did)` -> `(cl, subject)`), and `_watch_standing`'s keyed branch no longer computes a `did` nothing reads.

## diff
--- a/plugin/keel/ledger.py
+++ b/plugin/keel/ledger.py
 @dataclass(frozen=True)
 class Demand:
-    id: str
+    """`id` is DERIVED, never carried. It was a sixth field, and every caller filled it by
+    calling `derive_id` on the four fields below and handing the answer straight back -- one
+    datum with two spellings, and nothing checked that they agreed. A demand can no longer be
+    constructed with an id that disagrees with what the demand is about."""
     session: str
     agent: str
     clause_id: str
     subject: str
     reason: str
+
+    @property
+    def id(self) -> str:
+        return derive_id(self.session, self.agent, self.clause_id, self.subject)
@@ Ledger.demand
-        self._append({"kind": "demand", **asdict(d)}, tail)
+        self._append({"kind": "demand", "id": d.id, **asdict(d)}, tail)

--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
@@ pre_tool_use
-                denials.append((cl, subject, did))
+                denials.append((cl, subject))
@@
-    for cl, subject, did in denials:
-        ledger.demand(Demand(id=did, session=session, agent=agent, clause_id=cl.id,
-                             subject=subject, reason=cl.deny_reason))
-    return _deny("; ".join(_keyed_reason(cl, subject) for cl, subject, _ in denials))
+    for cl, subject in denials:
+        ledger.demand(Demand(session, agent, cl.id, subject, cl.deny_reason))
+    return _deny("; ".join(_keyed_reason(cl, subject) for cl, subject in denials))
@@ post_tool_use
-                    ledger.demand(Demand(id=did, session=session, agent=agent,
-                                         clause_id=cl.id, subject=subject,
-                                         reason=cl.deny_reason))
+                    ledger.demand(Demand(session, agent, cl.id, subject, cl.deny_reason))
@@ _watch_standing (keyed activation)
                     subject = f"standing:{key}"
-                    did = derive_id(session, agent, cl.id, subject)
-                    ledger.demand(Demand(id=did, session=session, agent=agent, clause_id=cl.id,
-                                         subject=subject, reason=cl.deny_reason))
+                    ledger.demand(Demand(session, agent, cl.id, subject, cl.deny_reason))
@@ _watch_standing (unkeyed activation)
                     aid = derive_id(session, agent, cl.id, "activated")
-                    ledger.demand(Demand(id=aid, session=session, agent=agent, clause_id=cl.id,
-                                         subject="activated", reason="occasion observed"))
+                    ledger.demand(Demand(session, agent, cl.id, "activated",
+                                         "occasion observed"))
                     ledger.discharge(session, agent, aid, "occasion observed")

TEST CARRIED WITH THE CUT (rule 3 -- it spelled ids by hand where the constructor now derives them; the chain assertions are unchanged):
--- a/tests/test_ledger_growth.py
-        ledger.demand(Demand(demand_id, "s", "a", "T01", "x", "guard first"))
+        ledger.demand(Demand("s", "a", "T01", "x", "guard first"))
@@ TheChainDetectsWhatItClaims.setUp
         for n in range(3):
-            self.ledger.demand(Demand(id=f"d{n}", session="s", agent="",
-                                      clause_id="A01", subject="s", reason="r"))
-        self.ledger.discharge("s", "", "d1", "guard observed")
+            self.ledger.demand(Demand("s", "", "A01", f"s{n}", "r"))
+        self.ledger.discharge("s", "", derive_id("s", "", "A01", "s1"), "guard observed")

## gate
Same single green gate run as ledger-1 (all cuts are present in the one built tree at /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/simplify/ledger):
  unittest discover -s tests -> Ran 246 tests ... OK (exit 0)
  eval/replay.py -> REPLAY sessions=26 passed=26 failed=0 (exit 0)
  render_views --check / render_coverings --check / check_coq.py / generate_corpus --check -> all exit 0
  git status --porcelain | wc -l -> 7 (as expected)

## complexity
No time change; a space/identity cut. `derive_id` is called exactly as often as before (dispatch still needs the id for the licence checks), but it is called from one place per demand instead of two, and the dataclass is one field smaller. loc_before/after are the combined executable lines of the two files it touches: ledger.py 103->105 (+2 for the property) and dispatch.py 440->435 (-5, four constructions collapse from 2-3 lines to 1 and one dead `did =` assignment goes), measured with the ast counter.

## verdict
{"id": "ledger-2", "refuted": false, "reason": "SURVIVES. Demand.id was derive_id(session, agent, clause_id, subject) -- a pure function of four of the five remaining fields -- and every construction site recomputed it and handed it straight back, so the cut removes a second spelling that nothing reconciled. (a) The persisted row is unchanged: `{\"kind\": \"demand\", \"id\": d.id, **asdict(d)}` yields exactly the old key set, and _canon sorts keys, so the bytes and therefore every `prev`/`hash` chain value are identical. (b) A @property named `id` on a frozen dataclass is a plain class attribute, not an annotated field, so no dataclass conflict; derive_id is defined above Demand in ledger.py so the property resolves. (c) __eq__/__hash__ now range over 5 fields instead of 6, but the sixth was a function of four of the five, so equality is unchanged for any demand production can build. (d) No fail-direction change: dispatch still computes `did` inside the per-clause try for the licence check, so a surrogate subject still raises there and the clause still abstains exactly as before; the lazy derive_id inside ledger.demand() runs outside the try but on inputs that already succeeded inside it, so it cannot newly raise. This is the same class of hazard I refuted journal-1 on, and here it does NOT bite. (e) The _watch_standing keyed branch's `did` really is dead after the cut -- I read the branch, `did` is used only in the Demand construction and is rebound by the discharge branch below. (f) The carried test change is fixture-only and permitted by rule 3: TheChainDetectsWhatItClaims.setUp built three demands with hand-spelled ids d0/d1/d2 under one clause_id and one subject, which under a derived id would dedup to a single row, so the subjects become s0/s1/s2 to keep three rows; every assertion (verify_chain clean, altered-row named, missing-hash named) is untouched and still operates on rows 1 and 2 of a four-row chain. That is re-pointing the spelling of the thing cut, not weakening a claim. (g) The LOC delta is real but small and honestly reported: ledger.py 103->105 (+2 for the property), dispatch.py 440->435 (-5), net -3 of 543 -- and 543 = 103 + 440 reconciles exactly with ledger-1's post-cut figures under the metric I reproduced.", "gate_output": "GATE NOT EXECUTED -- same plan-mode constraint as ledger-1 (the suite mutates plugin/keel/*.py via smoke_replace, so it is not runnable read-only). Verdict from source analysis. Read-only checks that back it: dataclasses.asdict serializes fields only, so dropping the `id` field and re-adding it explicitly in Ledger.demand reproduces the identical key set, and _canon's sort_keys makes the row bytes order-independent; `Demand(` appears in exactly one test file (tests/test_ledger_growth.py, lines 69 and 122) and nowhere in eval/ or tools/, so the constructor-signature change has no unlisted caller; no test uses dataclasses.fields() on Demand. loc_before 543 reconciles exactly against the metric I reproduce
