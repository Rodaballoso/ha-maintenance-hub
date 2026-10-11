"""Maintenance Hub: preventive maintenance tracking for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path

import voluptuous as vol
import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    SERVICE_ADD_ASSET,
    SERVICE_MARK_DONE,
    SERVICE_REMOVE_ASSET,
    SERVICE_SET_ODOMETER,
)
from .store import MaintenanceStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ("sensor", "binary_sensor", "button")
TEMPLATES_DIR = Path(__file__).parent / "templates"
REFRESH_INTERVAL = timedelta(hours=1)

ADD_ASSET_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required("asset_type"): cv.string,
        vol.Optional("odometer_km"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)
REMOVE_ASSET_SCHEMA = vol.Schema({vol.Required("asset_id"): cv.string})
MARK_DONE_SCHEMA = vol.Schema(
    {vol.Required("asset_id"): cv.string, vol.Required("task_id"): cv.string}
)
SET_ODOMETER_SCHEMA = vol.Schema(
    {
        vol.Required("asset_id"): cv.string,
        vol.Required("odometer_km"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)


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

    templates = await hass.async_add_executor_job(load_templates)
    store = MaintenanceStore(hass, templates)
    await store.async_load()
    hass.data[DOMAIN]["store"] = store
    _LOGGER.debug("Loaded %d maintenance templates", len(templates))

    @callback
    def _refresh(_now) -> None:
        store.async_refresh()

    # Remaining days change every day, so refresh the entities periodically.
    async_track_time_interval(hass, _refresh, REFRESH_INTERVAL)

    for platform in PLATFORMS:
        await async_load_platform(hass, platform, DOMAIN, {}, config)

    _register_services(hass, store)
    return True


def _register_services(hass: HomeAssistant, store: MaintenanceStore) -> None:
    """Register the integration services."""

    async def handle_add_asset(call: ServiceCall) -> None:
        try:
            asset_id = await store.async_add_asset(
                call.data["name"],
                call.data["asset_type"],
                call.data.get("odometer_km"),
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        _LOGGER.info("Added maintenance asset %s with id %s", call.data["name"], asset_id)

    async def handle_remove_asset(call: ServiceCall) -> None:
        try:
            await store.async_remove_asset(call.data["asset_id"])
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        _LOGGER.info("Removed maintenance asset %s", call.data["asset_id"])

    async def handle_mark_done(call: ServiceCall) -> None:
        try:
            await store.async_mark_done(call.data["asset_id"], call.data["task_id"])
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

    async def handle_set_odometer(call: ServiceCall) -> None:
        try:
            await store.async_set_odometer(
                call.data["asset_id"], call.data["odometer_km"]
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_ASSET, handle_add_asset, schema=ADD_ASSET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_ASSET, handle_remove_asset, schema=REMOVE_ASSET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_MARK_DONE, handle_mark_done, schema=MARK_DONE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_ODOMETER, handle_set_odometer, schema=SET_ODOMETER_SCHEMA
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry (reserved for the config-flow phase)."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
