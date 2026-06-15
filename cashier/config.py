import os
import uuid

# API base URL — override via env var or config file
# In production: store server LAN address. In dev: cloud or localhost.
API_BASE_URL = os.environ.get("GRILTEK_API_URL", "http://localhost:8000/api/v1")
LOCATION_ID = os.environ.get("GRILTEK_LOCATION_ID", "")
DEVICE_ID = os.environ.get("GRILTEK_DEVICE_ID", str(uuid.uuid4()))
TENANT_ID = os.environ.get("GRILTEK_TENANT_ID", "")

# PIN lockout
MAX_PIN_ATTEMPTS = 5
PIN_LOCKOUT_SECONDS = 60

# Receipt
RECEIPT_WIDTH_CHARS = 42
