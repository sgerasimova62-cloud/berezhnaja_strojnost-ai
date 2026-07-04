import json
import os
import urllib.request
import urllib.parse

from flask import Flask, request

from config import TELEGRAM_TOKEN
from bot import get_ai_answer

app = Flask(__name__)


def send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode("utf-8")

    urllib.request.urlopen(url, data=data)


@app.route("/", methods=["GET"])
def home():
    return "AI-консультант «Бережная стройность» работает 🌿"


@app.route("/health", methods=["GET"])
def health():
    return "OK"


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json()

    if not update:
        return "no update", 200

    message = update.get("message")

    if not message:
        return "no message", 200

    chat_id = message["chat"]["id"]
    user_text = message.get("text", "")

    if not user_text:
        send_telegram_message(chat_id, "Я пока умею отвечать только на текстовые сообщения 🌿")
        return "ok", 200

    if user_text.startswith("/start"):
        answer = (
            "Здравствуйте! 🌿\n\n"
            "Я — ваш AI-проводник к бережной стройности.\n"
            "Помогу разобраться в вопросах питания, здоровых привычек и марафона стройности.\n\n"
            "Напишите, что вас сейчас больше всего волнует."
        )
    else:
        try:
            answer = get_ai_answer(user_text)
        except Exception:
            answer = (
                "Сейчас я не смогла обработать сообщение.\n"
                "Попробуйте написать ещё раз чуть позже 🌿"
            )

    send_telegram_message(chat_id, answer)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
