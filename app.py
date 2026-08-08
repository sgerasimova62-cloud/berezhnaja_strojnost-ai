import json
import os
import urllib.error
import urllib.parse
import urllib.request

from flask import Flask, request

from config import TELEGRAM_TOKEN
from bot import get_ai_answer


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

app = Flask(__name__)


# =========================================================
# SUPABASE
# =========================================================

def supabase_headers(extra: dict | None = None) -> dict:
    """
    Поддерживает и новые ключи Supabase sb_secret_...,
    и старые JWT-ключи eyJ...
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }

    # Legacy anon/service_role JWT обычно используется и как Bearer.
    # Новый sb_secret_ ключ в Authorization Bearer не отправляем.
    if SUPABASE_KEY and not SUPABASE_KEY.startswith(
        ("sb_secret_", "sb_publishable_")
    ):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

    if extra:
        headers.update(extra)

    return headers


def log_supabase_error(action: str, error: Exception) -> None:
    print(f"[SUPABASE ERROR] {action}: {error}", flush=True)

    if isinstance(error, urllib.error.HTTPError):
        try:
            body = error.read().decode("utf-8")
            print(f"[SUPABASE RESPONSE] {body}", flush=True)
        except Exception:
            pass


def get_user_from_supabase(telegram_id: int):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[SUPABASE] URL or KEY is missing", flush=True)
        return None

    url = (
        f"{SUPABASE_URL}/rest/v1/users"
        f"?telegram_id=eq.{telegram_id}&select=*"
    )

    req = urllib.request.Request(
        url,
        method="GET",
        headers=supabase_headers(),
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data[0] if data else None

    except Exception as error:
        log_supabase_error("get_user", error)
        raise


def create_user_in_supabase(telegram_id: int) -> bool:
    """
    Создаёт пользователя только если его ещё нет.
    Возвращает True при успехе.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[SUPABASE] URL or KEY is missing", flush=True)
        return False

    try:
        existing_user = get_user_from_supabase(telegram_id)

        if existing_user:
            return True

        url = f"{SUPABASE_URL}/rest/v1/users"

        payload = json.dumps({
            "telegram_id": telegram_id,
            "stage": 0,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers=supabase_headers({
                "Prefer": "return=minimal",
            }),
        )

        with urllib.request.urlopen(req, timeout=20):
            pass

        return True

    except Exception as error:
        log_supabase_error("create_user", error)
        return False


def update_user_in_supabase(
    telegram_id: int,
    fields: dict,
) -> bool:
    """
    Обновляет данные пользователя.
    Возвращает True при успехе.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[SUPABASE] URL or KEY is missing", flush=True)
        return False

    url = (
        f"{SUPABASE_URL}/rest/v1/users"
        f"?telegram_id=eq.{telegram_id}"
    )

    payload = json.dumps(fields).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="PATCH",
        headers=supabase_headers({
            "Prefer": "return=minimal",
        }),
    )

    try:
        with urllib.request.urlopen(req, timeout=20):
            pass

        return True

    except Exception as error:
        log_supabase_error("update_user", error)
        return False


# =========================================================
# QUESTIONNAIRE
# =========================================================

def process_questionnaire_answer(
    chat_id: int,
    user_text: str,
):
    try:
        user = get_user_from_supabase(chat_id)
    except Exception:
        return (
            "Сейчас не получается сохранить Ваш ответ 🌿\n"
            "Попробуйте ещё раз немного позже."
        )

    if not user:
        return None

    stage = user.get("stage", 0) or 0

    if stage == 1:
        try:
            age = int(user_text)
        except ValueError:
            return (
                "Пожалуйста, укажите возраст числом. "
                "Например: 42"
            )

        if not 18 <= age <= 100:
            return (
                "Пожалуйста, проверьте возраст. "
                "Укажите число от 18 до 100."
            )

        if not update_user_in_supabase(
            chat_id,
            {"age": age, "stage": 2},
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Спасибо 🌿\n\n"
            "Какой у Вас рост в сантиметрах?"
        )

    if stage == 2:
        try:
            height = int(user_text)
        except ValueError:
            return (
                "Пожалуйста, укажите рост числом. "
                "Например: 165"
            )

        if not 120 <= height <= 230:
            return (
                "Пожалуйста, проверьте рост. "
                "Укажите значение в сантиметрах."
            )

        if not update_user_in_supabase(
            chat_id,
            {"height": height, "stage": 3},
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Принято 🌿\n\n"
            "Какой у Вас сейчас вес в килограммах?"
        )

    if stage == 3:
        try:
            weight = float(user_text.replace(",", "."))
        except ValueError:
            return (
                "Пожалуйста, укажите вес числом. "
                "Например: 72 или 72.5"
            )

        if not 35 <= weight <= 300:
            return (
                "Пожалуйста, проверьте вес и укажите "
                "значение в килограммах."
            )

        if not update_user_in_supabase(
            chat_id,
            {"weight": weight, "stage": 4},
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Хорошо 🌿\n\n"
            "Какого результата Вы хотите достичь?\n\n"
            "Например: снизить вес на 7 кг, убрать объёмы "
            "или стать энергичнее."
        )

    if stage == 4:
        if not update_user_in_supabase(
            chat_id,
            {"goal": user_text, "stage": 5},
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Поняла 🌿\n\n"
            "Какая у Вас сейчас физическая активность?\n\n"
            "Например: почти нет, хожу пешком, "
            "тренируюсь 1–2 раза или 3+ раза в неделю."
        )

    if stage == 5:
        if not update_user_in_supabase(
            chat_id,
            {"activity": user_text, "stage": 6},
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Что сейчас больше всего мешает прийти "
            "к результату?\n\n"
            "Например: вечерний голод, сладкое, переедание, "
            "нехватка времени, усталость или отсутствие режима."
        )

    if stage == 6:
        if not update_user_in_supabase(
            chat_id,
            {"difficulty": user_text, "stage": 7},
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Последний вопрос 🌿\n\n"
            "Есть ли заболевания, беременность, аллергии "
            "или ограничения по питанию?\n\n"
            "Если нет — просто напишите «нет»."
        )

    if stage == 7:
        if not update_user_in_supabase(
            chat_id,
            {
                "restrictions": user_text,
                "stage": 8,
            },
        ):
            return "Не удалось сохранить ответ. Попробуйте ещё раз 🌿"

        return (
            "Спасибо! 🌿 Анкета заполнена.\n\n"
            "Я сохранила Ваши ответы. Теперь можно перейти "
            "к персональному разбору и подобрать следующий шаг."
        )

    return None


# =========================================================
# TELEGRAM
# =========================================================

def send_telegram_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> None:
    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

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

    try:
        with urllib.request.urlopen(
            url,
            data=data,
            timeout=20,
        ):
            pass

    except Exception as error:
        print(
            f"[TELEGRAM ERROR] sendMessage: {error}",
            flush=True,
        )


def main_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": "📝 Начать персональный разбор"}],
            [{"text": "👩‍💼 Получить консультацию"}],
            [{"text": "🌿 Узнать о Марафоне стройности"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


# =========================================================
# FLASK
# =========================================================

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
            "Я пока умею отвечать только "
            "на текстовые сообщения 🌿",
        )
        return "ok", 200

    normalized_text = user_text.lower()
    reply_markup = None

    # -------------------------
    # START
    # -------------------------

    if user_text.startswith("/start"):
        answer = (
            "Здравствуйте! 🌿\n\n"
            "Я — AI-проводник проекта «Бережная стройность».\n"
            "Помогу разобраться с питанием, привычками "
            "и сделать первый шаг к Вашей цели "
            "без жёстких диет.\n\n"
            "Выберите подходящий вариант:"
        )

        reply_markup = main_keyboard()

    # -------------------------
    # QUESTIONNAIRE START
    # -------------------------

    elif normalized_text == "📝 начать персональный разбор":
        user_ready = create_user_in_supabase(chat_id)

        if not user_ready:
            answer = (
                "Сейчас не получается открыть персональный "
                "разбор 🌿\n\n"
                "Попробуйте ещё раз немного позже."
            )
        else:
            reset_ok = update_user_in_supabase(
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

            if reset_ok:
                answer = (
                    "Отлично, давайте познакомимся 🌿\n\n"
                    "Я задам несколько коротких вопросов "
                    "по одному. Ваши ответы помогут сделать "
                    "разбор персональным.\n\n"
                    "Первый вопрос:\n"
                    "Сколько Вам лет?"
                )
            else:
                answer = (
                    "Сейчас не получается начать анкету 🌿\n"
                    "Попробуйте ещё раз немного позже."
                )

    # -------------------------
    # CONSULTATION
    # -------------------------

    elif normalized_text in {
        "👩‍💼 получить консультацию",
        "консультация",
        "хочу консультацию",
        "записаться на консультацию",
        "связаться со специалистом",
        "/consultation",
    }:
        consultation_link = os.getenv(
            "CONSULTATION_LINK",
            "",
        ).strip()

        if consultation_link:
            answer = (
                "Конечно 🌿\n\n"
                "Перейдите по ссылке и кратко опишите "
                "свою цель и основную трудность:\n\n"
                f"{consultation_link}"
            )
        else:
            answer = (
                "Конечно 🌿\n\n"
                "Ссылка на личную консультацию "
                "сейчас настраивается. "
                "Пожалуйста, напишите немного позже."
            )

    # -------------------------
    # MARATHON
    # -------------------------

    elif normalized_text == "🌿 узнать о марафоне стройности":
        try:
            answer = get_ai_answer(
                "Кратко расскажи пользователю, как проходит "
                "Марафон стройности, какую поддержку он "
                "получает и кому подходит программа."
            )
        except Exception as error:
            print(
                f"[AI ERROR] marathon: {error}",
                flush=True,
            )

            answer = (
                "Марафон стройности помогает постепенно "
                "формировать полезные привычки, наладить питание "
                "и получать поддержку на пути к цели 🌿"
            )

    # -------------------------
    # QUESTIONNAIRE / AI
    # -------------------------

    else:
        questionnaire_answer = process_questionnaire_answer(
            chat_id,
            user_text,
        )

        if questionnaire_answer is not None:
            answer = questionnaire_answer
        else:
            try:
                answer = get_ai_answer(user_text)

            except Exception as error:
                print(
                    f"[AI ERROR] answer: {error}",
                    flush=True,
                )

                answer = (
                    "Сейчас я не смогла обработать сообщение.\n"
                    "Попробуйте написать ещё раз чуть позже 🌿"
                )

    send_telegram_message(
        chat_id,
        answer,
        reply_markup,
    )

    # Telegram должен получать 200 даже если внешний сервис дал сбой.
    return "ok", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
    )
