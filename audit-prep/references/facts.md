# Facts: inventory before you write

Read primary sources first. Ask the people only for what is left, once, as a list. Write
each fact into the platform record it belongs to, with the date you checked it.

## Sources, in order

1. **What the company already publishes.** Subprocessor page, privacy policy, DPA, terms,
   security, trust and data pages. These are commitments: every one becomes a measure or a
   vendor fact, and a contradiction is a finding. Reuse their wording for vendor
   descriptions, purposes and data locations.
2. **Repos.** READMEs, AGENTS.md, infrastructure as code, CI workflows, rules files
   (database and storage rules), release workflows, SECURITY.md.
3. **Cloud configuration, read-only.** IAM policy as JSON, log buckets and retention, audit
   log settings, backups and point-in-time recovery, delete protection, budgets and alerts,
   uptime checks, regions. Save the machine-readable export; it is the evidence.
4. **Identity and billing.** The SSO app list, the password manager's vault list, and card
   or bank statements: every paid tool is a vendor.
5. **The platform itself.** What is already there. People change it in the UI between your
   turns.

## Vendor categories to ask about

Hosting and cloud; database and storage; auth; email (transactional and marketing);
payments; bank; bookkeeping and tax; CRM; sales outreach and enrichment; support and chat;
analytics; error tracking; logging; code hosting and CI; code scanning; pentest firm; AI
and coding tools (each one: is training on your data off?); password manager; device
management; app stores and code-signing accounts (Apple, Microsoft, browser stores);
domain registrar and DNS; collaboration (docs, chat, video); community channels;
integration platforms and their test accounts; directories and listings. For each: is it
still used? If not, offboard it (task) instead of listing it.

## Claims to verify in code

For every public or policy claim, find the code path in **every** client and the backend:

- "Never stored", "deleted immediately", "memory only": search for writes to storage,
  local files, debug dumps, caches and settings that turn storing on. Check who can set
  those settings.
- "Hashed", "encrypted": find where the value is written, and whether a reversible copy
  exists. Find the key source; a key derived from non-secret values is no encryption.
- "MFA for every admin": the per-user MFA state from each identity provider, plus a list
  of accounts with no password login (they have no MFA switch, which is a fact, not a gap).
- "EU only": the region of every service, including auth, email and integrations, and
  every exception.
- "Least privilege": the IAM export, the roles of every service account and why each needs
  them, and user-managed keys with their dates.

Record a contradiction as a task and a finding, with the file and line. Fix the code or
the claim; never quietly reword the claim.

## People

- Everyone who ever had access, including former interns and contractors: a list of when
  they joined and left, and offboarding records for each departure. "No one else ever had
  access" is rarely true.
- Who is the security owner, who approves policies, and who is the management signer of
  the system description.
