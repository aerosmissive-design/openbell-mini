# OpenBell Mini

구 Discord 기반 `cgv-open-push`를 최소한으로 수정하여 **Telegram** 알림으로 전환한 독립 감시 프로그램입니다.

기존 OpenBell(openbell-fawn.vercel.app)과 **완전 분리**된 이중 감시 시스템입니다.

## 감시 대상 (용산만)

- CGV 용산아이파크몰 **IMAX**
- CGV 용산아이파크몰 **4DX**
- CGV 용산아이파크몰 **SCREENX**

## 변경 사항 (원본 대비 최소)

1. Discord → Telegram 교체
2. 감시 대상을 용산 특별관 3개로 축소
3. 환경변수: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
4. 나머지 수집/Diff 로직은 원본 유지

## 실행 방법

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

python cgv_open_push_main.py
```

또는 Docker:

```bash
docker build -t openbell-mini .
docker run -e TELEGRAM_BOT_TOKEN=... -e TELEGRAM_CHAT_ID=... -p 5000:5000 openbell-mini
```

## 상태 페이지

`http://localhost:5000` (Flask health + log)

## 라이선스

원본 [cgv-open-push](https://github.com/0w0i0n0g0/cgv-open-push) 는 AGPL-3.0 입니다.  
본 프로젝트도 동일 라이선스를 따릅니다.

## 원본

- https://github.com/0w0i0n0g0/cgv-open-push
