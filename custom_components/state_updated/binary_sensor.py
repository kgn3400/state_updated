"""Support for State updated."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ICON,
    CONF_ATTRIBUTE,
    CONF_DEVICE_ID,
    CONF_ENTITY_ID,
    CONF_ICON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall, State, callback
from homeassistant.helpers import (
    entity_platform,
    entity_registry as er,
    icon as ic,
    issue_registry as ir,
    start,
)
from homeassistant.helpers.device import async_device_info_to_link_from_device_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import CommonConfigEntry
from .component_api import ComponentApi
from .const import (
    CONF_LAST_UPDATED,
    CONF_NEW_VALUE,
    CONF_OLD_VALUE,
    CONF_SKIP_UNAVAILABLE,
    CONF_SKIP_UNKNOWN,
    DOMAIN,
    DOMAIN_NAME,
    LOGGER,
    TRANSLATION_KEY,
    TRANSLATION_KEY_MISSING_ENTITY,
)


# ------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: CommonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Entry for State updated setup."""

    async_add_entities([StateUpdatedBinarySensor(hass, entry)])


# ------------------------------------------------------
# ------------------------------------------------------
class StateUpdatedBinarySensor(BinarySensorEntity):
    """Sensor class for State updated."""

    entity_list: list[ComponentApi] = []

    # ------------------------------------------------------
    def __init__(
        self,
        hass: HomeAssistant,
        entry: CommonConfigEntry,
    ) -> None:
        """Binary sensor."""

        self.entry: CommonConfigEntry = entry
        self.hass = hass

        self.translation_key = TRANSLATION_KEY

        self.component_api: ComponentApi = entry.runtime_data.component_api

        self.coordinator: DataUpdateCoordinator = entry.runtime_data.coordinator
        self.component_api.coordinator = self.coordinator

        platform = entity_platform.async_get_current_platform()
        platform.async_register_entity_service(
            "reset_entity",
            None,
            self.async_reset_entity,
        )

        self.hass.services.async_register(
            DOMAIN, "reset_all", self.async_reset_all_service
        )

        self.entity_icon: str = None

        self._attr_device_info = async_device_info_to_link_from_device_id(
            hass,
            entry.options.get(CONF_DEVICE_ID),
        )

    # ------------------------------------------------------
    async def async_reset_entity(
        self, entity: StateUpdatedBinarySensor, call: ServiceCall
    ) -> None:
        """Reset entity."""
        await entity.component_api.async_reset()

    # ------------------------------------------------------------------
    async def async_reset_all_service(self, call: ServiceCall) -> None:
        """Reset all service."""

        for entity in StateUpdatedBinarySensor.entity_list:
            await entity.async_reset()

    # ------------------------------------------------------
    async def async_will_remove_from_hass(self) -> None:
        """When removed from hass."""
        StateUpdatedBinarySensor.entity_list.remove(self.component_api)

    # ------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Complete device setup after being added to hass."""

        # ------------------------------------------------------
        @callback
        def sensor_state_listener(
            event: Event[EventStateChangedData],
        ) -> None:
            """Handle state changes on the observed device."""
            if (tmp_state := event.data["new_state"]) is None:
                return

            if (
                self.entry.options.get(CONF_SKIP_UNKNOWN, False)
                and tmp_state.state == STATE_UNKNOWN
            ) or (
                self.entry.options.get(CONF_SKIP_UNAVAILABLE, False)
                and tmp_state.state == STATE_UNAVAILABLE
            ):
                return

            try:
                if CONF_ATTRIBUTE in self.entry.options:
                    new_value = tmp_state.attributes.get(
                        self.entry.options[CONF_ATTRIBUTE]
                    )
                else:
                    new_value = tmp_state.state

                if new_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    old_value = STATE_UNKNOWN

                    if (tmp_state := event.data["old_state"]) is not None:
                        if CONF_ATTRIBUTE in self.entry.options:
                            old_value = tmp_state.attributes.get(
                                self.entry.options[CONF_ATTRIBUTE]
                            )
                        else:
                            old_value = tmp_state.state

                    self.component_api.update_state(new_value, old_value)
                    self.async_schedule_update_ha_state(True)
            except (ValueError, TypeError) as ex:
                LOGGER.error(ex)

        await super().async_added_to_hass()

        await self.coordinator.async_config_entry_first_refresh()

        StateUpdatedBinarySensor.entity_list.append(self.component_api)

        self.entry.async_on_unload(self.entry.add_update_listener(self.update_listener))

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self.entry.options[CONF_ENTITY_ID],
                sensor_state_listener,
            )
        )
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

        self.async_on_remove(start.async_at_started(self.hass, self.hass_started))

    # ------------------------------------------------------
    async def async_verify_entity_exist(
        self,
    ) -> bool:
        """Verify entity exist."""

        state: State | None = self.hass.states.get(
            self.entry.options.get(CONF_ENTITY_ID)
        )

        if state is None:
            await self.async_create_issue_entity(
                self.entry.options.get(CONF_ENTITY_ID),
                TRANSLATION_KEY_MISSING_ENTITY,
            )
            self.coordinator.update_interval = None
            return False

        return True

    # ------------------------------------------------------
    async def hass_started(self, _event: Event) -> None:
        """Hass started."""

        if await self.async_verify_entity_exist():
            self.entity_icon = await self.async_get_icon(
                self.entry.options.get(CONF_ENTITY_ID)
            )

        self.component_api.set_point_in_time_trigger(self)

    # ------------------------------------------------------------------
    async def async_create_issue_entity(
        self, entity_id: str, translation_key: str
    ) -> None:
        """Create issue on entity."""

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            DOMAIN_NAME + datetime.now().isoformat(),
            issue_domain=DOMAIN,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders={
                "entity": entity_id,
                "state_updated_helper": self.entity_id,
            },
        )

    # ------------------------------------------------------
    async def update_listener(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Reload on config entry update."""
        # await hass.config_entries.async_reload(entry.entry_id)
        await self.component_api.async_config_entry_refresh()

    # ------------------------------------------------------
    @property
    def name(self) -> str:
        """Name.

        Returns:
            str: Name of sensor

        """
        return self.entry.title

    # ------------------------------------------------------
    @property
    def unique_id(self) -> str:
        """Unique id.

        Returns:
            str: Unique id

        """

        return self.entry.entry_id

    # ------------------------------------------------------
    @property
    def icon(self) -> str:
        """Icon.

        Returns:
            str: Icon name

        """

        if self.entry.options.get(CONF_ICON, "").strip() != "":
            return self.entry.options.get(CONF_ICON, "mdi:state-machine")

        return self.entity_icon

    # ------------------------------------------------------
    @property
    def is_on(self) -> bool:
        """Get the state."""

        return self.component_api.updated

    # ------------------------------------------------------
    @property
    def extra_state_attributes(self) -> dict:
        """Extra state attributes.

        Returns:
            dict: _description_

        """

        if self.component_api is None:
            return {}

        return {
            CONF_NEW_VALUE: self.component_api.new_value,
            CONF_OLD_VALUE: self.component_api.old_value,
            CONF_LAST_UPDATED: self.component_api.last_updated,  # .isoformat(),
            "text": self.component_api.text,
        }

    # ------------------------------------------------------
    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    # ------------------------------------------------------
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    # ------------------------------------------------------
    async def async_update(self) -> None:
        """Update the entity. Only used by the generic entity update service."""
        await self.coordinator.async_request_refresh()

    # ------------------------------------------------------
    async def async_get_icon(self, entity_id: str) -> str:
        """Get icon."""

        state: State | None = self.hass.states.get(entity_id)
        tmp_icon = state.attributes.get(ATTR_ICON, None)

        if tmp_icon is not None:
            return tmp_icon

        entity_registry = er.async_get(self.hass)
        source_entity = entity_registry.async_get(entity_id)

        if source_entity is not None:
            if source_entity.icon is not None:
                return source_entity.icon

            icons = await ic.async_get_icons(
                self.hass,
                "entity",
                integrations=[source_entity.platform],
                # "entity_component",
                # integrations=["sensor"],
            )

            if (
                icons is not None
                and source_entity.platform in icons
                and source_entity.domain in icons[source_entity.platform]
                and source_entity.translation_key
                in icons[source_entity.platform][source_entity.domain]
                and "default"
                in icons[source_entity.platform][source_entity.domain][
                    source_entity.translation_key
                ]
            ):
                return icons[source_entity.platform][source_entity.domain][
                    source_entity.translation_key
                ]["default"]

        return None
