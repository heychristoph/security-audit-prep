# Vanta

Uses the Manage Vanta API (`https://api.vanta.com/v1`). Not yet run against a live
account: the code follows Vanta's published OpenAPI spec. Report anything that differs.

## Setup

1. In Vanta, create an OAuth application with `vanta-api.all:read`, plus
   `vanta-api.all:write` for writes.
2. `export VANTA_CLIENT_ID=... VANTA_CLIENT_SECRET=...`
3. `prep.yaml`: `platform: vanta`, and `options.api_url` only for Vanta Gov.

## Mapping

- A Vanta control is both the framework control and the measure. It counts as implemented
  when every linked document is OK and every test is OK.
- Policies become POLICY documents, with their approval date as the approval.
- Vendor documents whose type or title says DPA count as the DPA.
- Risk scenarios become risks, linked to their controls.
- Not mapped: system description, statement of applicability, registers, tasks, findings
  and access reviews. The checks that need them are skipped. Check those in Vanta itself.

## Writes

- `create_control`: `POST /controls` (custom control).
- Link or unlink a document on a control: `POST /controls/{id}/add-document-to-control`,
  `DELETE /controls/{id}/documents/{documentId}`.
- Evidence: `POST /documents/{documentId}/uploads`. Pass the Vanta document id as the
  measure in `prep.py evidence`.
- Vanta's API cannot create a framework. `prep.py ai-framework --apply` writes
  `<name>.csv`. Import it under Frameworks > Custom frameworks with the exact name, then
  map the controls.
- Vanta's MCP server can also create risks and upload policies, if it is connected.
