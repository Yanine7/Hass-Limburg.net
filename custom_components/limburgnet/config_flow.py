"""Config flow for Limburg.net integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

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
            csv_content = user_input.get(CONF_CSV_CONTENT, "")

            # Handle different input types
            if isinstance(csv_content, list) and csv_content:
                csv_content = csv_content[0]
            elif isinstance(csv_content, dict):
                if "content" in csv_content:
                    csv_content = csv_content["content"]
                elif "file" in csv_content:
                    csv_content = csv_content["file"]
                else:
                    csv_content = str(csv_content)

            if isinstance(csv_content, bytes):
                csv_content = csv_content.decode("utf-8")
            elif not isinstance(csv_content, str):
                csv_content = str(csv_content)

            csv_content = (csv_content or "").strip()

            if not csv_content:
                errors[CONF_CSV_CONTENT] = "required"
            else:
                data = {
                    CONF_SOURCE_TYPE: SOURCE_TYPE_UPLOAD,
                    CONF_CSV_CONTENT: csv_content,
                }
                return self.async_create_entry(
                    title="Limburg.net waste pickup", data=data
                )

        data_schema = {
            vol.Required(CONF_CSV_CONTENT): selector.selector(
                {"text": {"multiline": True, "suffix": "Plak hier de CSV-inhoud van Limburg.net"}}
            ),
        }
        return self.async_show_form(
            step_id="upload",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
