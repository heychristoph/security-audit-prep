# The AI Audit and its framework

An AI Audit is a rehearsal run by a model. It is not an official audit, not an
attestation, and not a report a CPA firm can issue. Keep it apart from the real thing.

## Why a separate framework

An audit record sits on a framework, and trust portals show frameworks and their audits.
Putting the AI Audit on the real framework would present it as the real audit. So:

- The real framework (for example "SOC 2") keeps the official audit, now or later.
- A copy named "<Framework> Criteria, AI Audited" (for example "SOC 2 Criteria, AI
  Audited") carries the AI Audit. Its public description says it is an AI Audit and not an
  official audit, in one sentence. The public does not need internal details.

The copy has the same controls, with the same measure links, policy links and scope
decisions. Measures, evidence and documents are shared, not copied: evidence attached once
counts for both. Only the links exist twice, so they must stay in sync.

## Create and sync

```bash
python scripts/prep.py ai-framework                     # plan: every difference
python scripts/prep.py ai-framework --apply             # create or sync, then re-check
python scripts/prep.py ai-framework --apply \
  --audit "SOC 2 Type I, AI Audit" --firm "soc2-auditor (AI Audit, not an official audit)"
```

- Safe to re-run: a second run finds nothing to do.
- Links that exist only in the AI copy are removed, unless you pass `--no-prune`.
- A control that exists only in the copy is reported, not deleted. Delete it in the
  platform if the real framework dropped it.
- On platforms without a framework API (Vanta, Drata), the first run writes a CSV of the
  controls. Import it as a custom framework with the exact name, then run again to link.
- `prep.py check` reports `AI_FRAMEWORK_DRIFT` whenever the two differ, and
  `AI_AUDIT_ON_REAL_FRAMEWORK` if an AI Audit record sits on the real framework.

Whenever you link or unlink a measure or policy on a control, or change a scope decision,
the copy must follow. Run `--apply` after the change, or the check will fail.

## Running the AI Audit

1. `prep.py check` has no errors, and every warning has a decision.
2. Run the auditor in a fresh context, ideally with a different model than the one that
   prepared the records. The preparer should not grade its own work. The soc2-auditor
   skill (github.com/heychristoph/soc2-auditor) reads Probo, Vanta, Drata or a folder; point
   it at the AI-audited framework's id.
3. Findings go back into the platform as findings linked to the audit and to the risks
   they affect, with owners and due dates.
4. The report contains internal security detail. Attach it to the private audit record
   only when the person explicitly says so. Never publish it on a portal without that.
5. Fixes made after the as-of date do not change that report. They count toward the next
   run, with a new date.

## What AI Audits caught that preparation missed

Read lessons.md for the full list: records that disagreed, policies published without
approval, a vendor without a DPA, claims contradicted by code paths, no independent
oversight, and a continuity plan with no bounded recovery path. Run the checks and the
claim reviews in facts.md before the audit, not after.
