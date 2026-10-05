# Operating

## Recurring tasks

Make each one a recurring task in the platform, linked to its measure, so its evidence
lands where the auditor looks:

| Every | Task |
|---|---|
| Quarter | Access review (people, service accounts, keys, tokens, integrations); vulnerability review against the fix deadlines |
| Year | Risk assessment; policy review, re-approval and signing; security training; incident response tabletop; restore test; vendor review (fresh SOC 2 reports and DPAs); asset inventory review; independent oversight review; continuity exercise including break-glass access; pentest |
| Change | Pull request, automated review, required checks, deploy from the pipeline |

## Change management with AI review

- Protect the default branch. Require a pull request, passing checks (CI, secret scan,
  dependency scan, AI review) and resolved review threads. Allow admin bypass only through a
  pull request, so it is logged.
- An AI reviewer on every pull request is the compensating control when there is no second
  human. The change policy says so, and the risk register keeps the residual risk.
- Shared workflow files change in one master repo first. Wait for its review, fix, then
  copy them unchanged to the other repos, one push per branch. Every push can trigger a
  paid review.
- Never call a change done while a review is pending, a thread is open or a check is red.
  Look at the pull request: a reviewer still working is not a reviewer out of credits.

## Cost guardrails

- Platform AI features (vendor vetting, evidence description, assistants) run on someone's
  API key. Before any batch: estimate the cost (tokens per run × runs × price), run one,
  measure it, and ask. Stop the queue as soon as runs fail.
- Well-known vendors need their SOC 2 or ISO report and DPA, read from their trust pages.
  A deep vetting run adds cost, not audit value.
- Prefer configuration the platform can read through an API over evidence a person has to
  screenshot.

## Working with people

- Re-read the platform before every status answer. Report what is open from the platform,
  not from memory.
- Put what you need from a person into a task with the exact steps and click path.
- When a short instruction could mean an outward-facing action (a PR, a push, a deploy),
  say what it will include before you do it.
- When a request costs money or adds work with no audit value, say so and propose the
  smaller option. Do not just do it.
