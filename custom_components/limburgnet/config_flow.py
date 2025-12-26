"""Config flow for Limburg.net integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
            _LOGGER.debug("Raw file_path from user_input: %s (type: %s)", file_path, type(file_path))

            # File selector returns a list with file path
            if isinstance(file_path, list) and file_path:
                file_path = file_path[0]
                _LOGGER.debug("Extracted from list: %s", file_path)
            elif isinstance(file_path, str):
                _LOGGER.debug("file_path is string: %s", file_path)
            elif isinstance(file_path, dict):
                _LOGGER.debug("file_path is dict: %s", file_path)
                # FileSelector might return a dict with file info
                if "file" in file_path:
                    file_path = file_path["file"]
                elif "path" in file_path:
                    file_path = file_path["path"]
                elif "content" in file_path:
                    file_path = file_path["content"]
                else:
                    _LOGGER.warning("Unexpected dict structure: %s", file_path)
                    file_path = None
            else:
                _LOGGER.warning("Unexpected file_path type: %s", type(file_path))
                file_path = None

            if not file_path:
                _LOGGER.error("No file_path after processing. Original: %s", user_input.get(CONF_CSV_CONTENT))
                errors[CONF_CSV_CONTENT] = "required"
            else:
                try:
                    _LOGGER.debug("FileSelector returned path: %s (type: %s)", file_path, type(file_path))
                    
                    # FileSelector returns a path that may be a hash ID or file path
                    # Files are typically stored in www directory
                    path = None
                    possible_paths = []
                    if isinstance(file_path, str):
                        # Remove /local/ prefix if present (points to www directory)
                        if file_path.startswith("/local/"):
                            file_path = file_path[7:]  # Remove "/local/" prefix
                        
                        # Try multiple locations where uploaded files might be stored
                        
                        if Path(file_path).is_absolute():
                            possible_paths.append(Path(file_path))
                        else:
                            # Try www directory (most common for uploads)
                            www_base = Path(self.hass.config.path("www"))
                            possible_paths.append(www_base / file_path)
                            # Try www/uploads subdirectory
                            possible_paths.append(www_base / "uploads" / file_path)
                            # Try config directory
                            possible_paths.append(Path(self.hass.config.path(file_path)))
                            # Try as absolute path
                            possible_paths.append(Path(file_path))
                            
                            # Also search recursively in www directory for files with matching name/hash
                            if www_base.exists():
                                try:
                                    for found_file in www_base.rglob(file_path):
                                        if found_file.is_file():
                                            possible_paths.append(found_file)
                                            _LOGGER.debug("Found potential file via recursive search: %s", found_file)
                                except Exception as search_err:
                                    _LOGGER.debug("Recursive search failed: %s", search_err)
                        
                        # Find the first existing path
                        for test_path in possible_paths:
                            _LOGGER.debug("Checking if file exists at: %s", test_path)
                            if test_path.exists() and test_path.is_file():
                                path = test_path
                                _LOGGER.info("Found file at: %s", path)
                                break
                        
                        # If not found, try reading via HTTP (for files in www directory)
                        http_success = False
                        if not path or not path.exists():
                            # Try /local/ URL (www directory accessible via HTTP)
                            clean_path = file_path.lstrip("/")
                            local_url = f"http://127.0.0.1:8123/local/{clean_path}"
                            
                            try:
                                _LOGGER.debug("Trying to read file via HTTP: %s", local_url)
                                session = async_get_clientsession(self.hass)
                                async with session.get(local_url, timeout=5) as resp:
                                    if resp.status == 200:
                                        csv_content = await resp.text()
                                        csv_content = csv_content.strip()
                                        if csv_content:
                                            _LOGGER.info("Successfully read file via HTTP")
                                            http_success = True
                                            data = {
                                                CONF_SOURCE_TYPE: SOURCE_TYPE_UPLOAD,
                                                CONF_CSV_CONTENT: csv_content,
                                            }
                                            return self.async_create_entry(
                                                title="Limburg.net waste pickup", data=data
                                            )
                                    else:
                                        _LOGGER.debug("HTTP request returned status: %s", resp.status)
                            except Exception as http_err:
                                _LOGGER.debug("HTTP read failed: %s", http_err)
                    else:
                        _LOGGER.error("Unexpected file_path type: %s", type(file_path))
                        errors[CONF_CSV_CONTENT] = "read_error"
                        path = None
                    
                    # Only try file reading if HTTP didn't succeed and we have a path
                    if not http_success:
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
                            # Log all attempted paths for debugging
                            if isinstance(file_path, str) and possible_paths:
                                _LOGGER.error(
                                    "File not found. Original path: %s, Resolved path: %s, Tried %d locations: %s",
                                    file_path,
                                    path,
                                    len(possible_paths),
                                    [str(p) for p in possible_paths[:5]],  # Show first 5 paths
                                )
                            else:
                                _LOGGER.error(
                                    "File not found. file_path: %s (type: %s), path: %s",
                                    file_path,
                                    type(file_path),
                                    path,
                                )
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
