"""Maintenance logic and history for Maintenance Hub.

Assets and their intervals live in config subentries (editable from the UI).
This store only keeps the maintenance history per task and computes status.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SIGNAL_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
    SUBENTRY_ASSET,
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


def _key(asset_id: str, task_id: str) -> str:
    return f"{asset_id}:{task_id}"


class MaintenanceStore:
    """Maintenance history per task, and status computed from subentry data."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, templates: dict[str, dict]
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.templates = templates
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # "asset_id:task_id" -> {"last_date": iso, "last_km": float | None}
        self._history: dict[str, dict[str, Any]] = {}
        # Assets saved by version 0.2.x, migrated to subentries on setup.
        self.legacy_assets: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Load history from disk, converting the 0.2.x format if needed."""
        data = await self._store.async_load() or {}
        if "assets" in data:
            self.legacy_assets = data["assets"]
            for asset_id, asset in self.legacy_assets.items():
                for task_id, task in asset.get("tasks", {}).items():
                    self._history[_key(asset_id, task_id)] = {
                        "last_date": task["last_date"],
                        "last_km": task.get("last_km"),
                    }
            _LOGGER.info("Migrating %d asset(s) from version 0.2.x", len(self.legacy_assets))
        else:
            self._history = data.get("history", {})

    async def _async_save(self) -> None:
        await self._store.async_save({"history": self._history})

    @property
    def language(self) -> str:
        """Return 'es' for Spanish installations, 'en' otherwise."""
        lang = self.hass.config.language or "en"
        return "es" if lang.startswith("es") else "en"

    def label(self, key: str) -> str:
        """Return a localized UI label."""
        return LABELS[self.language][key]

    def _today(self) -> date:
        return dt_util.now().date()

    def asset_ids(self) -> list[str]:
        """Return the ids of all assets (one per asset subentry)."""
        return [
            sub_id
            for sub_id, sub in self.entry.subentries.items()
            if sub.subentry_type == SUBENTRY_ASSET
        ]

    def _asset(self, asset_id: str) -> dict[str, Any]:
        sub = self.entry.subentries.get(asset_id)
        if sub is None or sub.subentry_type != SUBENTRY_ASSET:
            raise ValueError(f"Unknown asset '{asset_id}'")
        return dict(sub.data)

    def _task(self, asset_id: str, task_id: str) -> dict[str, Any]:
        task = self._asset(asset_id)["tasks"].get(task_id)
        if task is None:
            raise ValueError(f"Unknown task '{task_id}'")
        return dict(task)

    def task_ids(self, asset_id: str) -> list[str]:
        """Return the task ids of an asset."""
        return list(self._asset(asset_id)["tasks"])

    def asset_summary(self, asset_id: str) -> tuple[str, str]:
        """Return (asset name, template name) for device registration."""
        asset = self._asset(asset_id)
        template = self.templates.get(asset["asset_type"], {})
        return asset["name"], template.get("name", asset["asset_type"])

    def task_name(self, asset_id: str, task_id: str) -> str:
        """Return the task name in the installation language."""
        task = self._task(asset_id, task_id)
        if self.language == "es" and task.get("name_es"):
            return task["name_es"]
        return task["name"]

    def status(self, asset_id: str, task_id: str) -> dict[str, Any]:
        """Compute remaining days/km and overdue state for one task."""
        asset = self._asset(asset_id)
        task = self._task(asset_id, task_id)
        trigger = task["trigger"]
        today = self._today()
        record = self._history.get(_key(asset_id, task_id), {})
        odometer = asset.get("odometer_km")

        remaining_days = None
        due_date = None
        overdue = False
        if TRIGGER_DAYS in trigger or TRIGGER_MONTHS in trigger:
            last = date.fromisoformat(record.get("last_date", today.isoformat()))
            due_date = add_months(last, trigger.get(TRIGGER_MONTHS, 0)) + timedelta(
                days=trigger.get(TRIGGER_DAYS, 0)
            )
            remaining_days = (due_date - today).days
            overdue = remaining_days < 0

        remaining_km = None
        last_km = record.get("last_km")
        if TRIGGER_KM in trigger and odometer is not None and last_km is not None:
            remaining_km = round(trigger[TRIGGER_KM] - (odometer - last_km), 1)
            overdue = overdue or remaining_km < 0

        return {
            "asset_id": asset_id,
            "task_id": task_id,
            "remaining_days": remaining_days,
            "remaining_km": remaining_km,
            "due_date": due_date.isoformat() if due_date else None,
            "overdue": overdue,
        }

    def odometer(self, asset_id: str) -> float | None:
        """Return the current odometer of an asset."""
        return self._asset(asset_id).get("odometer_km")

    async def async_sync(self) -> None:
        """Create history for new tasks and drop history of removed ones."""
        today = self._today().isoformat()
        valid: set[str] = set()
        changed = False
        for asset_id in self.asset_ids():
            asset = self._asset(asset_id)
            for task_id in asset["tasks"]:
                key = _key(asset_id, task_id)
                valid.add(key)
                if key not in self._history:
                    # New tasks start counting from today, so they are not overdue.
                    self._history[key] = {"last_date": today, "last_km": asset.get("odometer_km")}
                    changed = True
        for key in list(self._history):
            if key not in valid:
                del self._history[key]
                changed = True
        if changed:
            await self._async_save()

    async def async_mark_done(self, asset_id: str, task_id: str) -> None:
        """Record that a task was done today, at the current odometer."""
        self._task(asset_id, task_id)
        self._history[_key(asset_id, task_id)] = {
            "last_date": self._today().isoformat(),
            "last_km": self.odometer(asset_id),
        }
        await self._async_save()
        self.async_refresh()

    async def async_set_odometer(self, asset_id: str, odometer_km: float) -> None:
        """Update an asset's odometer. Rejects values below the last maintenance."""
        asset = self._asset(asset_id)
        for task_id in asset["tasks"]:
            record = self._history.get(_key(asset_id, task_id), {})
            last_km = record.get("last_km")
            if last_km is not None and odometer_km < last_km:
                raise ValueError(
                    "Odometer cannot be lower than the value recorded at the last maintenance"
                )
        for task_id in asset["tasks"]:
            record = self._history.setdefault(
                _key(asset_id, task_id),
                {"last_date": self._today().isoformat(), "last_km": None},
            )
            # First odometer reading becomes the baseline for km-based tasks.
            if record.get("last_km") is None:
                record["last_km"] = odometer_km
        await self._async_save()
        self._update_asset(asset_id, {"odometer_km": odometer_km})
        self.async_refresh()

    def _update_asset(self, asset_id: str, changes: dict[str, Any]) -> None:
        sub = self.entry.subentries[asset_id]
        self.hass.config_entries.async_update_subentry(
            self.entry, sub, data={**dict(sub.data), **changes}
        )

    async def async_remove_asset_history(self, asset_id: str) -> None:
        """Drop the history of an asset and its device, once its subentry is gone."""
        for key in [k for k in self._history if k.startswith(f"{asset_id}:")]:
            del self._history[key]
        await self._async_save()
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={(DOMAIN, asset_id)})
        if device is not None:
            registry.async_remove_device(device.id)

    @callback
    def async_refresh(self) -> None:
        """Tell all entities to recompute their state."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)
