"""The State updated integration."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device_id

# from homeassistant.helpers.device import (
#     async_remove_stale_devices_links_keep_current_device,
# )
from homeassistant.helpers.helper_integration import (
    async_handle_source_entity_changes,
    # async_remove_helper_config_entry_from_source_device,
    async_remove_helper_devices,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .component_api import ComponentApi
from .const import (
    CONF_CLEAR_UPDATES_AFTER_DURATION,
    CONF_CLEAR_UPDATES_AFTER_HOURS,
    DOMAIN,
    LOGGER,
)
from .hass_util import check_supress_config_update_listener

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]


# ------------------------------------------------------------------
# ------------------------------------------------------------------
@dataclass
class CommonData:
    """Common data."""

    coordinator: DataUpdateCoordinator
    component_api: ComponentApi


# The type alias needs to be suffixed with 'ConfigEntry'
type CommonConfigEntry = ConfigEntry[CommonData]


# ------------------------------------------------------------------
async def async_migrate_entry(hass: HomeAssistant, entry: CommonConfigEntry) -> bool:
    """Migrate old entry."""

    if entry.version < 2:
        pass

    if entry.version == 1:
        new_options: dict[str, Any] = entry.options.copy()

        timer_float: float = new_options.get(CONF_CLEAR_UPDATES_AFTER_HOURS, 25.0)
        hours: int = int(timer_float)
        minutes_float = (timer_float - hours) * 60
        minutes: int = int((timer_float - hours) * 60)
        seconds: int = round((minutes_float - minutes) * 60)
        duration_check: timedelta = timedelta(
            hours=hours, minutes=minutes, seconds=seconds
        )

        if duration_check.total_seconds() < 10:
            seconds = 10

        new_options[CONF_CLEAR_UPDATES_AFTER_DURATION] = {
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
        }

        hass.config_entries.async_update_entry(
            entry,
            data=new_options,
            options=new_options,
            version=2,  # Set new version
        )

        LOGGER.info("Migration to version %s successful", entry.version)

        return True
    return False


# ------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: CommonConfigEntry) -> bool:
    """Set up State updates from a config entry."""

    component_api: ComponentApi = ComponentApi(
        hass,
        entry,
    )

    coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=DOMAIN,
        update_interval=timedelta(minutes=1),
        update_method=component_api.async_update,
        config_entry=entry,
    )

    entry.runtime_data = CommonData(
        component_api=component_api,
        coordinator=coordinator,
    )

    entry.async_on_unload(entry.add_update_listener(config_update_listener))

    async_remove_helper_devices(
        hass,
        helper_config_entry_id=entry.entry_id,
        source_device_id=async_entity_id_to_device_id(
            hass, entry.options[CONF_ENTITY_ID]
        ),
        remove_all_devices=True,
    )

    def set_source_entity_id_or_uuid(source_entity_id: str) -> None:
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_ENTITY_ID: source_entity_id},
        )
        hass.config_entries.async_schedule_reload(entry.entry_id)

    async def source_entity_removed() -> None:
        # The source entity has been removed, we remove the config entry because
        # we do not allow replacing the input entity.
        await hass.config_entries.async_remove(entry.entry_id)

    entry.async_on_unload(
        async_handle_source_entity_changes(
            hass,
            helper_config_entry_id=entry.entry_id,
            set_source_entity_id_or_uuid=set_source_entity_id_or_uuid,
            source_device_id=async_entity_id_to_device_id(
                hass, entry.options[CONF_ENTITY_ID]
            ),
            source_entity_id_or_uuid=entry.options[CONF_ENTITY_ID],
            source_entity_removed=source_entity_removed,
        )
    )

    # async_remove_stale_devices_links_keep_current_device(
    #     hass,
    #     entry.entry_id,
    #     entry.options.get(CONF_DEVICE_ID),
    # )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


# ------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: CommonConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# ------------------------------------------------------------------
async def async_reload_entry(hass: HomeAssistant, entry: CommonConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# ------------------------------------------------------------------
@check_supress_config_update_listener()
async def config_update_listener(
    hass: HomeAssistant,
    config_entry: CommonConfigEntry,
) -> None:
    """Reload on config entry update."""

    await hass.config_entries.async_reload(config_entry.entry_id)
