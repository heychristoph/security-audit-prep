# Consistency: one fact, every record

An auditor reads a measure, its risks, the policy, the vendor, the evidence and the system
description side by side. When they disagree, the auditor concludes the control is not
designed. That is what made the first AI Audit adverse.

## The change procedure

When any fact changes (a control added, a gap closed, a vendor added or dropped, a
setting changed):

1. Change the measure: state, description, evidence.
2. Change every linked risk: description, note, treatment, owner. Then publish the risk list.
3. Change the policy if a rule changed (new version, approve, sign).
4. Change the vendor, asset or data record if the fact lives there, and republish its
   register.
5. Change the system description if it describes the control.
6. Change public pages (subprocessor list, privacy policy, data page) through a reviewed
   pull request.
7. If an AI-audited framework exists, run `prep.py ai-framework --apply` after any change
   to control links or scope.
8. Read back: `prep.py show "<measure>"`, then `prep.py check`. Done means both agree.

## Check codes

| Code | Level | Meaning and fix |
|---|---|---|
| `EVIDENCE_NONE` | error | Implemented with no evidence: attach it, or set the measure back to in progress |
| `EVIDENCE_POLICY_ONLY` | warn | Only policies linked: fine when the policy is the control, otherwise attach the record |
| `MEASURE_STATE_STALE` | warn | All tasks done but not implemented: check the system, then attach evidence and update |
| `MEASURE_UNKNOWN` | warn | Unknown state: find out |
| `MEASURE_OPEN_TASKS` | warn | Implemented with open tasks: the description and risks must state the gap |
| `MEASURE_NO_CONTROL` | warn | Not mapped to any control in scope |
| `RISK_NO_OWNER` | error | Assign an owner |
| `RISK_OLDER_THAN_MEASURE` | error | A linked measure changed after the risk: update the risk, publish the risk list |
| `RISK_TEXT_SAYS_GAP` | warn | Every measure is implemented, but the risk text still says the control is missing |
| `RISK_NO_MEASURE` | warn | Mitigated with no measure linked |
| `REGISTER_NOT_PUBLISHED`, `REGISTER_STALE` | error for risks, warn otherwise | Publish the register again |
| `POLICY_NOT_PUBLISHED`, `POLICY_NOT_APPROVED`, `POLICY_NOT_SIGNED` | error | Publish, approve and sign in the platform |
| `POLICY_APPROVAL_UNREAD`, `POLICY_SIGNATURE_UNREAD` | error | The read failed: fix the read; never assume none or some |
| `POLICY_DRAFT_PENDING` | warn | A newer draft is unpublished |
| `SYSTEM_SECTION_EMPTY` | error | Fill it; send all sections on update |
| `SYSTEM_NOT_APPROVED` | warn | Management approval pending: disclose it |
| `VENDOR_NO_DPA` | error | Personal data without a DPA: attach it, or write the exception on the risk |
| `VENDOR_NO_ASSET` | warn | Vendor missing from the asset list (turn off with `checks.vendor_assets: false`) |
| `DATA_CLASS_UNKNOWN`, `ASSET_CLASS_UNKNOWN`, `ASSET_NO_CLASS` | warn | Use only the policy's classes |
| `CONTROL_NOT_COVERED` | error | Applicable control with no implemented measure |
| `CONTROL_NA_NO_REASON` | error | Not applicable needs a reason |
| `CONTROL_NO_SCOPE_DECISION` | warn | Decide applicable or not |
| `CONTROL_NO_POLICY` | warn | Link the policy behind the control's measures |
| `AI_FRAMEWORK_MISSING` | warn | Create it before the AI Audit |
| `AI_FRAMEWORK_DRIFT` | error | Run `prep.py ai-framework --apply` |
| `AI_AUDIT_ON_REAL_FRAMEWORK` | error | Move the AI Audit to the AI-audited framework |
| `FINDING_OVERDUE` | error | Fix it, close it with a reason, or put it on a risk with a new date |
| `FINDING_OVERDUE_ON_RISK` | warn | The risk must state the new date |
| `FINDING_NO_DUE`, `FINDING_NO_OWNER` | warn | Give the finding a due date and an owner |
| `TASK_OVERDUE`, `TASK_NO_ASSIGNEE` | warn | Re-plan or assign |
| `ACCESS_REVIEW_NONE`, `ACCESS_REVIEW_UNDECIDED` | error | Complete a review with a decision for every account |
| `ACCESS_REVIEW_NO_NOTE`, `ACCESS_REVIEW_OLD` | warn | Add notes; run the next review |
| `PERSON_ENDED_ACTIVE` | warn | Offboard |
| `CONNECTOR` | warn | The connector could not read something; the related checks may be incomplete |

Settings for the checks live under `checks:` in prep.yaml (see assets/prep.example.yaml).

## What the checks cannot see

Do these by reading: claims against code (facts.md), exports that disagree, a DPA link
that points to a summary page instead of processor terms, vendor descriptions against the
public subprocessor page, and whether evidence shows the control as written.
