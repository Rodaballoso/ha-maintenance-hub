"""Shared base for Maintenance Hub task entities."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATED
from .store import MaintenanceStore


class MaintenanceTaskEntity:
    """Mixin: one entity bound to one task of one asset.

    Subclasses must also inherit from a Home Assistant entity class.
    """

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, store: MaintenanceStore, asset_id: str, task_id: str) -> None:
        self._store = store
        self._asset_id = asset_id
        self._task_id = task_id

    @property
    def _status(self) -> dict[str, Any]:
        return self._store.status(self._asset_id, self._task_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose ids so users can call services for this task."""
        return {"asset_id": self._asset_id, "task_id": self._task_id}

    async def async_added_to_hass(self) -> None:
        """Subscribe to store updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


def entity_unique_id(asset_id: str, task_id: str, kind: str) -> str:
    """Build a stable unique id for an entity."""
    return f"{DOMAIN}_{asset_id}_{task_id}_{kind}"
