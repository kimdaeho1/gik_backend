from typing import List, Optional
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, status, Depends, File, UploadFile, Query, BackgroundTasks
from app.core.container import Container
from app.utils.token import get_user_id_from_token, JWTBearer
from app.db.feed import (
    CreateFeedRequest,
    UpdateFeedRequest,
    ReportFeedRequest,
)
from app.services.feed_service import FeedService
from app.services.push_service import PushService

oauth2_scheme = JWTBearer(auto_error=False)
router = APIRouter(prefix="/v1/gik-backend/feed", tags=["Feed"])


# 피드 수정/등록 API는 이미지 업로드가 포함되어 있기 때문에, 요청형식이 multipart/form-data가 된다.
# FastAPI에서는 JSON Body와 파일을 동시에 받을 수 없어서, 텍스트 필드는 Form으로, 이미지는 File로 받는다.
# 따라서, CreateFeedRequest와 UpdateFeedRequest의 모델에 @classmethod를 정의하고 라우터에서 Depend로 받기.
# 피드 등록
@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_feed(
    create_feed_request: CreateFeedRequest = Depends(
        CreateFeedRequest.create_feed_request
    ),
    feedImages: Optional[List[UploadFile]] = File(default=[]),
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    유저 피드 생성
    - token: 사용자 인증 토큰
    - content: 피드 내용 (선택 사항)
    - status: 피드 공개 여부, true = 숨김, false = 숨기지 않음
    - secretStatus: 시크릿 피드 여부, true = 시크릿, false = 시크릿이 아님
    - feedImages: 업로드할 이미지 파일 리스트 (선택 사항)
    - price: 시크릿 피드 가격(선택 사항, 기본값 10)
    """
    result = await feed_service.create_feed(
        token=token,
        content=create_feed_request.content,
        status=create_feed_request.status,
        secret_status=create_feed_request.secretStatus,
        feed_images=feedImages,
        price=create_feed_request.price,
    )
    return {"success": True, "message": "피드가 성공적으로 게시되었습니다."}


# 피드 수정
@router.patch("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def update_feed(
    feed_id: str,
    update_feed_request: UpdateFeedRequest = Depends(
        UpdateFeedRequest.update_feed_request
    ),
    update_feed_images: Optional[List[UploadFile]] = File(default=[]),
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    유저 피드 업데이트
    - token: 사용자 인증 토큰
    - feed_id: 수정할 피드의 ID
    - content: 피드 내용 (선택 사항)
    - imageUrl: 수정하지 않을 이미지 URL 리스트 (선택 사항)
    - status: 피드 공개 여부
    - secretStatus: 피드 비밀 여부
    - update_feed_images: 새로 추가할 이미지 파일 리스트 (선택 사항)
    """
    result = await feed_service.update_feed(
        token=token,
        feed_id=feed_id,
        content=update_feed_request.content,
        image_urls=update_feed_request.imageUrl,
        status=update_feed_request.status,
        secret_status=update_feed_request.secretStatus,
        feed_images=update_feed_images,
        price=update_feed_request.price,
    )

    if result is False:
        return {
            "success": False,
            "message": "피드 수정에 실패했습니다. 권한이 없거나 시크릿 피드입니다.",
        }
    return {"success": True, "message": "피드가 성공적으로 수정되었습니다."}


# 피드 삭제
@router.delete("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def delete_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    유저 피드 삭제
    - token: 사용자 인증 토큰
    - feed_id: 삭제할 피드의 ID
    """
    result = await feed_service.delete_feed(token=token, feed_id=feed_id)
    return {"success": True, "message": "피드가 성공적으로 삭제되었습니다."}


# 내가 차단한사람의 피드와, 내가 차단한 피드는 둘다 보이지 않아야 한다.
# 피드 리스트 가져오기 - redis와 같은 캐싱을 사용해서 5개씩 가져오고, 로직 생각해보기.
@router.get("/list", status_code=status.HTTP_200_OK)
@inject
async def get_feed_list(
    page: int = Query(...),
    random: bool = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    전체 피드 리스트 가져오기
    - token: 사용자 인증 토큰
    - page: 페이지 번호 (1부터 시작)
    """
    result = await service.get_feed_list(
        token=token,
        page=page,
        random=random,
    )
    return {
        "success": True,
        "message": "피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }


@router.get("/list/{user_id}", status_code=status.HTTP_200_OK)
@inject
async def get_user_feed_list(
    user_id: str,
    page: int = Query(...),
    secretStatus: bool = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    특정 유저의 피드 리스트 가져오기
    - token: 사용자 인증 토큰
    - user_id: 피드 리스트를 가져올 대상 유저의 ID
    - page: 페이지 번호 (1부터 시작)
    """
    result = await service.get_user_feed_list(
        target_user_id=user_id,
        page=page,
        token=token,
        secret_status=secretStatus,
    )
    return {
        "success": True,
        "message": "유저 피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }


# 피드 조회하기
@router.get("/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def get_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    피드 상세 조회하기
    - token: 사용자 인증 토큰
    - feed_id: 조회할 피드의 ID
    """
    result = await feed_service.get_feed(token=token, feed_id=feed_id)
    return {
        "success": True,
        "message": "피드 조회에 성공했습니다.",
        "feed": result,
    }


# 피드 신고
@router.post("/report/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def report_feed(
    feed_id: str,
    report_feed_request: ReportFeedRequest,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    피드 신고하기
    - token: 사용자 인증 토큰
    - feed_id: 신고할 피드의 ID
    - reportedUserId: 신고당한 유저의 ID
    - reason: 신고 사유
    """
    await feed_service.report_feed(
        token=token,
        feed_id=feed_id,
        reported_user_id=report_feed_request.reportedUserId,
        reason=report_feed_request.reason,
    )
    return {"success": True, "message": "피드가 성공적으로 신고되었습니다."}


# 피드 차단
@router.post("/block/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def block_feed(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    피드 차단하기
    - token: 사용자 인증 토큰
    - feed_id: 차단할 피드의 ID
    """
    await feed_service.block_feed(
        token=token,
        feed_id=feed_id,
    )
    return {"success": True, "message": "피드가 성공적으로 차단되었습니다."}


# 피드 좋아요 / 좋아요 취소
@router.post("/like/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def like_feed(
    feed_id: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    """
    피드 좋아요 / 좋아요 취소
    - token: 사용자 인증 토큰
    - feed_id: 좋아요/좋아요 취소할 피드의 ID
    """
    result = await feed_service.like_feed(token=token, feed_id=feed_id)
    feed_user_id = await feed_service.get_feed_user_id(feed_id=feed_id)
    user_id = await get_user_id_from_token(token)
    if result == "like_feed":
        await push_service.send_push_to_user(
            background_tasks=background_tasks,
            user_id=feed_user_id,
            target_user_id=user_id,
            title_content="👍 좋아요를 받았어요!",
            body_content="내 피드에 누군가 좋아요를 눌렀어요. 지금 확인해 보세요!",
            data={"type": "feedLike", "feedId": feed_id},
            collapse_key=f"feed_like_{feed_id}",
            activity_type="feed_like",
        )
        return {"success": True, "message": "피드 좋아요가 성공적으로 처리되었습니다."}
    elif result == "unlike_feed":
        return {
            "success": True,
            "message": "피드 좋아요 취소가 성공적으로 처리되었습니다.",
        }


# 피드 좋아요 리스트 가져오기
@router.get("/like/user-list/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def get_feed_like_list(
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    피드 좋아요 리스트 가져오기
    - token: 사용자 인증 토큰
    - feed_id: 좋아요 리스트를 가져올 피드의 ID
    """
    result = await feed_service.get_feed_like_list(token=token, feed_id=feed_id)
    return {
        "success": True,
        "message": "피드 좋아요 리스트를 성공적으로 가져왔습니다.",
        "likeUsers": result,
    }


# 내 피드 리스트 가져오기
@router.get("/my-feed/list", status_code=status.HTTP_200_OK)
@inject
async def get_my_feed_list(
    page: int = Query(...),
    status: Optional[bool] = Query(...),
    secretStatus: Optional[bool] = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    내 피드 리스트 가져오기
    - token: 사용자 인증 토큰
    - page: 페이지 번호 (1부터 시작)
    - status: 피드 공개 여부, true = 숨김, false = 숨기지 않음
    - secretStatus: 시크릿 피드 여부, true = 시크릿, false = 시크릿이 아님
    """
    result = await service.get_my_feed_list(
        token=token, page=page, status=status, secret_status=secretStatus
    )
    return {
        "success": True,
        "message": "내 피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }


@router.get("/purchase/list", status_code=status.HTTP_200_OK)
@inject
async def get_purchase_feed_list(
    page: int = Query(...),
    token: str = Depends(oauth2_scheme),
    service: FeedService = Depends(Provide[Container.feed_service]),
):
    """
    구매한 피드 리스트 가져오기
    - token: 사용자 인증 토큰
    - page: 페이지 번호 (1부터 시작)
    """
    result = await service.get_purchase_feed_list(token=token, page=page)
    return {
        "success": True,
        "message": "구매한 피드 리스트를 성공적으로 가져왔습니다.",
        "feeds": result,
    }


# 해당 시크릿 피드 구매하기
@router.post("/purchase/{feed_id}", status_code=status.HTTP_200_OK)
@inject
async def purchase_secret_feed(
    background_tasks: BackgroundTasks,
    feed_id: str,
    token: str = Depends(oauth2_scheme),
    feed_service: FeedService = Depends(Provide[Container.feed_service]),
    push_service: PushService = Depends(Provide[Container.push_service]),
):
    """
    해당 유저의 시크릿 피드 구매하기
    - token: 사용자 인증 토큰
    - user_id: 시크릿 피드를 구매할 대상 유저의 ID
    """
    result = await feed_service.purchase_secret_feed(
        token=token,
        feed_id=feed_id,
    )

    feed_user_id = await feed_service.get_feed_user_id(feed_id=feed_id)
    user_id = await get_user_id_from_token(token)
    purchased_user_nickname = await feed_service.get_feed_user_nickname(user_id=user_id)
    await push_service.send_push_to_user(
        background_tasks=background_tasks,
        user_id=feed_user_id,
        target_user_id=user_id,
        title_content=f"{purchased_user_nickname}님이 내 시크릿 피드를 보고 갔어요. 👀",
        body_content="그사람의 시크릿 피드를 둘러보세요.",
        data={"type": "secret", "feedId": feed_id, "viewerId": user_id},
        collapse_key=f"secret_feed_{feed_id}",
        activity_type="secret",
    )
    return {
        "success": True,
        "message": "시크릿 피드 구매가 성공적으로 처리되었습니다.",
    }
