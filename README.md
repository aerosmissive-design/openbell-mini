# OpenBell Mini

구 Discord 기반 `cgv-open-push`를 최소 수정하여 **Telegram** + **최신 CGV API** 로 전환한 독립 감시 프로그램입니다.

기존 OpenBell과 완전 분리됩니다.

## 감시 대상

- CGV 용산아이파크몰 **IMAX / 4DX / SCREENX** (통합)

## 변경 요약

1. Discord → Telegram
2. 죽은 `ticket.cgv.co.kr` API → 최신 `cgv.co.kr` 예약 API
3. 용산 특별관만 유지
4. Railway 배포용 Dockerfile / railway.toml

## 환경변수

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## Railway 배포

1. https://railway.app → New Project → Deploy from GitHub
2. `aerosmissive-design/openbell-mini` 선택
3. Variables에 위 두 환경변수 추가
4. Deploy

## 로컬 실행

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python cgv_open_push_main.py
```

## 라이선스

원본 cgv-open-push는 AGPL-3.0. 본 프로젝트도 동일 계열을 따릅니다.
