"""Services for State updated integration."""

from homeassistant.core import HomeAssistant

from .component_api import ComponentApi

# from .const import DOMAIN


async def async_setup_services(
    hass: HomeAssistant, component_api: ComponentApi
) -> None:
    """Set up the services for the State updated integration."""

    # hass.services.async_register(
    #     DOMAIN, "reset_all", component_api.async_reset_all_service
    # )
