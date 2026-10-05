---
name: audit-prep
description: Prepares a company for a security audit (SOC 2 Type I or II, ISO 27001, GDPR and similar) inside its compliance platform (Probo, Vanta, Drata, or a folder of records). Sets scope, writes the system description, vendors, risks, minimal policies, measures and evidence, keeps every record that states the same fact in agreement, runs readiness checks, and sets up a separate "<Framework> Criteria, AI Audited" framework for an AI Audit. Use when asked to prepare for, fill, fix, check or get ready for a SOC 2, ISO 27001 or GDPR program, audit or trust center.
compatibility: Requires Python 3.10+ and pyyaml (scripts/requirements.txt). Platform connectors need network access and API credentials.
metadata:
  version: "0.1.0"
---

# Audit preparation

You prepare the company for an audit and keep it ready. The compliance platform is the
system of record; you fill it, fix it, and prove it. Every rule below exists because
breaking it once cost a revision, a burned budget or an adverse AI Audit. The stories
are in [references/lessons.md](references/lessons.md).

## Rules

1. **The platform is the only to-do list and the truth.** Open items go into platform
   tasks, decisions into the platform (scope in the statement of applicability, audit type
   in the audit record, system boundary in the system description). No plan or status
   files in repos. Re-read the platform in the same turn before any status answer: people
   work in its UI between your turns.
2. **Nothing is done until its evidence is attached.** Before a task is done or a measure
   implemented, attach evidence from a primary source (config export, audit log, command
   output, pull request) and confirm it is there (`prep.py evidence` does both). If only a
   person can supply it, leave the measure in progress and name the file in a task.
3. **Evidence shows the control as written.** A note, a count, a required-check name, a
   summary, or a PDF that disagrees with the machine-readable export is not evidence. When
   two exports disagree, the measure stays in progress and the risk says why.
4. **One fact, every record, one change.** When a measure changes, update in the same
   change every record that states the same fact: linked risks (description, note,
   treatment, owner), policy, vendor or asset, evidence, system description, public pages.
   Republish the registers. Then read them back (`prep.py show`) and run `prep.py check`.
5. **Claims need the source, from every client.** "Never stored", "hash only", MFA,
   encryption, residency and rate limits need the configuration or the code path, checked
   in every client (backend, web, desktop, extension, scripts), not a summary.
6. **Verify, never flip.** A state that looks stale is checked against the real system,
   in both directions. Pressure to look ready is not evidence. Flipping measures to
   implemented without it produced an adverse AI Audit.
7. **Policies are the minimum you follow.** Simple words, one screen, no tool or vendor
   names, limits you can always meet, the person running an agent is responsible for it.
   Approved and signed by the security owner in the platform; published is not approved.
   See [references/policies.md](references/policies.md).
8. **The system description is management's.** Fill every section from facts, keep it
   draft until management approves it, and never describe a control the measures and
   evidence do not support.
9. **The AI Audit gets its own framework.** Create "<Framework> Criteria, AI Audited" and
   put the AI Audit's record there, never on the real framework. An AI Audit is not an
   official audit. See [references/ai-audit.md](references/ai-audit.md).
10. **Ask before anything outward-facing or paid.** Production infrastructure, IAM, DNS,
    repository settings, publishing, sending, deleting data, and any LLM or paid batch job
    (estimate the cost, run one, then ask). Everything inside the platform you just do.
11. **Read before you ask.** Read the terminal, the repos, public pages and the platform
    yourself. Ask only for what only a person knows or can do, once, as a list.
12. **Done means reviewed.** Do not call a change done while a code review is pending, a
    review thread is open or a check is red.

## Setup

```bash
pip install -r scripts/requirements.txt
cp assets/prep.example.yaml <work dir>/prep.yaml     # platform, ids, frameworks in scope
python scripts/prep.py status
```

Run the scripts from the folder that holds `prep.yaml` (or pass `--config`). Credentials
come from the environment; never print them. Platform setup:
[Probo](references/connectors/probo.md), [Vanta](references/connectors/vanta.md),
[Drata](references/connectors/drata.md), [folder](references/connectors/folder.md).

## Workflow

Copy this checklist into your working notes (not a repo file) and keep it current:

```
- [ ] 1. Scope       frameworks, criteria, Type I or II, system boundary
- [ ] 2. Facts       inventory systems, vendors, people, data from primary sources
- [ ] 3. Records     system description, assets, data, vendors, risks, privacy records
- [ ] 4. Policies    minimal set, approved and signed
- [ ] 5. Measures    one per control activity, mapped to every framework, honest state
- [ ] 6. Gaps        tasks in the platform; fixes through reviewed changes
- [ ] 7. Evidence    attached to every implemented measure
- [ ] 8. Check       prep.py check until no errors; decide every warning
- [ ] 9. AI Audit    prep.py ai-framework --apply, run the audit in a fresh context
- [ ] 10. Operate    recurring tasks, findings back into the platform
```

**1. Scope.** Pick frameworks and criteria, record every exclusion with a reason, decide
Type I or Type II, and draw the system boundary. [references/scoping.md](references/scoping.md)

**2. Facts.** Read before writing: repos, cloud configuration (read-only exports), public
pages (subprocessor list, privacy policy, DPA, data and security pages), billing and SSO
for tools. Then ask the people once for what is left. [references/facts.md](references/facts.md)

**3. Records.** Fill the system description (all sections), assets, data categories,
vendors with DPAs, risks with owners, and privacy records. [references/records.md](references/records.md)

**4. Policies.** [references/policies.md](references/policies.md)

**5–7. Measures, gaps and evidence.** Write each measure as the control that exists today,
link it to every framework's controls and to its policy, risks and vendors, and attach
evidence. Gaps become tasks with owners and dates. Production fixes go through reviewed
changes and scripts that ask before they act. [references/evidence.md](references/evidence.md)

**8. Check.** `python scripts/prep.py check`. Errors block the audit. Every warning gets a
decision: fix it, or record why it is fine on the record it names. Rule by rule:
[references/consistency.md](references/consistency.md)

**9. AI Audit.** `python scripts/prep.py ai-framework` shows the plan; `--apply` creates or
syncs the AI-audited framework, `--audit "<name>" --firm "<auditor>"` adds the audit record
on it. Run the AI Audit (for example the soc2-auditor skill) in a fresh context or with
another model. [references/ai-audit.md](references/ai-audit.md)

**10. Operate.** Findings go back into the platform, linked to risks. Recurring reviews,
tests and trainings are recurring tasks. [references/operating.md](references/operating.md)

## Commands

| Command | Use |
|---|---|
| `prep.py status` | Counts, audits, error total and the next step |
| `prep.py check [--only CODES] [--json]` | Readiness checks; exit code 1 while errors remain |
| `prep.py show "<measure>"` | The measure with its risks, documents, tasks and controls, to read back after a change |
| `prep.py evidence "<measure>" FILE...` | Attach files and confirm the platform shows them |
| `prep.py ai-framework [--apply] [--audit NAME --firm F]` | Create or sync "<Framework> Criteria, AI Audited" |
| `prep.py snapshot -o FILE` | Save the normalized snapshot, e.g. before and after a change |

## When things go wrong

- A connector call fails: report the error. Do not conclude the record is missing ("could
  not read approvals" is not "no approval").
- The platform cannot do something through its API (a file upload, publishing a register,
  creating a framework): use the documented fallback in the connector page, or put a task
  for the person with the exact click path. Never write "pending" for something they may
  already have done in the UI; check first.
- A person contradicts the platform ("I already did that"): re-read the platform and the
  system, then fix the record. Do not argue from an earlier fetch.
