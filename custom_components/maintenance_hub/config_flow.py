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


def _asset_schema(templates: dict[str, dict]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name"): selector.TextSelector(),
            vol.Required("asset_type"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=key, label=template.get("name", key))
                        for key, template in templates.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("odometer_km"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="km"
                )
            ),
        }
    )


def _interval_fields(tasks: dict[str, dict[str, Any]]) -> dict[vol.Optional, selector.Selector]:
    """One optional number field per task and unit, e.g. oil_change_km."""
    fields: dict[Any, Any] = {}
    for task_id, task in tasks.items():
        for unit in UNITS:
            fields[
                vol.Optional(
                    f"{task_id}_{unit}",
                    description={"suggested_value": task["trigger"].get(unit)},
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, mode=selector.NumberSelectorMode.BOX
                )
            )
    return fields


def _task_summary(tasks: dict[str, dict[str, Any]]) -> str:
    lines = []
    for task_id, task in tasks.items():
        units = ", ".join(f"{unit}" for unit in UNITS if unit in task["trigger"])
        lines.append(f"- {task_id}: {task['name']} ({units})")
    return "\n".join(lines)


class AssetSubentryFlow(ConfigSubentryFlow):
    """Add or edit an asset: name, type, odometer and task intervals."""

    def _templates(self) -> dict[str, dict]:
        return self.hass.data[DOMAIN]["templates"]

    def _reload(self) -> None:
        self.hass.config_entries.async_schedule_reload(self._get_entry().entry_id)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a new asset from a template."""
        templates = self._templates()
        errors: dict[str, str] = {}

        if user_input is not None:
            template = templates.get(user_input["asset_type"])
            if template is None:
                return self.async_abort(reason="unknown_template")
            data = build_asset_data(
                template,
                user_input["name"],
                user_input["asset_type"],
                user_input.get("odometer_km"),
            )
            self._reload()
            return self.async_create_subentry(title=user_input["name"], data=data)

        return self.async_show_form(
            step_id="user", data_schema=_asset_schema(templates), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit the name and the maintenance intervals of an asset."""
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        tasks: dict[str, dict[str, Any]] = {
            task_id: dict(task) for task_id, task in subentry.data["tasks"].items()
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            new_tasks: dict[str, dict[str, Any]] = {}
            for task_id, task in tasks.items():
                trigger: dict[str, float | int] = {}
                for unit in UNITS:
                    value = user_input.get(f"{task_id}_{unit}")
                    if value:
                        trigger[unit] = float(value) if unit == TRIGGER_KM else int(value)
                if not trigger:
                    errors["base"] = "no_trigger"
                new_tasks[task_id] = {**task, "trigger": trigger}

            if not errors:
                data = {**dict(subentry.data), "name": user_input["name"], "tasks": new_tasks}
                self.hass.config_entries.async_update_subentry(
                    entry, subentry, data=data, title=user_input["name"]
                )
                self._reload()
                return self.async_abort(reason="reconfigure_successful")

        schema = vol.Schema(
            {
                vol.Required("name", default=subentry.data["name"]): selector.TextSelector(),
                **_interval_fields(tasks),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
            description_placeholders={"tasks": _task_summary(tasks)},
        )
