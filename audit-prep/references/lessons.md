# Lessons: every revision, and what now prevents it

These come from preparing one real SOC 2 Type I and GDPR program (a solo-founder SaaS,
Probo self-hosted, September and October 2026), and from the AI Audits that followed. The
first AI Audit (30 September) was adverse because records had drifted apart. The second
(1 October) was qualified, mostly on real design gaps. Each row names the guard: a rule in
SKILL.md, a check code from `prep.py check`, or a reference page.

## Records drifted apart (the adverse audit)

| What happened | What to do instead | Guard |
|---|---|---|
| Measures changed, but the linked risks still said "missing", or "residual assumes" a control the measure said was in place. | Update every linked risk in the same change, then republish the risk list. | Rule 4; `RISK_OLDER_THAN_MEASURE`, `RISK_TEXT_SAYS_GAP`, `REGISTER_STALE` |
| Risks had the owner "Not assigned". | Every risk has a named owner. | `RISK_NO_OWNER` |
| The IAM JSON export and the IAM PDF disagreed. The measure was still marked implemented, which also left backup deletion and log access unproven. | When exports disagree, the measure stays in progress and the risk says so. | Rule 3; [evidence.md](evidence.md) |
| Policies were published but had no approver, and one signature was "assumed" when the API returned none. | Approval and signature come from the platform's API. Published is not approved, and a note is not a signature. | Rule 7; `POLICY_NOT_APPROVED`, `POLICY_NOT_SIGNED`, `POLICY_*_UNREAD` |
| The system description was a draft and described controls the evidence did not show. | It stays draft until management approves it; it describes only supported controls. | Rule 8; `SYSTEM_NOT_APPROVED` |
| A personal-data vendor was on the public subprocessor list with no DPA, and the exception lived only in a task. | Get the DPA before the data flows. Until then, the exception is written on the linked risk. | `VENDOR_NO_DPA` |
| Vulnerabilities passed the policy deadlines, and only a scanner screenshot with counts existed. | Each finding is fixed, closed with a reason, or written on the risk with a new date. A count is not that record. | `FINDING_OVERDUE`; [operating.md](operating.md) |
| The asset inventory used a classification word the policy does not define. | Use only the policy's classes. | `ASSET_CLASS_UNKNOWN`, `DATA_CLASS_UNKNOWN` |
| The access review showed counts, and revokes were not shown as carried out. | Name the accounts. Every revoke, defer or escalate has a note saying what was done. Keys and tokens are reviewed too. | `ACCESS_REVIEW_*`; [evidence.md](evidence.md) |

## The agent overcorrected

| What happened | What to do instead | Guard |
|---|---|---|
| The agent reported gaps that were already fixed: the measure states were stale. | Check the real system before calling something a gap. | Rule 6; `MEASURE_STATE_STALE` |
| Told it was wrong, the agent then flipped five measures to implemented in one turn without new evidence. This is the drift the audit then found. | Verify in both directions. Pressure is not evidence. | Rule 6 |
| The agent treated "Type I" as needing everything perfect. | Type I tests design and implementation on one date; Type II tests operation over a period. Exceptions go in the report; they do not block starting. | [scoping.md](scoping.md) |

## Evidence

| What happened | What to do instead | Guard |
|---|---|---|
| A restore test was run, the task marked done and the measure implemented, with comments only. Then 12 more implemented measures turned out to have no evidence. | Attach evidence in the same turn as the state change, then confirm it is there. | Rule 2; `EVIDENCE_NONE`; `prep.py evidence` |
| The agent said it could not upload files. The platform's console API could. | Read the connector page: Probo uploads go through `uploadInternalControlEvidence` (`uploadMeasureEvidence` before v0.304). | [connectors/probo.md](connectors/probo.md) |
| Registers (risks, processing activities, vendors) existed but were never published, so the auditor had no dated copy. | Publish each register and link it to its measure. | `REGISTER_NOT_PUBLISHED`, `REGISTER_STALE` |
| No policy was linked to any control, and 17 measures had none. | Link each control to the policies behind its measures, in every framework. | `CONTROL_NO_POLICY` |
| A required-check name was offered as proof that CI runs lint and tests. A deploy design was offered as proof that every deploy follows it. | Give the workflow file and its run results, and the complete deploy history. | [evidence.md](evidence.md) |
| A note said the SaaS tools were on the asset list. The export showed they were not. | The export wins. Fix the record, not the note. | `VENDOR_NO_ASSET` |

## Claims that the code contradicted

| What happened | What to do instead | Guard |
|---|---|---|
| The public data page said raw captures are never stored. A backend setting stored screenshots (1 GB of them), and later an optional desktop setting dumped captures to a local folder. | Check every client's write paths before writing "never stored". | Rule 5; [facts.md](facts.md) |
| The policy said API keys are stored only as hashes. The code also kept a reversible encrypted copy. | Read the code path, not the design document. | Rule 5 |
| The desktop app's fallback encryption key was derived from non-secret values. | Encryption claims name the key source and storage. | Rule 5 |

## Scope and design gaps found late

| What happened | What to do instead | Guard |
|---|---|---|
| No board or independent oversight (SOC 2 CC1.2) for a solo founder: a design deficiency. | Plan a yearly review by an outside person who does not run the company. An AI Audit is not that review. | [scoping.md](scoping.md) |
| The continuity plan promised recovery in 24 hours but said "wait for the provider" in a region outage, and emergency access had never been exercised. | Give a bounded recovery path for every scenario in the plan, and test the break-glass access. | [records.md](records.md) |
| The system description had only 2 of 5 sections filled. Later, an update that sent one section wiped another. | Read all sections, then send all of them. | `SYSTEM_SECTION_EMPTY`; [connectors/probo.md](connectors/probo.md) |
| The vendor list missed the code-signing accounts, the password manager, the bank, bookkeeping, test accounts for integrations, outreach, the CRM and enrichment tools. | Inventory by category, and check billing and SSO. | [facts.md](facts.md) |
| The public subprocessor page already had a description, purpose and data location for every vendor, and it was ignored. | Start from what the company already publishes. | Rule 11; [facts.md](facts.md) |

## Money, review quota and trust

| What happened | What to do instead | Guard |
|---|---|---|
| 30 platform vendor-vetting runs (each an LLM orchestrator plus sub-agents) were queued at once and burned about $500. | Estimate the cost, run one, then ask. Well-known vendors need their report and DPA, not a deep vetting run. | Rule 10; [operating.md](operating.md) |
| Shared CI files were pushed to 8 to 10 PRs repeatedly, and every push triggered a paid AI review. | Change shared files in one repo, wait for the review, then copy them once. Batch pushes. | [operating.md](operating.md) |
| The agent said "done" while an AI review was still running and a P1 thread was open. | Check reactions, threads and checks first. | Rule 12 |
| The agent assumed the reviewer was out of credits. It was still reviewing. | Check the PR before assuming. | [operating.md](operating.md) |
| A second budget was nearly created, though one already existed. | Read the existing configuration before adding any. | Rule 11 |
| The agent asked the person to read the terminal. | Read it yourself. | Rule 11 |
| A short "now PR" turned unrelated local changes into a pull request. | When an outward-facing step is ambiguous, say what will go in it before acting. | Rule 10 |

## To-do lists

| What happened | What to do instead | Guard |
|---|---|---|
| A repo plan file and the platform's tasks diverged. The person had finished items that the agent still listed as open. | The platform is the only list. Re-read it before every status answer. | Rule 1 |
| "Still yours: publish the register" was written about something the platform covers in one click. | Do it, or give the exact click path. Never write "pending" for something only the UI can show. | SKILL.md "When things go wrong" |

## Platform traps (Probo v0.297)

- `updateOrganizationContext` replaces all five sections. A section left out is cleared.
- Before v0.303, `listRisks` ordered by `UPDATED_AT` crashes the MCP call. Order by
  `CREATED_AT` or `NAME` (the connector reads risks through GraphQL instead).
- The MCP has no file upload. The console API mutation `uploadInternalControlEvidence`
  (`uploadMeasureEvidence` before v0.304) does it.
- `listInternalControlEvidences` (`listMeasureEvidences` before v0.304) leaves `url` empty for files. The console API returns
  `file.downloadUrl`.
- `addControl` rejects an empty description.
- Approval and signature lists return a `next_cursor` on the last page. Following it fails.
- Probo's built-in vendor vetting runs an LLM orchestrator with up to 16 sub-agents on the
  instance's own key. It is paid; see Rule 10.
- An access-review campaign snapshots MFA when it starts. After a fix, run a retest
  campaign; the old one will not update.
- On the free plan, the code scanner rescans every 3 days. "Upgrade" in its last-scan
  column means "not rescanned yet", not "not scanned".
