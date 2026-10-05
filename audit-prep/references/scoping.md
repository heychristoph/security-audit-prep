# Scope

Decide these first, and record each decision in the platform, not in a repo file.

## Frameworks and criteria

- **SOC 2.** Security (CC1–CC9) is always in. Add Availability (A1) and Confidentiality (C1)
  when customers depend on uptime or send confidential data. That covers almost every B2B
  SaaS. Processing Integrity (PI1) and Privacy (P1–P8) are often excluded. Record the
  reason in the statement of applicability, for example "AI output is non-deterministic by
  design" or "privacy is covered by the GDPR framework".
- **GDPR, ISO 27001 and others** are separate frameworks in the same platform. Map them to
  the same measures, so one control set serves every framework. Never duplicate measures
  per framework.
- Every control gets a scope decision: applicable, or not applicable with a reason
  (`CONTROL_NO_SCOPE_DECISION`, `CONTROL_NA_NO_REASON`).

## Type I or Type II

- **Type I**: are the controls designed well and in place on one date? No track record is
  needed. Open exceptions appear in the report; they do not block starting.
- **Type II**: did the controls operate during a period (usually 3–12 months)? Every rule
  in every policy is sampled, so write only rules you follow (see policies.md). The period
  cannot start before change management (pull requests, review, protected branches) is
  live, because every change in the period is sampled.
- Record the choice on the audit record in the platform.

## System boundary

- In scope: every component that stores, processes or transmits customer data. That means
  clients (web, desktop, browser extension, mobile), backend, hosting, integrations, CI/CD,
  and the compliance platform itself if it holds evidence.
- Out of scope needs a reason, for example a marketing site with no customer data. When the
  site carries privacy or data claims, keep it in scope; the claims are commitments.
- Subservice organizations (cloud, payment, email and so on) are carved out by name, with
  what each provides. Their SOC 2 reports and DPAs go on the vendor records.
- Write the boundary into the system description's architecture section.

## Small teams and solo founders

Design gaps an auditor will raise. Plan them from the start:

- **Independent oversight (CC1.2).** Without a board, name an outside person (advisor,
  investor or fractional CISO) who reviews risks, incidents, findings and control status
  once a year. The record names the reviewer and the date. An AI Audit is not this review.
- **Segregation of duties in change management (CC8.1).** Pull requests with an automated
  AI review and required checks are the compensating control for a second human. The
  change policy describes it, and the risk register records the residual risk.
- **Emergency access.** A break-glass path (password manager emergency access or a sealed
  envelope) with a named trusted person, exercised once and recorded.
- **Key-person risk.** The continuity plan says who can operate the system if the founder
  cannot.

## Auditor

Before booking, ask whether the auditor accepts exports from your platform and an AI review
as the compensating control for a second reviewer. For a rehearsal, run the AI Audit on the
separate AI-audited framework first (ai-audit.md).
