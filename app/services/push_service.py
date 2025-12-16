from typing import Dict, List, Optional
from datetime import timedelta
import time, json
from fastapi import HTTPException, BackgroundTasks
from firebase_admin import messaging
from app.utils.firebase_init import init_firebase_admin
from app.db.db_connection import db
from app.repository.user_repository import UserRepository
from app.utils.token import get_user_id_from_token
import uuid


class PushService:
    def __init__(self, db, user_repository: UserRepository):
        self.db = db
        self.user_repository = user_repository
        init_firebase_admin()

    def _build_message(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]],
        image_url: Optional[str],
        ttl_seconds: Optional[int],
        collapse_key: Optional[str],
        sound: Optional[str],
        badge: Optional[int],
        android_priority: str,
        mutable_content: bool,
        content_available: bool,
    ) -> messaging.Message:

        # collapse_key = 메세지 그룹화 키, 동일한 키를 가진 메세지는 하나로 묶어서 처리.
        # priority = 메세지 우선순위, high로 설정하면 즉시 전송 시도.
        # ttl = 메세지 유효기간, 3600초 = 1시간
        # restricted_package_name = 메세지를 수신할 앱의 패키지 이름
        # notification = 메세지 알림 설정
        # fcm_options = FCM 옵션 설정
        # direct_boot_ok = 디바이스가 Direct Boot 모드(암호 해제 전)에서도 메세지 수신 가능
        android_cfg = messaging.AndroidConfig(
            priority=android_priority,
            ttl=timedelta(seconds=ttl_seconds) if ttl_seconds else None,
            collapse_key=collapse_key,
            # title, body : 지정하면 설정한 본문을 덮어씀
            # icon : 알림 아이콘
            # color: 아이콘 색상
            # sound: 알림 도착시 재생할 sound, sound 리소스 파일명
            # tag: 알림 태그, 기존 알림을 교체하기 위한 식별자. 같은 태그면 기존 알림을 덮어쓰고, 같지 않으면 새로운 알림이 생성됨
            # click_action: 알림 클릭 시 동작
            # body_loc_key: 다국어 지원을 위한 본문 키
            # title_loc_key: 다국어 지원을 위한 제목 키
            # channal_id: 안드로이드 8.0 이상에서 알림 채널 ID
            # sticky: 알림 패널에서 클릭하면 자동으로 사라짐 , False나 미지정이면, 사용자가 알림에서 클릭하면 사라짐.
            # local_only: 알림이 현재 기기에만 해당되는지 여부, True로 설정하면 다른 기기에는 알림이 표시되지 않음
            # prority: 알림 우선순위(default, min, low, high, max, normanl 중 하나)
            # event_timestamp: 알림에 표시할 이벤트 타임스탬프
            # vibrate_timings_millis: 진동 패턴[0, 500, 200, 500]: 0ms 대기, 500ms 진동, 200ms 대기, 500ms 진동
            # default_vibrate_timings: 기본 진동 패턴 사용 여부
            # default_sound: 기본 알림음 사용 여부
            # visibility: 알림 가시성. (private/public/secret)
            # notification_count: 알림을 나타내는 항목 개수, 메세지 여러개를 하나의 알림으로 표시할 때.
            notification=messaging.AndroidNotification(
                sound=sound,
                image=image_url,
                sticky=False,
                priority="high",
                local_only=False,
                default_sound=True,
                default_vibrate_timings=True,
            ),
            direct_boot_ok=True,
        )

        # apns헤더들
        # apns-priority: 10(즉시 전송), 5(백그라운드 전송)
        # apns-expiration: 만료 시각(epoch seconds)
        # apns-topic: 앱의 번들 ID
        # apns-collapse-id: 동일한 ID를 가진 메세지는 하나로 묶어서 처리
        # apns-push-type: alert, background, voip, complication, fileprovider, mdm 중 하나
        apns_headers = {
            "apns-priority": "10",
            "apns-push-type": "alert",
            "apns-expiration": str(int(time.time()) + int(ttl_seconds)),
        }

        # alert: 문자열 또는 messaging.ApsAlert 인스턴스
        # badge: 메세지와 함게 표시할 배지 숫자
        # sound: 알림 사운드
        # content_available: 백그라운드 알림을 설정할지 여부
        # category: 메세지 유형을 나타내는 문자열 식별자
        # thread_id: 메시지를 그룹화하기 위한 앱 전용 문자열 식별자
        # mutable_content: 클라이언트에서 앱 확장을 사용해 알림을 수정할 수 있도록 지원할 지 여부를 나타내는 불리언 값
        aps = messaging.Aps(
            sound=sound or "default",
            badge=badge,
            content_available=content_available,
            mutable_content=mutable_content,
        )

        # headers: 헤더, 딕셔너리 형태의 apnps-priority, apns-expiration, apns-topic등. apns_priority 10 -> 즉시 전송
        # payload: payload APNSPayload객체. 커스텀 데이터들을 담음
        # fcm_options
        # live_activity_token IOS 16.1 이상에서 라이브 액티비티 지원
        apns_cfg = messaging.APNSConfig(
            headers=apns_headers,
            payload=messaging.APNSPayload(aps=aps),
        )

        # message 객체 생성
        # data
        # notification
        # android
        # webpush
        # apns
        # fcm_options
        # token
        # topic
        # condition
        return messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=title, body=body, image=image_url
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            android=android_cfg,
            apns=apns_cfg,
        )

    async def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        user_no: int,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        ttl_seconds: Optional[int] = 3600,
        collapse_key: Optional[str] = None,
        sound: Optional[str] = "default",
        badge: Optional[int] = None,
        android_priority: str = "high",
        mutable_content: bool = False,
        content_available: bool = False,
        is_chat: bool = False,
    ) -> Dict:
        push_id = (data or {}).get("pushId")

        payload_obj = {
            "pushId": push_id,
            "title": title,
            "body": body,
            "imageUrl": image_url,
            "data": data or {},
            "ttlSeconds": ttl_seconds,
            "collapseKey": collapse_key,
            "sound": sound,
            "badge": badge,
            "androidPriority": android_priority,
            "mutableContent": mutable_content,
            "contentAvailable": content_available,
        }
        # 사용자 푸시 동의 여부 확인
        if not await self.check_user_push_alarm(user_no):
            await self._insert_push_user_log(
                user_no=user_no,
                push_id=push_id,
                push_type=data.get("type"),
                token=token,
                status="NO_AGREE",
                payload_obj=payload_obj,
                delivery_state="FAILED",
            )
            return

        # 토큰이 비어있으면 실패 처리. token empty.
        if not token:
            push_id = (data or {}).get("pushId")
            await self._insert_push_user_log(
                user_no=user_no,
                push_id=push_id,
                push_type=data.get("type"),
                token="",
                status="FAIL",
                payload_obj=payload_obj,
                error_code="404",
                error_message="token empty",
                delivery_state="FAILED",
            )
            return

        msg = self._build_message(
            token=token,
            title=title,
            body=body,
            data=data,
            image_url=image_url,
            ttl_seconds=ttl_seconds,
            collapse_key=collapse_key,
            sound=sound,
            badge=badge,
            android_priority=android_priority,
            mutable_content=mutable_content,
            content_available=content_available,
        )

        try:
            messaging.send(msg, dry_run=False)
            try:
                if is_chat is True:
                    return
                await self._insert_push_user_log(
                    user_no=user_no,
                    push_id=push_id,
                    push_type=data.get("type"),
                    token=token,
                    status="SUCCESS",
                    payload_obj=payload_obj,
                    delivery_state="DELIVERED",
                )
            except Exception:
                raise HTTPException(f"push log insert fail: {msg}")

        except Exception as e:
            try:
                await self._insert_push_user_log(
                    user_no=user_no,
                    push_id=push_id,
                    push_type=data.get("type"),
                    token=token,
                    status="FAIL",
                    payload_obj=payload_obj,
                    error_code=getattr(e, "code", None),
                    error_message=str(e),
                    delivery_state="FAILED",
                )
            except Exception:
                raise HTTPException(f"push log insert fail: {msg}")

    async def _insert_push_user_log(
        self,
        *,
        user_no: Optional[int],
        push_id: str,
        push_type: str,
        token: str,
        status: str,
        payload_obj: Dict,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        delivery_state: str = "NONE",
    ) -> None:
        try:
            async with db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO push_user_log
                            (user_no, push_id, push_type, token, status, payload, error_code, error_message, delivery_state)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_no,
                            push_id,
                            push_type,
                            token,
                            status,
                            json.dumps(payload_obj, ensure_ascii=False),
                            error_code,
                            error_message,
                            delivery_state,
                        ),
                    )
                await conn.commit()
        except Exception as e:
            print(f"푸시 로그 삽입 실패: {e}")
            pass

    async def check_user_push_alarm(self, user_no: int) -> bool:
        async with db.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT profile_alarm_agree FROM users WHERE user_no = %s",
                    (user_no,),
                )
                result = await cur.fetchone()
                if result is not None:
                    return result[0]

                await cur.execute(
                    "SELECT profile_alarm_agree FROM biz_account WHERE user_no = %s",
                    (user_no,),
                )
                result = await cur.fetchone()
                if result is not None:
                    return result[0]

                return False

    async def push_task(
        self,
        token: str,
        title: str,
        body: str,
        data: Dict[str, str],
        ttl_seconds: int,
        collapse_key: str,
        android_priority: str,
        mutable_content: bool,
        content_available: bool,
        user_no: int,
        is_chat: bool,
    ):
        await self.send_to_token(
            token=token,
            title=title,
            body=body,
            data=data,
            user_no=user_no,
            ttl_seconds=ttl_seconds,
            collapse_key=collapse_key,
            android_priority=android_priority,
            mutable_content=mutable_content,
            content_available=content_available,
            is_chat=is_chat,
        )

    async def send_push_to_user(
        self,
        background_tasks: BackgroundTasks,
        user_id: str,
        target_user_id: str,
        title_content: str,
        body_content: str,
        data: str,
        collapse_key: str,
        activity_type: str,
        is_chat: Optional[bool] = False,
    ):
        # 본인이 본인껄 보거나, 게시글에 좋아요를 누르는 경우는 보내지 않는다
        if user_id == target_user_id:
            return

        # 차단되었는지 확인
        # user_id = 푸시 받는사람
        # target_user_id = 푸시 보내는사람
        is_blocked = await self.user_repository.check_user_block(
            user_id=target_user_id, target_user_id=user_id
        )

        if is_blocked:
            return

        # fcm 가져오기
        target_token = await self.user_repository.fetch_user_fcm(user_id)

        # 푸시를 전송할 상대의 user_no가져오기
        target_user_no = await self.user_repository.fetch_user_no(user_id)

        # 푸시를 전송할 상대의 user_no에서 user_id 가져오기
        target_user_no_id = await self.user_repository.fetch_user_id(target_user_no)

        # 푸시를 전송할 상대의 수신 동의 여부 가져오기
        target_push_agree = await self.user_repository.fetch_user_alarm_setting(
            target_user_no_id
        )
        if not target_push_agree.get(activity_type, False):
            print("사용자가 해당 푸시 수신에 동의하지 않았습니다.")
            return

        push_id = str(uuid.uuid4())
        background_tasks.add_task(
            self.push_task,
            target_token,
            title=title_content,
            body=body_content,
            data={**data, "pushId": push_id},
            ttl_seconds=3600,
            collapse_key=collapse_key,
            android_priority="high",
            mutable_content=True,
            content_available=True,
            user_no=target_user_no,
            is_chat=is_chat,
        )

    async def send_chat_push(
        self,
        token,
        chat_id: str,
        chat_type: str,
        chat_user_list: List[str],
        chat_message: str,
        chat_title: Optional[str],
        background_tasks: BackgroundTasks,
    ):

        user_id = await get_user_id_from_token(token)
        is_chat = True
        # 만약 유저 리스트 안에 내 아이디가 있을경우 제외
        if user_id in chat_user_list:
            chat_user_list.remove(user_id)

        if chat_type == "group":
            data = {"type": "group", "chatTitle": chat_title, "chatId": chat_id}
            collapse_key = f"group_chat_{chat_title}"
            activity_type = "group_chat"

            for target_user_id in chat_user_list:
                await self.send_push_to_user(
                    background_tasks=background_tasks,
                    user_id=target_user_id,
                    target_user_id=user_id,
                    title_content=chat_title,
                    body_content=chat_message,
                    data=data,
                    collapse_key=collapse_key,
                    activity_type=activity_type,
                    is_chat=True,
                )
        else:
            for target_user_id in chat_user_list:
                target_user_nickname = await self.user_repository.fetch_user_nickname(
                    user_id
                )
                data = {
                    "type": "personal",
                    "chatTitle": target_user_nickname,
                    "chatId": chat_id,
                }
                collapse_key = f"personal_chat_{target_user_id}"
                activity_type = "personal_chat"

                await self.send_push_to_user(
                    background_tasks=background_tasks,
                    user_id=target_user_id,
                    target_user_id=user_id,
                    title_content=target_user_nickname,
                    body_content=chat_message,
                    data=data,
                    collapse_key=collapse_key,
                    activity_type=activity_type,
                    is_chat=True,
                )
        return True
