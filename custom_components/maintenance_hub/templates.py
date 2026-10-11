"""Load maintenance templates and build asset data from them."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .const import CATEGORY_EQUIPMENT, SUPPORTED_TRIGGERS

_LOGGER = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_templates() -> dict[str, dict]:
    """Load every YAML template shipped with the integration, keyed by asset type."""
    templates: dict[str, dict] = {}
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            _LOGGER.exception("Could not load maintenance template %s", path.name)
            continue
        asset_type = data.get("asset_type", path.stem)
        templates[asset_type] = data
    return templates


def build_asset_data(
    template: dict, name: str, asset_type: str, odometer_km: float | None
) -> dict[str, Any]:
    """Build the subentry data for a new asset from a template."""
    tasks: dict[str, dict[str, Any]] = {}
    for task in template.get("tasks", []):
        trigger = {
            key: value
            for key, value in task.get("trigger", {}).items()
            if key in SUPPORTED_TRIGGERS
        }
        if not trigger:
            _LOGGER.warning("Task %s in %s has no supported trigger", task.get("id"), asset_type)
            continue
        tasks[task["id"]] = {
            "name": task["name"],
            "name_es": task.get("name_es"),
            "trigger": trigger,
        }
    return {
        "name": name,
        "asset_type": asset_type,
        "category": template.get("category", CATEGORY_EQUIPMENT),
        "odometer_km": odometer_km,
        "tasks": tasks,
    }
