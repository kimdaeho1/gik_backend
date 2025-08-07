from fastapi import FastAPI, status
from app.routers import image
from app.routers import user, community, token
from app.db.db_connection import db


app = FastAPI()
app.include_router(image.router)
app.include_router(user.router)
app.include_router(community.router)
app.include_router(token.router)

@app.get("/")
async def root():
    return {"message": "gik_backend is running"}

@app.get("/v1/gik/health", status_code=status.HTTP_200_OK)
async def health():
    return {"message": "OK"}


@app.on_event("startup")
async def startup_event():
    await db.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await db.close()
