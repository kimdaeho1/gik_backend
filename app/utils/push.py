# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import firebase_admin
# from firebase_admin import credentials, messaging


# cred = credentials.Certificate("/path/to/your/firebase-service-account.json")
# firebase_admin.initialize_app(cred)

# app = FastAPI()


# class PushNotificationRequest(BaseModel):
#     title: str
#     body: str
#     token: str


# @app.post("/v1/gik-backend/notification", status_code=200)
# async def send_notification(request: PushNotificationRequest):
#     try:

#         message = messaging.Message(
#             notification=messaging.Notification(
#                 title=request.title,
#                 body=request.body,
#             ),
#             token=request.token,
#         )

#         response = messaging.send(message)
#         return {"message": "Notification sent successfully", "response": response}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
