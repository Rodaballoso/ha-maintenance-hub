"""Button to mark each maintenance task as done."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaintenanceTaskEntity, entity_unique_id
from .store import MaintenanceStore


class MaintenanceDoneButton(MaintenanceTaskEntity, ButtonEntity):
    """Press to record that the task was done now."""

    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, store: MaintenanceStore, asset_id: str, task_id: str) -> None:
        super().__init__(store, asset_id, task_id)
        self._attr_name = f"{store.task_name(asset_id, task_id)} - {store.label('done')}"
        self._attr_unique_id = entity_unique_id(asset_id, task_id, "done")

    async def async_press(self) -> None:
        await self._store.async_mark_done(self._asset_id, self._task_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one done button per task, grouped under each asset."""
    store: MaintenanceStore = hass.data[DOMAIN]["store"]
    for asset_id in store.asset_ids():
        entities = [
            MaintenanceDoneButton(store, asset_id, task_id)
            for task_id in store.task_ids(asset_id)
        ]
        async_add_entities(entities, config_subentry_id=asset_id)
