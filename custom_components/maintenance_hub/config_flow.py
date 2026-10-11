"""Config and subentry flows for Maintenance Hub."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, SUBENTRY_ASSET, TRIGGER_DAYS, TRIGGER_KM, TRIGGER_MONTHS
from .templates import build_asset_data

UNITS = (TRIGGER_MONTHS, TRIGGER_DAYS, TRIGGER_KM)

# Asset types offered in the "Add" menu, in order. Each needs a template file.
SHIPPED_ASSET_TYPES = ("boiler", "nas", "car", "motorcycle")


class MaintenanceHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add Maintenance Hub from the UI. Only one instance is allowed."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Assets are added as subentries."""
        return {SUBENTRY_ASSET: AssetSubentryFlow}

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Maintenance Hub", data={})

        return self.async_show_form(step_id="user")


def _needs_odometer(template: dict) -> bool:
    """Only assets with distance-based tasks ask for the odometer."""
    return any(TRIGGER_KM in task.get("trigger", {}) for task in template.get("tasks", []))


def _name_schema(template: dict) -> vol.Schema:
    fields: dict[Any, Any] = {vol.Required("name"): selector.TextSelector()}
    if _needs_odometer(template):
        fields[vol.Required("odometer_km")] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="km"
            )
        )
    return vol.Schema(fields)


def _interval_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, mode=selector.NumberSelectorMode.BOX)
    )


def _task_summary(tasks: dict[str, dict[str, Any]]) -> str:
    lines = []
    for task_id, task in tasks.items():
        units = ", ".join(unit for unit in UNITS if unit in task["trigger"])
        lines.append(f"- {task_id}: {task['name']} ({units})")
    return "\n".join(lines)


def _parse_trigger(user_input: dict[str, Any], prefix: str) -> dict[str, float | int]:
    """Read the interval fields. `prefix` is '<task_id>' or 'new_task'."""
    trigger: dict[str, float | int] = {}
    for unit in UNITS:
        value = user_input.get(f"{prefix}_{unit}")
        if value:
            trigger[unit] = float(value) if unit == TRIGGER_KM else int(value)
    return trigger


def _new_task_id(name: str, existing: dict[str, Any]) -> str:
    """Build a task id from its name, unique within the asset."""
    base = "".join(char if char.isalnum() else "_" for char in name.lower()).strip("_") or "task"
    task_id, counter = base, 2
    while task_id in existing:
        task_id = f"{base}_{counter}"
        counter += 1
    return task_id


class AssetSubentryFlow(ConfigSubentryFlow):
    """Add an asset (chosen from a menu) or edit its name, intervals and tasks."""

    def _templates(self) -> dict[str, dict]:
        return self.hass.data[DOMAIN]["templates"]

    def _reload(self) -> None:
        self.hass.config_entries.async_schedule_reload(self._get_entry().entry_id)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Show the menu of asset types to add."""
        templates = self._templates()
        options = [f"add_{asset_type}" for asset_type in SHIPPED_ASSET_TYPES if asset_type in templates]
        if not options:
            return self.async_abort(reason="unknown_template")
        return self.async_show_menu(step_id="user", menu_options=options)

    async def _async_add_asset(
        self, asset_type: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        template = self._templates().get(asset_type)
        if template is None:
            return self.async_abort(reason="unknown_template")

        if user_input is not None:
            data = build_asset_data(
                template, user_input["name"], asset_type, user_input.get("odometer_km")
            )
            self._reload()
            return self.async_create_entry(title=user_input["name"], data=data)

        return self.async_show_form(
            step_id=f"add_{asset_type}",
            data_schema=_name_schema(template),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit the name, the intervals of each task, and add new tasks."""
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        tasks: dict[str, dict[str, Any]] = {
            task_id: dict(task) for task_id, task in subentry.data["tasks"].items()
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            new_tasks: dict[str, dict[str, Any]] = {}
            for task_id, task in tasks.items():
                trigger = _parse_trigger(user_input, task_id)
                if not trigger:
                    errors["base"] = "no_trigger"
                new_tasks[task_id] = {**task, "trigger": trigger}

            new_name = user_input.get("new_task_name", "").strip()
            if new_name:
                trigger = _parse_trigger(user_input, "new_task")
                if not trigger:
                    errors["base"] = "no_trigger"
                else:
                    task_id = _new_task_id(new_name, new_tasks)
                    new_tasks[task_id] = {"name": new_name, "name_es": None, "trigger": trigger}

            if not errors:
                data = {**dict(subentry.data), "name": user_input["name"], "tasks": new_tasks}
                self.hass.config_entries.async_update_subentry(
                    entry, subentry, data=data, title=user_input["name"]
                )
                self._reload()
                return self.async_abort(reason="reconfigure_successful")

        fields: dict[Any, Any] = {
            vol.Required("name", default=subentry.data["name"]): selector.TextSelector(),
        }
        for task_id, task in tasks.items():
            for unit in UNITS:
                fields[
                    vol.Optional(
                        f"{task_id}_{unit}",
                        description={"suggested_value": task["trigger"].get(unit)},
                    )
                ] = _interval_selector()
        fields[vol.Optional("new_task_name")] = selector.TextSelector()
        for unit in UNITS:
            fields[vol.Optional(f"new_task_{unit}")] = _interval_selector()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders={"tasks": _task_summary(tasks)},
        )


def _make_add_step(asset_type: str):
    """Build the step that adds one asset type (add_boiler, add_nas, ...)."""

    async def _step(self: AssetSubentryFlow, user_input: dict[str, Any] | None = None):
        return await self._async_add_asset(asset_type, user_input)

    _step.__name__ = f"async_step_add_{asset_type}"
    return _step


for _asset_type in SHIPPED_ASSET_TYPES:
    setattr(AssetSubentryFlow, f"async_step_add_{_asset_type}", _make_add_step(_asset_type))
