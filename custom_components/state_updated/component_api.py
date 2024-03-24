"""Component api."""

from datetime import UTC, datetime, timedelta
from typing import Any

from custom_components.pypi_updates.const import CONF_CLEAR_UPDATES_AFTER_HOURS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_LAST_UPDATED,
    CONF_NEW_VALUE,
    CONF_OLD_VALUE,
    CONF_TEXT_TEMPLATE,
    CONF_UPDATED,
)


# ------------------------------------------------------------------
# ------------------------------------------------------------------
# @dataclass
class ComponentApi:
    """State updated interface."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Component api."""
        self.hass = hass
        self.entry: ConfigEntry = entry
        self.coordinator: DataUpdateCoordinator

        self.updated: bool = entry.options[CONF_UPDATED]
        self.last_updated: datetime = datetime.fromisoformat(
            entry.options[CONF_LAST_UPDATED]
        )

        self.new_value: Any = entry.options[CONF_NEW_VALUE]
        self.old_value: Any = entry.options[CONF_OLD_VALUE]
        self.create_text_from_template()

    # ------------------------------------------------------------------
    async def async_reset(self) -> None:
        """Reset."""

        self.updated = False
        self.text = ""
        tmp_options: dict[str, Any] = self.entry.options.copy()
        tmp_options[CONF_UPDATED] = self.updated

        self.hass.config_entries.async_update_entry(
            self.entry, data=tmp_options, options=tmp_options
        )
        await self.coordinator.async_refresh()

    # ------------------------------------------------------------------
    def update_state(self, new_value: Any, old_value: Any) -> None:
        """Update state."""

        if old_value in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if self.new_value not in ("", new_value):
                self.old_value = self.new_value
                self.new_value = new_value
            else:
                return

        else:
            self.new_value = new_value
            self.old_value = old_value

        if self.new_value != self.old_value:
            self.updated = True
            self.last_updated = datetime.now(UTC)
            self.create_text_from_template()
            tmp_options: dict[str, Any] = self.entry.options.copy()
            tmp_options[CONF_NEW_VALUE] = self.new_value
            tmp_options[CONF_OLD_VALUE] = self.old_value
            tmp_options[CONF_UPDATED] = self.updated
            tmp_options[CONF_LAST_UPDATED] = self.last_updated.isoformat()

            self.hass.config_entries.async_update_entry(
                self.entry, data=tmp_options, options=tmp_options
            )

    # ------------------------------------------------------------------
    async def async_update(self) -> None:
        """Update."""

        if self.updated and (
            self.last_updated
            + timedelta(hours=self.entry.options[CONF_CLEAR_UPDATES_AFTER_HOURS])
        ) < datetime.now(UTC):
            self.updated = False
            self.text = ""
            tmp_options: dict[str, Any] = self.entry.options.copy()
            tmp_options[CONF_UPDATED] = self.updated

            self.hass.config_entries.async_update_entry(
                self.entry, data=tmp_options, options=tmp_options
            )
            await self.coordinator.async_refresh()

    # ------------------------------------------------------------------
    async def async_config_entry_refresh(self) -> None:
        """Update."""
        await self.async_update()

    # ------------------------------------------------------------------
    def create_text_from_template(self) -> None:
        """Create text from template."""

        if self.updated and self.entry.options.get(CONF_TEXT_TEMPLATE, "") != "":
            values: dict[str, Any] = {
                CONF_ENTITY_ID: self.entry.options.get(CONF_ENTITY_ID, ""),
                CONF_ATTRIBUTE: self.entry.options.get(CONF_ATTRIBUTE, ""),
                CONF_NEW_VALUE: self.new_value,
                CONF_OLD_VALUE: self.old_value,
                CONF_LAST_UPDATED: self.last_updated.isoformat(),
            }

            value_template: Template | None = Template(
                str(self.entry.options.get(CONF_TEXT_TEMPLATE)), self.hass
            )

            self.text = value_template.async_render_with_possible_json_value(
                self.new_value, variables=values
            )

        else:
            self.text = ""