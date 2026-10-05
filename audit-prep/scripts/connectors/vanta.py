"""Vanta connector (Manage Vanta API, https://api.vanta.com/v1).

Not yet run against a live Vanta account: endpoints and fields follow Vanta's published
OpenAPI spec (developer.vanta.com/reference/manage-vanta.json). Report anything that
differs and fix it here.

Vanta model -> snapshot:
  Frameworks                         -> frameworks
  Framework controls                 -> controls (ref = control external id); in Vanta the
                                        control is also the measure, so each control links
                                        to itself as its one measure
  Control documents and tests        -> measure state and evidence count: IMPLEMENTED when
                                        every linked document is OK and every test is OK
  Policies (status, approvedAtDate)  -> documents of type POLICY with their approval
  Vendors and vendor documents       -> vendors; a document whose type or title says DPA
                                        counts as the DPA
  Risk scenarios and their controls  -> risks
  People                             -> people

Writes: create a custom control, link or unlink a document to a control, upload a file to
a document (evidence). Vanta has no API to create a framework: `ai-framework` writes a CSV
to import in Vanta (Frameworks > Custom frameworks), then links through the API.

Options:
  api_url   default https://api.vanta.com (Vanta Gov: https://api.vanta-gov.com)
Environment:
  VANTA_CLIENT_ID, VANTA_CLIENT_SECRET   OAuth application with vanta-api.all:read and,
                                         for writes, vanta-api.all:write
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from core import PrepError, http_json, http_multipart, secret

from .base import Connector, empty_snapshot

PAGE = 100
OK_TESTS = {"OK", "NOT_APPLICABLE", "DEACTIVATED"}
OK_DOCS = {"OK", "Not relevant"}


class Platform(Connector):
    name = "vanta"

    def __init__(self, options: dict, config: dict):
        super().__init__(options, config)
        root = (options.get("api_url") or "https://api.vanta.com").rstrip("/")
        self.api = root + "/v1"
        client_id, client_secret = secret("VANTA_CLIENT_ID"), secret("VANTA_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise PrepError("Set VANTA_CLIENT_ID and VANTA_CLIENT_SECRET.")
        token = http_json(f"{root}/oauth/token", method="POST", body={
            "client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials",
            "scope": options.get("scope", "vanta-api.all:read vanta-api.all:write"),
        })
        self.headers = {"Authorization": f"Bearer {token['access_token']}"}
        self.warnings: list[str] = []

    def get(self, path: str, **params):
        return http_json(f"{self.api}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else ""), headers=self.headers)

    def pages(self, path: str, **params):
        cursor = None
        while True:
            query = dict(params, pageSize=PAGE)
            if cursor:
                query["pageCursor"] = cursor
            results = (self.get(path, **query) or {}).get("results", {})
            yield from results.get("data", [])
            info = results.get("pageInfo", {})
            if not info.get("hasNextPage"):
                return
            cursor = info.get("endCursor")

    def safe(self, label: str, fn, default):
        try:
            return fn()
        except PrepError as e:
            self.warnings.append(f"{label}: {e}")
            return default

    def snapshot(self) -> dict:
        snap = empty_snapshot("vanta", self.api, ["approvals", "vendors", "people"])
        measures: dict[str, dict] = {}
        for f in self.pages("/frameworks"):
            snap["frameworks"].append({"id": f["id"], "name": f.get("displayName") or f["id"], "description": f.get("description") or ""})
            for c in self.safe(f"framework {f['id']} controls", lambda: list(self.pages(f"/frameworks/{f['id']}/controls")), []):
                snap["controls"].append({
                    "id": f"{f['id']}:{c['id']}", "framework_id": f["id"], "ref": c.get("externalId") or c["id"],
                    "name": c.get("name") or "", "description": c.get("description") or "", "best_practice": True,
                    "maturity_level": None, "measure_ids": [c["id"]], "document_ids": [],
                })
                measures.setdefault(c["id"], c)

        for cid, c in measures.items():
            docs = self.safe(f"control {cid} documents", lambda: list(self.pages(f"/controls/{cid}/documents")), [])
            tests = self.safe(f"control {cid} tests", lambda: list(self.pages(f"/controls/{cid}/tests")), [])
            ok = docs or tests
            done = all(d.get("uploadStatus") in OK_DOCS for d in docs) and all(t.get("status") in OK_TESTS for t in tests)
            snap["measures"].append({
                "id": cid, "name": c.get("name") or cid, "description": c.get("description") or "",
                "category": ", ".join(c.get("domains") or []),
                "state": "IMPLEMENTED" if ok and done else ("IN_PROGRESS" if ok else "UNKNOWN"),
                "evidence_count": sum(1 for d in docs if d.get("uploadStatus") == "OK") + sum(1 for t in tests if t.get("status") == "OK"),
                "document_ids": [d["id"] for d in docs], "risk_ids": [], "task_ids": [],
                "updated_at": c.get("modificationDate"),
            })
            for d in docs:
                for ctrl in snap["controls"]:
                    if ctrl["measure_ids"] == [cid] and d["id"] not in ctrl["document_ids"]:
                        ctrl["document_ids"].append(d["id"])

        for p in self.safe("policies", lambda: list(self.pages("/policies")), []):
            approved = p.get("approvedAtDate")
            snap["documents"].append({
                "id": p["id"], "title": p.get("name") or "", "type": "POLICY", "updated_at": approved, "draft_newer": False,
                "published": {"version": str((p.get("latestVersion") or {}).get("version") or ""), "published_at": approved,
                              "approvals": [{"name": None, "state": "APPROVED", "at": approved}] if approved else [],
                              "approval_error": None, "signatures": None, "signature_error": None},
            })

        for v in self.safe("vendors", lambda: list(self.pages("/vendors")), []):
            if v.get("status") == "ARCHIVED":
                continue
            docs = self.safe(f"vendor {v['name']} documents", lambda: list(self.pages(f"/vendors/{v['id']}/documents")), [])
            dpa = any("dpa" in f"{d.get('type')} {d.get('title')}".lower() or "data processing" in f"{d.get('type')} {d.get('title')}".lower()
                      for d in docs)
            snap["vendors"].append({
                "id": v["id"], "name": v["name"], "category": (v.get("category") or {}).get("displayName"),
                "description": v.get("servicesProvided") or v.get("additionalNotes") or "", "countries": [],
                "level": 1, "personal_data": None, "dpa_file": dpa, "dpa_url": "", "updated_at": None,
            })

        for r in self.safe("risk scenarios", lambda: list(self.pages("/risk-scenarios")), []):
            if r.get("isArchived"):
                continue
            controls = self.safe(f"risk {r['riskId']} controls", lambda: list(self.pages(f"/risk-scenarios/{r['riskId']}/controls")), [])
            snap["risks"].append({
                "id": r["riskId"], "ref": r["riskId"], "name": r.get("description") or r["riskId"],
                "description": r.get("detailedDescription") or "", "note": r.get("note") or "",
                "treatment": (r.get("treatment") or "").upper() or None, "owner": r.get("owner"), "residual_score": None,
                "measure_ids": [c.get("id") or c.get("controlId") for c in controls], "updated_at": None,
            })

        for p in self.safe("people", lambda: list(self.pages("/people")), []):
            employment = p.get("employment") or {}
            name = p.get("name") or {}
            snap["people"].append({"id": p["id"], "name": name.get("display") or " ".join(filter(None, [name.get("first"), name.get("last")])),
                                   "email": p.get("emailAddress"), "state": employment.get("status"),
                                   "contract_end": employment.get("endDate")})
        snap["warnings"].extend(self.warnings)
        return snap

    # --- writes ---

    def create_control(self, framework_id: str, control: dict) -> str:
        out = http_json(f"{self.api}/controls", method="POST", headers=self.headers, body={
            "externalId": control["ref"], "name": control["name"], "description": control.get("description") or control["name"],
        })
        return out["id"]

    def link_control(self, control_id: str, resource_id: str) -> None:
        control_id = control_id.split(":")[-1]
        http_json(f"{self.api}/controls/{control_id}/add-document-to-control", method="POST",
                  headers=self.headers, body={"documentId": resource_id})

    def unlink_control(self, control_id: str, resource_id: str) -> None:
        control_id = control_id.split(":")[-1]
        http_json(f"{self.api}/controls/{control_id}/documents/{resource_id}", method="DELETE", headers=self.headers)

    def upload_evidence(self, measure_id: str, path: Path) -> str:
        """measure_id is the Vanta document (evidence request) the file belongs to."""
        out = http_multipart(f"{self.api}/documents/{measure_id}/uploads", {"description": path.name}, {"file": path}, self.headers)
        return (out or {}).get("id", "")
