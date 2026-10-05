# Measures, gaps and evidence

## Measures

- One measure per control activity that exists or will exist: "MFA on every admin
  account", "Restore test once a year". Its description states what is true today, how it
  is checked, and any remaining gap. It names the systems and configuration (policies may
  not; measures should).
- Link each measure to the controls it serves in every framework, to its policy, to its
  risks and to the vendors it depends on.
- State: implemented only with evidence attached (`EVIDENCE_NONE`). In progress while any
  part of the control as written is not shown. Not applicable needs a reason.
- Open tasks on an implemented measure are fine for improvements. The description and the
  risks must state the remaining gap (`MEASURE_OPEN_TASKS`).

## Gaps

- Every gap is a task in the platform: an owner, a deadline, a priority, linked to its
  measure. Recurring work (quarterly access review, yearly restore test) is a recurring
  task.
- Fixes to production go through reviewed changes. A script that changes production asks
  for a typed confirmation, says what it will do, is safe to run twice, and has a matching
  undo or cleanup script. Open a pull request so it is reviewed before anyone runs it.
- Ask before running anything that changes infrastructure, IAM, DNS or repository settings.

## Evidence

Good evidence is primary, dated and machine-readable, and shows the control as written:

| Control | Evidence |
|---|---|
| MFA | Per-user MFA export from each identity provider, plus a screenshot for accounts with no password login |
| Least privilege | IAM policy export (JSON), with a note mapping each service account role to its need |
| Access review | The completed campaign: every account by name, its decision, and a note for each revoke, defer or escalate. Covers keys, tokens and integrations, not only people |
| Change management | Ruleset or branch protection export, workflow files, and a run list showing every production change went through the pipeline |
| Vulnerability deadlines | Finding-level export with found and closed dates, and the risk acceptances with new dates. Not a count |
| Backups and restore | Backup schedule and retention, delete protection, and a restore test report (method, backups used, times, comparison, cleanup, audit log entries) |
| Logging | Log bucket retention and who can read or change logs (from the IAM export) |
| Release signing | Signature or notarization verification of a shipped build, and the workflow condition that guards releases |
| Vendor | The DPA file and the vendor's current SOC 2 or ISO report reference on the vendor record |
| Policy | The approved and signed version in the platform |

Rules:

- Attach it to the measure in the same turn you change the state, then confirm with
  `prep.py evidence` (it uploads and re-reads) or the platform.
- Written records (tabletop exercise, management review, decisions) are documents linked to
  the measure. Registers are published documents.
- When two exports disagree (a JSON and a PDF of the same policy, a note and an export),
  the measure is not implemented until they agree. Write the conflict on the risk.
- Do not offer a summary, a count, a check name or a design document in place of the
  configuration or the run history.
- Remove personal details the auditor does not need, such as other people's emails and
  phone numbers.
