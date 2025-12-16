from datetime import datetime
from zoneinfo import ZoneInfo


# db의 전역 시간 설정을 Asia/Seoul로 설정. 하지만 쓰일 수도 있는 코드라서 유지.
def kst():
    """
    한국 시간으로 표시하기
    """
    return datetime.now(ZoneInfo("Asia/Seoul"))


KST = ZoneInfo("Asia/Seoul")


def to_datetime(value):
    """datetime 변환 + KST timezone-aware 로 통일"""

    if value is None:
        return None

    # 이미 datetime 객체인 경우
    if isinstance(value, datetime):
        # tzinfo 없으면 KST 부여, 있으면 그대로 사용
        if value.tzinfo is None:
            return value.replace(tzinfo=KST)
        return value

    # 문자열 → datetime 변환
    if isinstance(value, str):
        dt = None
        try:
            dt = datetime.fromisoformat(value)
        except:
            try:
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except:
                return None

        # timezone 정보 없다면 KST 부여
        if dt.tzinfo is None:
            return dt.replace(tzinfo=KST)
        return dt

    return None
