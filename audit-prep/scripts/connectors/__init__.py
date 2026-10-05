"""Connectors turn a compliance platform into a snapshot and carry out writes.

A connector is a module here with a class `Platform(Connector)` (see base.py). Add a
platform by adding a module and a page in references/connectors/; nothing else changes.
"""

import importlib

NAMES = ("probo", "vanta", "drata", "folder")


def load(config: dict):
    name = config["platform"]
    module = importlib.import_module(f"connectors.{name}")
    return module.Platform(config.get("options") or {}, config)
