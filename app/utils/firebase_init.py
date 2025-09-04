import os
import firebase_admin
from firebase_admin import credentials


def init_firebase_admin():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account = {
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_ADMIN_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_ADMIN_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_ADMIN_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_ADMIN_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_ADMIN_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": os.getenv(
            "FIREBASE_ADMIN_AUTH_PROVIDER_X509_CERT_URL"
        ),
        "client_x509_cert_url": os.getenv("FIREBASE_ADMIN_CLIENT_X509_CERT_URL"),
        "universe_domain": "googleapis.com",
    }

    cred = credentials.Certificate(service_account)
    return firebase_admin.initialize_app(cred)
