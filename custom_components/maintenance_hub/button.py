"""Button to mark each maintenance task as done."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, SIGNAL_ASSET_ADDED
from .entity import MaintenanceTaskEntity, entity_unique_id
from .store import MaintenanceStore


class MaintenanceDoneButton(MaintenanceTaskEntity, ButtonEntity):
    """Press to record that the task was done now."""

    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, store: MaintenanceStore, asset_id: str, task_id: str) -> None:
        super().__init__(store, asset_id, task_id)
        self._attr_name = f"{store.display_name(asset_id, task_id)} - {store.label('done')}"
        self._attr_unique_id = entity_unique_id(asset_id, task_id, "done")

    async def async_press(self) -> None:
        await self._store.async_mark_done(self._asset_id, self._task_id)


def _entities_for_asset(store: MaintenanceStore, asset_id: str) -> list[MaintenanceDoneButton]:
    return [MaintenanceDoneButton(store, asset_id, tid) for tid in store.task_ids(asset_id)]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Create buttons for existing assets and for assets added later."""
    store: MaintenanceStore = hass.data[DOMAIN]["store"]

    entities: list[MaintenanceDoneButton] = []
    for asset_id in store.asset_ids():
        entities.extend(_entities_for_asset(store, asset_id))
    async_add_entities(entities)

    @callback
    def _on_asset_added(asset_id: str) -> None:
        async_add_entities(_entities_for_asset(store, asset_id))

    async_dispatcher_connect(hass, SIGNAL_ASSET_ADDED, _on_asset_added)
