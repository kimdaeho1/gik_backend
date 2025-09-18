# 베이스 이미지를 설정합니다. Python 3.11 slim 버전을 사용합니다.
FROM python:3.11-slim

# 작업 디렉토리를 설정합니다.
WORKDIR /app

RUN mkdir -p /tmp

# MySQL 클라이언트를 설치하기 위한 패키지 업데이트 및 설치
RUN apt-get update && apt-get install -y default-mysql-client

# 호스트의 현재 디렉토리에 있는 모든 파일을 이미지의 /app 디렉토리로 복사합니다.
COPY . /app

# Python 패키지 설치를 위해 requirements.txt 파일을 복사합니다.
COPY requirements.txt .

# 필요한 Python 패키지를 설치합니다.
RUN pip install --no-cache-dir -r requirements.txt

# 환경 변수 설정
ARG DB_HOST
ARG DB_PORT
ARG DB_USER
ARG DB_PASSWORD
ARG DB_NAME
ARG JWT_SECRET_KEY
ARG HASH_ALGORITHM
ARG AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ARG AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ARG S3_BUCKET=${S3_BUCKET}
ARG GOOGLE_API_KEY_PATH=${GOOGLE_API_KEY_PATH}
ARG GOOGLE_API_KEY_LOCAL_PATH=${GOOGLE_API_KEY_LOCAL_PATH}
ARG IOS_BUNDLE_ID=${IOS_BUNDLE_ID}
ARG IOS_ISSUER_ID=${IOS_ISSUER_ID}
ARG IOS_KEY_ID=${IOS_KEY_ID}
ARG IOS_API_PRIVATE_KEY=${IOS_API_PRIVATE_KEY}

# 런타임에 사용할 수 있도록 환경 변수를 설정
ENV DB_HOST=${DB_HOST}
ENV DB_PORT=${DB_PORT}
ENV DB_USER=${DB_USER}
ENV DB_PASSWORD=${DB_PASSWORD}
ENV DB_NAME=${DB_NAME}
ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENV HASH_ALGORITHM=${HASH_ALGORITHM}
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV S3_BUCKET=${S3_BUCKET}
ENV GOOGLE_API_KEY_PATH=${GOOGLE_API_KEY_PATH}
ENV GOOGLE_API_KEY_LOCAL_PATH=${GOOGLE_API_KEY_LOCAL_PATH}
ENV IOS_BUNDLE_ID=${IOS_BUNDLE_ID}
ENV IOS_ISSUER_ID=${IOS_ISSUER_ID}
ENV IOS_KEY_ID=${IOS_KEY_ID}
ENV IOS_API_PRIVATE_KEY=${IOS_API_PRIVATE_KEY}

# 컨테이너 내부에서 env.config 파일을 생성합니다.
RUN mkdir -p /app/utils && \
    echo "[ENV]" > /app/utils/env.config && \
    echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}" >> /app/utils/env.config && \
    echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}" >> /app/utils/env.config && \
    echo "S3_BUCKET=${S3_BUCKET}" >> /app/utils/env.config

# 컨테이너 내부에서 애플리케이션을 실행하는 명령어를 설정합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
