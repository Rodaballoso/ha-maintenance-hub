"""Maintenance Hub: preventive maintenance tracking for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []  # filled in as sensor/binary_sensor/button land
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from configuration.yaml (no config flow yet)."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["templates"] = await hass.async_add_executor_job(load_templates)
    _LOGGER.debug(
        "Loaded %d maintenance templates", len(hass.data[DOMAIN]["templates"])
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry (reserved for the config-flow phase)."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
