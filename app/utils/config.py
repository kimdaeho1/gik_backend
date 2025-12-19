import os
import base64

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("HASH_ALGORITHM")
IOS_BUNDLE_ID = os.getenv("IOS_BUNDLE_ID")
IOS_ISSUER_ID = os.getenv("IOS_ISSUER_ID")
IOS_KEY_ID = os.getenv("IOS_KEY_ID")
IOS_API_PRIVATE_KEY = base64.b64decode(os.getenv("IOS_API_PRIVATE_KEY")).decode("UTF-8")

CUSTOM_AUTH_CODE = os.getenv("CUSTOM_AUTH_CODE")
CUSTOM_AUTH_TOKEN = os.getenv("CUSTOM_AUTH_TOKEN")
BANNER_ID = os.getenv("BANNER_ID")
CARD_ID = os.getenv("CARD_ID")
