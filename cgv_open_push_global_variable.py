import os

##################################################
# ENV (Telegram)
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")


##################################################
# Telegram target keys (용산만)
# LOG / ANNOUNCEMENT 도 동일 채팅으로 전송
telegram_target_map = {
    "LOG": telegram_chat_id,
    "ANNOUNCEMENT": telegram_chat_id,
    "YONGSAN-IMAX": telegram_chat_id,
    "YONGSAN-4DX": telegram_chat_id,
    "YONGSAN-SCREENX": telegram_chat_id,
}


##################################################
# cgv_open_push_movie.py
# 용산만 운영 + 코드 수정 최소화 → movie 감시 비활성화

movie_url = 'http://ticket.cgv.co.kr/CGV2011/RIA/CJ000.aspx/CJ_TICKET_SCHEDULE_TOTAL_PLAY_YMD'

movie_cookies = {
    '_INSIGHT_CK_1': 'f1d83d00493551cd7875517dd21cf81d|5e76eb13a569e162f1a8517dd21cf81d:1705916707000',
    'WMONID': 'zvGaitKgTbw',
    '_gid': 'GA1.3.895218779.1709345361',
    'CgvPopAd-ticket': '^%^uA257^%^uA24D^%^uA248^%^uA251^%^uA24C^%^uA25C',
    '_gat_UA-47951671-5': '1',
    '_gat_UA-47951671-7': '1',
    '_gat_UA-47126437-1': '1',
    '_gat': '1',
    'ASP.NET_SessionId': '3qi04s2s5lgd33kmszdarrvp',
    '_ga_559DE9WSKZ': 'GS1.1.1709348096.22.1.1709348100.56.0.0',
    '_ga': 'GA1.1.1033028224.1705195852',
    '_ga_SSGE1ZCJKG': 'GS1.3.1709348096.23.1.1709348100.56.0.0',
}

movie_headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'http://ticket.cgv.co.kr',
    'Pragma': 'no-cache',
    'Referer': 'http://ticket.cgv.co.kr/Reservation/Reservation.aspx?MOVIE_CD=&MOVIE_CD_GROUP=&PLAY_YMD=&THEATER_CD=&PLAY_NUM=&PLAY_START_TM=&AREA_CD=&SCREEN_CD=&THIRD_ITEM=&SCREEN_RATING_CD=',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

# 영화 개별 감시 비활성화 (용산 특별관만)
movie_json_data = []
movie_target_name = []


##################################################
# cgv_open_push_screen.py  (용산만)

screen_url = 'http://ticket.cgv.co.kr/CGV2011/RIA/CJ000.aspx/CJ_TICKET_SCHEDULE_TOTAL_PLAY_YMD'

screen_cookies = {
    '_INSIGHT_CK_1': 'f1d83d00493551cd7875517dd21cf81d|5e76eb13a569e162f1a8517dd21cf81d:1705916707000',
    'WMONID': 'zvGaitKgTbw',
    '_gid': 'GA1.3.1750462509.1711519151',
    'ASP.NET_SessionId': 'o0453f5oqurfws4f1abdzxij',
    '_gat_UA-47951671-5': '1',
    '_gat_UA-47951671-7': '1',
    '_gat_UA-47126437-1': '1',
    '_gat': '1',
    '_ga_559DE9WSKZ': 'GS1.1.1711519151.1.1.1711519200.0.0.0',
    '_ga': 'GA1.1.1033028224.1705195852',
    '_ga_SSGE1ZCJKG': 'GS1.3.1711519151.1.1.1711519200.0.0.0',
}

screen_headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'http://ticket.cgv.co.kr',
    'Pragma': 'no-cache',
    'Referer': 'http://ticket.cgv.co.kr/Reservation/Reservation.aspx?MOVIE_CD=&MOVIE_CD_GROUP=&PLAY_YMD=&THEATER_CD=&PLAY_NUM=&PLAY_START_TM=&AREA_CD=&SCREEN_CD=&THIRD_ITEM=&SCREEN_RATING_CD=',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

screen_json_data = [
    # 용산아이파크몰 IMAX관
    {
        'REQSITE': 'x02PG4EcdFrHKluSEQQh4A==',
        'TheaterCd': 'LMP+XuzWskJLFG41YQ7HGA==',
        'ISNormal': 'ECFppiyFz/nvSGsg7VwPQw==',
        'MovieGroupCd': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'ScreenRatingCd': 'kXwoR3tnLM/+Tu0BILP3Qg==',
        'MovieTypeCd': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Subtitle_CD': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'SOUNDX_YN': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Third_Attr_CD': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Language': 'zqWM417GS6dxQ7CIf65+iA==',
    },
    # 용산아이파크몰 4DX관
    {
        'REQSITE': 'x02PG4EcdFrHKluSEQQh4A==',
        'TheaterCd': 'LMP+XuzWskJLFG41YQ7HGA==',
        'ISNormal': 'ECFppiyFz/nvSGsg7VwPQw==',
        'MovieGroupCd': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'ScreenRatingCd': '9sxNW0kL/ZE3ioyEu1Em8w==',
        'MovieTypeCd': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Subtitle_CD': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'SOUNDX_YN': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Third_Attr_CD': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Language': 'zqWM417GS6dxQ7CIf65+iA==',
    },
    # 용산아이파크몰 SCREENX관
    {
        'REQSITE': 'x02PG4EcdFrHKluSEQQh4A==',
        'TheaterCd': 'LMP+XuzWskJLFG41YQ7HGA==',
        'ISNormal': 'ECFppiyFz/nvSGsg7VwPQw==',
        'MovieGroupCd': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'ScreenRatingCd': '1WlMxB/T2xWstAhFsiNSfQ==',
        'MovieTypeCd': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Subtitle_CD': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'SOUNDX_YN': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Third_Attr_CD': 'nG6tVgEQPGU2GvOIdnwTjg==',
        'Language': 'zqWM417GS6dxQ7CIf65+iA==',
    },
]

screen_target_name = [
    "YONGSAN-IMAX",
    "YONGSAN-4DX",
    "YONGSAN-SCREENX",
]
