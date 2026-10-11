"""Remaining days or kilometres for each maintenance task."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaintenanceTaskEntity, entity_unique_id
from .store import MaintenanceStore


class MaintenanceRemainingSensor(MaintenanceTaskEntity, SensorEntity):
    """Days remaining (time-based) or km remaining (distance-based) for a task.

    If a task has both, the state shows days and km is in the attributes.
    """

    def __init__(self, store: MaintenanceStore, asset_id: str, task_id: str) -> None:
        super().__init__(store, asset_id, task_id)
        self._attr_unique_id = entity_unique_id(asset_id, task_id, "remaining")

    @property
    def native_value(self) -> int | None:
        status = self._status
        if status["remaining_days"] is not None:
            return status["remaining_days"]
        return status["remaining_km"]

    @property
    def native_unit_of_measurement(self) -> str | None:
        status = self._status
        if status["remaining_days"] is not None:
            return UnitOfTime.DAYS
        if status["remaining_km"] is not None:
            return UnitOfLength.KILOMETERS
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self._status
        return {
            **super().extra_state_attributes,
            "remaining_km": status["remaining_km"],
            "due_date": status["due_date"],
            "overdue": status["overdue"],
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one sensor per task, grouped under each asset's subentry."""
    store: MaintenanceStore = hass.data[DOMAIN]["store"]
    for asset_id in store.asset_ids():
        entities = [
            MaintenanceRemainingSensor(store, asset_id, task_id)
            for task_id in store.task_ids(asset_id)
        ]
        async_add_entities(entities, config_subentry_id=asset_id)
