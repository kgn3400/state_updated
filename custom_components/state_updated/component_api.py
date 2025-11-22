"""Component api."""

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity import get_unit_of_measurement
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_CLEAR_UPDATES_AFTER_DURATION,
    CONF_CLEAR_UPDATES_AFTER_HOURS,
    CONF_LAST_UPDATED,
    CONF_NEW_VALUE,
    CONF_OLD_VALUE,
    CONF_RESTORE_STATE_AFTER_RESTART,
    CONF_TEXT,
    CONF_TEXT_TEMPLATE,
    CONF_UPDATED,
    DOMAIN,
    DOMAIN_NAME,
    TRANSLATION_KEY_MISSING_ENTITY,
)
from .hass_util import PointInUTCTimeTrigger, set_supress_config_update_listener


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
        self.updated: bool = False
        self.last_updated: datetime = datetime.now(UTC).isoformat()
        self.text: str = ""
        self.new_value: Any = ""
        self.old_value: Any = ""
        self.duration = timedelta(
            **(
                self.entry.options.get(
                    CONF_CLEAR_UPDATES_AFTER_DURATION,
                    {
                        "hours": 25,
                        "minutes": 0,
                        "seconds": 0,
                    },
                )
            )
        )

        self.uom: str = self.get_uom()
        self.point_in_time_trigger: PointInUTCTimeTrigger = None

        # if entry.options.get(CONF_RESTORE_STATE_AFTER_RESTART, False):
        #     self.updated: bool = entry.options.get(CONF_UPDATED, False)
        # self.last_updated: datetime = datetime.fromisoformat(
        #     entry.options.get(CONF_LAST_UPDATED, datetime.now(UTC).isoformat)
        # )
        #     self.text: str = entry.options.get(CONF_TEXT, "")
        #     self.new_value: Any = entry.options.get(CONF_NEW_VALUE, "")
        #     self.old_value: Any = entry.options.get(CONF_OLD_VALUE, "")
        #     self.create_text_from_template()

    # ------------------------------------------------------------------
    def set_point_in_time_trigger(self, entity: Entity) -> None:
        """Set point in time trigger."""

        self.point_in_time_trigger = PointInUTCTimeTrigger(
            entity,
            callback_trigger=self.async_clear_updated,
        )

        # Check if state has to be restored
        if self.entry.options.get(CONF_RESTORE_STATE_AFTER_RESTART, False):
            state: State = self.hass.states.get(self.entry.options[CONF_ENTITY_ID])

            if not state:
                return

            if CONF_ATTRIBUTE in self.entry.options:
                self.new_value = state.attributes.get(
                    self.entry.options[CONF_ATTRIBUTE]
                )
            else:
                self.new_value = state.state

            if self.new_value != self.entry.options.get(CONF_NEW_VALUE, ""):
                return

            # if the state has been updated and we have a duration and the last updated time is in the future, start the

            self.last_updated: datetime = datetime.fromisoformat(
                self.entry.options.get(CONF_LAST_UPDATED, datetime.now(UTC).isoformat)
            )

            if (
                self.entry.options.get(CONF_UPDATED, False)
                and self.last_updated is not None
                and self.duration is not None
                and (self.last_updated + self.duration) > datetime.now(UTC)
            ):
                self.point_in_time_trigger.start(
                    point_in_time_UTC=self.last_updated + self.duration
                )
                self.updated: bool = self.entry.options.get(CONF_UPDATED, False)
                self.last_updated: datetime = datetime.fromisoformat(
                    self.entry.options.get(
                        CONF_LAST_UPDATED, datetime.now(UTC).isoformat
                    )
                )
                self.text: str = self.entry.options.get(CONF_TEXT, "")
                self.new_value: Any = self.entry.options.get(CONF_NEW_VALUE, "")
                self.old_value: Any = self.entry.options.get(CONF_OLD_VALUE, "")
                self.create_text_from_template()
            else:
                self.updated = False
                self.last_updated = datetime.now(UTC)
                self.text = ""
                self.new_value = ""
                self.old_value = ""

            self.update_config()

    # ------------------------------------------------------------------
    async def async_reset(self) -> None:
        """Reset."""

        self.updated = False
        self.text = ""

        self.update_config()
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

            self.update_config()
            self.point_in_time_trigger.start(duration=self.duration)

        self.uom = self.get_uom()

    # ------------------------------------------------------------------
    @set_supress_config_update_listener()
    def update_config(self) -> None:
        """Update config."""

        tmp_options: dict[str, Any] = self.entry.options.copy()
        tmp_options[CONF_NEW_VALUE] = self.new_value
        tmp_options[CONF_OLD_VALUE] = self.old_value
        tmp_options[CONF_UPDATED] = self.updated
        tmp_options[CONF_TEXT] = self.text
        tmp_options[CONF_LAST_UPDATED] = self.last_updated.isoformat()

        self.hass.config_entries.async_update_entry(
            self.entry, data=tmp_options, options=tmp_options
        )

    # ------------------------------------------------------------------
    async def async_clear_updated(self) -> None:
        """Update."""

        self.updated = False
        self.text = ""
        self.new_value = ""
        self.old_value = ""

        self.update_config()
        await self.coordinator.async_refresh()

    # ------------------------------------------------------------------
    async def async_update(self) -> None:
        """Update."""

        return
        if self.updated and (
            self.last_updated
            + timedelta(hours=self.entry.options[CONF_CLEAR_UPDATES_AFTER_HOURS])
        ) < datetime.now(UTC):
            self.updated = False
            self.text = ""

            self.update_config()
            await self.coordinator.async_refresh()

    # ------------------------------------------------------------------
    async def async_config_entry_refresh(self) -> None:
        """Config entry hass been updated."""
        await self.async_update()

    # ------------------------------------------------------------------
    def get_uom(self) -> str:
        """Get uom."""

        if self.entry.options.get(CONF_ENTITY_ID, "") != "":
            try:
                tmp_uom: str = get_unit_of_measurement(
                    self.hass,
                    self.entry.options.get(CONF_ENTITY_ID),
                )

                if tmp_uom is not None:
                    if tmp_uom == "%":
                        return tmp_uom

                    return " " + tmp_uom
            except HomeAssistantError:
                pass

        return ""

    # ------------------------------------------------------------------
    def create_text_from_template(self) -> None:
        """Create text from template."""

        if self.updated and self.entry.options.get(CONF_TEXT_TEMPLATE, ""):
            values: dict[str, Any] = {
                CONF_ENTITY_ID: self.entry.options.get(CONF_ENTITY_ID, ""),
                CONF_ATTRIBUTE: self.entry.options.get(CONF_ATTRIBUTE, ""),
                CONF_NEW_VALUE: self.new_value + self.uom,
                CONF_OLD_VALUE: self.old_value + self.uom,
                CONF_LAST_UPDATED: self.last_updated.isoformat(),
            }

            try:
                value_template: Template | None = Template(
                    str(self.entry.options.get(CONF_TEXT_TEMPLATE)), self.hass
                )

                self.text = value_template.async_render(values)
            except (TypeError, TemplateError) as e:
                self.create_issue_template(
                    str(e),
                    value_template.template,
                    TRANSLATION_KEY_MISSING_ENTITY,
                )

        else:
            self.text = ""

    # ------------------------------------------------------------------
    def create_issue_template(
        self,
        error_txt: str,
        template: str,
        translation_key: str,
    ) -> None:
        """Create issue on entity."""

        if (
            self.last_error_template != template
            or error_txt != self.last_error_txt_template
        ):
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                DOMAIN_NAME + datetime.now().isoformat(),
                issue_domain=DOMAIN,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=translation_key,
                translation_placeholders={
                    "error_txt": error_txt,
                    "template": template,
                },
            )
            self.last_error_template = template
            self.last_error_txt_template = error_txt
