"""Probo connector (probo.com or self-hosted).

Reads go through the console GraphQL API: it returns links and counts in a few paginated
queries, where the MCP needs one call per measure, control and document. Writes go through
the published MCP tools. Evidence files go through the console mutation
uploadInternalControlEvidence (uploadMeasureEvidence before v0.304), because the MCP has no
upload tool. Probo v0.304 renamed measures to internal controls in GraphQL and MCP; the
connector detects which names the instance uses.

Options (prep.yaml `options`):
  url              instance root, e.g. https://probo.example.com
  organization_id  required
  token_command    optional shell command that prints the token (for example, read it from
                   the agent's MCP config); used when PROBO_TOKEN is not set
Environment:
  PROBO_TOKEN      Probo OAuth access token, with or without the "Bearer " prefix

Known Probo behaviour (v0.297):
  - updateOrganizationContext replaces all five sections; a section left out is cleared.
  - listRisks ordered by UPDATED_AT panics in the MCP before v0.303; this connector does not use it.
  - addControl rejects an empty description; the control name is used instead.
  - Signature and approval lists return a next_cursor on the last page, and following it
    fails. Single pages of 100 are read here.
"""

from __future__ import annotations

import itertools
import json
import urllib.error
import urllib.request
from pathlib import Path

from core import PrepError, http_json, http_multipart, secret

from .base import Connector, empty_snapshot

PAGE = 100
LINKS = "(first: 100) { edges { node { id } } pageInfo { hasNextPage } }"
VERSIONS = "versions(first: 50) { edges { node { id title documentType status major minor publishedAt } } }"
REGISTERS = {
    "risks": "risksDocument",
    "vendors": "thirdPartiesDocument",
    "assets": "assetListDocument",
    "data": "dataListDocument",
    "processing_activities": "processingActivitiesDocument",
    "findings": "findingsDocument",
}
APPROVAL_TYPES = ("POLICY", "PLAN", "PROCEDURE", "GOVERNANCE")


class Platform(Connector):
    name = "probo"

    def __init__(self, options: dict, config: dict):
        super().__init__(options, config)
        self.base = (options.get("url") or "").rstrip("/")
        self.org = options.get("organization_id")
        if not self.base or not self.org:
            raise PrepError("Probo needs options.url and options.organization_id in prep.yaml.")
        token = secret("PROBO_TOKEN", options.get("token_command"))
        if not token:
            raise PrepError("Set PROBO_TOKEN to a Probo OAuth token, or options.token_command to a command that prints it.")
        self.auth = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        self._mcp_session = None
        self._ids = itertools.count(1)
        self.warnings: list[str] = []

    # --- console GraphQL ---

    def gql(self, query: str, variables: dict | None = None) -> dict:
        out = http_json(
            f"{self.base}/api/console/v1/graphql", method="POST",
            headers={"Authorization": self.auth}, body={"query": query, "variables": variables or {}},
        )
        if out.get("errors"):
            raise PrepError("Probo GraphQL error: " + json.dumps(out["errors"])[:400])
        return out["data"]

    def connection(self, node_id: str, typename: str, field: str, fields: str, args: str = "") -> list[dict]:
        query = (
            f"query($id: ID!, $after: CursorKey) {{ node(id: $id) {{ ... on {typename} {{ "
            f"{field}(first: {PAGE}, after: $after{args}) {{ pageInfo {{ hasNextPage endCursor }} "
            f"edges {{ node {{ {fields} }} }} }} }} }} }}"
        )
        items, after = [], None
        while True:
            conn = self.gql(query, {"id": node_id, "after": after})["node"][field]
            items.extend(e["node"] for e in conn["edges"])
            if not conn["pageInfo"]["hasNextPage"]:
                return items
            after = conn["pageInfo"]["endCursor"]

    def internal_controls(self) -> bool:
        """Probo v0.304 renamed measures to internal controls in GraphQL and MCP. The
        snapshot keeps calling them measures; only the API names differ."""
        if not hasattr(self, "_internal_controls"):
            found = self.gql('query { __type(name: "InternalControl") { name } }')["__type"]
            self._internal_controls = found is not None
        return self._internal_controls

    def ids(self, conn: dict | None, where: str) -> list[str]:
        conn = conn or {}
        if (conn.get("pageInfo") or {}).get("hasNextPage"):
            self.warnings.append(f"{where}: more than 100 links; only the first 100 were read")
        return [e["node"]["id"] for e in conn.get("edges", [])]

    # --- MCP ---

    def mcp(self, tool: str, **arguments) -> dict:
        if self._mcp_session is None:
            self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                     "clientInfo": {"name": "audit-prep", "version": "1"}})
            self._rpc("notifications/initialized", None, notify=True)
        result = self._rpc("tools/call", {"name": tool, "arguments": arguments})
        if result.get("isError"):
            text = " ".join(c.get("text", "") for c in result.get("content", []))
            raise PrepError(f"Probo {tool} failed: {text[:400]}")
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        for content in result.get("content", []):
            if content.get("type") == "text":
                return json.loads(content["text"])
        return {}

    def _rpc(self, method: str, params, notify: bool = False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = next(self._ids)
        if params is not None:
            body["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "Authorization": self.auth}
        if self._mcp_session:
            headers["Mcp-Session-Id"] = self._mcp_session
        req = urllib.request.Request(f"{self.base}/api/mcp/v1", data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                self._mcp_session = resp.headers.get("Mcp-Session-Id") or self._mcp_session or ""
                raw, ctype = resp.read().decode(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raise PrepError(f"Probo MCP {method} failed with HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from e
        if notify:
            return None
        if "text/event-stream" in ctype:
            messages = [json.loads(line[5:]) for line in raw.splitlines() if line.startswith("data:")]
            reply = next((m for m in messages if m.get("id") == body["id"]), messages[-1] if messages else {})
        else:
            reply = json.loads(raw)
        if reply.get("error"):
            raise PrepError(f"Probo MCP {method}: {reply['error'].get('message')}")
        return reply.get("result", {})

    @staticmethod
    def _created_id(out: dict) -> str:
        for value in out.values():
            if isinstance(value, dict) and value.get("id"):
                return value["id"]
        raise PrepError(f"Probo did not return an id: {json.dumps(out)[:300]}")

    # --- snapshot ---

    def snapshot(self) -> dict:
        snap = empty_snapshot("probo", f"{self.base} organization {self.org}", [
            "applicability", "registers", "approvals", "signatures", "access_reviews", "system",
            "tasks", "findings", "vendors", "assets", "data", "people",
        ])
        org = self.org
        ic = self.internal_controls()
        mf = "internalControls" if ic else "measures"
        top = self.gql(
            "query($id: ID!) { node(id: $id) { ... on Organization { name "
            "context { product architecture team processes customers } "
            + " ".join(f"{field} {{ id {VERSIONS} }}" for field in REGISTERS.values())
            + " } } }", {"id": org},
        )["node"]
        snap["organization"] = {"id": org, "name": top["name"]}
        snap["system"]["sections"] = {k: (top.get("context") or {}).get(k) or "" for k in
                                      ("product", "architecture", "team", "processes", "customers")}
        for name, field in REGISTERS.items():
            published = _latest_published((top.get(field) or {}).get("versions"))
            snap["registers"][name] = published["publishedAt"] if published else None

        for f in self.connection(org, "Organization", "frameworks", "id name description"):
            snap["frameworks"].append({"id": f["id"], "name": f["name"], "description": f.get("description") or ""})
            for c in self.connection(f["id"], "Framework", "controls",
                                     "id sectionTitle name description bestPractice maturityLevel "
                                     f"{mf}{LINKS} documents{LINKS}"):
                snap["controls"].append({
                    "id": c["id"], "framework_id": f["id"], "ref": c["sectionTitle"], "name": c["name"],
                    "description": c.get("description") or "", "best_practice": c.get("bestPractice"),
                    "maturity_level": c.get("maturityLevel"),
                    "measure_ids": self.ids(c[mf], f"control {c['sectionTitle']}"),
                    "document_ids": self.ids(c["documents"], f"control {c['sectionTitle']}"),
                })

        for soa in self.connection(org, "Organization", "statementsOfApplicability", "id name"):
            for s in self.connection(soa["id"], "StatementOfApplicability", "applicabilityStatements",
                                     "id applicability justification control { id }"):
                snap["applicability"].append({
                    "id": s["id"], "soa_id": soa["id"], "control_id": s["control"]["id"],
                    "applicable": s["applicability"], "justification": s.get("justification") or "",
                })

        for m in self.connection(org, "Organization", mf,
                                 "id name description state category updatedAt evidences(first: 1) { totalCount } "
                                 f"documents{LINKS} risks{LINKS} tasks{LINKS}"):
            snap["measures"].append({
                "id": m["id"], "name": m["name"], "state": m["state"], "description": m.get("description") or "",
                "category": m.get("category") or "", "evidence_count": m["evidences"]["totalCount"],
                "document_ids": self.ids(m["documents"], f"measure {m['name']}"),
                "risk_ids": self.ids(m["risks"], f"measure {m['name']}"),
                "task_ids": self.ids(m["tasks"], f"measure {m['name']}"),
                "updated_at": m["updatedAt"],
            })

        for r in self.connection(org, "Organization", "risks",
                                 "id referenceId name description note treatment residualRiskScore updatedAt "
                                 f"owner {{ fullName }} {mf}{LINKS}"):
            snap["risks"].append({
                "id": r["id"], "ref": r.get("referenceId") or "", "name": r["name"],
                "description": r.get("description") or "", "note": r.get("note") or "",
                "treatment": r.get("treatment"), "owner": (r.get("owner") or {}).get("fullName"),
                "residual_score": r.get("residualRiskScore"),
                "measure_ids": self.ids(r[mf], f"risk {r.get('referenceId')}"),
                "updated_at": r["updatedAt"],
            })

        for d in self.connection(org, "Organization", "documents", f"id updatedAt {VERSIONS}",
                                 ", filter: { status: [ACTIVE] }"):
            snap["documents"].append(self._document(d))

        personal = set()
        for item in self.connection(org, "Organization", "data",
                                    f"id name dataClassification updatedAt owner {{ fullName }} thirdParties{LINKS}"):
            vendor_ids = self.ids(item["thirdParties"], f"data {item['name']}")
            personal.update(vendor_ids)
            snap["data"].append({"id": item["id"], "name": item["name"], "classification": item.get("dataClassification"),
                                 "owner": (item.get("owner") or {}).get("fullName"), "vendor_ids": vendor_ids,
                                 "updated_at": item.get("updatedAt")})
        for pa in self.connection(org, "Organization", "processingActivities", f"id name updatedAt thirdParties{LINKS}"):
            vendor_ids = self.ids(pa["thirdParties"], f"processing activity {pa['name']}")
            personal.update(vendor_ids)
            snap["processing_activities"].append({"id": pa["id"], "name": pa["name"], "vendor_ids": vendor_ids,
                                                  "updated_at": pa.get("updatedAt")})

        for v in self.connection(org, "Organization", "thirdParties",
                                 "id name category description countries level dataProcessingAgreementUrl updatedAt "
                                 "dataPrivacyAgreement { id file { id } }"):
            snap["vendors"].append({
                "id": v["id"], "name": v["name"], "category": v.get("category"), "description": v.get("description") or "",
                "countries": v.get("countries") or [], "level": v.get("level"),
                "personal_data": True if v["id"] in personal else None,
                "dpa_file": bool((v.get("dataPrivacyAgreement") or {}).get("file")),
                "dpa_url": v.get("dataProcessingAgreementUrl") or "", "updated_at": v["updatedAt"],
            })

        for a in self.connection(org, "Organization", "assets",
                                 f"id name assetType dataTypesStored updatedAt owner {{ fullName }} thirdParties{LINKS}"):
            snap["assets"].append({"id": a["id"], "name": a["name"], "type": a.get("assetType"),
                                   "classification_text": a.get("dataTypesStored") or "",
                                   "owner": (a.get("owner") or {}).get("fullName"),
                                   "vendor_ids": self.ids(a["thirdParties"], f"asset {a['name']}"),
                                   "updated_at": a.get("updatedAt")})

        # A task links to one measure (before v0.304), one internal control (v0.304 to v0.306)
        # or several internal controls (v0.307 on).
        task_fields = {f["name"] for f in self.gql('query { __type(name: "Task") { fields { name } } }')["__type"]["fields"]}
        task_link = next(f for f in ("internalControls", "internalControl", "measure") if f in task_fields)
        for t in self.connection(org, "Organization", "tasks",
                                 "id name state priority deadline recurrenceInterval assignedTo { fullName } "
                                 + (f"{task_link}{LINKS}" if task_link == "internalControls" else f"{task_link} {{ id }}")):
            measure_ids = self.ids(t[task_link], f"task {t['name']}") if task_link == "internalControls" \
                else [m["id"] for m in [t.get(task_link)] if m]
            snap["tasks"].append({"id": t["id"], "name": t["name"], "state": t["state"], "priority": t.get("priority"),
                                  "deadline": t.get("deadline"), "recurring": bool(t.get("recurrenceInterval")),
                                  "assignee": (t.get("assignedTo") or {}).get("fullName"),
                                  "measure_id": measure_ids[0] if measure_ids else None})

        for f in self.connection(org, "Organization", "findings",
                                 "id referenceId kind status priority dueDate description updatedAt owner { fullName } risk { id }"):
            snap["findings"].append({"id": f["id"], "ref": f.get("referenceId") or "", "kind": f.get("kind"),
                                     "status": f.get("status"), "priority": f.get("priority"), "due": f.get("dueDate"),
                                     "description": f.get("description") or "",
                                     "owner": (f.get("owner") or {}).get("fullName"),
                                     "risk_id": (f.get("risk") or {}).get("id"), "updated_at": f.get("updatedAt")})

        for a in self.connection(org, "Organization", "audits", "id name firm state framework { id }"):
            snap["audits"].append({"id": a["id"], "name": a.get("name") or "", "firm": a.get("firm") or "",
                                   "state": a.get("state"), "framework_id": (a.get("framework") or {}).get("id")})

        for p in self.connection(org, "Organization", "profiles",
                                 "id fullName emailAddress state kind position contract { end }"):
            snap["people"].append({"id": p["id"], "name": p.get("fullName"), "email": p.get("emailAddress"),
                                   "state": p.get("state"), "contract_end": (p.get("contract") or {}).get("end")})

        campaigns = self.connection(org, "Organization", "accessReviewCampaigns", "id name status completedAt")
        for camp in campaigns:
            entries = []
            if camp.get("status") == "COMPLETED":
                for e in self.connection(camp["id"], "AccessReviewCampaign", "entries",
                                         "email fullName decision decisionNote isAdmin mfaStatus"):
                    entries.append({"email": e.get("email"), "name": e.get("fullName"), "decision": e.get("decision"),
                                    "note": e.get("decisionNote") or "", "is_admin": e.get("isAdmin"),
                                    "mfa": e.get("mfaStatus")})
            snap["access_reviews"].append({"id": camp["id"], "name": camp.get("name") or "", "status": camp.get("status"),
                                           "completed_at": camp.get("completedAt"), "entries": entries})

        snap["warnings"].extend(self.warnings)
        return snap

    def _document(self, d: dict) -> dict:
        versions = [e["node"] for e in d["versions"]["edges"]]
        latest = max(versions, key=_version_key) if versions else {}
        published = _latest_published(d["versions"])
        doc = {
            "id": d["id"], "title": latest.get("title") or "", "type": latest.get("documentType"),
            "updated_at": d.get("updatedAt"), "published": None,
            "draft_newer": bool(published and latest and _version_key(latest) > _version_key(published)
                                and latest.get("status") != "PUBLISHED"),
        }
        if not published:
            return doc
        doc["published"] = {"version": f"{published['major']}.{published['minor']}", "published_at": published.get("publishedAt"),
                            "approvals": None, "approval_error": None, "signatures": None, "signature_error": None}
        if doc["type"] not in APPROVAL_TYPES:
            return doc
        try:
            node = self.gql(
                "query($id: ID!) { node(id: $id) { ... on DocumentVersion { "
                "approvalQuorums(first: 20) { edges { node { status decisions(first: 50) { edges { node { "
                "state decidedAt approver { fullName } } } } } } } } } }", {"id": published["id"]})["node"]
            doc["published"]["approvals"] = [
                {"name": (dec["node"].get("approver") or {}).get("fullName"), "state": dec["node"]["state"],
                 "at": dec["node"].get("decidedAt")}
                for q in node["approvalQuorums"]["edges"] for dec in q["node"]["decisions"]["edges"]
            ]
        except PrepError as e:
            doc["published"]["approval_error"] = str(e)
        try:
            node = self.gql(
                "query($id: ID!) { node(id: $id) { ... on DocumentVersion { signatures(first: 100) { edges { node { "
                "state signedAt signedBy { fullName } } } } } } }", {"id": published["id"]})["node"]
            doc["published"]["signatures"] = [
                {"name": (s["node"].get("signedBy") or {}).get("fullName"), "state": s["node"]["state"],
                 "at": s["node"].get("signedAt")}
                for s in node["signatures"]["edges"]
            ]
        except PrepError as e:
            doc["published"]["signature_error"] = str(e)
        return doc

    # --- writes ---

    def create_framework(self, name: str, description: str) -> str:
        return self._created_id(self.mcp("addFramework", organization_id=self.org, name=name, description=description))

    def create_control(self, framework_id: str, control: dict) -> str:
        args = {
            "organization_id": self.org, "framework_id": framework_id, "section_title": control["ref"],
            "name": control["name"], "description": control.get("description") or control["name"],
            "best_practice": bool(control.get("best_practice", True)),
            "maturity_level": control.get("maturity_level") or "NONE",
        }
        return self._created_id(self.mcp("addControl", **args))

    def link_control(self, control_id: str, resource_id: str) -> None:
        self.mcp("linkControl", control_id=control_id, resource_id=resource_id)

    def unlink_control(self, control_id: str, resource_id: str) -> None:
        self.mcp("unlinkControl", control_id=control_id, resource_id=resource_id)

    def add_applicability(self, soa_id: str, control_id: str, applicable: bool, justification: str | None) -> str:
        return self._created_id(self.mcp("addApplicabilityStatement", statement_of_applicability_id=soa_id,
                                         control_id=control_id, applicability=applicable, justification=justification))

    def update_applicability(self, statement_id: str, applicable: bool, justification: str | None) -> None:
        self.mcp("updateApplicabilityStatement", id=statement_id, applicability=applicable, justification=justification)

    def create_audit(self, framework_id: str, name: str, firm: str, state: str) -> str:
        return self._created_id(self.mcp("addAudit", organization_id=self.org, framework_id=framework_id,
                                         name=name, firm=firm, state=state))

    def upload_evidence(self, measure_id: str, path: Path) -> str:
        mutation, key = (("uploadInternalControlEvidence", "internalControlId") if self.internal_controls()
                         else ("uploadMeasureEvidence", "measureId"))
        operations = {
            "query": f"mutation($input: {mutation[0].upper()}{mutation[1:]}Input!) {{ {mutation}(input: $input) "
                     "{ evidenceEdge { node { id state } } } }",
            "variables": {"input": {key: measure_id, "file": None}},
        }
        out = http_multipart(
            f"{self.base}/api/console/v1/graphql",
            {"operations": json.dumps(operations), "map": json.dumps({"0": ["variables.input.file"]})},
            {"0": path}, {"Authorization": self.auth},
        )
        if out.get("errors"):
            raise PrepError("Probo upload failed: " + json.dumps(out["errors"])[:400])
        return out["data"][mutation]["evidenceEdge"]["node"]["id"]


def _version_key(v: dict) -> tuple:
    return (v.get("major") or 0, v.get("minor") or 0)


def _latest_published(versions: dict | None) -> dict | None:
    nodes = [e["node"] for e in (versions or {}).get("edges", []) if e["node"].get("status") == "PUBLISHED"]
    if not nodes:
        return None
    return max(nodes, key=_version_key)
