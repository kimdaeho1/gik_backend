from datetime import datetime
from zoneinfo import ZoneInfo

# db의 전역 시간 설정을 Asia/Seoul로 설정. 하지만 쓰일 수도 있는 코드라서 유지.
def kst():
    """
    한국 시간으로 표시하기
    """
    return datetime.now(ZoneInfo("Asia/Seoul"))
