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
TRIGGER_HOURS = "hours"  # reserved: not evaluated yet
SUPPORTED_TRIGGERS = (TRIGGER_DAYS, TRIGGER_MONTHS, TRIGGER_KM)

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"

# Services
SERVICE_ADD_ASSET = "add_asset"
SERVICE_REMOVE_ASSET = "remove_asset"
SERVICE_MARK_DONE = "mark_done"
SERVICE_SET_ODOMETER = "set_odometer"

# Dispatcher signals
SIGNAL_ASSET_ADDED = f"{DOMAIN}_asset_added"
SIGNAL_ASSET_REMOVED = f"{DOMAIN}_asset_removed"
SIGNAL_UPDATED = f"{DOMAIN}_updated"
