"""Readiness checks: find the drift an auditor would find, before the audit.

Every rule comes from a correction made while preparing a real SOC 2 program, or from a
finding of the AI Audit that followed (references/lessons.md has the story behind each).
A rule reads only the snapshot, so it works for every platform. Errors block the audit;
warnings need a look and a decision.
"""

from __future__ import annotations

import re
from datetime import timedelta

import aiframework
from core import PrepError, now, parse_time

DONE = {"DONE", "CANCELED", "DUPLICATE"}
OPEN = {"BACKLOG", "TODO", "IN_PROGRESS"}
POLICY_TYPES = {"POLICY", "PLAN", "PROCEDURE", "GOVERNANCE"}
SLACK = timedelta(seconds=60)
# A vendor that is its own controller, not our processor, needs no DPA (GDPR Art. 28).
CONTROLLER = re.compile(r"independent controller|not a (sub)?processor|is a controller", re.I)
GAP_WORDS = re.compile(
    r"\b(not yet|missing|planned|pending|to ?do|residual assumes|not in place|not implemented|not enabled|"
    r"not configured|will be|no evidence)\b", re.I)
DEFAULTS = {
    "evidence_record_types": ["RECORD", "REGISTER", "REPORT"],
    "approval_types": ["POLICY", "PLAN"],
    "signature_types": ["POLICY"],
    "data_classes": ["Public", "Internal", "Confidential", "Secret"],
    "vendor_assets": True,
    "access_review_max_age_days": 100,
    "personal_data_vendors": [],
    "no_dpa_needed": [],
}

RULES = []


def rule(*needs):
    def deco(fn):
        RULES.append((fn, needs))
        return fn
    return deco


class Ctx:
    def __init__(self, snap: dict, config: dict):
        self.snap, self.config = snap, config
        self.opt = {**DEFAULTS, **(config.get("checks") or {})}
        self.out: list[dict] = []
        self.measures = {m["id"]: m for m in snap["measures"]}
        self.risks = {r["id"]: r for r in snap["risks"]}
        self.docs = {d["id"]: d for d in snap["documents"]}
        self.tasks = {t["id"]: t for t in snap["tasks"]}
        self.statements: dict[str, list[dict]] = {}
        for s in snap["applicability"]:
            self.statements.setdefault(s["control_id"], []).append(s)
        self.ai_names = {f["name"] for f in snap["frameworks"] if f["name"].endswith(", AI Audited")}
        wanted = config.get("frameworks")
        self.in_scope = [f for f in snap["frameworks"]
                         if (f["name"] in wanted or f["id"] in wanted if wanted else f["name"] not in self.ai_names)]

    def add(self, level: str, code: str, record: str, message: str):
        self.out.append({"level": level, "code": code, "record": record, "message": message})

    def measure_tasks(self, m: dict) -> list[dict]:
        ids = set(m.get("task_ids") or [])
        return [t for t in self.snap["tasks"] if t["id"] in ids or t.get("measure_id") == m["id"]]


def _day(value) -> str:
    t = parse_time(value)
    return t.date().isoformat() if t else "never"


# --- measures and evidence ---

@rule()
def evidence(ctx: Ctx):
    record_types = set(ctx.opt["evidence_record_types"])
    for m in ctx.snap["measures"]:
        if m["state"] != "IMPLEMENTED" or m["evidence_count"]:
            continue
        docs = [ctx.docs[d] for d in m["document_ids"] if d in ctx.docs]
        if any(d["type"] in record_types for d in docs):
            continue
        if docs:
            ctx.add("warn", "EVIDENCE_POLICY_ONLY", f"measure '{m['name']}'",
                    "Implemented, but only policies are linked. Fine when the policy is the control (roles, approvals); "
                    "otherwise attach the record that shows the control working.")
        else:
            ctx.add("error", "EVIDENCE_NONE", f"measure '{m['name']}'",
                    "Implemented with no evidence file and no record. Attach evidence from a primary source, or set it "
                    "back to in progress and name the missing file in a task.")


@rule("tasks")
def measure_states(ctx: Ctx):
    for m in ctx.snap["measures"]:
        tasks = ctx.measure_tasks(m)
        if m["state"] == "UNKNOWN":
            ctx.add("warn", "MEASURE_UNKNOWN", f"measure '{m['name']}'", "State is unknown. Check the real system and set it.")
        if m["state"] not in ("IMPLEMENTED", "NOT_APPLICABLE") and tasks and all(t["state"] in DONE for t in tasks) \
                and any(t["state"] == "DONE" and not t["recurring"] for t in tasks):
            ctx.add("warn", "MEASURE_STATE_STALE", f"measure '{m['name']}'",
                    f"Every task is done but the measure is {m['state']}. Check the system: if the control is in place, "
                    "attach evidence and set it implemented. Never change the state without the evidence.")
        if m["state"] == "IMPLEMENTED":
            still_open = [t["name"] for t in tasks if t["state"] in OPEN and not t["recurring"]]
            if still_open:
                ctx.add("warn", "MEASURE_OPEN_TASKS", f"measure '{m['name']}'",
                        f"Implemented with open tasks ({'; '.join(still_open[:3])}). The measure and its risks must "
                        "state the remaining gap.")


# --- risks and registers ---

@rule()
def risks(ctx: Ctx):
    for r in ctx.snap["risks"]:
        label = f"risk {r['ref'] or r['name']}"
        if not r.get("owner") or r["owner"].strip().lower() in ("not assigned", "none", "unassigned"):
            ctx.add("error", "RISK_NO_OWNER", label, "No owner. Every risk has a named owner.")
        linked = [ctx.measures[i] for i in r["measure_ids"] if i in ctx.measures]
        updated = parse_time(r.get("updated_at"))
        newer = [m for m in linked if updated and parse_time(m.get("updated_at")) and parse_time(m["updated_at"]) > updated + SLACK]
        if newer:
            names = ", ".join(f"'{m['name']}' ({_day(m['updated_at'])})" for m in newer[:3])
            ctx.add("error", "RISK_OLDER_THAN_MEASURE", label,
                    f"Linked measure changed after the risk was last updated on {_day(r['updated_at'])}: {names}. "
                    "Re-read the measure and update the risk's description, note, treatment and owner to match, "
                    "then publish the risk list.")
        if linked and all(m["state"] == "IMPLEMENTED" for m in linked):
            hit = GAP_WORDS.search(f"{r.get('description', '')} {r.get('note', '')}")
            if hit:
                ctx.add("warn", "RISK_TEXT_SAYS_GAP", label,
                        f"Every linked measure is implemented, but the risk text says '{hit.group(0)}'. "
                        "Make the note state the control as the measure states it, plus any gap the evidence still shows.")
        if not linked and r.get("treatment") == "MITIGATED":
            ctx.add("warn", "RISK_NO_MEASURE", label, "Treatment is mitigated but no measure is linked.")


@rule("registers")
def registers(ctx: Ctx):
    sources = {"risks": "risks", "vendors": "vendors", "assets": "assets", "data": "data",
               "processing_activities": "processing_activities", "findings": "findings"}
    for register, key in sources.items():
        items = ctx.snap.get(key) or []
        if not items or register not in ctx.snap["registers"]:
            continue
        level = "error" if register == "risks" else "warn"
        published = parse_time(ctx.snap["registers"][register])
        times = [parse_time(i.get("updated_at")) for i in items if parse_time(i.get("updated_at"))]
        newest = max(times) if times else None
        if published is None:
            ctx.add(level, "REGISTER_NOT_PUBLISHED", f"{register} register",
                    "Never published. Publish it so the auditor has a dated copy.")
        elif newest and newest > published + SLACK:
            ctx.add(level, "REGISTER_STALE", f"{register} register",
                    f"Changed on {_day(newest)} after the last publish on {_day(published)}. Publish it again.")


# --- policies and system description ---

@rule("approvals")
def policies(ctx: Ctx):
    approval_types = set(ctx.opt["approval_types"])
    signature_types = set(ctx.opt["signature_types"])
    for d in ctx.snap["documents"]:
        if d["type"] not in approval_types:
            continue
        label = f"{d['type'].lower()} '{d['title']}'"
        p = d["published"]
        if not p:
            ctx.add("error", "POLICY_NOT_PUBLISHED", label, "No published version.")
            continue
        if p["approval_error"]:
            ctx.add("error", "POLICY_APPROVAL_UNREAD", label,
                    f"Approvals could not be read ({p['approval_error'][:120]}). That is not the same as no approval: fix the read.")
        elif not any(a["state"] == "APPROVED" for a in p["approvals"] or []):
            ctx.add("error", "POLICY_NOT_APPROVED", label,
                    f"Version {p['version']} is published with no approval. Published is not approved: the security owner "
                    "approves it in the platform. A note is not an approval.")
        if d["type"] in signature_types and "signatures" in ctx.snap["capabilities"]:
            if p["signature_error"]:
                ctx.add("error", "POLICY_SIGNATURE_UNREAD", label,
                        f"Signatures could not be read ({p['signature_error'][:120]}). A signature the API did not return is not a signature.")
            elif not any(s["state"] == "SIGNED" for s in p["signatures"] or []):
                ctx.add("error", "POLICY_NOT_SIGNED", label, f"Version {p['version']} has no signature.")
        if d["draft_newer"]:
            ctx.add("warn", "POLICY_DRAFT_PENDING", label, "A newer draft is not published. Publish and approve it, or delete it.")


@rule("system")
def system(ctx: Ctx):
    for section, text in ctx.snap["system"]["sections"].items():
        if not (text or "").strip():
            ctx.add("error", "SYSTEM_SECTION_EMPTY", f"system description: {section}",
                    "Empty. Fill it from facts; when updating, send every section (some platforms clear the ones you leave out).")
    if ctx.snap["system"].get("approved") is not True:
        ctx.add("warn", "SYSTEM_NOT_APPROVED", "system description",
                "Management has not approved it. It stays draft until management approves it, and the audit discloses that. "
                "It must not describe a control that the measures and evidence do not support.")


# --- vendors, assets, data ---

@rule("vendors")
def vendors(ctx: Ctx):
    named = {n.lower() for n in ctx.opt["personal_data_vendors"]}
    exempt = {n.lower() for n in ctx.opt["no_dpa_needed"]}
    asset_vendors = {v for a in ctx.snap["assets"] for v in a["vendor_ids"]}
    asset_names = {a["name"].lower() for a in ctx.snap["assets"]}
    for v in ctx.snap["vendors"]:
        if v.get("level") not in (None, 1):
            continue
        label = f"vendor '{v['name']}'"
        controller = CONTROLLER.search(v.get("description") or "")
        if (v.get("personal_data") or v["name"].lower() in named) and not (v.get("dpa_file") or v.get("dpa_url")) \
                and not controller and v["name"].lower() not in exempt:
            ctx.add("error", "VENDOR_NO_DPA", label,
                    "Receives personal data but has no DPA on its record. Attach the DPA (signed, or the vendor's published "
                    "terms), or stop the data flow; "
                    "until then write the open exception on the linked risk, not only in a task. If it is an independent "
                    "controller, say so in its description, or list it under checks.no_dpa_needed.")
        if ctx.opt["vendor_assets"] and "assets" in ctx.snap["capabilities"] \
                and v["id"] not in asset_vendors and v["name"].lower() not in asset_names:
            ctx.add("warn", "VENDOR_NO_ASSET", label,
                    "Not on the asset list. If the asset policy lists SaaS tools, add it (checks.vendor_assets: false turns this off).")


@rule("data")
def classes(ctx: Ctx):
    allowed = {c.lower() for c in ctx.opt["data_classes"]}
    for d in ctx.snap["data"]:
        if d.get("classification") and d["classification"].lower() not in allowed:
            ctx.add("warn", "DATA_CLASS_UNKNOWN", f"data '{d['name']}'",
                    f"Class '{d['classification']}' is not in the data classification policy ({', '.join(ctx.opt['data_classes'])}).")
    for a in ctx.snap["assets"]:
        text = (a.get("classification_text") or "").strip()
        first = re.split(r"[\s.,:;]", text, maxsplit=1)[0].lower() if text else ""
        if not text:
            ctx.add("warn", "ASSET_NO_CLASS", f"asset '{a['name']}'", "No data class stated.")
        elif first not in allowed:
            ctx.add("warn", "ASSET_CLASS_UNKNOWN", f"asset '{a['name']}'",
                    f"Starts with '{first}', not a class from the policy ({', '.join(ctx.opt['data_classes'])}). Use only the policy's words.")


# --- controls and the AI Audit framework ---

@rule()
def controls(ctx: Ctx):
    in_scope_ids = {f["id"] for f in ctx.in_scope}
    linked_measures = set()
    for c in ctx.snap["controls"]:
        if c["framework_id"] not in in_scope_ids:
            continue
        linked_measures.update(c["measure_ids"])
        label = f"control {c['ref']}"
        stmts = ctx.statements.get(c["id"], [])
        if "applicability" in ctx.snap["capabilities"] and not stmts:
            ctx.add("warn", "CONTROL_NO_SCOPE_DECISION", label, "No scope decision. Mark it applicable, or not applicable with a reason.")
        if stmts and not any(s["applicable"] for s in stmts):
            if not any((s["justification"] or "").strip() for s in stmts):
                ctx.add("error", "CONTROL_NA_NO_REASON", label, "Not applicable without a reason.")
            continue
        ms = [ctx.measures[i] for i in c["measure_ids"] if i in ctx.measures]
        if not any(m["state"] == "IMPLEMENTED" for m in ms):
            states = ", ".join(f"'{m['name']}' {m['state']}" for m in ms[:4]) or "none linked"
            ctx.add("error", "CONTROL_NOT_COVERED", label, f"No implemented measure ({states}).")
        if not any(ctx.docs[d]["type"] in POLICY_TYPES for d in c["document_ids"] if d in ctx.docs):
            ctx.add("warn", "CONTROL_NO_POLICY", label,
                    "No policy linked to the control. Link the policy behind its measures; an auditor reads policies per criterion.")
    for m in ctx.snap["measures"]:
        if m["state"] != "NOT_APPLICABLE" and m["id"] not in linked_measures:
            ctx.add("warn", "MEASURE_NO_CONTROL", f"measure '{m['name']}'", "Not linked to any control in the frameworks in scope.")


@rule()
def ai_audit(ctx: Ctx):
    if not ctx.config.get("ai_audit"):
        return
    try:
        real, ai, name = aiframework.pair(ctx.snap, ctx.config)
    except PrepError as e:
        ctx.add("error", "AI_FRAMEWORK_CONFIG", "ai_audit", str(e))
        return
    if ai is None:
        ctx.add("warn", "AI_FRAMEWORK_MISSING", f"framework '{name}'",
                "Not created yet. Run prep.py ai-framework --apply before the AI Audit.")
    else:
        ops = aiframework.plan(ctx.snap, real, ai, name)
        if ops:
            names = aiframework.resource_names(ctx.snap)
            sample = "; ".join(aiframework.describe(o, names) for o in ops[:4])
            ctx.add("error", "AI_FRAMEWORK_DRIFT", f"framework '{name}'",
                    f"{len(ops)} differences from '{real['name']}' ({sample}). Run prep.py ai-framework --apply.")
    marker = ((ctx.config.get("ai_audit") or {}).get("firm") or "").lower()
    for a in ctx.snap["audits"]:
        text = f"{a['name']} {a['firm']}".lower()
        is_ai = "ai audit" in text or "ai-audit" in text or (marker and marker in text)
        if is_ai and a["framework_id"] == real["id"]:
            ctx.add("error", "AI_AUDIT_ON_REAL_FRAMEWORK", f"audit '{a['name']}'",
                    f"An AI Audit sits on '{real['name']}'. Move it to '{name}': an AI Audit is not an official audit.")


# --- findings, tasks, access reviews, people ---

@rule("findings")
def findings(ctx: Ctx):
    for f in ctx.snap["findings"]:
        if f["status"] not in ("OPEN", "IN_PROGRESS"):
            continue
        label = f"finding {f['ref'] or f['id']}"
        due = parse_time(f.get("due"))
        if due and due < now():
            if f.get("risk_id"):
                ctx.add("warn", "FINDING_OVERDUE_ON_RISK", label,
                        f"Past its due date {_day(due)}. The linked risk must state the new date.")
            else:
                ctx.add("error", "FINDING_OVERDUE", label,
                        f"Past its due date {_day(due)} and not on a risk. Fix it, close it with a reason, or write it on "
                        "the linked risk with a new date. A scanner count is not that record.")
        if not due:
            ctx.add("warn", "FINDING_NO_DUE", label, "Open with no due date.")
        if not f.get("owner"):
            ctx.add("warn", "FINDING_NO_OWNER", label, "Open with no owner.")


@rule("tasks")
def tasks(ctx: Ctx):
    for t in ctx.snap["tasks"]:
        if t["state"] not in OPEN:
            continue
        due = parse_time(t.get("deadline"))
        if due and due < now():
            ctx.add("warn", "TASK_OVERDUE", f"task '{t['name']}'", f"Deadline {_day(due)} has passed.")
        if not t.get("assignee"):
            ctx.add("warn", "TASK_NO_ASSIGNEE", f"task '{t['name']}'", "Open with no assignee.")


@rule("access_reviews")
def access_reviews(ctx: Ctx):
    done = [c for c in ctx.snap["access_reviews"] if c["status"] == "COMPLETED"]
    if not done:
        ctx.add("error", "ACCESS_REVIEW_NONE", "access reviews", "No completed access review.")
        return
    latest = max(done, key=lambda c: parse_time(c.get("completed_at")) or now())
    label = f"access review '{latest['name']}'"
    age = now() - (parse_time(latest.get("completed_at")) or now())
    if age.days > ctx.opt["access_review_max_age_days"]:
        ctx.add("warn", "ACCESS_REVIEW_OLD", label, f"Completed {age.days} days ago.")
    undecided = [e for e in latest["entries"] if not e.get("decision") or e["decision"] == "PENDING"]
    if undecided:
        ctx.add("error", "ACCESS_REVIEW_UNDECIDED", label, f"{len(undecided)} accounts have no decision.")
    silent = [e["email"] or e["name"] for e in latest["entries"]
              if e.get("decision") in ("REVOKE", "DEFER", "ESCALATE") and not (e.get("note") or "").strip()]
    if silent:
        ctx.add("warn", "ACCESS_REVIEW_NO_NOTE", label,
                f"{len(silent)} revoke, defer or escalate decisions have no note ({', '.join(silent[:3])}). "
                "The note says why, and for revokes that the access was removed.")


@rule("people")
def people(ctx: Ctx):
    for p in ctx.snap["people"]:
        end = parse_time(p.get("contract_end"))
        if end and end < now() and p.get("state") == "ACTIVE":
            ctx.add("warn", "PERSON_ENDED_ACTIVE", f"person '{p['name']}'", "Contract ended but the profile is active. Offboard.")


@rule()
def connector_warnings(ctx: Ctx):
    for w in ctx.snap.get("warnings", []):
        ctx.add("warn", "CONNECTOR", ctx.snap["platform"], w)


def run(snap: dict, config: dict, only: set[str] | None = None) -> list[dict]:
    ctx = Ctx(snap, config)
    caps = set(snap.get("capabilities", []))
    for fn, needs in RULES:
        if all(n in caps for n in needs):
            fn(ctx)
    found = ctx.out
    if only:
        found = [f for f in found if f["code"] in only]
    return sorted(found, key=lambda f: (f["level"] != "error", f["code"], f["record"]))
