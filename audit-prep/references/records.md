# Records

## System description

Sections (Probo's organization context uses these five; other platforms have similar):

- **Product:** what the service does, for whom, and the commitments made to customers
  (security, availability, confidentiality, data location, deletion).
- **Architecture:** components in scope, where they run, data flows, subservice
  organizations with what each provides, and what is out of scope and why.
- **Team:** roles and who holds them (security owner, management signer, outside reviewer),
  and how AI agents are used and who is responsible for them.
- **Processes:** change management, access, incident response, backup and recovery, vendor
  management, risk assessment, monitoring.
- **Customers:** controls the customers are responsible for (their own user access, their
  devices, their exports).

Read every section before an update and send them all back: some platforms clear any
section you leave out. Keep the description draft until management approves it. Write
nothing that the measures and evidence do not support.

## Risks

- About 20 to 30 risks, rated for inherent and residual impact and likelihood, each with an
  owner, a treatment and linked measures.
- The note states the controls as the linked measures state them today, plus any gap the
  evidence still shows, with dates. It never says a control is missing when its measure
  says it is in place, and never "assumes" a control.
- An open exception (a missing DPA, a past-due vulnerability, a disagreement between two
  exports) is written on the linked risk with a date, not only in a task.
- After any change, publish the risk list (Probo: `publishRiskList`).

## Vendors

- One record per vendor: legal name, what it does for you, the data it receives, where it
  is processed, its certification (SOC 2 or ISO report link) and the DPA (a file or the
  vendor's published processor terms).
- Personal data reaches a processor only with a DPA in place. An independent controller
  (a messaging app you use as an individual, a bank) needs none. Say so in its description.
- Offboarded vendors: an offboarding task (delete account, remove secrets and code paths,
  delete data), then archive the record.
- The public subprocessor list, the vendor register and the privacy policy name the same
  vendors.

## Assets and data

- Assets: production projects, accounts, repositories, devices, domains, and the SaaS tools
  when the asset policy says so. Each has an owner and a data class.
- Data categories use only the classes the data classification policy defines.

## Privacy records (GDPR)

Records of processing (as controller and as processor), transfer impact assessments for
each non-EU vendor, a DPIA for high-risk processing (for example, monitoring workers),
legitimate interest assessments, a DPO assessment with its triggers, and data subject
request handling. Publish each register and link it to its measure.

## Business continuity

For each scenario in the plan (data loss, region outage, key person unavailable, account
takeover, vendor failure): a bounded recovery path with a target time, who acts, and how it
was tested. "Wait for the provider" is not a path. Restore tests restore real backups into
copies, compare them, then delete the copies; the report is evidence.
