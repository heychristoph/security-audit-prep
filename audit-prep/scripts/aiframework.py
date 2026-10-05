"""The "<Framework> Criteria, AI Audited" framework.

An AI Audit is not an official audit, so it never sits on the real framework's audit
record. It gets its own framework: a copy of the real framework's controls with the same
measure links, document links and scope decisions. Measures, evidence and documents are
shared, not copied. Only the links exist twice, so they must be kept in sync: `plan`
lists every difference, `apply` makes the AI framework match the real one.
"""

from __future__ import annotations

import csv
from pathlib import Path

from core import PrepError


def ai_name(config: dict, real: dict) -> str:
    return (config.get("ai_audit") or {}).get("name") or f"{real['name']} Criteria, AI Audited"


def ai_description(real: dict) -> str:
    # Public on trust portals: say what it is, nothing internal.
    return f"The {real['name']} criteria, assessed in an AI Audit. An AI Audit is not an official {real['name']} audit or attestation."


def find_framework(snap: dict, wanted: str) -> dict | None:
    for f in snap["frameworks"]:
        if wanted in (f["id"], f["name"]):
            return f
    return None


def pair(snap: dict, config: dict) -> tuple[dict, dict | None, str]:
    """The real framework named in ai_audit.framework, its AI copy (or None) and the copy's name."""
    wanted = (config.get("ai_audit") or {}).get("framework")
    if not wanted:
        raise PrepError("Set ai_audit.framework in prep.yaml to the real framework the AI Audit copies.")
    real = find_framework(snap, wanted)
    if not real:
        names = ", ".join(f["name"] for f in snap["frameworks"]) or "none"
        raise PrepError(f"Framework '{wanted}' not found. Frameworks: {names}.")
    name = ai_name(config, real)
    return real, find_framework(snap, name), name


def plan(snap: dict, real: dict, ai: dict | None, name: str, prune: bool = True) -> list[dict]:
    """Operations that make the AI framework match the real one. Empty when in sync."""
    ops: list[dict] = []
    if ai is None:
        ops.append({"op": "create_framework", "name": name, "description": ai_description(real)})
    controls = lambda fid: {c["ref"]: c for c in snap["controls"] if c["framework_id"] == fid}
    real_controls = controls(real["id"])
    ai_controls = controls(ai["id"]) if ai else {}
    statements: dict[str, list[dict]] = {}
    for s in snap["applicability"]:
        statements.setdefault(s["control_id"], []).append(s)

    for ref, rc in sorted(real_controls.items()):
        ac = ai_controls.get(ref)
        if ac is None:
            ops.append({"op": "create_control", "ref": ref, "control": rc})
        have = set(ac["measure_ids"] + ac["document_ids"]) if ac else set()
        want = set(rc["measure_ids"] + rc["document_ids"])
        for rid in sorted(want - have):
            ops.append({"op": "link", "ref": ref, "resource_id": rid})
        if prune:
            for rid in sorted(have - want):
                ops.append({"op": "unlink", "ref": ref, "resource_id": rid})
        ai_by_soa = {s["soa_id"]: s for s in statements.get(ac["id"], [])} if ac else {}
        for s in statements.get(rc["id"], []):
            current = ai_by_soa.get(s["soa_id"])
            if current is None:
                ops.append({"op": "add_applicability", "ref": ref, "soa_id": s["soa_id"],
                            "applicable": s["applicable"], "justification": s["justification"]})
            elif (current["applicable"], current["justification"]) != (s["applicable"], s["justification"]):
                ops.append({"op": "update_applicability", "ref": ref, "statement_id": current["id"],
                            "applicable": s["applicable"], "justification": s["justification"]})
    for ref in sorted(set(ai_controls) - set(real_controls)):
        ops.append({"op": "extra_control", "ref": ref})
    return ops


def describe(op: dict, names: dict[str, str]) -> str:
    kind = op["op"]
    if kind == "create_framework":
        return f"create framework '{op['name']}'"
    if kind == "create_control":
        return f"{op['ref']}: create control"
    if kind in ("link", "unlink"):
        return f"{op['ref']}: {kind} {names.get(op['resource_id'], op['resource_id'])}"
    if kind in ("add_applicability", "update_applicability"):
        verb = "add" if kind.startswith("add") else "set"
        state = "applicable" if op["applicable"] else "not applicable"
        return f"{op['ref']}: {verb} scope decision '{state}'"
    if kind == "extra_control":
        return f"{op['ref']}: only in the AI framework; delete it in the platform if the real framework dropped it"
    return str(op)


def apply(connector, snap: dict, real: dict, ai: dict | None, ops: list[dict], log=print, out_dir: str = ".") -> dict | None:
    """Carry out the plan. Safe to re-run: a second run finds nothing left to do."""
    framework_id = ai["id"] if ai else None
    ai_ids = {c["ref"]: c["id"] for c in snap["controls"] if ai and c["framework_id"] == ai["id"]}
    for op in ops:
        kind = op["op"]
        if kind == "create_framework":
            try:
                framework_id = connector.create_framework(op["name"], op["description"])
            except PrepError as e:
                path = write_import_csv(snap, real, op["name"], out_dir)
                raise PrepError(f"{e} Wrote {path}: import it as a custom framework named '{op['name']}', "
                                "then run ai-framework --apply again to link it.") from e
        elif kind == "create_control":
            if not framework_id:
                raise PrepError("No AI framework id; create the framework first.")
            ai_ids[op["ref"]] = connector.create_control(framework_id, op["control"])
        elif kind == "link":
            connector.link_control(ai_ids[op["ref"]], op["resource_id"])
        elif kind == "unlink":
            connector.unlink_control(ai_ids[op["ref"]], op["resource_id"])
        elif kind == "add_applicability":
            connector.add_applicability(op["soa_id"], ai_ids[op["ref"]], op["applicable"], op["justification"] or None)
        elif kind == "update_applicability":
            connector.update_applicability(op["statement_id"], op["applicable"], op["justification"] or None)
        elif kind == "extra_control":
            log(f"skipped: {op['ref']} exists only in the AI framework")
            continue
        log(f"done: {kind} {op.get('ref', op.get('name', ''))}")
    return {"id": framework_id}


def resource_names(snap: dict) -> dict[str, str]:
    names = {m["id"]: f"measure '{m['name']}'" for m in snap["measures"]}
    names.update({d["id"]: f"document '{d['title']}'" for d in snap["documents"]})
    return names


def write_import_csv(snap: dict, real: dict, name: str, out_dir: str) -> Path:
    """For platforms without a framework API: the copy as a CSV to import in their UI."""
    path = Path(out_dir) / (name.replace(",", "").replace(" ", "-") + ".csv")
    measures = {m["id"]: m["name"] for m in snap["measures"]}
    scope = {s["control_id"]: s for s in snap["applicability"]}
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "description", "controls", "applicable", "justification"])
        for c in sorted((c for c in snap["controls"] if c["framework_id"] == real["id"]), key=lambda c: c["ref"]):
            s = scope.get(c["id"], {})
            w.writerow([c["ref"], c["name"], c["description"], "; ".join(measures.get(i, i) for i in c["measure_ids"]),
                        s.get("applicable", True), s.get("justification", "")])
    return path
