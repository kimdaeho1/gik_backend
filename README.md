# gik_backend

긱(gik) 서비스의 백엔드 API 서버. 유저 매칭·커뮤니티·피드·시크릿 콘텐츠 결제·기프티콘·비즈 매장 운영을 단일 백엔드에서 처리한다.

FastAPI 기반 비동기 서버로, AWS ECS(Fargate가 아닌 EC2 bridge 네트워크) 위에서 운영되며 GitHub Actions로 ECR 빌드·ECS 배포가 자동화되어 있다.

---

## 기술 스택

| 영역 | 사용 기술 |
| --- | --- |
| Language | Python 3.11 |
| Web framework | FastAPI 0.115 + Uvicorn |
| DB | MySQL (aiomysql 비동기 풀, minsize=5 / maxsize=30, autocommit) |
| ORM/쿼리 | Raw SQL + SQLAlchemy 2.0 (혼용) |
| DI | dependency-injector |
| Auth | python-jose JWT (HS256), bcrypt |
| Storage | AWS S3 (boto3) + Pillow (썸네일) |
| Push | Firebase Admin SDK (FCM) |
| Payments | Google Play `androidpublisher` v3 / Apple App Store Server API (ES256 JWS) |
| 외부 API | Giftishow Biz API (기프티콘 발송), httpx 비동기 |
| Container | Docker (python:3.11-slim) |
| Registry / Runtime | AWS ECR + ECS (ap-northeast-2) |
| CI/CD | GitHub Actions |
| 로깅 | RotatingFileHandler (10MB × 5) + CloudWatch awslogs |

---

## 디렉토리 구조

```
.
├── Dockerfile                  # python:3.11-slim 베이스, mysql-client 포함
├── requirements.txt
├── .github/workflows/
│   ├── build.yml               # main 푸시 → backend-prod 이미지 ECR push
│   ├── deploy.yml              # workflow_dispatch → prod ECS task definition 등록·배포
│   ├── dev-build.yml           # develop 푸시 → backend-dev 이미지 ECR push
│   └── dev-deploy.yml          # workflow_dispatch → dev ECS task definition 등록·배포
└── app/
    ├── main.py                 # FastAPI 앱 / DI 컨테이너 wiring / startup·shutdown 훅
    ├── core/
    │   └── container.py        # dependency-injector Container (Service·Repository 의존성 그래프)
    ├── db/                     # Pydantic 요청 스키마 + DB 모듈
    │   ├── db_connection.py    # aiomysql 풀, get_connection() 컨텍스트 매니저
    │   └── {biz, chat, community, credit, feed, feed_comment, gift,
    │         image, payment, user}.py
    ├── repository/             # 데이터 접근 계층 (점진적 도입 중)
    │   └── {biz, community, feed, feed_comment, gift, user}_repository.py
    ├── routers/                # FastAPI 라우터 (11개 도메인)
    │   └── {biz, chat, community, credit, feed, feed_comment, gift,
    │         image, payment, token, user}.py
    ├── services/               # 비즈니스 로직
    │   └── {biz, community, credit, feed, feed_comment, gift, image,
    │         payment, push, token, user}_service.py
    └── utils/
        ├── config.py           # JWT·iOS 키 등 환경변수 바인딩
        ├── token.py            # JWT 생성·검증·JWTBearer (user_id / biz_id 양쪽 지원)
        ├── security.py         # bcrypt 해시·검증
        ├── s3_upload.py        # S3 업로드 + 파일명 생성 + 다중 업로드 헬퍼
        ├── firebase_init.py    # Firebase Admin lazy init (env에서 service account 조립)
        ├── logging_config.py   # 로깅 dictConfig
        └── utils.py            # KST 시간 변환 헬퍼
```

### 아키텍처 노트

- **계층 분리**: Router → Service → Repository → DB. Repository 패턴은 user / feed / feed_comment / community / biz / gift에 도입 완료. image / credit / payment / token은 Service에서 SQL을 직접 다루는 과도기 상태(Container 주석 참고).
- **DI**: `app/core/container.py`의 `Container`가 Service·Repository를 `providers.Factory`로 정의. `main.py`에서 `container.wire(modules=[...])`로 라우터에 주입.
- **DB 연결**: `app/main.py`의 startup 이벤트에서 `db.connect()`로 풀 생성, shutdown에서 `db.close()`. 라우터/서비스는 `Database.get_connection()` 비동기 컨텍스트 매니저로 커넥션을 빌려 쓴다.
- **인증**: `JWTBearer(auto_error=False)`로 라우터 의존성 주입. payload에 `user_id` 또는 `biz_id` 둘 중 하나가 있어야 통과 → 일반 유저용/비즈 계정용 토큰을 같은 검증 로직으로 처리.
- **시간대**: 서비스 전체 KST(Asia/Seoul) 기준. DB·푸시·결제 시간은 `app/utils/utils.py:to_datetime`을 통과시켜 timezone-aware로 통일.

---

## 도메인별 기능 요약

라우터 prefix는 모두 `/v1/gik-backend` (헬스 체크는 `/v1/gik`).

### User (`/user`, `/my-profile`, `/users/...`, `/secret/...`, 외)
- 회원가입(인증/비인증 분리), 본인인증, 닉네임 중복 확인, 탈퇴
- 프로필 항목별 PATCH: 닉네임 / 해시태그 / 기본정보(나이·키·몸무게·국가) / FCM / 희망 관계 / 포지션 / 소통 스타일 / 자기소개 / BDSM 타입 / 알람 11종 / 프로필 이미지
- 위치 기반 헬스체크(위경도) → 근처 유저 정렬
- 차단·신고·즐겨찾기·팔로우·언팔로우·찔러보기
- **시크릿 앨범**: 요청 → 상대방 푸시 → 수락/거절/취소/허용 취소 → 열람권 부여, 결제 기록 별도 추적
- **크레딧(고래 코인)**: 광고 리워드 지급, 프로필 조회·시크릿 열람 시 차감, 환전(coin↔dolphin), 히스토리(all/use/earn)
- **비즈 리뷰**: 작성·수정·삭제·차단·신고, 비즈 사장에게 새 리뷰 푸시
- **비즈 쿠폰**: 사용자 쿠폰 사용 처리

### Biz (`/biz/...`)
- 비즈 계정 로그인 → `biz_id` 페이로드 JWT 발급(별도 access/refresh)
- 매장 정보·이미지 관리, 매장 리스트·상세 조회
- 쿠폰 CRUD, 받은 리뷰에 답글

### Community (`/community/...`)
- 게시글 CRUD (multipart 이미지 첨부)
- 카테고리: `talk`, `meet`, `info`, `story`, `event`
- 좋아요·댓글·댓글 좋아요·차단·신고·검색
- 토큰 기반 좋아요/댓글 시 게시글 작성자에게 푸시 자동 전송

### Feed (`/feed/...`, `/feed/comment/...`)
- 피드 등록/수정/삭제 (텍스트 + 이미지 multipart)
- **시크릿 피드**: `secretStatus=true` + `price` 설정 → 다른 유저는 코인 차감 후 열람
- 리스트: 전체(랜덤 옵션) / 유저별 / 내 피드 / 시크릿 전용 / 내가 구매한 / 즐겨찾기
- 좋아요(시크릿 여부에 따라 푸시 타입 분기), 댓글 CRUD·차단·신고
- 시크릿 피드 구매자 리스트 → 블라인드 프로필 추가 결제로 신원 열람

### Chat (`/chat/send-push`)
- 1:1·그룹 채팅 메시지 발생 시 FCM 푸시. 채팅 스토리지 자체는 별도(이 서버는 알림 게이트웨이 역할).

### Image (`/community/images`, `/images`, `/chat/images`, `/group-profile/images`, `/secret/images`)
- 용도별 S3 prefix 분리 (`community/{boardId}/`, `{label}/{userId}/`, `group_chat/{chatId}/...` 등)
- 게시판 이미지 업로드 시 첫 장은 Pillow로 200×200 썸네일 자동 생성·별도 업로드
- 시크릿 앨범 업로드 / 인덱스 기반 부분 수정

### Credit (`/credit`, `/credit-history/test`)
- 토큰의 user_id로 잔액·내역 조회 (CreditManager 직접 사용)

### Payment (`/purchase/verify-android`, `/purchase/verify-ios`)
- **Android**: Google Play `androidpublisher` v3로 구매 토큰 검증, 가격·통화·주문ID·구매시각(KST) 추출 후 영수증 저장. `purchaseState=0` 구매 처리 / `=1` 환불 처리.
- **iOS**: App Store Server API(`storekit` / `storekit-sandbox`)에 ES256 JWT로 호출 → `signedTransactionInfo` JWS를 x5c 인증서로 검증·디코딩 → Receipt 저장.
- 코인 패키지 매핑(`gik_coin_10/30/55/120/250/700/1500`), 120/250 프로모션 시 iOS는 2배 지급 분기.

### Token (`/token/refresh`, `/token/{user_id}`, `/token/logout`)
- 리프레시 토큰 회전 발급 (1일 access / 30일 refresh)
- 신규 토큰 발급 시 활성 유저 검증
- 로그아웃 시 DB에서 토큰 invalidate

### Gift (`/gift/...`)
- Giftishow Biz API 프록시: 카테고리/브랜드/상품 리스트, 상품 상세, 구매(코인 차감 + 외부 발송), 발송 후 취소
- 비즈머니 잔액 조회

---

## 환경 변수

ECS task definition (`*-deploy.yml`)에 정의된 시크릿이 그대로 컨테이너 환경변수로 주입된다.

| 카테고리 | 변수 |
| --- | --- |
| DB | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |
| JWT | `JWT_SECRET_KEY`, `HASH_ALGORITHM` |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`, `CLOUDFRONT_URL` |
| Google API | `GOOGLE_API_KEY_PATH` (S3 키), `GOOGLE_API_KEY_LOCAL_PATH` (컨테이너 내부 다운로드 경로) |
| Firebase | `FIREBASE_ADMIN_PROJECT_ID`, `FIREBASE_ADMIN_PRIVATE_KEY`, `FIREBASE_ADMIN_PRIVATE_KEY_ID`, `FIREBASE_ADMIN_CLIENT_EMAIL`, `FIREBASE_ADMIN_CLIENT_ID`, `FIREBASE_ADMIN_AUTH_PROVIDER_X509_CERT_URL`, `FIREBASE_ADMIN_CLIENT_X509_CERT_URL` |
| iOS IAP | `IOS_BUNDLE_ID`, `IOS_ISSUER_ID`, `IOS_KEY_ID`, `IOS_API_PRIVATE_KEY` (Base64) |
| Giftishow | `CUSTOM_AUTH_CODE`, `CUSTOM_AUTH_TOKEN` |
| 기타 | `BANNER_ID`, `CARD_ID` |

기동 시 `app/main.py`에서 필수 환경변수를 검사하고, 누락 시 `EnvironmentError`로 기동을 중단한다. 또한 S3에 저장된 Google 서비스 계정 키를 `GOOGLE_API_KEY_LOCAL_PATH`에 다운로드한 뒤 androidpublisher 클라이언트가 이를 사용한다.

---

## 로컬 실행

```bash
# 1) 의존성
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) 환경변수 (.env 또는 셸 export)
export DB_HOST=... DB_PORT=3306 DB_USER=... DB_PASSWORD=... DB_NAME=...
export JWT_SECRET_KEY=... HASH_ALGORITHM=HS256
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... S3_BUCKET=...
# (이하 위 표 참고)

# 3) 기동
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t gik_backend .
docker run --rm -p 80:80 \
  -e DB_HOST=... -e DB_PORT=3306 -e DB_USER=... -e DB_PASSWORD=... -e DB_NAME=... \
  -e JWT_SECRET_KEY=... -e HASH_ALGORITHM=HS256 \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... -e S3_BUCKET=... \
  gik_backend
```

기본 포트는 80. 컨테이너 내부에서 `uvicorn app.main:app --host 0.0.0.0 --port 80`으로 실행된다.

### 헬스 체크

```bash
curl http://localhost:8000/                  # {"message":"gik_backend is running"}
curl http://localhost:8000/v1/gik/health     # {"message":"OK"}
```

### API 문서

- Swagger UI: `/docs`
- ReDoc: `/redoc`

---

## 배포 (CI/CD)

### 브랜치 → 환경 매핑

| 브랜치 | 빌드 워크플로 | 이미지 | 배포 워크플로 |
| --- | --- | --- | --- |
| `main` | `build.yml` (push) | `gik/backend-prod:latest` | `deploy.yml` (수동) |
| `develop` | `dev-build.yml` (push) | `gik/backend-dev:latest` | `dev-deploy.yml` (수동) |

### 배포 흐름

1. 브랜치에 push → GitHub Actions가 Docker 이미지를 빌드하고 ECR에 push.
2. Actions 탭에서 **Deploy to ECS** (또는 `(DEV) Deploy to ECS`)를 수동으로 실행.
3. 워크플로가 task definition JSON을 그 자리에서 생성 → `aws ecs register-task-definition`.
4. `aws ecs update-service ... --force-new-deployment`로 서비스 갱신.
5. 동일 family의 이전 ACTIVE task definition들을 deregister하여 누적 방지.

ECS 컨테이너 사양:
- prod: cpu 512 / memory 512 / memoryReservation 256, networkMode bridge
- dev: cpu 128 / memory 256 / memoryReservation 64
- platform: X86_64 / Linux
- 로그: `/ecs/{ECS_SERVICE}` CloudWatch group, prefix `ecs`

### 필요한 GitHub Secrets

`AWS_ACCESS_KEY`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `AWS_ACCOUNT_ID`, `ECS_CLUSTER`, `ECS_SERVICE`, `ECS_SERVICE_TASK_DEFINITION`, 그리고 위 [환경 변수](#환경-변수) 표의 모든 값.

---

## 인증 모델

- **일반 유저**: `user_id`를 페이로드에 담은 JWT. access 1일 / refresh 30일.
- **비즈 계정**: `biz_id`를 페이로드에 담은 JWT. 동일한 `JWTBearer`가 두 종류 토큰을 동시에 수용.
- 라우터에서는 `Depends(JWTBearer(auto_error=False))`로 토큰을 받고, `get_user_id_from_token` / `get_biz_id_from_token` 헬퍼로 식별자만 꺼내 쓴다.

---

## 주요 외부 의존성

- **AWS S3**: 모든 미디어(프로필·시크릿·게시판·피드·채팅·그룹채팅·비즈 매장·리뷰 이미지) 저장.
- **Firebase Cloud Messaging**: 좋아요·댓글·팔로우·시크릿 앨범 요청·리뷰·찔러보기·채팅 등 모든 푸시.
- **Google Play / App Store**: 인앱 결제 영수증 검증 및 환불 처리.
- **Giftishow Biz API**: 기프티콘 카탈로그·발송·취소·비즈머니.

---

## 라이선스

내부 프로젝트 (별도 라이선스 명시 전).
