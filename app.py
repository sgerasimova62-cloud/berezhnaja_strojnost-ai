import json
import os
import urllib.parse
import urllib.request

from flask import Flask, request

from config import TELEGRAM_TOKEN
from bot import get_ai_answer

app = Flask(__name__)


def send_telegram_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False,
        )

    data = urllib.parse.urlencode(payload).encode("utf-8")

    with urllib.request.urlopen(url, data=data, timeout=20):
        pass


@app.route("/", methods=["GET"])
def home():
    return "AI-консультант «Бережная стройность» работает 🌿"


@app.route("/health", methods=["GET"])
def health():
    return "OK"


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)

    if not update:
        return "no update", 200

    message = update.get("message")

    if not message:
        return "no message", 200

    chat_id = message["chat"]["id"]
    user_text = message.get("text", "").strip()

    if not user_text:
        send_telegram_message(
            chat_id,
            "Я пока умею отвечать только на текстовые сообщения 🌿",
        )
        return "ok", 200

    normalized_text = user_text.lower()
    reply_markup = None

    if user_text.startswith("/start"):
        answer = (
            "Здравствуйте! 🌿\n\n"
            "Я — AI-проводник проекта «Бережная стройность».\n"
            "Помогу разобраться с питанием, привычками и сделать "
            "первый шаг к Вашей цели без жёстких диет.\n\n"
            "Выберите подходящий вариант:"
        )

        reply_markup = {
            "keyboard": [
                [{"text": "📝 Начать персональный разбор"}],
                [{"text": "👩‍💼 Получить консультацию"}],
                [{"text": "🌿 Узнать о Марафоне стройности"}],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }

    elif normalized_text == "📝 начать персональный разбор":
        answer = (
            "Отлично, давайте познакомимся 🌿\n\n"
            "Ответьте, пожалуйста, одним сообщением:\n\n"
            "1. Ваш возраст.\n"
            "2. Рост и текущий вес.\n"
            "3. Какого результата хотите достичь.\n"
            "4. Какая у Вас активность.\n"
            "5. Что мешает больше всего: вечерний голод, сладкое, "
            "переедание, нехватка времени, усталость или отсутствие режима.\n"
            "6. Есть ли заболевания, беременность, аллергии или "
            "ограничения по питанию.\n\n"
            "Эти данные нужны для общих рекомендаций и не заменяют "
            "консультацию врача."
        )

    elif normalized_text in {
        "👩‍💼 получить консультацию",
        "консультация",
        "хочу консультацию",
        "записаться на консультацию",
        "связаться со специалистом",
        "/consultation",
    }:
        consultation_link = os.environ.get(
            "CONSULTATION_LINK",
            "",
        ).strip()

        if consultation_link:
            answer = (
                "Конечно 🌿\n\n"
                "Перейдите по ссылке и кратко опишите свою цель "
                "и основную трудность:\n\n"
                f"{consultation_link}"
            )
        else:
            answer = (
                "Конечно 🌿\n\n"
                "Ссылка на личную консультацию сейчас настраивается. "
                "Пожалуйста, напишите немного позже."
            )

    elif normalized_text == "🌿 узнать о марафоне стройности":
        try:
            answer = get_ai_answer(
                "Кратко расскажи пользователю, как проходит "
                "Марафон стройности, какую поддержку он получает "
                "и кому подходит программа."
            )
        except Exception:
            answer = (
                "Марафон стройности помогает постепенно формировать "
                "полезные привычки, наладить питание и получать поддержку "
                "на пути к цели 🌿"
            )

    else:
        try:
            answer = get_ai_answer(user_text)
        except Exception:
            answer = (
                "Сейчас я не смогла обработать сообщение.\n"
                "Попробуйте написать ещё раз чуть позже 🌿"
            )

    send_telegram_message(
        chat_id,
        answer,
        reply_markup,
    )

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
