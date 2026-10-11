"""Persistent data and maintenance logic for Maintenance Hub."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
import logging
from typing import Any
import uuid

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CATEGORY_EQUIPMENT,
    DOMAIN,
    SIGNAL_ASSET_ADDED,
    SIGNAL_ASSET_REMOVED,
    SIGNAL_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
    SUPPORTED_TRIGGERS,
    TRIGGER_DAYS,
    TRIGGER_KM,
    TRIGGER_MONTHS,
)

_LOGGER = logging.getLogger(__name__)

LABELS = {
    "en": {"overdue": "overdue", "done": "done"},
    "es": {"overdue": "vencida", "done": "hecho"},
}


def add_months(day: date, months: int) -> date:
    """Add calendar months to a date, clamping the day to the end of the month."""
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


class MaintenanceStore:
    """Holds assets and their maintenance tasks, persisted in .storage."""

    def __init__(self, hass: HomeAssistant, templates: dict[str, dict]) -> None:
        self.hass = hass
        self.templates = templates
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._assets: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Load the saved assets from disk."""
        data = await self._store.async_load()
        if data:
            self._assets = data.get("assets", {})

    async def _async_save(self) -> None:
        await self._store.async_save({"assets": self._assets})

    @property
    def language(self) -> str:
        """Return 'es' for Spanish installations, 'en' otherwise."""
        lang = self.hass.config.language or "en"
        return "es" if lang.startswith("es") else "en"

    def label(self, key: str) -> str:
        """Return a localized UI label."""
        return LABELS[self.language][key]

    def asset_ids(self) -> list[str]:
        """Return all asset ids."""
        return list(self._assets)

    def task_ids(self, asset_id: str) -> list[str]:
        """Return the task ids of an asset."""
        return list(self._get_asset(asset_id)["tasks"])

    def asset_summary(self, asset_id: str) -> tuple[str, str]:
        """Return (asset name, template name) for device registration."""
        asset = self._get_asset(asset_id)
        template = self.templates.get(asset["asset_type"], {})
        return asset["name"], template.get("name", asset["asset_type"])

    def task_name(self, asset_id: str, task_id: str) -> str:
        """Return the task name in the installation language."""
        task = self._get_task(self._get_asset(asset_id), task_id)
        if self.language == "es" and task.get("name_es"):
            return task["name_es"]
        return task["name"]

    def _get_asset(self, asset_id: str) -> dict[str, Any]:
        asset = self._assets.get(asset_id)
        if asset is None:
            raise ValueError(f"Unknown asset '{asset_id}'")
        return asset

    @staticmethod
    def _get_task(asset: dict[str, Any], task_id: str) -> dict[str, Any]:
        task = asset["tasks"].get(task_id)
        if task is None:
            raise ValueError(f"Unknown task '{task_id}'")
        return task

    def _today(self) -> date:
        return dt_util.now().date()

    def status(self, asset_id: str, task_id: str) -> dict[str, Any]:
        """Compute remaining days/km and overdue state for one task."""
        asset = self._get_asset(asset_id)
        task = self._get_task(asset, task_id)
        trigger = task["trigger"]
        today = self._today()

        remaining_days = None
        due_date = None
        overdue = False
        if TRIGGER_DAYS in trigger or TRIGGER_MONTHS in trigger:
            last = date.fromisoformat(task["last_date"])
            due_date = add_months(last, trigger.get(TRIGGER_MONTHS, 0)) + timedelta(
                days=trigger.get(TRIGGER_DAYS, 0)
            )
            remaining_days = (due_date - today).days
            overdue = remaining_days < 0

        remaining_km = None
        odometer = asset.get("odometer_km")
        if TRIGGER_KM in trigger and odometer is not None and task.get("last_km") is not None:
            used = odometer - task["last_km"]
            remaining_km = round(trigger[TRIGGER_KM] - used, 1)
            overdue = overdue or remaining_km < 0

        return {
            "asset_id": asset_id,
            "task_id": task_id,
            "remaining_days": remaining_days,
            "remaining_km": remaining_km,
            "due_date": due_date.isoformat() if due_date else None,
            "overdue": overdue,
        }

    async def async_add_asset(
        self, name: str, asset_type: str, odometer_km: float | None = None
    ) -> str:
        """Create an asset and its tasks from a template. Returns the asset id."""
        template = self.templates.get(asset_type)
        if template is None:
            raise ValueError(f"Unknown asset type '{asset_type}'")

        today = self._today().isoformat()
        tasks: dict[str, dict[str, Any]] = {}
        for task in template.get("tasks", []):
            trigger = {
                key: value
                for key, value in task.get("trigger", {}).items()
                if key in SUPPORTED_TRIGGERS
            }
            if not trigger:
                _LOGGER.warning(
                    "Task %s in %s has no supported trigger", task.get("id"), asset_type
                )
                continue
            tasks[task["id"]] = {
                "name": task["name"],
                "name_es": task.get("name_es"),
                "trigger": trigger,
                # Start counting from today, so new tasks are not overdue.
                "last_date": today,
                "last_km": odometer_km,
            }

        asset_id = uuid.uuid4().hex[:8]
        self._assets[asset_id] = {
            "name": name,
            "asset_type": asset_type,
            "category": template.get("category", CATEGORY_EQUIPMENT),
            "odometer_km": odometer_km,
            "tasks": tasks,
        }
        await self._async_save()
        async_dispatcher_send(self.hass, SIGNAL_ASSET_ADDED, asset_id)
        return asset_id

    async def async_remove_asset(self, asset_id: str) -> None:
        """Delete an asset, its entities and its device."""
        self._get_asset(asset_id)
        del self._assets[asset_id]
        await self._async_save()
        async_dispatcher_send(self.hass, SIGNAL_ASSET_REMOVED, asset_id)

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, asset_id)})
        if device is not None:
            device_registry.async_remove_device(device.id)

    async def async_mark_done(self, asset_id: str, task_id: str) -> None:
        """Record that a task was done today, at the current odometer."""
        asset = self._get_asset(asset_id)
        task = self._get_task(asset, task_id)
        task["last_date"] = self._today().isoformat()
        task["last_km"] = asset.get("odometer_km")
        await self._async_save()
        self.async_refresh()

    async def async_set_odometer(self, asset_id: str, odometer_km: float) -> None:
        """Update an asset's odometer. Rejects values below the last maintenance."""
        asset = self._get_asset(asset_id)
        for task in asset["tasks"].values():
            if task.get("last_km") is not None and odometer_km < task["last_km"]:
                raise ValueError(
                    "Odometer cannot be lower than the value recorded at the last maintenance"
                )
        asset["odometer_km"] = odometer_km
        # First odometer reading becomes the baseline for km-based tasks.
        for task in asset["tasks"].values():
            if task.get("last_km") is None:
                task["last_km"] = odometer_km
        await self._async_save()
        self.async_refresh()

    @callback
    def async_refresh(self) -> None:
        """Tell all entities to recompute their state."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)
