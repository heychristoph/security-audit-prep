# security-audit-prep

An agent skill that prepares a company for a security audit (SOC 2 Type I or II, ISO 27001,
GDPR) in its compliance platform, and keeps it ready. It fills scope, the system
description, vendors, risks, minimal policies, measures and evidence; keeps every record
that states the same fact in agreement; runs readiness checks; and sets up a separate
"<Framework> Criteria, AI Audited" framework so an AI Audit never sits on the real one.

Part of a set:

- **security-audit-prep** (this repo): get ready, stay ready.
- [soc2-auditor](https://github.com/heychristoph/soc2-auditor): runs an AI Audit modeled on
  a SOC 2 Type 1 or Type 2 examination.
- [iso27001-auditor](https://github.com/heychristoph/iso27001-auditor): the same for ISO 27001.

It follows the open [Agent Skills](https://agentskills.io/specification) format, so the
`audit-prep/` folder works with Claude Code, Codex, Cursor, Gemini CLI and other agents that
read `SKILL.md`. Deterministic work runs in plain Python.

## Where the rules come from

Every rule and check comes from a real preparation: a solo-founder SaaS getting ready
for SOC 2 Type I and GDPR in a self-hosted Probo, in September and October 2026. Each
revision was turned into a rule. The AI Audit's verdicts were turned into checks: the
first was adverse because records had drifted apart, the second qualified. The full list
is in [audit-prep/references/lessons.md](audit-prep/references/lessons.md).

## Install

```bash
git clone git@github.com:heychristoph/security-audit-prep.git
pip install -r security-audit-prep/audit-prep/scripts/requirements.txt
```

Make `audit-prep/` visible to your agent: copy or symlink it into the agent's skills
directory (for Claude Code, `~/.claude/skills/audit-prep`), or tell the agent to read
`audit-prep/SKILL.md`.

## Quick start

```bash
cp security-audit-prep/audit-prep/assets/prep.example.yaml prep.yaml   # fill in platform and ids
export PROBO_TOKEN=...
python security-audit-prep/audit-prep/scripts/prep.py status
python security-audit-prep/audit-prep/scripts/prep.py check
python security-audit-prep/audit-prep/scripts/prep.py ai-framework           # plan
python security-audit-prep/audit-prep/scripts/prep.py ai-framework --apply   # create or sync
```

Then ask your agent: *"Prepare us for the SOC 2 audit."*

## Platforms

| Platform | Read | Write | Status |
|---|---|---|---|
| Probo | console GraphQL | MCP tools and evidence upload | tested on v0.297 |
| Vanta | Manage Vanta API | controls, document links, evidence; framework through CSV import | written to the spec, not yet run live |
| Drata | public API v2 | controls, evidence; framework through CSV upload | written to the spec, not yet run live |
| Folder | YAML records in git | everything | tested |

A new platform is one module in `audit-prep/scripts/connectors/` and one page in
`audit-prep/references/connectors/`.

## Tests

```bash
python -m unittest discover -s tests
```

The tests start from the folder template, plant one defect per rule, and check that the
right code fires and that the AI-framework sync is idempotent.

## Not legal or audit advice

The skill prepares records. It does not replace an auditor, and an AI Audit is not an
official audit or attestation.
