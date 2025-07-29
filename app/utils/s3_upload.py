import os
import boto3
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

# s3에서 가져올 파일, 보안 정책이슈로 presigned url을 생성해서 업로드 
def generate_presigned_url(s3_key_with_filename: str, expiration: int = 300) -> str | None:
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': s3_key_with_filename
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"Presigned URL 생성 실패: {e}")
        return None
