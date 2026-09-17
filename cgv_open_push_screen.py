import os
import sys
import time
from cgv_open_push_function import save_log_info, save_log_error
from cgv_modern import fetch_window_signature, format_added_lines

# 용산 특별관(IMAX/4DX/SCREENX) 통합 감시 — 최신 CGV API 사용
def screen_main(url, cookies, headers, json_data, target_name, message_queue):
    """url/cookies/headers/json_data 는 호환용으로 받고 무시 (최소 수정 유지)."""
    try:
        save_log_info(f"{target_name} modern CGV watcher start")
        response1 = fetch_window_signature(days=14)
        save_log_info(f"{target_name} initial signature lines={len(response1.splitlines())}")
        while True:
            time.sleep(5)
            try:
                response2 = fetch_window_signature(days=14)
            except Exception as e:
                save_log_error(f"{target_name} fetch error: {e}")
                time.sleep(60)
                continue

            if response1 != response2:
                added = format_added_lines(response1, response2)
                if added:
                    save_log_info(f"{target_name} added:\n{added}")
                    try:
                        message_queue.put(
                            [target_name, f"**예매 오픈 알림 (용산 특별관)**\n{added}"]
                        )
                    except Exception as e:
                        save_log_error(f"{target_name} queue error: {e}")
                        time.sleep(5)
                        message_queue.put(
                            [target_name, f"**예매 오픈 알림 (용산 특별관)**\n{added}"]
                        )
                response1 = response2
            else:
                save_log_info(f"{target_name} no change (lines={len(response2.splitlines())})")
            time.sleep(295)
    except Exception as e:
        save_log_error(f"{target_name} fatal: {e}")
        os.execl(sys.executable, sys.executable, *sys.argv)
