from fastapi import FastAPI, status
from app.routers import image

app = FastAPI()
app.include_router(image.router)

@app.get("/")
async def root():
    return {"message": "gik_backend is running"}

@app.get("/v1/gik/health", status_code=status.HTTP_200_OK)
async def health():
    return {"message": "OK"}
