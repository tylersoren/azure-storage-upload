import os

STORAGE_URL = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
if not STORAGE_URL:
  raise ValueError("Need to define AZURE_STORAGE_ACCOUNT_URL")

CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
if not CONTAINER_NAME:
  raise ValueError("Need to define AZURE_STORAGE_CONTAINER_NAME")

TENANT_ID = os.getenv("AZURE_TENANT_ID")
if not TENANT_ID:
    raise ValueError("Need to define TENANT_ID environment variable")

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
if not CLIENT_ID:
    raise ValueError("Need to define CLIENT_ID environment variable")

CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
if not CLIENT_SECRET:
    raise ValueError("Need to define CLIENT_SECRET environment variable")

# AUTHORITY = "https://login.microsoftonline.com/common"  # For multi-tenant app
AUTHORITY = "https://login.microsoftonline.com/<azure ad tenant name>.onmicrosoft.com"

REDIRECT_PATH = "/getAToken"  # It will be used to form an absolute URL
    # And that absolute URL must match your app's redirect_uri set in AAD

# Map roles to directory
ROLES = dict(
  Admin = ["Finance","Shared","Marketing","Sandbox"],
  Finance = ["Finance","Shared"],
  Marketing = ["Marketing", "Shared"],
)

# Map directory display name to container path
PATHS = dict(
  # root = "",
  Finance = "finance/",
  Marketing  = "marketing/",
  Shared = "shared/",
  Sandbox = "sandbox/"
)

# You can find the proper permission names from this document
# https://docs.microsoft.com/en-us/graph/permissions-reference
SCOPE = ["User.Read "]

SESSION_TYPE = "filesystem"  # So token cache will be stored in server-side session

