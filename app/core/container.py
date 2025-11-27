from dependency_injector import containers, providers
from app.db.db_connection import Database

# from app.repository.user_repository import UserRepository
from app.services.user_service import UserService
from app.services.image_service import ImageService
from app.services.push_service import PushService
from app.services.community_service import CommunityService
from app.services.token_service import TokenService
from app.services.feed_service import FeedService
from app.services.feed_comment_service import FeedCommentService
from app.services.biz_service import BizService

from app.repository.feed_repository import FeedRepository
from app.repository.feed_comment_repository import FeedCommentRepository
from app.repository.user_repository import UserRepository
from app.repository.community_repository import CommunityRepository
from app.repository.biz_repository import BizRepository
from app.db.db_connection import db


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.routers.user",
            "app.routers.image",
            "app.routers.community",
            "app.routers.token",
            "app.routers.credit",
            "app.routers.payment",
            "app.routers.feed",
            "app.routers.feed_comment",
            "app.routers.chat",
            "app.routers.biz",
        ]
    )
    # main.py에서 생성한 db 객체를 그대로 쓰기.
    database = providers.Object(db)

    # 레포지토리 컨테이너
    feed_repository = providers.Factory(FeedRepository, db=database)
    feed_comment_repository = providers.Factory(FeedCommentRepository, db=database)
    user_repository = providers.Factory(UserRepository, db=database)
    community_repository = providers.Factory(CommunityRepository, db=database)
    biz_repository = providers.Factory(BizRepository, db=database)

    # 서비스 컨테이너
    image_service = providers.Factory(ImageService, db=database)
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        feed_repository=feed_repository,
        image_service=image_service,
    )
    push_service = providers.Factory(
        PushService, db=database, user_repository=user_repository
    )
    community_service = providers.Factory(
        CommunityService, community_repository=community_repository, db=database
    )
    token_service = providers.Factory(TokenService, db=database)
    feed_service = providers.Factory(
        FeedService,
        feed_repository=feed_repository,
    )
    feed_comment_service = providers.Factory(
        FeedCommentService,
        feed_comment_repository=feed_comment_repository,
        user_repository=user_repository,
    )
    biz_service = providers.Factory(
        BizService,
        biz_repository=biz_repository,
        image_service=image_service,
    )

    # 나중에 레포지토리 추가할떄 추가하기
    # image_repository = providers.Factory(UserRepository, db=database)
    # credit_repository = providers.Factory(UserRepository, db=database)
    # payment_repository = providers.Factory(UserRepository, db=database)
    # token_repository = providers.Factory(UserRepository, db=database)

    # 유저쪽 리펙토링이 마무리 되면 나머지 코드들도 Factory, 의존성 주입으로 변경.
