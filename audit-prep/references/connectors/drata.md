# Drata

Uses the Drata public API v2 (`https://public-api.drata.com/public/v2`). Not yet run
against a live account. The paths are in `PATHS` in `scripts/connectors/drata.py`. A read
that fails becomes a `CONNECTOR` warning, so the other checks still run. Fix the path there
and report it.

## Setup

1. In Drata, create an API key with read scopes, plus write scopes for controls and
   evidence.
2. `export DRATA_API_KEY=...`
3. `prep.yaml`: `platform: drata`. Add `options.workspace_id` when the account has more
   than one workspace, and `options.api_url` for EU or APAC.

## Mapping

- Framework requirements become controls. Workspace controls become measures, linked to
  the requirements they map to. A control counts as implemented when Drata marks it ready.
- The evidence library supplies the evidence count per control.
- Policies become POLICY documents. Vendors take their DPA from vendor documents whose type
  or name says DPA. Risks and personnel are mapped too.
- Not mapped: system description, statement of applicability, registers, tasks, findings
  and access reviews.

## Writes

- `create_control`: create a workspace control.
- Evidence: create an evidence-library item linked to the control. Pass the control id as
  the measure in `prep.py evidence`.
- Drata's API cannot create a custom framework. `prep.py ai-framework --apply` writes
  `<name>.csv`. Upload it as a custom framework's requirements (code, name, description)
  with the exact name, then map the controls.
- Drata's MCP server can create and update evidence and controls, if it is connected.
