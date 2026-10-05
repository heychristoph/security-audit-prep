"""Tests on the folder platform: a clean template, then one planted defect per rule.

Run: python -m unittest discover -s tests
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parent.parent / "audit-prep"
sys.path.insert(0, str(SKILL / "scripts"))

import aiframework  # noqa: E402
import checks  # noqa: E402
import connectors  # noqa: E402

CONFIG = {"platform": "folder", "options": {"path": "records"}, "frameworks": ["SOC 2"],
          "ai_audit": {"framework": "SOC 2"}}


class Records:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp())
        shutil.copytree(SKILL / "assets" / "folder-template", self.dir / "records")
        self.config = {**CONFIG, "_dir": str(self.dir)}

    def edit(self, name: str, fn):
        p = self.dir / "records" / name
        data = yaml.safe_load(p.read_text())
        fn(data)
        p.write_text(yaml.safe_dump(data, sort_keys=False))

    def connector(self):
        return connectors.load(self.config)

    def codes(self, level: str | None = None) -> set[str]:
        found = checks.run(self.connector().snapshot(), self.config)
        return {f["code"] for f in found if level is None or f["level"] == level}

    def sync_ai_framework(self):
        c = self.connector()
        snap = c.snapshot()
        real, ai, name = aiframework.pair(snap, self.config)
        ops = aiframework.plan(snap, real, ai, name)
        aiframework.apply(c, snap, real, ai, ops, log=lambda s: None, out_dir=str(self.dir))
        return len(ops)


class CleanTemplate(unittest.TestCase):
    def test_template_has_no_errors_once_ai_framework_exists(self):
        r = Records()
        self.assertIn("AI_FRAMEWORK_MISSING", r.codes())
        r.sync_ai_framework()
        self.assertEqual(r.codes("error"), set())

    def test_ai_framework_sync_is_idempotent(self):
        r = Records()
        self.assertGreater(r.sync_ai_framework(), 0)
        self.assertEqual(r.sync_ai_framework(), 0)
        names = {f["name"] for f in r.connector().snapshot()["frameworks"]}
        self.assertIn("SOC 2 Criteria, AI Audited", names)


class PlantedDefects(unittest.TestCase):
    def setUp(self):
        self.r = Records()
        self.r.sync_ai_framework()

    def assertError(self, code):
        self.assertIn(code, self.r.codes("error"))

    def test_implemented_measure_without_evidence(self):
        shutil.rmtree(self.r.dir / "records" / "evidence" / "mfa")
        self.r.edit("measures.yaml", lambda ms: ms[0].update(documents=[]))
        self.assertError("EVIDENCE_NONE")

    def test_measure_changed_after_its_risk(self):
        self.r.edit("measures.yaml", lambda ms: ms[0].update(updated_at="2026-02-01T09:00:00Z"))
        self.assertError("RISK_OLDER_THAN_MEASURE")

    def test_risk_without_owner(self):
        self.r.edit("risks.yaml", lambda rs: rs[0].update(owner="Not assigned"))
        self.assertError("RISK_NO_OWNER")

    def test_risk_text_still_says_gap(self):
        self.r.edit("risks.yaml", lambda rs: rs[0].update(note="MFA is not yet enabled on the registrar."))
        self.assertIn("RISK_TEXT_SAYS_GAP", self.r.codes("warn"))

    def test_published_policy_without_approval_or_signature(self):
        self.r.edit("documents.yaml", lambda ds: ds[0].update(approved_by=None, signed_by=[]))
        self.assertError("POLICY_NOT_APPROVED")
        self.assertError("POLICY_NOT_SIGNED")

    def test_personal_data_vendor_without_dpa(self):
        self.r.edit("vendors.yaml", lambda vs: vs[0].update(dpa_file=False, dpa_url=""))
        self.assertError("VENDOR_NO_DPA")

    def test_independent_controller_needs_no_dpa(self):
        self.r.edit("vendors.yaml", lambda vs: vs[0].update(dpa_file=False, dpa_url="",
                                                            description="Independent controller of its own data."))
        self.assertNotIn("VENDOR_NO_DPA", self.r.codes())

    def test_system_description_section_wiped(self):
        self.r.edit("system.yaml", lambda s: s["sections"].update(team=""))
        self.assertError("SYSTEM_SECTION_EMPTY")

    def test_applicable_control_without_implemented_measure(self):
        self.r.edit("measures.yaml", lambda ms: ms[1].update(state="IN_PROGRESS"))
        self.assertError("CONTROL_NOT_COVERED")

    def test_not_applicable_without_reason(self):
        def drop(f):
            f["controls"][2]["justification"] = ""
        self.r.edit("frameworks/soc-2.yaml", drop)
        self.assertError("CONTROL_NA_NO_REASON")

    def test_link_added_to_real_framework_only(self):
        def link(f):
            f["controls"][0]["measures"].append("scanning")
        self.r.edit("frameworks/soc-2.yaml", link)
        self.assertError("AI_FRAMEWORK_DRIFT")
        self.assertEqual(self.r.sync_ai_framework(), 1)
        self.assertNotIn("AI_FRAMEWORK_DRIFT", self.r.codes())

    def test_ai_audit_on_the_real_framework(self):
        self.r.edit("audits.yaml", lambda a: a.append({"id": "a1", "name": "SOC 2 Type I, AI Audit", "firm": "soc2-auditor",
                                                        "state": "NOT_STARTED", "framework": "soc-2"}))
        self.assertError("AI_AUDIT_ON_REAL_FRAMEWORK")

    def test_overdue_finding_not_on_a_risk(self):
        self.r.edit("findings.yaml", lambda f: f.append({"id": "f1", "ref": "FND-1", "status": "OPEN",
                                                         "due": "2026-01-01T00:00:00Z", "owner": "Security owner"}))
        self.assertError("FINDING_OVERDUE")

    def test_classification_word_not_in_policy(self):
        self.r.edit("assets.yaml", lambda a: a[0].update(classification="Sensitive. Customer data."))
        self.assertIn("ASSET_CLASS_UNKNOWN", self.r.codes("warn"))

    def test_access_review_with_undecided_account(self):
        self.r.edit("access-reviews.yaml", lambda c: c[0]["entries"].append({"email": "x@example.com", "decision": None}))
        self.assertError("ACCESS_REVIEW_UNDECIDED")

    def test_every_task_done_but_measure_open(self):
        self.r.edit("measures.yaml", lambda ms: ms[1].update(state="IN_PROGRESS"))
        self.r.edit("tasks.yaml", lambda ts: ts.append({"id": "t2", "name": "Turn on scanning", "state": "DONE",
                                                        "measure": "scanning"}))
        self.assertIn("MEASURE_STATE_STALE", self.r.codes("warn"))


if __name__ == "__main__":
    unittest.main()
