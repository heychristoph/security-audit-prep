"""Drata connector (public API v2).

Not yet run against a live Drata account. Paths follow Drata's v2 reference
(developers.drata.com/openapi/reference/v2) and the workspace pattern
/public/v2/workspaces/{workspaceId}/<resource>. Any read that fails becomes a warning in
the snapshot, so `check` still runs; fix the path in PATHS and report it.

Drata model -> snapshot:
  Frameworks and their requirements  -> frameworks and controls (ref = requirement code)
  Workspace controls                 -> measures, linked to the requirements they map to
  Evidence library (with controls)   -> evidence count per measure
  Policies                           -> documents of type POLICY (approval from the
                                        published version)
  Vendors and vendor documents       -> vendors; a document whose type or name says DPA
                                        counts as the DPA
  Risks                              -> risks
  Personnel                          -> people

Writes: create a control, upload an evidence-library item linked to a control. Drata has
no API to create a custom framework: `ai-framework` writes the requirements CSV to upload
in Drata (Frameworks > Custom framework), then maps controls through the API.

Options:
  api_url        default https://public-api.drata.com (EU public-api.eu.drata.com,
                 APAC public-api.apac.drata.com)
  workspace_id   optional when the account has one workspace
Environment:
  DRATA_API_KEY  API key; read scopes, plus write scopes for evidence and controls
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from core import PrepError, http_json, http_multipart, secret

from .base import Connector, empty_snapshot

PAGE = 200
PATHS = {
    "frameworks": "/workspaces/{ws}/frameworks",
    "requirements": "/workspaces/{ws}/frameworks/{fid}/requirements",
    "controls": "/workspaces/{ws}/controls",
    "control_requirements": "/workspaces/{ws}/controls/{cid}/requirements",
    "evidence": "/workspaces/{ws}/evidence-library",
    "policies": "/policies",
    "vendors": "/vendors",
    "vendor_documents": "/vendors/{vid}/documents",
    "risks": "/risks",
    "personnel": "/personnel",
}


class Platform(Connector):
    name = "drata"

    def __init__(self, options: dict, config: dict):
        super().__init__(options, config)
        self.api = (options.get("api_url") or "https://public-api.drata.com").rstrip("/") + "/public/v2"
        key = secret("DRATA_API_KEY")
        if not key:
            raise PrepError("Set DRATA_API_KEY.")
        self.headers = {"Authorization": f"Bearer {key}"}
        self.warnings: list[str] = []
        self.ws = options.get("workspace_id")
        if not self.ws:
            workspaces = list(self.pages("/workspaces"))
            if len(workspaces) != 1:
                raise PrepError("Set options.workspace_id; workspaces: "
                                + ", ".join(f"{w['id']} ({w.get('name')})" for w in workspaces))
            self.ws = workspaces[0]["id"]

    def path(self, key: str, **ids) -> str:
        return PATHS[key].format(ws=self.ws, **ids)

    def pages(self, path: str, **params):
        cursor = None
        while True:
            query = [("size", PAGE)] + [(k, v) for k, vs in params.items() for v in (vs if isinstance(vs, list) else [vs])]
            if cursor:
                query.append(("cursor", cursor))
            data = http_json(f"{self.api}{path}?{urllib.parse.urlencode(query)}", headers=self.headers) or {}
            yield from data.get("data", [])
            cursor = (data.get("pagination") or {}).get("cursor")
            if not cursor:
                return

    def safe(self, label: str, fn, default):
        try:
            return fn()
        except PrepError as e:
            self.warnings.append(f"{label}: {e}")
            return default

    def snapshot(self) -> dict:
        snap = empty_snapshot("drata", f"{self.api} workspace {self.ws}", ["approvals", "vendors", "people"])
        controls = self.safe("controls", lambda: list(self.pages(self.path("controls"), isArchived="false")), [])
        evidence: dict[str, int] = {}
        for item in self.safe("evidence library", lambda: list(self.pages(self.path("evidence"), **{"expand[]": ["controls"]})), []):
            for c in item.get("controls") or []:
                evidence[str(c.get("id"))] = evidence.get(str(c.get("id")), 0) + 1

        requirement_measures: dict[str, list[str]] = {}
        for c in controls:
            cid = str(c["id"])
            reqs = c.get("requirements")
            if reqs is None:
                reqs = self.safe(f"control {c.get('code')} requirements",
                                 lambda: list(self.pages(self.path("control_requirements", cid=cid))), [])
            for r in reqs:
                requirement_measures.setdefault(str(r.get("id")), []).append(cid)
            ready = c.get("isReady")
            snap["measures"].append({
                "id": cid, "name": c.get("name") or c.get("code") or cid, "description": c.get("description") or "",
                "category": c.get("code") or "",
                "state": "IMPLEMENTED" if ready else ("NOT_APPLICABLE" if c.get("isMonitored") is False and c.get("archivedAt") else
                                                     ("IN_PROGRESS" if ready is False else "UNKNOWN")),
                "evidence_count": evidence.get(cid, 0), "document_ids": [], "risk_ids": [], "task_ids": [],
                "updated_at": c.get("updatedAt"),
            })

        for f in self.safe("frameworks", lambda: list(self.pages(self.path("frameworks"))), []):
            fid = str(f["id"])
            snap["frameworks"].append({"id": fid, "name": f.get("name") or f.get("tag") or fid, "description": f.get("description") or ""})
            for r in self.safe(f"framework {fid} requirements", lambda: list(self.pages(self.path("requirements", fid=fid))), []):
                rid = str(r["id"])
                snap["controls"].append({
                    "id": rid, "framework_id": fid, "ref": r.get("name") or r.get("code") or rid,
                    "name": r.get("description") or r.get("name") or "", "description": r.get("longDescription") or "",
                    "best_practice": True, "maturity_level": None,
                    "measure_ids": requirement_measures.get(rid, []), "document_ids": [],
                })

        for p in self.safe("policies", lambda: list(self.pages(self.path("policies"))), []):
            current = p.get("currentVersion") or p.get("latestVersion") or {}
            approved = current.get("approvedAt") or p.get("approvedAt")
            snap["documents"].append({
                "id": str(p["id"]), "title": p.get("name") or "", "type": "POLICY", "updated_at": p.get("updatedAt"),
                "draft_newer": False,
                "published": {"version": str(current.get("version") or ""), "published_at": current.get("publishedAt") or approved,
                              "approvals": [{"name": None, "state": "APPROVED", "at": approved}] if approved else [],
                              "approval_error": None, "signatures": None, "signature_error": None},
            })

        for v in self.safe("vendors", lambda: list(self.pages(self.path("vendors"))), []):
            vid = str(v["id"])
            docs = self.safe(f"vendor {v.get('name')} documents", lambda: list(self.pages(self.path("vendor_documents", vid=vid))), [])
            text = lambda d: json.dumps([d.get("type"), d.get("name"), d.get("fileName")]).lower()
            snap["vendors"].append({
                "id": vid, "name": v.get("name") or vid, "category": v.get("category"), "description": v.get("servicesProvided") or "",
                "countries": [], "level": 1, "personal_data": True if v.get("hasPii") or v.get("dataStored") else None,
                "dpa_file": any("dpa" in text(d) or "data processing" in text(d) for d in docs), "dpa_url": "",
                "updated_at": v.get("updatedAt"),
            })

        for r in self.safe("risks", lambda: list(self.pages(self.path("risks"))), []):
            owners = r.get("owners") or []
            snap["risks"].append({
                "id": str(r.get("id") or r.get("riskId")), "ref": r.get("riskId") or "", "name": r.get("title") or r.get("name") or "",
                "description": r.get("description") or "", "note": r.get("treatmentDetails") or r.get("notes") or "",
                "treatment": (r.get("treatmentPlan") or r.get("treatment") or "").upper() or None,
                "owner": ", ".join(o.get("email") or o.get("firstName") or "" for o in owners) or None,
                "residual_score": r.get("residualScore"),
                "measure_ids": [str(c.get("id")) for c in r.get("controls") or []], "updated_at": r.get("updatedAt"),
            })

        for p in self.safe("personnel", lambda: list(self.pages(self.path("personnel"), **{"expand[]": ["user"]})), []):
            user = p.get("user") or {}
            snap["people"].append({"id": str(p["id"]), "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                                   "email": user.get("email"), "state": p.get("employmentStatus"),
                                   "contract_end": p.get("separatedAt")})
        snap["warnings"].extend(self.warnings)
        return snap

    # --- writes ---

    def create_control(self, framework_id: str, control: dict) -> str:
        out = http_json(f"{self.api}{self.path('controls')}", method="POST", headers=self.headers, body={
            "code": control["ref"], "name": control["name"], "description": control.get("description") or control["name"],
        })
        return str(out["id"])

    def upload_evidence(self, measure_id: str, path: Path) -> str:
        """Creates an evidence-library item from the file, linked to the control (measure)."""
        out = http_multipart(f"{self.api}{self.path('evidence')}",
                             {"name": path.stem, "controlIds": json.dumps([int(measure_id)] if measure_id.isdigit() else [measure_id])},
                             {"file": path}, self.headers)
        return str((out or {}).get("id", ""))
