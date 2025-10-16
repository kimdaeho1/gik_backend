import os
import boto3
from datetime import datetime
from typing import List
from fastapi import UploadFile, HTTPException, status
from botocore.exceptions import ClientError

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
CLOUDFRONT_URL = os.getenv("CLOUDFRONT_URL")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def upload_file_to_s3(file_object, s3_key, filename):
    try:
        s3_client.upload_fileobj(
            file_object,
            S3_BUCKET,
            s3_key + filename,
        )
        return True
    except ClientError as e:
        print(e)
        return False


def generate_filename(filename: str) -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S%f")[:-3]
    extension = filename.split(".")[-1] or "jpg"
    return f"{timestamp}.{extension}"


def image_url_list(
    s3_key: str,
    images: List[UploadFile],
):
    """
    이미지를 S3에 업로드 하고 url리스트를 반환
    """
    image_url_list = []
    try:
        for idx, file in enumerate(images):
            str_filename = generate_filename(file.filename)
            if not upload_file_to_s3(file.file, s3_key, str_filename):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image {file.filename} to S3",
                )
            image_url_list.append(s3_key + str_filename)
        return image_url_list
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload images to S3 {str(e)}",
        )
