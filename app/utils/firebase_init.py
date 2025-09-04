import os, json, firebase_admin
from firebase_admin import credentials

def init_firebase_admin():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_str = os.getenv("FIREBASE_CREDENTIALS")
    if not cred_str:
        raise ValueError("FIREBASE_CREDENTIALS environment variable is not set")
    
    cred_info = json.loads(cred_str)
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)
