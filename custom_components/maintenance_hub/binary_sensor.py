"""Overdue flag for each maintenance task."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaintenanceTaskEntity, entity_unique_id
from .store import MaintenanceStore


class MaintenanceOverdueSensor(MaintenanceTaskEntity, BinarySensorEntity):
    """On when a task is past its time or distance limit."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, store: MaintenanceStore, asset_id: str, task_id: str) -> None:
        super().__init__(store, asset_id, task_id)
        self._attr_name = f"{store.task_name(asset_id, task_id)} - {store.label('overdue')}"
        self._attr_unique_id = entity_unique_id(asset_id, task_id, "overdue")

    @property
    def is_on(self) -> bool:
        return self._status["overdue"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one overdue sensor per task, grouped under each asset."""
    store: MaintenanceStore = hass.data[DOMAIN]["store"]
    for asset_id in store.asset_ids():
        entities = [
            MaintenanceOverdueSensor(store, asset_id, task_id)
            for task_id in store.task_ids(asset_id)
        ]
        async_add_entities(entities, config_subentry_id=asset_id)
