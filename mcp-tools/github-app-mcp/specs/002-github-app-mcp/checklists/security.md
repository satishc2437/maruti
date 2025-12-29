# Security/Policy Requirements Quality Checklist: github-app-mcp

**Purpose**: Validate that the written requirements for authentication, authorization/policy guardrails, secret handling, and auditability are complete, clear, consistent, and objectively verifiable (unit tests for the spec, not implementation tests).
**Created**: 2025-12-22
**Feature**: specs/002-github-app-mcp/spec.md

**Defaults used**:
- **Audience/Timing**: PR reviewer gate
- **Scope**: Auth/policy/audit/secret-handling requirements only (not full product spec)
- **NFR posture**: Treat unspecified limits/performance/retry/rate-limit semantics as requirements-quality gaps to be resolved in the spec

## Requirement Completeness

- [x] CHK001 - Are all supported high-level operations explicitly enumerated (and nothing else) in the requirements? [Completeness, Spec §FR-005]
- [x] CHK002 - Are minimum read capabilities defined at the same level of specificity as minimum write capabilities? [Completeness, Spec §FR-006, Spec §FR-007]
- [x] CHK003 - Are repository scoping requirements fully specified (install-scope + optional allowlist + how the allowlist is configured)? [Completeness, Spec §FR-004, Spec §Assumptions]
- [x] CHK004 - Are all “secret” categories explicitly listed (private key material, private key path, JWT, installation token, installation identifiers) so redaction expectations are unambiguous? [Gap]
- [x] CHK005 - Are audit log record fields defined precisely (required vs optional fields, and an explicit schema)? [Gap, Spec §FR-011]
- [x] CHK006 - Are denial behaviors specified for each class of invalid request (out-of-scope repo, unsupported operation, policy violation, insufficient permissions, rate limiting)? [Completeness, Spec §Edge Cases, Spec §FR-013]
- [x] CHK007 - Are startup/configuration failure requirements defined (missing env var, unreadable key file, invalid key) and how those failures are surfaced safely? [Gap, Spec §FR-003a]
- [x] CHK008 - Are requirements defined for how large file changes are handled (max file size, max total payload, binary handling) and whether they are supported/excluded? [Gap, Spec §Edge Cases]

## Requirement Clarity

- [x] CHK009 - Is “exclusively as a GitHub App (not a user)” defined in a way that can be objectively validated (e.g., what identity fields/artifact attribution prove this)? [Clarity, Spec §FR-001, Spec §FR-010]
- [x] CHK010 - Is the prohibition on PATs/personal credentials defined with clear detection boundaries (what counts as “includes a PAT”, and how false positives/negatives are treated)? [Clarity, Spec §FR-002, Spec §Acceptance Criteria]
- [x] CHK011 - Is “installation identifiers must remain opaque to agents” defined precisely (which identifiers are included/excluded, and do URLs/IDs returned from GitHub count)? [Ambiguity, Spec §FR-012]
- [x] CHK012 - Is “no generic ‘call arbitrary GitHub API’ capability” operationally defined (e.g., prohibition on raw path/method passthrough, headers, GraphQL queries)? [Clarity, Spec §FR-005]
- [x] CHK013 - Are “policy guardrails” defined with concrete configuration knobs and decision rules (what inputs drive allow/deny/alternate outcomes)? [Clarity, Spec §FR-008, Spec §FR-009]
- [x] CHK014 - Is “protected branch” defined (default branch only vs any protected branch, and whether detection is required vs config-driven)? [Ambiguity, Spec §FR-008, Spec §User Story 2]
- [x] CHK015 - Are “clear, non-secret error messages” defined with examples of permitted vs prohibited details? [Clarity, Spec §FR-013]

## Requirement Consistency

- [x] CHK016 - Do the allow-list requirements align between the requirements section and the acceptance criteria (no operation appears in one but not the other)? [Consistency, Spec §FR-005, Spec §Acceptance Criteria]
- [x] CHK017 - Do the audit requirements align between FR-011 and Success Criteria SC-001 (same completeness expectation and same field set)? [Consistency, Spec §FR-011, Spec §Success Criteria]
- [x] CHK018 - Are policy behaviors consistent across user stories (e.g., PR-only workflow requirements do not conflict with minimum write operations)? [Consistency, Spec §User Story 1, Spec §User Story 2, Spec §FR-007, Spec §FR-008]
- [x] CHK019 - Are the “no secret exposure” constraints consistent across outputs, logs, and errors (no conflicting guidance in any section)? [Consistency, Spec §FR-003, Spec §FR-012, Spec §FR-013]

## Acceptance Criteria Quality

- [x] CHK020 - Do acceptance criteria cover both positive and negative cases for each key guardrail (PAT rejection, out-of-scope repo, unsupported op, protected-branch denial/alternate, audit always)? [Coverage, Spec §Acceptance Criteria]
- [x] CHK021 - Are acceptance criteria uniquely numbered without duplicates (to support traceability), and do they reference the correct FRs? [Traceability, Spec §Acceptance Criteria]
- [x] CHK022 - Do acceptance criteria state observable outputs without relying on hidden internal behavior (e.g., correlation IDs, safe error text, URLs/IDs) and avoid requiring secrets for verification? [Measurability, Spec §Acceptance Criteria, Spec §FR-011]
- [x] CHK023 - Is “PR-based alternative” defined as a concrete outcome (whether it is guidance-only vs server performs branch+PR automatically), and is that consistent across the doc? [Ambiguity, Spec §User Story 2, Spec §Acceptance Criteria]

## Scenario Coverage

- [x] CHK024 - Are primary scenarios defined for the full MVP flow (branch → commit → PR → comment) including preconditions and required inputs? [Completeness, Spec §User Story 1]
- [x] CHK025 - Are exception scenarios defined for “app not installed” and “insufficient permissions” with distinct, measurable agent-facing outcomes? [Coverage, Spec §Edge Cases, Spec §FR-004, Spec §FR-013]
- [x] CHK026 - Are rate limit and transient failure scenarios specified with clear expectations (retry policy as a requirement vs implementation detail, and what agents see)? [Gap, Spec §Edge Cases]
- [x] CHK027 - Are revocation/uninstall scenarios defined with expected error semantics and audit outcomes? [Coverage, Spec §User Story 3, Spec §Acceptance Criteria]

## Edge Case Coverage

- [x] CHK028 - Is branch name conflict behavior specified (idempotency vs error, and whether auto-suffixing is allowed)? [Gap, Spec §Edge Cases]
- [x] CHK029 - Is behavior specified for partial success within multi-step operations (e.g., commit succeeds but PR creation fails) including audit semantics? [Gap]
- [x] CHK030 - Are requirements defined for request size/time bounds to prevent runaway operations (max files, max bytes, max latency, timeout behavior)? [Gap, Spec §Dependencies & Constraints]

## Non-Functional Requirements

- [x] CHK031 - Are performance expectations quantified beyond “human-scale” (e.g., target latency ranges, backoff caps) so they are testable? [Gap, Spec §Dependencies & Constraints]
- [x] CHK032 - Are security requirements for network egress explicitly specified (GitHub API host allowlist, redirects, proxy behavior)? [Gap]
- [x] CHK033 - Are audit log privacy requirements specified (whether file contents, commit diffs, or request bodies may be logged; required redaction strategy)? [Completeness, Spec §FR-011, Spec §FR-012]

## Dependencies & Assumptions

- [x] CHK034 - Are all host-provided configuration inputs specified (names, required/optional, format), including the private key *path* requirement and its confidentiality expectations? [Completeness, Spec §FR-003a, Spec §Dependencies & Constraints]
- [x] CHK035 - Are assumptions about installation selection/enumeration explicitly stated as requirements or enforced constraints (e.g., agents cannot enumerate installations)? [Clarity, Spec §Assumptions]

## Ambiguities & Conflicts

- [x] CHK036 - Is there any ambiguity about whether returning GitHub artifact IDs/URLs could leak installation scope, and is that addressed explicitly? [Ambiguity, Spec §FR-012]
- [x] CHK037 - Are there any conflicts between “keep installation identifiers opaque” and the need for operational debugging/support (e.g., what correlation IDs link to internally)? [Conflict, Spec §FR-011, Spec §FR-012]
- [x] CHK038 - Is the meaning of “high-level intent” sufficiently defined to distinguish allowed requests from prohibited low-level ones (examples, boundaries, and rejection criteria)? [Ambiguity, Spec §FR-009]
