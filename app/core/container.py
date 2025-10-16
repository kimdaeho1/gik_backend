from dependency_injector import containers, providers
from app.db.db_connection import Database

# from app.repository.user_repository import UserRepository
from app.services.user_service import UserService
from app.services.image_service import ImageService
from app.services.push_service import PushService
from app.services.community_service import CommunityService
from app.services.token_service import TokenService


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
        ]
    )

    # main.py에서 생성한 db 객체를 그대로 쓰기.
    database = providers.Object(db)
    user_service = providers.Factory(UserService, db=database)
    image_service = providers.Factory(ImageService, db=database)
    push_service = providers.Factory(
        PushService, db=database, user_service=user_service
    )
    community_service = providers.Factory(CommunityService, db=database)
    token_service = providers.Factory(TokenService, db=database)

    # 나중에 레포지토리 추가할떄 추가하기
    # user_repository = providers.Factory(UserRepository, db=database)
    # image_repository = providers.Factory(UserRepository, db=database)
    # community_repository = providers.Factory(UserRepository, db=database)
    # credit_repository = providers.Factory(UserRepository, db=database)
    # payment_repository = providers.Factory(UserRepository, db=database)
    # token_repository = providers.Factory(UserRepository, db=database)

    # 유저쪽 리펙토링이 마무리 되면 나머지 코드들도 Factory, 의존성 주입으로 변경.
