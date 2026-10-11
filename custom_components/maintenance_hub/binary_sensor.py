"""Overdue flag for each maintenance task."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, SIGNAL_ASSET_ADDED
from .entity import MaintenanceTaskEntity, entity_unique_id
from .store import MaintenanceStore


class MaintenanceOverdueSensor(MaintenanceTaskEntity, BinarySensorEntity):
    """On when a task is past its time or distance limit."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, store: MaintenanceStore, asset_id: str, task_id: str) -> None:
        super().__init__(store, asset_id, task_id)
        self._attr_name = f"{store.display_name(asset_id, task_id)} - {store.label('overdue')}"
        self._attr_unique_id = entity_unique_id(asset_id, task_id, "overdue")

    @property
    def is_on(self) -> bool:
        return self._status["overdue"]


def _entities_for_asset(store: MaintenanceStore, asset_id: str) -> list[MaintenanceOverdueSensor]:
    return [MaintenanceOverdueSensor(store, asset_id, tid) for tid in store.task_ids(asset_id)]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Create overdue sensors for existing assets and for assets added later."""
    store: MaintenanceStore = hass.data[DOMAIN]["store"]

    entities: list[MaintenanceOverdueSensor] = []
    for asset_id in store.asset_ids():
        entities.extend(_entities_for_asset(store, asset_id))
    async_add_entities(entities)

    @callback
    def _on_asset_added(asset_id: str) -> None:
        async_add_entities(_entities_for_asset(store, asset_id))

    async_dispatcher_connect(hass, SIGNAL_ASSET_ADDED, _on_asset_added)
