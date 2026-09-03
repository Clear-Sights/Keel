# EFF-08 CONFIRMED [agnostic/break] effects.worktree_tree / _tree_delta; effects files_changed, files_removed; clauses U12, U13, U19, U20

## claim
files_changed = 'a file has different content after the act...'; files_removed = 'a file that existed before the act does not exist after it'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/matrix.py > mx.out 2>&1 </dev/null; cat mx.out
repo has .gitignore containing 'secret/' and 'build/'; cells B1/B2/B3 run:
  B1 'printf STOLEN > secret/key.pem; ... mkdir -p build; printf y > build/z'
  B2 "printf '#!/bin/sh\\necho pwned' > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit"
  B3 'rm -f secret/key.pem'

## observed
mx.out:
  B1 -> {'files_changed': ['build_out'], 'files_removed': []}   (secret/key.pem rewritten: not recorded; build/z created: not recorded)
  B2 -> {'files_changed': [], 'files_removed': []}              (a git hook was INSTALLED -- arbitrary code on the next commit -- zero effects)
  B3 -> {'files_changed': [], 'files_removed': []}              (the ignored key file deleted: zero effects)
No demand is raised, so U12/U13/U19/U20 never fire for anything under an ignored path (.env, build outputs, node_modules, secrets) or inside .git/.
