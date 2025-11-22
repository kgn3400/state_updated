"""Config flow for State updated integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import voluptuous as vol

# from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_DEVICE_ID,
    CONF_ENTITY_ID,
    CONF_ICON,
    CONF_NAME,
)
from homeassistant.core import State, callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)
from homeassistant.helpers.selector import (
    BooleanSelector,
    DurationSelector,
    DurationSelectorConfig,
    IconSelector,
    TemplateSelector,
)

from .const import (
    CONF_CLEAR_UPDATES_AFTER_DURATION,
    CONF_DEFAULT_TEXT_TEMPLATE,
    CONF_LAST_UPDATED,
    CONF_NEW_VALUE,
    CONF_OLD_VALUE,
    CONF_RESTORE_STATE_AFTER_RESTART,
    CONF_SKIP_UNAVAILABLE,
    CONF_SKIP_UNKNOWN,
    CONF_TEXT_TEMPLATE,
    CONF_UPDATED,
    DOMAIN,
)
from .hass_util import Translate


# ------------------------------------------------------------------
async def _validate_input(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate user input."""
    duration: timedelta = timedelta(**user_input[CONF_CLEAR_UPDATES_AFTER_DURATION])
    if duration.total_seconds() < 10:
        raise SchemaFlowError("error_duration")

    return user_input


# ------------------------------------------------------------------
async def user_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for the user step."""

    return vol.Schema(
        {
            vol.Optional(
                CONF_NAME,
            ): selector.TextSelector(),
            vol.Required(
                CONF_ENTITY_ID,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False),
                # selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, multiple=False),
            ),
        }
    )


# ------------------------------------------------------------------
async def init_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for the init step."""
    options = handler.options.copy()

    dev_id: str = ""

    if handler.parent_handler.init_step == "user":
        try:
            entity_registry = er.async_get(handler.parent_handler.hass)
            dev_id = entity_registry.async_get(options[CONF_ENTITY_ID]).device_id
        except AttributeError:
            dev_id = ""

        if dev_id is None:
            dev_id = ""

    return vol.Schema(
        {
            vol.Optional(
                CONF_ATTRIBUTE,
            ): selector.AttributeSelector(
                selector.AttributeSelectorConfig(entity_id=options[CONF_ENTITY_ID])
            ),
            vol.Optional(
                CONF_ICON,
            ): IconSelector(),
            vol.Optional(CONF_DEVICE_ID, default=dev_id): selector.DeviceSelector(),
            # vol.Required(CONF_CLEAR_UPDATES_AFTER_HOURS, default=25): NumberSelector(
            #     NumberSelectorConfig(
            #         min=0.1,
            #         max=999,
            #         step="any",
            #         mode=NumberSelectorMode.BOX,
            #         unit_of_measurement="hours",
            #     )
            # ),
            vol.Required(
                CONF_CLEAR_UPDATES_AFTER_DURATION,
                default={
                    "hours": 25,
                    "minutes": 0,
                    "seconds": 0,
                },
            ): DurationSelector(
                DurationSelectorConfig(enable_day=False, allow_negative=False)
            ),
            vol.Optional(
                CONF_TEXT_TEMPLATE,
                default=options.get(
                    CONF_TEXT_TEMPLATE,
                    await Translate(
                        handler.parent_handler.hass
                    ).async_get_localized_str(
                        CONF_DEFAULT_TEXT_TEMPLATE,
                        load_only=CONF_DEFAULT_TEXT_TEMPLATE,
                    ),
                ),
            ): TemplateSelector(),
            vol.Required(
                CONF_RESTORE_STATE_AFTER_RESTART, default=False
            ): BooleanSelector(),
            vol.Required(CONF_SKIP_UNKNOWN, default=False): BooleanSelector(),
            vol.Required(CONF_SKIP_UNAVAILABLE, default=False): BooleanSelector(),
        },
    )


CONFIG_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "user": SchemaFlowFormStep(user_schema, next_step="user_extra"),
    "user_extra": SchemaFlowFormStep(init_schema, validate_user_input=_validate_input),
}
OPTIONS_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "init": SchemaFlowFormStep(init_schema, validate_user_input=_validate_input),
}


# ------------------------------------------------------------------
# ------------------------------------------------------------------
class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow."""

    VERSION = 2
    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""

        if CONF_NAME in options:
            title: str = options[CONF_NAME]
        else:
            title = options[CONF_ENTITY_ID]
            title = title[title.find(".") + 1 :] + " updated"
            title = title.replace("_", " ")

        return cast(str, title)

    # ------------------------------------------------------------------
    @callback
    def async_config_flow_finished(self, options: Mapping[str, Any]) -> None:
        """Take necessary actions after the config flow is finished, if needed.

        The options parameter contains config entry options, which is the union of user
        input from the config flow steps.
        """
        options[CONF_NEW_VALUE] = options[CONF_OLD_VALUE] = self.get_current_state(
            options
        )

        options[CONF_UPDATED] = False
        options[CONF_LAST_UPDATED] = datetime.now(UTC).isoformat()

    # ------------------------------------------------------------------
    def get_current_state(self, user_input: dict[str, Any]) -> Any:
        """Get current state."""
        tmp_state: Any = ""
        state: State | None = self.hass.states.get(user_input[CONF_ENTITY_ID])

        if state is not None:
            if CONF_ATTRIBUTE in user_input:
                tmp_state = state.attributes.get(user_input[CONF_ATTRIBUTE])
            else:
                tmp_state = state.state

        return tmp_state
