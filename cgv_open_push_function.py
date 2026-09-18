import json
import re
import subprocess
import time
import requests
import logging
import datetime
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from cgv_open_push_global_variable import telegram_bot_token, telegram_chat_id

def run_cgv_open_push_status():
    while True:
        save_log_info("cgv_open_push_status.py restarted.")
        process = subprocess.Popen(['python', 'cgv_open_push_status.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3600)
        process.kill()

# 로그 저장
def save_log_info(log, is_log_file=False):
    if is_log_file:
        logging.info(log)
    print(f"[{datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}] {log}", flush=True)

def save_log_error(log, is_log_file=True):
    if is_log_file:
        logging.error(log)
    print(f"[{datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}] {log}", flush=True)

# Telegram 전송 (HTML — 바로 예매 링크용)
def send_telegram_message(text):
    if not telegram_bot_token or not telegram_chat_id:
        save_log_error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    try:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            save_log_error(f"Telegram send failed: {r.status_code} {r.text}")
            return False
        return True
    except Exception as e:
        save_log_error(f"Telegram send exception: {e}")
        return False

# request의 응답 객체를 받아 현재시간의 차이를 계산
def calculate_response_delay(response):
    response_time_str = response.headers['Date']
    response_time = datetime.strptime(response_time_str, '%a, %d %b %Y %H:%M:%S GMT')
    current_time = datetime.now(timezone.utc).replace(tzinfo = None)
    time_difference = abs(current_time - response_time)
    return time_difference

# 받은 정보들로 get 요청을 보내고 json을 응답받는다. json 데이터 값인 xml을 추출하여 문자열로 리턴한다.
def get_request_to_cgv_api(url, cookies, headers, json_data, target_name):
    response = requests.post(
        url = url,
        cookies = cookies,
        headers = headers,
        json = json_data,
        verify = False,
    )
    response_body = response.content
    save_log_info(f'{target_name} response delay : {calculate_response_delay(response)}', True)
    response_text = response_body.decode('utf-8-sig')
    data = json.loads(response_text)
    xml_string = data['d']['DATA']
    return xml_string

# XML 문자열을 받아서 PlayDays 태그를 XML 문자열로 반환
def extract_playdays(xml_string):
    try:
        xml = ET.fromstring(xml_string)
        playdays = xml.find('.//PlayDays')
        return ET.tostring(playdays, encoding='unicode', method='xml') if playdays is not None else None
    except:
        return ""

# XML 문자열과 태그를 받아서 해당 태그를 모두 XML 문자열로 반환
def extract_xml_object_by_tag(xml_string, tag):
    try:
        xml = ET.fromstring(xml_string)
        data = xml.findall(f'.//{tag}')
        return ''.join([ET.tostring(item, encoding='unicode', method='xml') for item in data] if data is not None else [])
    except:
        return ""

# 문자열과 태그를 받아서 해당 태그 사이의 문자열을 모두 반환
def extract_text_between_tag(xml_string, tag):
    pattern = re.compile(r'<{}>(.*?)</{}>'.format(re.escape(tag), re.escape(tag)))
    return ', '.join(pattern.findall(xml_string))

# XML 문자열을 받아 태그 사이의 값을 모두 추출하여 ", "으로 구분된 문자열로 리턴
def extract_all_text_from_xml(xml_string):
    pattern = re.compile(r'<.*?>(.*?)</.*?>')
    return ', '.join(pattern.findall(xml_string))

# 문자열과 태그를 받아서 해당 태그와 내용을 모두 삭제된 문자열을 반환
def remove_text_between_tag(xml_string, tag):
    pattern = re.compile(r'<{}>(.*?)</{}>'.format(re.escape(tag), re.escape(tag)))
    return pattern.sub('', xml_string)

# 특별관 예매 오픈 알림에 필요 없는 태그 제거하기
def screen_remove_useless_tags(xml_string):
    useless_tags = {"PLAY_YMD", "GROUP_CD", "MOVIE_CD", "RATING_CD", "PLATFORM_CD", "TRANS_CD", "PLATFORM_ATTR_CD", "MOVIE_COLLAGE_YN", "TICKET_RATE", "STAR_POINT", "SOUNDX_YN", "THIRD_ATTR_CD", "MOVIE_ATTR_CD", "MOVIE_PKG_YN", "MOVIE_NOSHOW_YN", "POSTER", "MOVIE_IDX", "THIRD_ATTR_NM", }
    for tag in useless_tags:
        xml_string = remove_text_between_tag(xml_string, tag)
    return xml_string
