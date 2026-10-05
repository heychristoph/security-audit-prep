"""Folder connector: the compliance records as YAML files, for teams without a platform.

Layout under options.path (relative to prep.yaml). assets/folder-template/ has a starter.
Every file is optional; a missing one is an empty list.

  frameworks/<name>.yaml  {id, name, description, controls: [{ref, name, description,
                           measures: [ids], documents: [ids], applicable, justification}]}
  measures.yaml           [{id, name, state, description, category, documents: [ids],
                           updated_at}]
  risks.yaml              [{id, ref, name, description, note, treatment, owner,
                           residual_score, measures: [ids], updated_at}]
  documents.yaml          [{id, title, type, version, published_at, approved_by,
                           approved_at, signed_by: [names], draft_newer}]
  vendors.yaml            [{id, name, category, description, personal_data, dpa_file, dpa_url}]
  assets.yaml             [{id, name, type, classification, owner, vendors: [ids]}]
  data.yaml               [{id, name, classification, owner, vendors: [ids]}]
  tasks.yaml              [{id, name, state, priority, deadline, recurring, assignee, measure}]
  findings.yaml           [{id, ref, kind, status, priority, due, description, owner, risk}]
  audits.yaml             [{id, name, firm, state, framework}]
  people.yaml             [{id, name, email, state, contract_end}]
  access-reviews.yaml     [{id, name, status, completed_at, entries: [...]}]
  system.yaml             {approved: false, sections: {product, architecture, team,
                           processes, customers}}
  evidence/<measure id>/  the evidence files; their count is the measure's evidence

Keep the folder in git: the history is the change record. Do not keep a separate to-do
file; tasks.yaml is the list.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from core import PrepError

from .base import Connector, empty_snapshot


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "framework"


class Platform(Connector):
    name = "folder"

    def __init__(self, options: dict, config: dict):
        super().__init__(options, config)
        self.root = Path(config.get("_dir", ".")) / options.get("path", "records")
        if not self.root.is_dir():
            raise PrepError(f"Records folder {self.root} does not exist. Copy assets/folder-template there.")

    def read(self, name: str, default=None):
        p = self.root / name
        return (yaml.safe_load(p.read_text()) if p.exists() else None) or (default if default is not None else [])

    def write(self, name: str, data) -> None:
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    def framework_files(self):
        return sorted((self.root / "frameworks").glob("*.yaml")) if (self.root / "frameworks").is_dir() else []

    def snapshot(self) -> dict:
        snap = empty_snapshot("folder", str(self.root), [
            "applicability", "approvals", "signatures", "system", "tasks", "findings", "vendors", "assets", "data",
            "people", "access_reviews",
        ])
        for path in self.framework_files():
            f = yaml.safe_load(path.read_text()) or {}
            fid = f.get("id") or path.stem
            snap["frameworks"].append({"id": fid, "name": f.get("name") or fid, "description": f.get("description") or ""})
            for c in f.get("controls") or []:
                cid = f"{fid}:{c['ref']}"
                snap["controls"].append({
                    "id": cid, "framework_id": fid, "ref": c["ref"], "name": c.get("name") or "",
                    "description": c.get("description") or "", "best_practice": True, "maturity_level": None,
                    "measure_ids": list(c.get("measures") or []), "document_ids": list(c.get("documents") or []),
                })
                if "applicable" in c:
                    snap["applicability"].append({"id": cid, "soa_id": "scope", "control_id": cid,
                                                  "applicable": bool(c["applicable"]), "justification": c.get("justification") or ""})
        tasks = self.read("tasks.yaml")
        for m in self.read("measures.yaml"):
            folder = self.root / "evidence" / str(m["id"])
            snap["measures"].append({
                "id": m["id"], "name": m["name"], "state": m.get("state", "UNKNOWN"), "description": m.get("description") or "",
                "category": m.get("category") or "",
                "evidence_count": sum(1 for p in folder.iterdir() if p.is_file()) if folder.is_dir() else 0,
                "document_ids": list(m.get("documents") or []),
                "risk_ids": [r["id"] for r in self.read("risks.yaml") if m["id"] in (r.get("measures") or [])],
                "task_ids": [t["id"] for t in tasks if t.get("measure") == m["id"]],
                "updated_at": _iso(m.get("updated_at")),
            })
        for r in self.read("risks.yaml"):
            snap["risks"].append({"id": r["id"], "ref": r.get("ref") or r["id"], "name": r.get("name") or "",
                                  "description": r.get("description") or "", "note": r.get("note") or "",
                                  "treatment": r.get("treatment"), "owner": r.get("owner"), "residual_score": r.get("residual_score"),
                                  "measure_ids": list(r.get("measures") or []), "updated_at": _iso(r.get("updated_at"))})
        for d in self.read("documents.yaml"):
            published = None
            if d.get("published_at") or d.get("version"):
                published = {
                    "version": str(d.get("version") or ""), "published_at": _iso(d.get("published_at")),
                    "approvals": [{"name": d["approved_by"], "state": "APPROVED", "at": _iso(d.get("approved_at"))}] if d.get("approved_by") else [],
                    "approval_error": None,
                    "signatures": [{"name": n, "state": "SIGNED", "at": None} for n in d.get("signed_by") or []],
                    "signature_error": None,
                }
            snap["documents"].append({"id": d["id"], "title": d.get("title") or "", "type": (d.get("type") or "OTHER").upper(),
                                      "updated_at": None, "draft_newer": bool(d.get("draft_newer")), "published": published})
        for v in self.read("vendors.yaml"):
            snap["vendors"].append({"id": v["id"], "name": v["name"], "category": v.get("category"),
                                    "description": v.get("description") or "", "countries": v.get("countries") or [],
                                    "level": 1, "personal_data": v.get("personal_data"), "dpa_file": bool(v.get("dpa_file")),
                                    "dpa_url": v.get("dpa_url") or "", "updated_at": None})
        for a in self.read("assets.yaml"):
            snap["assets"].append({"id": a["id"], "name": a["name"], "type": a.get("type"),
                                   "classification_text": a.get("classification") or "", "owner": a.get("owner"),
                                   "vendor_ids": list(a.get("vendors") or []), "updated_at": None})
        for d in self.read("data.yaml"):
            snap["data"].append({"id": d["id"], "name": d["name"], "classification": d.get("classification"),
                                 "owner": d.get("owner"), "vendor_ids": list(d.get("vendors") or []), "updated_at": None})
        for t in tasks:
            snap["tasks"].append({"id": t["id"], "name": t["name"], "state": t.get("state", "TODO"), "priority": t.get("priority"),
                                  "deadline": _iso(t.get("deadline")), "recurring": bool(t.get("recurring")),
                                  "assignee": t.get("assignee"), "measure_id": t.get("measure")})
        for f in self.read("findings.yaml"):
            snap["findings"].append({"id": f["id"], "ref": f.get("ref") or f["id"], "kind": f.get("kind"), "status": f.get("status", "OPEN"),
                                     "priority": f.get("priority"), "due": _iso(f.get("due")), "description": f.get("description") or "",
                                     "owner": f.get("owner"), "risk_id": f.get("risk"), "updated_at": None})
        for a in self.read("audits.yaml"):
            snap["audits"].append({"id": a["id"], "name": a.get("name") or "", "firm": a.get("firm") or "",
                                   "state": a.get("state"), "framework_id": a.get("framework")})
        for p in self.read("people.yaml"):
            snap["people"].append({"id": p["id"], "name": p.get("name"), "email": p.get("email"),
                                   "state": p.get("state", "ACTIVE"), "contract_end": _iso(p.get("contract_end"))})
        snap["access_reviews"] = [{**c, "completed_at": _iso(c.get("completed_at")), "entries": c.get("entries") or []}
                                  for c in self.read("access-reviews.yaml")]
        system = self.read("system.yaml", {})
        snap["system"] = {"sections": {k: (system.get("sections") or {}).get(k) or "" for k in
                                       ("product", "architecture", "team", "processes", "customers")},
                          "approved": system.get("approved")}
        return snap

    # --- writes ---

    def _framework(self, framework_id: str) -> tuple[Path, dict]:
        for path in self.framework_files():
            f = yaml.safe_load(path.read_text()) or {}
            if (f.get("id") or path.stem) == framework_id:
                return path, f
        raise PrepError(f"No framework {framework_id} in {self.root / 'frameworks'}.")

    def _control(self, control_id: str):
        framework_id, ref = control_id.split(":", 1)
        path, f = self._framework(framework_id)
        for c in f.get("controls") or []:
            if c["ref"] == ref:
                return path, f, c
        raise PrepError(f"No control {ref} in framework {framework_id}.")

    def create_framework(self, name: str, description: str) -> str:
        fid = _slug(name)
        self.write(f"frameworks/{fid}.yaml", {"id": fid, "name": name, "description": description, "controls": []})
        return fid

    def create_control(self, framework_id: str, control: dict) -> str:
        path, f = self._framework(framework_id)
        f.setdefault("controls", []).append({"ref": control["ref"], "name": control["name"],
                                             "description": control.get("description") or "", "measures": [], "documents": []})
        path.write_text(yaml.safe_dump(f, sort_keys=False, allow_unicode=True))
        return f"{framework_id}:{control['ref']}"

    def _set_link(self, control_id: str, resource_id: str, add: bool) -> None:
        path, f, c = self._control(control_id)
        documents = {d["id"] for d in self.read("documents.yaml")}
        key = "documents" if resource_id in documents else "measures"
        items = c.setdefault(key, [])
        if add and resource_id not in items:
            items.append(resource_id)
        if not add and resource_id in items:
            items.remove(resource_id)
        path.write_text(yaml.safe_dump(f, sort_keys=False, allow_unicode=True))

    def link_control(self, control_id: str, resource_id: str) -> None:
        self._set_link(control_id, resource_id, True)

    def unlink_control(self, control_id: str, resource_id: str) -> None:
        self._set_link(control_id, resource_id, False)

    def add_applicability(self, soa_id: str, control_id: str, applicable: bool, justification: str | None) -> str:
        self.update_applicability(control_id, applicable, justification)
        return control_id

    def update_applicability(self, statement_id: str, applicable: bool, justification: str | None) -> None:
        path, f, c = self._control(statement_id)
        c["applicable"], c["justification"] = applicable, justification or ""
        path.write_text(yaml.safe_dump(f, sort_keys=False, allow_unicode=True))

    def create_audit(self, framework_id: str, name: str, firm: str, state: str) -> str:
        audits = self.read("audits.yaml")
        audit_id = f"audit-{len(audits) + 1}"
        audits.append({"id": audit_id, "name": name, "firm": firm, "state": state, "framework": framework_id})
        self.write("audits.yaml", audits)
        return audit_id

    def upload_evidence(self, measure_id: str, path: Path) -> str:
        folder = self.root / "evidence" / measure_id
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, folder / path.name)
        return str(folder / path.name)


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value
