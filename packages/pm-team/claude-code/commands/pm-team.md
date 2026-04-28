---
description: Drive a product idea from intent through interview, parallel feature specs, reviewer gate, spec PR, and (after your approval) work-item creation on the ADO or GitHub Kanban board. Three modes — fresh, feedback, approved.
argument-hint: <intent...> | feedback <pr#> | approved <pr#>
---

User arguments: $ARGUMENTS

Trigger the `pm-team` skill, which routes between three modes based on the argument shape:

- `feedback <pr#>` (e.g., `feedback 1234`) → **feedback mode**: fetch PR comments, dispatch revisions, re-review, push to the same branch.
- `approved <pr#>` (e.g., `approved 1234`) → **approved mode**: verify the spec PR is merged, then dispatch `board-manager` to seed the board with WIs.
- Anything else → **fresh mode**: treat `$ARGUMENTS` as the user's initial intent statement; conduct the interactive interview, decompose into features, fan out to `requirements-analyst`s, gate via `spec-reviewer`, commit specs, open the spec PR, and stop for human review.

The platform (Azure DevOps vs GitHub) is auto-detected from `git remote get-url origin`. Don't ask the user to specify it unless detection is ambiguous; if the user passed `--platform <ado|gh>` in `$ARGUMENTS`, honor it.

Do not perform the workflow yourself in the main agent — load and execute the `pm-team` skill, which has the full mode-routed workflow.
