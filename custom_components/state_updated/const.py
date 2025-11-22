"""Constants for State updated integration."""

from logging import Logger, getLogger

DOMAIN = "state_updated"
DOMAIN_NAME = "State updated"
LOGGER: Logger = getLogger(__name__)

CONF_CLEAR_UPDATES_AFTER_DURATION = "clear_update_after_duration"
CONF_CLEAR_UPDATES_AFTER_HOURS = "clear_update_after_hours"
CONF_RESTORE_STATE_AFTER_RESTART = "restore_state_after_restart"
CONF_NEW_VALUE = "new_value"
CONF_OLD_VALUE = "old_value"
CONF_LAST_UPDATED = "last_updated"
CONF_UPDATED = "updated"
CONF_TEXT_TEMPLATE = "text_template"
CONF_TEXT = "text"
CONF_SKIP_UNKNOWN = "skip_unknown"
CONF_SKIP_UNAVAILABLE = "skip_unavailable"
CONF_DEFAULT_TEXT_TEMPLATE = "config.step.user_extra.data.default_text_template"

TRANSLATION_KEY = DOMAIN

TRANSLATION_KEY_MISSING_ENTITY = "missing_entity"
