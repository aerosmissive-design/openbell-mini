import time
from cgv_open_push_function import save_log_info, save_log_error
from cgv_modern import fetch_window_signature, format_added_lines

def screen_main(url, cookies, headers, json_data, target_name, message_queue):
    save_log_info(f"{target_name} modern CGV watcher start")
    response1 = ""
    for attempt in range(10):
        try:
            response1, debug = fetch_window_signature(days=14)
            save_log_info(
                f"{target_name} initial signature lines={len(response1.splitlines())} debug={debug}"
            )
            break
        except Exception as e:
            save_log_error(f"{target_name} bootstrap fail ({attempt+1}/10): {e}")
            time.sleep(30)
    else:
        save_log_error(f"{target_name} bootstrap gave up; will keep retrying in loop")

    while True:
        time.sleep(5)
        try:
            response2, debug = fetch_window_signature(days=14)
        except Exception as e:
            save_log_error(f"{target_name} fetch error: {e}")
            time.sleep(90)
            continue

        if response1 != response2:
            added = format_added_lines(response1, response2)
            if added:
                save_log_info(f"{target_name} added:\n{added}")
                try:
                    message_queue.put(
                        [target_name, f"<b>예매 오픈 알림 (용산 특별관)</b>\n{added}"]
                    )
                except Exception as e:
                    save_log_error(f"{target_name} queue error: {e}")
            else:
                save_log_info(f"{target_name} signature changed but no added lines debug={debug}")
            response1 = response2
        else:
            save_log_info(
                f"{target_name} no change (lines={len(response2.splitlines())}) debug={debug}"
            )
        time.sleep(295)
