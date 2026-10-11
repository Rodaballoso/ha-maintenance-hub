"""Constants for Maintenance Hub."""

DOMAIN = "maintenance_hub"

# Asset categories
CATEGORY_EQUIPMENT = "equipment"
CATEGORY_IT = "it"
CATEGORY_VEHICLE = "vehicle"

# Config subentry type: one per asset
SUBENTRY_ASSET = "asset"

# Trigger keys used in templates and in asset data
TRIGGER_DAYS = "days"
TRIGGER_MONTHS = "months"
TRIGGER_KM = "km"
TRIGGER_HOURS = "hours"  # reserved: not evaluated yet
SUPPORTED_TRIGGERS = (TRIGGER_DAYS, TRIGGER_MONTHS, TRIGGER_KM)

# Storage (history of maintenance records only; assets live in subentries)
STORAGE_VERSION = 1  # same as 0.2.x, so existing data is read directly
STORAGE_KEY = f"{DOMAIN}.data"

# Services
SERVICE_ADD_ASSET = "add_asset"
SERVICE_REMOVE_ASSET = "remove_asset"
SERVICE_MARK_DONE = "mark_done"
SERVICE_SET_ODOMETER = "set_odometer"

# Dispatcher signal: ask all entities to recompute their state
SIGNAL_UPDATED = f"{DOMAIN}_updated"
