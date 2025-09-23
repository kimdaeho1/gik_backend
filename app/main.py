from fastapi import FastAPI, status, HTTPException
from app.routers import image
from app.routers import user, community, token, credit, payment
from app.db.db_connection import db
import os
import boto3
from botocore.exceptions import ClientError
from app.utils.logging_config import setup_logging
from app.utils.logging_config import get_logger

setup_logging()
logger = get_logger(__name__)


app = FastAPI()
app.include_router(credit.router)
app.include_router(payment.router)
app.include_router(image.router)
app.include_router(user.router)
app.include_router(community.router)
app.include_router(token.router)


def get_env_variable(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise EnvironmentError(f"Required environment variable {var_name} is not set.")
    return value


# 환경 변수 확인 및 설정
try:
    DB_HOST = get_env_variable("DB_HOST")
    DB_PORT = get_env_variable("DB_PORT")
    DB_USER = get_env_variable("DB_USER")
    DB_PASSWORD = get_env_variable("DB_PASSWORD")
    DB_NAME = get_env_variable("DB_NAME")
    JWT_SECRET_KEY = get_env_variable("JWT_SECRET_KEY")
    HASH_ALGORITHM = get_env_variable("HASH_ALGORITHM")
    S3_BUCKET = get_env_variable("S3_BUCKET")
    AWS_ACCESS_KEY_ID = get_env_variable("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = get_env_variable("AWS_SECRET_ACCESS_KEY")
    GOOGLE_API_KEY_PATH = get_env_variable("GOOGLE_API_KEY_PATH")
    GOOGLE_API_KEY_LOCAL_PATH = get_env_variable("GOOGLE_API_KEY_LOCAL_PATH")
except EnvironmentError as e:
    raise
except Exception as e:
    raise


try:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    with open(GOOGLE_API_KEY_LOCAL_PATH, "wb") as file:
        s3_client.download_fileobj(S3_BUCKET, GOOGLE_API_KEY_PATH, file)
except ClientError as e:
    raise HTTPException(status_code=404, detail=f"File not found in S3: {e}")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error downloading file: {e}")


@app.get("/")
async def root():
    return {"message": "gik_backend is running"}


@app.get("/v1/gik/health", status_code=status.HTTP_200_OK)
async def health():
    return {"message": "OK"}


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up and connecting to the database.")
    await db.connect()
    logger.info("Connected to the database.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down and disconnecting from the database.")
    await db.close()
    logger.info("Disconnected from the database.")
