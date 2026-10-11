"""Maintenance Hub: preventive maintenance tracking for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from types import MappingProxyType
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import ulid as ulid_util

from .const import (
    DOMAIN,
    SERVICE_ADD_ASSET,
    SERVICE_MARK_DONE,
    SERVICE_REMOVE_ASSET,
    SERVICE_SET_ODOMETER,
    SUBENTRY_ASSET,
)
from .store import MaintenanceStore
from .templates import build_asset_data, load_templates

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]
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


def _get_store(hass: HomeAssistant) -> MaintenanceStore:
    """Return the store, or fail if the integration is not set up."""
    store = hass.data.get(DOMAIN, {}).get("store")
    if store is None:
        raise HomeAssistantError("Maintenance Hub is not set up")
    return store


def _get_entry(hass: HomeAssistant) -> ConfigEntry:
    entry = hass.data.get(DOMAIN, {}).get("entry")
    if entry is None:
        raise HomeAssistantError("Maintenance Hub is not set up")
    return entry


def _reload(hass: HomeAssistant) -> None:
    hass.config_entries.async_schedule_reload(_get_entry(hass).entry_id)


def _register_services(hass: HomeAssistant) -> None:
    """Register the integration services once."""

    async def handle_add_asset(call: ServiceCall) -> None:
        templates = hass.data[DOMAIN]["templates"]
        asset_type = call.data["asset_type"]
        template = templates.get(asset_type)
        if template is None:
            raise HomeAssistantError(f"Unknown asset type '{asset_type}'")
        data = build_asset_data(
            template, call.data["name"], asset_type, call.data.get("odometer_km")
        )
        subentry = ConfigSubentry(
            data=MappingProxyType(data),
            subentry_id=ulid_util.ulid_now(),
            subentry_type=SUBENTRY_ASSET,
            title=call.data["name"],
            unique_id=None,
        )
        entry = _get_entry(hass)
        hass.config_entries.async_add_subentry(entry, subentry)
        _reload(hass)
        _LOGGER.info("Added maintenance asset %s with id %s", call.data["name"], subentry.subentry_id)

    async def handle_remove_asset(call: ServiceCall) -> None:
        store = _get_store(hass)
        asset_id = call.data["asset_id"]
        entry = _get_entry(hass)
        if asset_id not in store.asset_ids():
            raise HomeAssistantError(f"Unknown asset '{asset_id}'")
        hass.config_entries.async_remove_subentry(entry, asset_id)
        await store.async_remove_asset_history(asset_id)
        _reload(hass)
        _LOGGER.info("Removed maintenance asset %s", asset_id)

    async def handle_mark_done(call: ServiceCall) -> None:
        try:
            await _get_store(hass).async_mark_done(call.data["asset_id"], call.data["task_id"])
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

    async def handle_set_odometer(call: ServiceCall) -> None:
        try:
            await _get_store(hass).async_set_odometer(
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Load templates and register services for the integration domain."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["templates"] = await hass.async_add_executor_job(load_templates)
    _register_services(hass)
    return True


async def _migrate_legacy_assets(
    hass: HomeAssistant, entry: ConfigEntry, store: MaintenanceStore
) -> None:
    """Turn assets saved by version 0.2.x into subentries, keeping their ids."""
    for asset_id, asset in store.legacy_assets.items():
        tasks = {
            task_id: {
                "name": task["name"],
                "name_es": task.get("name_es"),
                "trigger": task["trigger"],
            }
            for task_id, task in asset.get("tasks", {}).items()
        }
        data = {
            "name": asset["name"],
            "asset_type": asset["asset_type"],
            "category": asset.get("category"),
            "odometer_km": asset.get("odometer_km"),
            "tasks": tasks,
        }
        subentry = ConfigSubentry(
            data=MappingProxyType(data),
            subentry_id=asset_id,
            subentry_type=SUBENTRY_ASSET,
            title=asset["name"],
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(entry, subentry)
    store.legacy_assets = {}


@callback
def _remove_orphan_devices(hass: HomeAssistant, entry: ConfigEntry, asset_ids: set[str]) -> None:
    """Remove devices of assets whose subentry no longer exists."""
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        for domain, ident in device.identifiers:
            if domain == DOMAIN and ident not in asset_ids:
                registry.async_remove_device(device.id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Maintenance Hub from the entry added in the UI."""
    store = MaintenanceStore(hass, entry, hass.data[DOMAIN]["templates"])
    await store.async_load()
    if store.legacy_assets:
        await _migrate_legacy_assets(hass, entry, store)
    await store.async_sync()
    _remove_orphan_devices(hass, entry, set(store.asset_ids()))

    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["entry"] = entry

    @callback
    def _refresh(_now) -> None:
        store.async_refresh()

    # Remaining days change every day, so refresh the entities periodically.
    entry.async_on_unload(async_track_time_interval(hass, _refresh, REFRESH_INTERVAL))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Maintenance Hub."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop("store", None)
        hass.data[DOMAIN].pop("entry", None)
    return unload_ok
