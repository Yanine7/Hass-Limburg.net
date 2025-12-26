"""Constants for the Limburg.net integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "limburgnet"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_SOURCE_URL = "source_url"
CONF_SOURCE_TYPE = "source_type"
CONF_CSV_CONTENT = "csv_content"

SOURCE_TYPE_URL = "url"
SOURCE_TYPE_UPLOAD = "upload"
DEFAULT_SCAN_INTERVAL = timedelta(hours=12)

# Supported waste types as defined by Limburg.net CSV export.
WASTE_TYPES = {
    "Huisvuil",
    "Tuinafval",
    "Keukenafval",
    "Textiel",
    "PMD",
    "Papier & Karton",
}
