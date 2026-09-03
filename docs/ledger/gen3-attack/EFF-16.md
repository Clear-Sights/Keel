# EFF-16 UNVERIFIED [agnostic/unverified] dispatch._effect_record (`if isinstance(event.get('keel_effect'), dict): return`)

## claim
'A record already on the event is a RECORDED session (the corpus) and is kept as-is; a live event never carries one, because the host builds the event and keel_effect is not a field it knows.'

## reproducer
Not executed as an attack. The field is exercised benignly by tests/test_bidirectional_chain.py, which passes a fully synthetic all-false record through the real shim and has it honoured; I did not attempt to make a host event carry the field.

## observed
Reading only: any path by which an all-false (or all-favourable) `keel_effect` reaches the hook -- a host that echoes unknown fields, a replay/corpus tool pointed at a live state dir, a wrapper hook -- turns the entire observer off with no fault recorded, because the early return happens before any snapshot/delta and before any journal note. Reported as a suspicion, not a break.
