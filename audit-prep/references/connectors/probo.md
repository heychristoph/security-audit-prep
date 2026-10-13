# Probo

Reads use the console GraphQL API (`/api/console/v1/graphql`), writes use the MCP tools
(`/api/mcp/v1`), and evidence uploads use the console mutation `uploadInternalControlEvidence`.
The same OAuth token works for all three. Tested against Probo v0.297 (self-hosted).

Probo v0.304 renamed measures to "internal controls" in GraphQL, MCP and the CLI: the MCP
tools are `getInternalControl`, `listInternalControlEvidences` and so on, and before v0.304
they were `getMeasure`, `listMeasureEvidences`, and the upload was `uploadMeasureEvidence`.
The connector detects which names the instance uses. This skill still says "measure".

## Setup

1. In Probo, create an OAuth access token for your account (Settings, API access).
2. `prep.yaml`:

```yaml
platform: probo
options:
  url: https://probo.example.com
  organization_id: <id from the console URL>
  # token_command: <command that prints the token>   # optional, instead of PROBO_TOKEN
```

3. `export PROBO_TOKEN=...`, or set `token_command` to a command that prints it (for
   example, one that reads the Authorization header of the agent's Probo MCP entry).
   The token is never printed.

## Mapping

| Probo | Snapshot |
|---|---|
| Framework, its controls (section title = ref) | frameworks, controls |
| Statements of applicability | applicability (one statement of applicability can hold the statements of several frameworks) |
| Measures, evidence count, linked documents, risks, tasks | measures |
| Risks (owner, note, treatment, linked measures) | risks |
| Documents, latest published version, approval decisions, signatures | documents |
| Published risks, vendors, assets, data, processing activities and findings documents | registers |
| Third parties (DPA file or URL); personal data = linked to a data category or processing activity | vendors |
| Organization context (product, architecture, team, processes, customers) | system |
| Tasks, findings, audits, people, access review campaigns and entries | same names |

## Writes

| Action | How |
|---|---|
| AI framework, controls, links, scope decisions, audit record | MCP: `addFramework`, `addControl`, `linkControl`, `unlinkControl`, `addApplicabilityStatement`, `updateApplicabilityStatement`, `addAudit` |
| Evidence file | console multipart `uploadInternalControlEvidence` (`uploadMeasureEvidence` before v0.304) (`prep.py evidence`) |
| Everything else (measures, risks, vendors, documents, tasks) | the Probo MCP tools directly, as the workflow needs |

## Traps

- `updateOrganizationContext` replaces all five sections: read them all, send them all.
- Publish registers after changes: `publishRiskList`, `publishThirdPartyList`,
  `publishAssetList`, `publishDataList`, `publishProcessingActivityList`,
  `publishFindingList`.
- `listRisks` ordered by `UPDATED_AT` crashes the MCP call; use `CREATED_AT` or `NAME`.
- `addControl` rejects an empty description (the connector falls back to the name).
- Approval and signature lists return a `next_cursor` on their last page; following it
  fails. Read one page of 100.
- `vetThirdParty` starts a paid multi-agent LLM run on the instance's API key. Estimate the
  cost and ask first.
- An access review campaign keeps the MFA state from when it started. After fixing MFA, run
  a retest campaign.
