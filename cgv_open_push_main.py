import queue
import time
import atexit
import multiprocessing
from cgv_open_push_function import *
from cgv_open_push_global_variable import *
from cgv_open_push_movie import movie_main
from cgv_open_push_screen import screen_main
from logging.handlers import RotatingFileHandler

# Telegram 메시지 큐
message_queue = multiprocessing.Queue()

def telegram_worker():
    """큐에서 메시지를 꺼내 Telegram으로 전송"""
    while True:
        try:
            if not message_queue.empty():
                message = message_queue.get()
                target = message[0]
                text = message[1]
                # 앞에 타겟 이름 붙여서 구분
                full_text = f"[{target}]\n{text}"
                print(f"send_telegram : {target} → {text[:80]}...")
                send_telegram_message(full_text)
            else:
                time.sleep(0.5)
        except Exception as e:
            save_log_error(f"telegram_worker error: {e}")
            time.sleep(2)

# 프로세스 배열
processes = []

# 로그 저장 (최대 5MB씩 3개 백업본 저장)
handlers = [RotatingFileHandler('cgv-open-push.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')]
logging.basicConfig(handlers=handlers, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# status 서버 실행
p = multiprocessing.Process(target=run_cgv_open_push_status)
processes.append(p)
p.start()
time.sleep(1)

# Telegram 워커 시작
p = multiprocessing.Process(target=telegram_worker)
processes.append(p)
p.start()
time.sleep(1)

# 서버 시작 알림
message_queue.put(["LOG", "OpenBell Mini (cgv-open-push) server started..."])

# 영화관 프로세스 (현재 비활성화)
for data in enumerate(movie_json_data):
    p = multiprocessing.Process(target=movie_main, args=(movie_url, movie_cookies, movie_headers, data[1], movie_target_name[data[0]], message_queue))
    processes.append(p)
    p.start()
    time.sleep(1)

# 특별관 프로세스 (용산만)
for data in enumerate(screen_json_data):
    p = multiprocessing.Process(target=screen_main, args=(screen_url, screen_cookies, screen_headers, data[1], screen_target_name[data[0]], message_queue))
    processes.append(p)
    p.start()
    time.sleep(1)

# 종료 시 알림
def send_stopped_message():
    message_queue.put(["LOG", "OpenBell Mini server stopped..."])
atexit.register(send_stopped_message)

# 메인 프로세스는 살아있기만 하면 됨
print("OpenBell Mini started. Watching Yongsan IMAX / 4DX / SCREENX ...")
while True:
    time.sleep(60)
