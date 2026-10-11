"""Remaining days or kilometres for each maintenance task."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, SIGNAL_ASSET_ADDED
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


def _entities_for_asset(store: MaintenanceStore, asset_id: str) -> list[SensorEntity]:
    return [MaintenanceRemainingSensor(store, asset_id, tid) for tid in store.task_ids(asset_id)]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Create sensors for existing assets and for assets added later."""
    store: MaintenanceStore = hass.data[DOMAIN]["store"]

    entities: list[SensorEntity] = []
    for asset_id in store.asset_ids():
        entities.extend(_entities_for_asset(store, asset_id))
    async_add_entities(entities)

    @callback
    def _on_asset_added(asset_id: str) -> None:
        async_add_entities(_entities_for_asset(store, asset_id))

    async_dispatcher_connect(hass, SIGNAL_ASSET_ADDED, _on_asset_added)
