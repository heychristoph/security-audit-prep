"""The contract between connectors and the rest of the skill.

A connector reads the compliance platform into a snapshot (plain JSON, shape below) and
offers a few writes. Checks and the AI-framework planner only ever see the snapshot, so
they work the same for every platform.

Snapshot shape. Ids are the platform's own ids. Times are ISO 8601 strings. A list a
platform does not have stays empty, and its name is left out of `capabilities`, so the
checks that need it are skipped instead of failing.

  platform, source, taken_at
  capabilities   list of: applicability, registers, approvals, signatures, access_reviews,
                 system, tasks, findings, vendors, assets, data, people
  frameworks     [{id, name, description}]
  controls       [{id, framework_id, ref, name, description, best_practice, maturity_level,
                   measure_ids, document_ids}]
  applicability  [{id, soa_id, control_id, applicable, justification}]
  measures       [{id, name, state, description, category, evidence_count, document_ids,
                   risk_ids, task_ids, updated_at}]
                 state is one of NOT_STARTED, IN_PROGRESS, IMPLEMENTED, NOT_IMPLEMENTED,
                 NOT_APPLICABLE, UNKNOWN
  risks          [{id, ref, name, description, note, treatment, owner, residual_score,
                   measure_ids, updated_at}]
  documents      [{id, title, type, updated_at, draft_newer, published}]
                 published is None or {version, published_at, approvals, approval_error,
                 signatures, signature_error}; approvals and signatures are lists of
                 {name, state, at}, or None when they could not be read
  registers      {risks|vendors|assets|data|processing_activities|findings: published_at or None}
  vendors        [{id, name, category, description, countries, level, personal_data,
                   dpa_file, dpa_url, updated_at}]
  assets         [{id, name, type, classification_text, owner, vendor_ids, updated_at}]
  data           [{id, name, classification, owner, vendor_ids, updated_at}]
  processing_activities [{id, name, vendor_ids, updated_at}]
  tasks          [{id, name, state, priority, deadline, recurring, assignee, measure_id}]
                 state is one of BACKLOG, TODO, IN_PROGRESS, DONE, CANCELED, DUPLICATE
  findings       [{id, ref, kind, status, priority, due, description, owner, risk_id,
                   updated_at}]
  audits         [{id, name, firm, state, framework_id}]
  system         {sections: {name: text}, approved: True, False or None}
  people         [{id, name, email, state, contract_end}]
  access_reviews [{id, name, status, completed_at, entries: [{email, name, decision, note,
                   is_admin, mfa}]}]
  warnings       [text]   anything the connector could not read
"""

from __future__ import annotations

from pathlib import Path

from core import PrepError, now

LISTS = (
    "frameworks", "controls", "applicability", "measures", "risks", "documents", "vendors", "assets",
    "data", "processing_activities", "tasks", "findings", "audits", "people", "access_reviews", "warnings",
)


def empty_snapshot(platform: str, source: str, capabilities: list[str]) -> dict:
    snap = {name: [] for name in LISTS}
    snap.update({
        "platform": platform,
        "source": source,
        "taken_at": now().isoformat(),
        "capabilities": sorted(capabilities),
        "registers": {},
        "system": {"sections": {}, "approved": None},
    })
    return snap


class Connector:
    """Base class. Subclasses implement snapshot() and whichever writes the platform has."""

    name = "base"

    def __init__(self, options: dict, config: dict):
        self.options = options
        self.config = config

    def snapshot(self) -> dict:
        raise NotImplementedError

    def _unsupported(self, what: str):
        raise PrepError(
            f"The {self.name} connector cannot {what} through the API. "
            f"See references/connectors/{self.name}.md for the manual step."
        )

    # Writes. Each returns the new id where one is created.
    def create_framework(self, name: str, description: str) -> str:
        self._unsupported("create a framework")

    def create_control(self, framework_id: str, control: dict) -> str:
        self._unsupported("create a control")

    def link_control(self, control_id: str, resource_id: str) -> None:
        self._unsupported("link a measure or document to a control")

    def unlink_control(self, control_id: str, resource_id: str) -> None:
        self._unsupported("unlink a measure or document from a control")

    def add_applicability(self, soa_id: str, control_id: str, applicable: bool, justification: str | None) -> str:
        self._unsupported("add a scope decision")

    def update_applicability(self, statement_id: str, applicable: bool, justification: str | None) -> None:
        self._unsupported("change a scope decision")

    def create_audit(self, framework_id: str, name: str, firm: str, state: str) -> str:
        self._unsupported("create an audit record")

    def upload_evidence(self, measure_id: str, path: Path) -> str:
        self._unsupported("upload evidence")
