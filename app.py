import json
import os
import urllib.parse
import urllib.request

from flask import Flask, request

from config import TELEGRAM_TOKEN
from bot import get_ai_answer

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = Flask(__name__)
def save_user_to_supabase(telegram_id: int) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    url = f"{SUPABASE_URL}/rest/v1/users"

    payload = json.dumps({
        "telegram_id": telegram_id,
        "stage": 0,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates",
        },
    )

    with urllib.request.urlopen(req, timeout=20):
        pass
def get_user_from_supabase(telegram_id: int):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    url = (
        f"{SUPABASE_URL}/rest/v1/users"
        f"?telegram_id=eq.{telegram_id}&select=*"
    )

    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "apikey": SUPABASE_KEY,
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data:
        return data[0]

    return None


def update_user_in_supabase(telegram_id: int, fields: dict) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    url = (
        f"{SUPABASE_URL}/rest/v1/users"
        f"?telegram_id=eq.{telegram_id}"
    )

    payload = json.dumps(fields).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="PATCH",
        headers={
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )

    with urllib.request.urlopen(req, timeout=20):
        pass


def process_questionnaire_answer(chat_id: int, user_text: str):
    user = get_user_from_supabase(chat_id)

    if not user:
        return None

    stage = user.get("stage", 0) or 0

    if stage == 1:
        try:
            age = int(user_text)
        except ValueError:
            return "Пожалуйста, укажите возраст числом. Например: 42"

        update_user_in_supabase(
            chat_id,
            {"age": age, "stage": 2},
        )
        return "Спасибо 🌿\n\nКакой у Вас рост в сантиметрах?"

    if stage == 2:
        try:
            height = int(user_text)
        except ValueError:
            return "Пожалуйста, укажите рост числом. Например: 165"

        update_user_in_supabase(
            chat_id,
            {"height": height, "stage": 3},
        )
        return "Принято 🌿\n\nКакой у Вас сейчас вес в килограммах?"

    if stage == 3:
        try:
            weight = float(user_text.replace(",", "."))
        except ValueError:
            return "Пожалуйста, укажите вес числом. Например: 72 или 72.5"

        update_user_in_supabase(
            chat_id,
            {"weight": weight, "stage": 4},
        )
        return (
            "Хорошо 🌿\n\n"
            "Какого результата Вы хотите достичь? "
            "Например: снизить вес на 7 кг, убрать объёмы, "
            "стать энергичнее."
        )

    if stage == 4:
        update_user_in_supabase(
            chat_id,
            {"goal": user_text, "stage": 5},
        )
        return (
            "Поняла 🌿\n\n"
            "Какая у Вас сейчас физическая активность? "
            "Например: почти нет, хожу пешком, тренируюсь "
            "1–2 раза или 3+ раза в неделю."
        )

    if stage == 5:
        update_user_in_supabase(
            chat_id,
            {"activity": user_text, "stage": 6},
        )
        return (
            "Что сейчас больше всего мешает прийти к результату?\n\n"
            "Например: вечерний голод, сладкое, переедание, "
            "нехватка времени, усталость или отсутствие режима."
        )

    if stage == 6:
        update_user_in_supabase(
            chat_id,
            {"difficulty": user_text, "stage": 7},
        )
        return (
            "Последний вопрос 🌿\n\n"
            "Есть ли заболевания, беременность, аллергии "
            "или ограничения по питанию?\n\n"
            "Если нет — просто напишите «нет»."
        )

    if stage == 7:
        update_user_in_supabase(
            chat_id,
            {"restrictions": user_text, "stage": 8},
        )

        return (
            "Спасибо! 🌿 Анкета заполнена.\n\n"
            "Я получила Ваши ответы и теперь могу сделать "
            "разбор более персональным."
        )

    return None
    
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
        save_user_to_supabase(chat_id)

        update_user_in_supabase(
            chat_id,
            {
                "stage": 1,
                "age": None,
                "height": None,
                "weight": None,
                "goal": None,
                "activity": None,
                "difficulty": None,
                "restrictions": None,
            },
        )

        answer = (
            "Отлично, давайте познакомимся 🌿\n\n"
            "Я задам несколько коротких вопросов по одному. "
            "Ваши ответы помогут сделать разбор персональным.\n\n"
            "Первый вопрос:\n"
            "Сколько Вам лет?"
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
            questionnaire_answer = process_questionnaire_answer(
                chat_id,
                user_text,
           )

            if questionnaire_answer is not None:
                answer = questionnaire_answer
            else:
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
