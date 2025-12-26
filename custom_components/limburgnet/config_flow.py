"""Config flow for Limburg.net integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)

from .const import (
    CONF_CSV_CONTENT,
    CONF_SOURCE_TYPE,
    CONF_SOURCE_URL,
    DOMAIN,
    SOURCE_TYPE_UPLOAD,
    SOURCE_TYPE_URL,
)


class LimburgNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Limburg.net."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            source_type = user_input.get(CONF_SOURCE_TYPE)

            if source_type == SOURCE_TYPE_URL:
                return await self.async_step_url()

            if source_type == SOURCE_TYPE_UPLOAD:
                return await self.async_step_upload()

            errors["base"] = "invalid_source_type"

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SOURCE_TYPE, default=SOURCE_TYPE_URL
                ): vol.In({SOURCE_TYPE_URL: "URL", SOURCE_TYPE_UPLOAD: "CSV upload"}),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_url(self, user_input: dict | None = None) -> FlowResult:
        """Handle URL/file path input step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_SOURCE_TYPE] = SOURCE_TYPE_URL
            return self.async_create_entry(
                title="Limburg.net waste pickup", data=user_input
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_URL): str,
            }
        )
        return self.async_show_form(
            step_id="url",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_upload(self, user_input: dict | None = None) -> FlowResult:
        """Handle CSV upload step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            file_path = user_input.get(CONF_CSV_CONTENT)

            # File selector returns a list with file path
            if isinstance(file_path, list) and file_path:
                file_path = file_path[0]
            elif isinstance(file_path, str):
                pass
            else:
                file_path = None

            if not file_path:
                errors[CONF_CSV_CONTENT] = "required"
            else:
                try:
                    _LOGGER.debug("FileSelector returned path: %s (type: %s)", file_path, type(file_path))
                    
                    # FileSelector returns a path that may start with /local/ (www directory)
                    # or be a relative/absolute path
                    if isinstance(file_path, str):
                        # Remove /local/ prefix if present (points to www directory)
                        if file_path.startswith("/local/"):
                            file_path = file_path[7:]  # Remove "/local/" prefix
                        
                        # Resolve path relative to www directory (where uploads go)
                        if not Path(file_path).is_absolute():
                            # Try www directory first (where FileSelector uploads files)
                            www_path = Path(self.hass.config.path("www", file_path))
                            if www_path.exists():
                                path = www_path
                            else:
                                # Try as absolute path
                                abs_path = Path(file_path)
                                if abs_path.exists():
                                    path = abs_path
                                else:
                                    # Try config directory as last resort
                                    path = Path(self.hass.config.path(file_path))
                        else:
                            path = Path(file_path)
                    else:
                        _LOGGER.error("Unexpected file_path type: %s", type(file_path))
                        errors[CONF_CSV_CONTENT] = "read_error"
                        path = None
                    
                    if path and path.exists():
                        _LOGGER.debug("Reading CSV file from: %s", path)
                        csv_content = await self.hass.async_add_executor_job(
                            lambda: path.read_text(encoding="utf-8")
                        )
                        csv_content = csv_content.strip()

                        if not csv_content:
                            errors[CONF_CSV_CONTENT] = "empty_file"
                        else:
                            data = {
                                CONF_SOURCE_TYPE: SOURCE_TYPE_UPLOAD,
                                CONF_CSV_CONTENT: csv_content,
                            }
                            return self.async_create_entry(
                                title="Limburg.net waste pickup", data=data
                            )
                    else:
                        _LOGGER.error("File not found. Tried path: %s", path)
                        errors[CONF_CSV_CONTENT] = "file_not_found"
                except FileNotFoundError as err:
                    _LOGGER.exception("FileNotFoundError: %s", err)
                    errors[CONF_CSV_CONTENT] = "file_not_found"
                except Exception as err:
                    _LOGGER.exception("Error reading uploaded CSV file: %s", err)
                    errors[CONF_CSV_CONTENT] = "read_error"

        data_schema = {
            vol.Required(CONF_CSV_CONTENT): selector.FileSelector(
                selector.FileSelectorConfig(accept=".csv,text/csv")
            ),
        }
        return self.async_show_form(
            step_id="upload",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
