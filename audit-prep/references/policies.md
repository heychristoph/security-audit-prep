# Policies

In a Type II audit every rule is sampled. A rule you do not follow becomes an exception.
So write the minimum an auditor needs, and only rules you follow.

## How to write them

- Simple English, one screen or less per policy. Each rule appears in one policy only;
  others refer to it.
- No names of systems or vendors you might change (password manager, scanner, pentest firm,
  AI tools, cloud). Those, and current settings, go in measures, assets and vendors.
- No "today we..." statements. The policy says what must be true; measures say how.
- Numbers are limits you can always meet ("at least", "within"), not today's exact setting.
- Roles are defined once, in the Information Security Policy: the security owner is the
  founder or someone the founder names. Every other policy says "the security owner".
- AI agents: the person who runs an agent is responsible for what it does. Do not require a
  human approval for each agent action.
- Prefer the lighter control when it passes: MFA, not passkeys or security keys; access
  changes recorded in audit logs, not written approvals. When a rule the auditor needs
  looks heavy (CC6.2: access is approved before it is granted), keep it as light as
  possible and explain why it stays.
- Before each rule ask: does an auditor need it, do we do it, will it survive a tool change?

## The usual set

Information Security (roles, scope, yearly review), Acceptable Use (devices, BYOD with the
device agent, AI tools), Access Control, Change Management (pull requests, review, CI,
deploys from the pipeline), Encryption, Data Classification and Retention (the only class
words anyone may use), Backup, Business Continuity and Disaster Recovery Plan, Incident
Response (including breach notice deadlines), Vulnerability Management (fix deadlines by
severity), Vendor Management (DPA before personal data flows), Risk Management, Logging and
Monitoring, People Security and Code of Conduct, Asset Management, Data Protection (GDPR).
Skip a cookie policy when the site sets no non-essential cookies; the privacy policy covers
it.

## Approval and signing

- The security owner approves each version in the platform (an approval decision), and it
  is signed there. Published with no approver is not approved. A note is not a signature.
- Link each policy to the measures it governs and to the framework controls of those
  measures, in every framework, the AI-audited copy included (`CONTROL_NO_POLICY`).
- Changing a policy means a new version, approved and signed again. The checks flag
  `POLICY_DRAFT_PENDING` when a newer draft sits unpublished.
- Commitments in a policy (deadlines, retention periods, uptime) are the numbers the
  measures, risks and public pages must match.
