from fastapi import FastAPI, status
from app.routers import image
from app.routers import user
from app.db.db_connection import db
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.include_router(image.router)
app.include_router(user.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

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
