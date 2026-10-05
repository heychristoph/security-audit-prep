#!/usr/bin/env python3
"""audit-prep command line. Run from the folder that holds prep.yaml, or pass --config.

  status                      what the platform holds, and the next step
  check [--only CODES]        readiness checks; exit code 1 when any error is left
  show MEASURE                a measure with its risks, documents, tasks and controls
  ai-framework [--apply]      plan (default) or apply the "<X> Criteria, AI Audited" sync
       [--audit NAME --firm F]   also create the AI Audit record on that framework
  evidence MEASURE FILE...    attach evidence files to a measure, then confirm they are there
  snapshot [-o FILE]          write the normalized snapshot as JSON
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aiframework  # noqa: E402
import checks  # noqa: E402
import connectors  # noqa: E402
from core import PrepError, load_config  # noqa: E402


def load(args):
    config = load_config(args.config)
    if getattr(args, "snapshot", None):
        return config, None, json.loads(Path(args.snapshot).read_text())
    connector = connectors.load(config)
    return config, connector, connector.snapshot()


def find_measure(snap: dict, key: str) -> dict:
    exact = [m for m in snap["measures"] if key in (m["id"], m["name"])]
    if exact:
        return exact[0]
    loose = [m for m in snap["measures"] if key.lower() in m["name"].lower()]
    if len(loose) == 1:
        return loose[0]
    if not loose:
        raise PrepError(f"No measure matches '{key}'.")
    raise PrepError(f"'{key}' matches {len(loose)} measures: " + "; ".join(m["name"] for m in loose[:8]))


def cmd_status(args):
    config, _, snap = load(args)
    print(f"{snap['platform']}: {snap['source']}")
    states = collections.Counter(m["state"] for m in snap["measures"])
    print("measures:", ", ".join(f"{k.lower()} {v}" for k, v in sorted(states.items())))
    for f in snap["frameworks"]:
        n = sum(1 for c in snap["controls"] if c["framework_id"] == f["id"])
        print(f"framework '{f['name']}': {n} controls")
    open_tasks = [t for t in snap["tasks"] if t["state"] in checks.OPEN]
    by_priority = collections.Counter(t.get("priority") or "NONE" for t in open_tasks)
    print("open tasks:", len(open_tasks), "(" + ", ".join(f"{k.lower()} {v}" for k, v in sorted(by_priority.items())) + ")")
    for a in snap["audits"]:
        fw = next((f["name"] for f in snap["frameworks"] if f["id"] == a["framework_id"]), "?")
        print(f"audit '{a['name']}' on '{fw}': {a['state']}")
    found = checks.run(snap, config)
    errors = sum(f["level"] == "error" for f in found)
    print(f"check: {errors} errors, {len(found) - errors} warnings")
    print("next:", "fix the errors from `prep.py check`" if errors else "review the warnings, then run the AI Audit")


def cmd_check(args):
    config, _, snap = load(args)
    only = set(args.only.split(",")) if args.only else None
    found = checks.run(snap, config, only)
    if args.json:
        print(json.dumps(found, indent=1))
    else:
        by_code = collections.defaultdict(list)
        for f in found:
            by_code[(f["level"], f["code"])].append(f)
        for (level, code), items in by_code.items():
            if level == "warn" and args.errors_only:
                continue
            print(f"\n{level.upper()} {code} ({len(items)})")
            for f in items[: args.limit]:
                print(f"  - {f['record']}: {f['message']}")
            if len(items) > args.limit:
                print(f"  ... {len(items) - args.limit} more (use --limit or --json)")
        errors = sum(f["level"] == "error" for f in found)
        print(f"\n{errors} errors, {len(found) - errors} warnings.")
    return 1 if any(f["level"] == "error" for f in found) else 0


def cmd_show(args):
    _, _, snap = load(args)
    m = find_measure(snap, args.measure)
    print(f"MEASURE {m['name']} [{m['state']}] updated {m['updated_at']}")
    print(f"  {m['description']}")
    print(f"  evidence files: {m['evidence_count']}")
    for d in (x for x in snap["documents"] if x["id"] in m["document_ids"]):
        print(f"  document: {d['title']} ({d['type']})")
    for c in (x for x in snap["controls"] if m["id"] in x["measure_ids"]):
        fw = next((f["name"] for f in snap["frameworks"] if f["id"] == c["framework_id"]), "?")
        print(f"  control: {c['ref']} in '{fw}'")
    for t in (x for x in snap["tasks"] if x["id"] in m["task_ids"] or x.get("measure_id") == m["id"]):
        print(f"  task: {t['name']} [{t['state']}]")
    for r in (x for x in snap["risks"] if x["id"] in m["risk_ids"] or m["id"] in x["measure_ids"]):
        print(f"\nRISK {r['ref']} {r['name']} [{r['treatment']}] owner {r['owner'] or 'NONE'} updated {r['updated_at']}")
        print(f"  description: {r['description']}")
        print(f"  note: {r['note']}")
    published = snap["registers"].get("risks")
    print(f"\nrisk list last published: {published or 'never'}")


def cmd_ai_framework(args):
    config, connector, snap = load(args)
    real, ai, name = aiframework.pair(snap, config)
    ops = aiframework.plan(snap, real, ai, name, prune=not args.no_prune)
    names = aiframework.resource_names(snap)
    if not ops:
        print(f"'{name}' matches '{real['name']}': nothing to do.")
    else:
        print(f"{len(ops)} changes to make '{name}' match '{real['name']}':")
        for op in ops[: args.limit]:
            print("  " + aiframework.describe(op, names))
        if len(ops) > args.limit:
            print(f"  ... {len(ops) - args.limit} more")
    if args.apply and ops:
        result = aiframework.apply(connector, snap, real, ai, ops, log=lambda s: print("  " + s), out_dir=config["_dir"])
        ai = {"id": result["id"], "name": name}
        snap = connector.snapshot()
        real, ai, _ = aiframework.pair(snap, config)
        left = aiframework.plan(snap, real, ai, name, prune=not args.no_prune)
        left = [o for o in left if o["op"] != "extra_control"]
        print("in sync now." if not left else f"{len(left)} differences left; run again and read the errors.")
    elif ops:
        print("Dry run. Add --apply to make these changes.")
    if args.audit:
        if not args.apply:
            print(f"Would create audit '{args.audit}' on '{name}' (firm: {args.firm}). Add --apply.")
        elif any(a["name"] == args.audit for a in snap["audits"]):
            print(f"Audit '{args.audit}' exists.")
        else:
            framework = aiframework.find_framework(snap, name)
            audit_id = connector.create_audit(framework["id"], args.audit, args.firm, args.state)
            print(f"Created audit '{args.audit}' ({audit_id}) on '{name}'.")


def cmd_evidence(args):
    config, connector, snap = load(args)
    m = find_measure(snap, args.measure)
    before = m["evidence_count"]
    for f in args.files:
        path = Path(f)
        if not path.is_file():
            raise PrepError(f"{path} is not a file.")
        evidence_id = connector.upload_evidence(m["id"], path)
        print(f"attached {path.name} to '{m['name']}' ({evidence_id})")
    after = find_measure(connector.snapshot(), m["id"])["evidence_count"]
    print(f"evidence files on '{m['name']}': {before} -> {after}")
    if after < before + len(args.files):
        raise PrepError("The platform does not show every file. Check the measure before calling it done.")


def cmd_snapshot(args):
    _, _, snap = load(args)
    text = json.dumps(snap, indent=1)
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output}")
    else:
        print(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="path to prep.yaml (default: ./prep.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("check")
    p.add_argument("--only", help="comma-separated codes")
    p.add_argument("--json", action="store_true")
    p.add_argument("--errors-only", action="store_true")
    p.add_argument("--limit", type=int, default=10, help="records shown per code")
    p.add_argument("--snapshot", help="check a saved snapshot instead of the live platform")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("show")
    p.add_argument("measure", help="measure id or (part of its) name")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("ai-framework")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--no-prune", action="store_true", help="keep links that exist only in the AI framework")
    p.add_argument("--audit", help="name of the AI Audit record to create on the AI framework")
    p.add_argument("--firm", default="AI Audit (not an official audit)")
    p.add_argument("--state", default="NOT_STARTED")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(fn=cmd_ai_framework)
    p = sub.add_parser("evidence")
    p.add_argument("measure", help="measure id or (part of its) name")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_evidence)
    p = sub.add_parser("snapshot")
    p.add_argument("-o", "--output")
    p.set_defaults(fn=cmd_snapshot)

    args = parser.parse_args(argv)
    try:
        return args.fn(args) or 0
    except PrepError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
