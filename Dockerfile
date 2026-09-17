FROM python:3.10

LABEL name="openbell-mini"

WORKDIR /

COPY * .

# Telegram
ENV TELEGRAM_BOT_TOKEN=""
ENV TELEGRAM_CHAT_ID=""

RUN pip install -r requirements.txt

ENTRYPOINT ["python"]
CMD ["cgv_open_push_main.py"]

EXPOSE 5000
