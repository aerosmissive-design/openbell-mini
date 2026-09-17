import os

##################################################
# ENV (Telegram)
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

##################################################
# movie 감시 비활성화
movie_url = ""
movie_cookies = {}
movie_headers = {}
movie_json_data = []
movie_target_name = []

##################################################
# screen: 용산 특별관 1개 워커로 통합 (IMAX+4DX+SCREENX)
screen_url = ""
screen_cookies = {}
screen_headers = {}
screen_json_data = [{}]  # dummy one entry for process loop
screen_target_name = ["YONGSAN-SPECIAL"]
