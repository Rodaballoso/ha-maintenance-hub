"""Constants for Maintenance Hub."""

DOMAIN = "maintenance_hub"

# Asset categories
CATEGORY_EQUIPMENT = "equipment"
CATEGORY_IT = "it"
CATEGORY_VEHICLE = "vehicle"
CATEGORIES = [CATEGORY_EQUIPMENT, CATEGORY_IT, CATEGORY_VEHICLE]

# Trigger keys used in templates
TRIGGER_DAYS = "days"
TRIGGER_MONTHS = "months"
TRIGGER_KM = "km"
TRIGGER_HOURS = "hours"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"

# Services
SERVICE_ADD_ASSET = "add_asset"
SERVICE_MARK_DONE = "mark_done"
SERVICE_SET_ODOMETER = "set_odometer"
